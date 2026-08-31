# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import base64
import logging
import os
from io import BytesIO
from struct import unpack
from typing import Optional, Union

from mvt.common.utils import convert_mactime_to_iso, trim_prefix

from ..base import IOSExtraction

BINARY_COOKIES_REL_PATHS = "/Cookies.binarycookies"
BINARY_COOKIES_ROOT_PATHS = [
    "**/Cookies.binarycookies",
    "**.binarycookies"
]


class BinaryCookies(IOSExtraction):
    """This module extracts data from Cookies.binarycookies files."""

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

    def serialize(self, record: dict) -> Union[dict, list]:
        returned = []
        if record.get("creation"):
            returned.append ({
                "timestamp": record["creation"],
                "module": self.__class__.__name__,
                "event": "binary_cookie_create",
                "data": record,
            })
        if record.get("expires"):
            returned.append ({
                "timestamp": record["expires"],
                "module": self.__class__.__name__,
                "event": "binary_cookie_expires",
                "data": record,
            })

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            for ioc in self.indicators.get_iocs("domains"):
                    if ioc["value"] in result.get("domain"):
                        result["matched_indicator"] = ioc
                        self.log.warning("Found mention of a malicious domain \"%s\" : %s at %s",
                                            ioc["value"], result.get("domain"), result["creation"])
                        self.detected.append(result)
            if result.get("source"):  # support for legacy outputs
                proc_name = os.path.basename(result["source"]).split(".binarycookies")[0]
                if proc_name != "Cookies":
                    ioc = self.indicators.check_process(proc_name)
                    if ioc:
                        result["matched_indicator"] = ioc
                        self.detected.append(result)

    def _process_binary_cookies_file(self, file_path: str) -> None:
        binary_file = open(file_path, "rb")
        signature = b"cook"
        if binary_file.read(4) == signature:
            numPages = unpack(">i", binary_file.read(4))[0]
            pageOffsets = [unpack(">i", binary_file.read(4))[0] for _ in range(numPages)]
            pages = [binary_file.read(ps) for ps in pageOffsets]
            cookie_info_list = []
            for index, page in enumerate(pages):
                page = BytesIO(page)
                pageStart = page.read(4)
                if pageStart!=b'\x00\x00\x01\x00':
                    self.log.warning("Malformed cookie in %s", file_path)
                    continue
                numCookies = unpack("<i", page.read(4))[0]
                cookieOffsets = [unpack("<i", page.read(4))[0] for _ in range(numCookies)]
                page.read(4)
                for offset in cookieOffsets:
                    cookie_entry = {}
                    page.seek(offset)
                    cookieSize = unpack("<i", page.read(4))[0]
                    cookie = BytesIO(page.read(cookieSize))
                    unknownOne = cookie.read(4)
                    cookieFlags = unpack("<i", cookie.read(4))[0]
                    if cookieFlags == 0:
                        cookieFlags = None
                    elif cookieFlags == 1:
                        cookieFlags = "Secure"
                    elif cookieFlags == 4:
                        cookieFlags = "HttpOnly"
                    elif cookieFlags == 5:
                        cookieFlags = "Secure; HttpOnly"
                    else:
                        cookieFlags = "Unknown"
                    unknownTwo = cookie.read(4)
                    domainOffset = unpack("<i", cookie.read(4))[0]
                    nameOffset = unpack("<i", cookie.read(4))[0]
                    pathOffset = unpack("<i", cookie.read(4))[0]
                    valueOffset = unpack("<i", cookie.read(4))[0]
                    commentOffset = unpack("<i", cookie.read(4))[0]
                    endHeader = cookie.read(4)
                    if endHeader!=b'\x00\x00\x00\x00':
                        self.log.warning(endHeader)
                        self.log.warning("Malformed cookie in %s", file_path)
                        continue
                    expiresEpoch = unpack("<d", cookie.read(8))[0]
                    cookie_entry["expires"] = convert_mactime_to_iso(expiresEpoch)
                    creationEpoch = unpack("<d", cookie.read(8))[0]
                    cookie_entry["creation"] = convert_mactime_to_iso(creationEpoch)

                    if commentOffset != 0:
                        cookie.seek(commentOffset-4)
                        cookie_entry["comment"] = cookie.read(domainOffset-commentOffset).decode("utf-8").rstrip("\u0000")
                    cookie.seek(domainOffset-4)
                    cookie_entry["domain"] = cookie.read(nameOffset-domainOffset).decode("utf-8").rstrip("\u0000")
                    cookie.seek(nameOffset-4)
                    cookie_entry["name"] = cookie.read(pathOffset-nameOffset).decode("utf-8").rstrip("\u0000")
                    cookie.seek(pathOffset-4)
                    cookie_entry["path"] = cookie.read(valueOffset-pathOffset).decode("utf-8").rstrip("\u0000")
                    cookie.seek(valueOffset-4)
                    cookie_value = cookie.read(cookieSize-valueOffset)
                    try:
                        cookie_entry["value"] = cookie_value.decode("utf-8").rstrip("\u0000")
                    except:
                        cookie_entry["value"] = base64.b64encode(cookie_value)
                    cookie_entry["source"] = trim_prefix(file_path, self.target_path)
                    self.results.append(cookie_entry)

    def run(self) -> None:
        if self.is_backup:
            for binary_cookies_file in self._get_backup_files_from_manifest_pattern(relative_path_pattern=BINARY_COOKIES_REL_PATHS):
                binary_cookies = self._get_backup_file_from_id(binary_cookies_file["file_id"])
                if not binary_cookies:
                    continue

                self._process_binary_cookies_file(binary_cookies)
        elif self.is_fs_dump:
            for binary_cookies in self._get_fs_files_from_patterns(BINARY_COOKIES_ROOT_PATHS):
                self._process_binary_cookies_file(binary_cookies)

        self.log.info("Extracted a total of %d binary cookies records", len(self.results))