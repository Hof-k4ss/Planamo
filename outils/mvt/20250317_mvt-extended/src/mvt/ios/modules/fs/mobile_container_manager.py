# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import plistlib

from typing import Optional

from ..base import IOSExtraction

MOBILE_CONTAINER_MANAGER_CONTAINERS_PATH = [
    "private/var/root/Library/MobileContainerManager/containers.sqlite3",
    "private/var/mobile/Library/MobileContainerManager/references.sqlite3"
]


class MobileContainerManager(IOSExtraction):
    """This module extracts information from the containers.sqlite3 database file."""

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

    def _find_suspicious_entries(self) -> None:
        for result in self.results:
            if result["code_signing_id_text"].startswith("tmp") or result["code_signing_id_text"].startswith("bd_tool"):
                self.log.warning("Found mention of a very suspicious container (named tmp* / bd_tool*) : \"%s\"", result["code_signing_id_text"])
                if (result not in self.detected) : self.detected.append(result)
            
            if (result["data"].get("com.apple.MobileContainerManager.Entitlements") is not None):
                entitlementsDict = result["data"].get("com.apple.MobileContainerManager.Entitlements")
                for entitlementKey in entitlementsDict.keys():
                    entitlementValue = entitlementsDict[entitlementKey]
                    if entitlementKey == "application-identifier":
                        if self.indicators:
                            ioc = self.indicators.check_process(entitlementValue)
                            if ioc:
                                result["matched_indicator"] = ioc
                                self.log.warning("Found mention of a malicious container (\"%s\") : \"%s\"", entitlementValue, result["code_signing_id_text"])
                                if (result not in self.detected) : self.detected.append(result)
                    if (entitlementKey == "com.apple.rootless.install" or entitlementKey == "run-unsigned-code") and result["code_signing_id_text"] not in ["com.apple.backupd","com.apple.BackupAgent2"]:
                        self.log.warning("Found mention of a malicious container (com.apple.rootless.install) : \"%s\"", result["code_signing_id_text"])
                        if (result not in self.detected) : self.detected.append(result)
                    
    def check_indicators(self) -> None:
        self._find_suspicious_entries()
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_process(result["code_signing_id_text"])
            if ioc:
                self.log.warning("Found mention of a known malicious container \"%s\"", ioc["value"])
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

    def _extract_containers_data(self) -> None:
        conn = self._open_sqlite_db(self.file_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT
                *
            FROM code_signing_info
            LEFT JOIN code_signing_data ON code_signing_info.id = code_signing_data.cs_info_id;
        """)
        
        for row in cur:
            if len(row) >= 8:
                data = plistlib.loads(row[8])
            else:
                data = ""
            entry = {
                "csi_id" : row[0],
                "code_signing_id_text" : row[1],
                "invalid" : row[2],
                "placeholder" : row[3],
                "registered_by_caller" : row[4],
                "data_container_class" : row[5],
                "csd_id" : row[6],
                "data" : data
            }

            self.results.append(entry)
            
        cur.close()
        conn.close()

        self.log.info("Extracted information on %d containers", len(self.results))

    def run(self) -> None:
        self._find_ios_database(root_paths=MOBILE_CONTAINER_MANAGER_CONTAINERS_PATH)
        self.log.info("Found containers.sqlite3 at path: %s", self.file_path)
        self._extract_containers_data()
