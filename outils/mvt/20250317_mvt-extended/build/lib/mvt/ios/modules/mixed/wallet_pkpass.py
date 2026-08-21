import logging
import json
import json5
import os
import tempfile

from typing import Optional

from mvt.common.utils import CustomJSONEncoder, trim_prefix

from ..base import IOSExtraction

WALLET_PKPASSES_BACKUP_RELPATH = "Library/Passes/Cards/*.pkpass/*"
WALLET_PKPASSES_ROOT_PATHS = ["private/var/mobile/Library/Passes/Cards/*.pkpass/*"]

class WalletPkpass(IOSExtraction):
    """This module extracts pkpasses stored in the Wallet application."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = None,
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            module_options=module_options,
            log=log,
            results=results,
        )
    
    def serialize(self, record: dict) -> dict:
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "pkpass_added_to_wallet",
            "data": f"Pkpass {record['data']['description'] if 'description' in record['data'] else 'unknown'} "
                    f"from {record['data']['organizationName'] if 'organizationName' in record['data'] else 'unknown'} "
                    f"registered in the wallet.",
        }

    def find_suspicious(self) -> None:
        for result in self.results:
            if "pass.json" not in result["embeddedFiles"]:
                self.log.warning("Pkpass folder without pass.json %s", str(result))
                self.detected.append(result)

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            if result["id"] == "sample.pkpass":
                self.log.warning("Found a \"sample.pkpass\" file %s (Pegasus)", str(result))
                self.detected.append(result)
    
    def _checkPng(self, pngFilePath, fileRealPath = "") -> None:
        if not pngFilePath or not os.path.exists(pngFilePath):
            self.log.warning("File not found : %s", fileRealPath)
            return
        if (os.stat(pngFilePath).st_size == 0):
            self.log.warning("Empty file : %s", pngFilePath)
            return
        with open(pngFilePath, "rb") as handle:
            raw_data = handle.read()
        header = raw_data[0:8].hex()
        if not (header == "89504e470d0a1a0a" or header == "ffd8ffe000104a46" or header.startswith("474946383961")):
            self.log.warning("Not a PNG/JPEG/GIF header (\"%s\") for file %s", header, pngFilePath)
        if b"plist" in raw_data:
            self.log.warning("Found a BLASTPASS sample at %s", pngFilePath)
        
    def _processPass(self, passFilePath) -> dict:
        for encoding in ["utf8", "ISO-8859-1", "utf-16le", "utf-32le"]:
            with open(passFilePath, "rb") as binaryPassFileHandle:
                # we try different encodings until we find the right one
                try:
                    binaryPassFile = binaryPassFileHandle.read()
                    passData = json5.loads(binaryPassFile, encoding=encoding)
                    temp_dir = tempfile.TemporaryDirectory()
                    temp_file_path = os.path.join(temp_dir.name, "temp")
                    with open(temp_file_path, "w") as handle:
                        # we need to make sure that the data will be able to be properly dumped
                        # error cases are when the message contain an emoji for example
                        try:
                            json.dump(passData, handle, indent=4, default=str, ensure_ascii=False, allow_nan=True, cls=CustomJSONEncoder)
                        except:
                            binaryPassFile = binaryPassFile.decode("raw_unicode_escape").encode("utf-16", "surrogatepass").decode("utf-16")
                            passData = json5.loads(binaryPassFile, encoding=encoding)
                    break
                except:
                    continue
        return passData

    def run(self) -> None:
        pkpasses = {}

        if self.is_backup:
            for walletPkpassFile in self._get_backup_files_from_manifest(WALLET_PKPASSES_BACKUP_RELPATH):
                pkpass_collect_file_path = self._get_backup_file_from_id(walletPkpassFile["file_id"])
                pkpass_file_path = os.path.join("/private/var/mobile", walletPkpassFile["relative_path"])
                pkpass_id = pkpass_file_path.split("/private/var/mobile/Library/Passes/Cards/")[1].split("/")[0]
                if pkpass_id not in pkpasses:
                    pkpasses[pkpass_id] = {
                        "id" : pkpass_id,
                        "passPath" : None,
                        "embeddedFiles" : set(),
                        "isodate" : None,
                    }
                fileName = os.path.basename(pkpass_file_path)
                pkpasses[pkpass_id]["embeddedFiles"].add(fileName)
                
                if fileName == "pass.json":
                    pkpasses[pkpass_id]["passPath"] = pkpass_file_path
                    pkpasses[pkpass_id]["data"] = self._processPass(pkpass_collect_file_path)
                    pkpasses[pkpass_id]["isodate"] = self._get_file_last_modified_time(pkpass_collect_file_path)

                elif fileName.endswith(".png"):
                    self._checkPng(pkpass_collect_file_path, os.path.join(pkpass_file_path,fileName))

        elif self.is_fs_dump:
            for walletPkpassFile in self._get_fs_files_from_patterns(WALLET_PKPASSES_ROOT_PATHS):
                pkpass_file_path = trim_prefix(walletPkpassFile, self.target_path)
                pkpass_id = pkpass_file_path.split("/private/var/mobile/Library/Passes/Cards/")[1].split("/")[0]
                if pkpass_id not in pkpasses:
                    pkpasses[pkpass_id] = {
                        "id" : pkpass_id,
                        "passPath" : None,
                        "embeddedFiles" : set(),
                        "isodate" : None,
                    }
                
                fileName = os.path.basename(pkpass_file_path)
                pkpasses[pkpass_id]["embeddedFiles"].add(fileName)
                
                if fileName == "pass.json":
                    pkpasses[pkpass_id]["passPath"] = pkpass_file_path
                    pkpasses[pkpass_id]["data"] = self._processPass(walletPkpassFile)
                    pkpasses[pkpass_id]["isodate"] = self._get_file_last_modified_time(walletPkpassFile)
                elif fileName.endswith(".png"):
                    self._checkPng(walletPkpassFile)

        for key in pkpasses:
            self.results.append(pkpasses[key])
        self.find_suspicious()

