# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import plistlib
from typing import Optional, Union
from mvt.common.utils import convert_datetime_to_iso

from ..base import IOSExtraction

XPC_ACTIVITY2_ROOT_PATHS = [
    "private/var/root/Library/Preferences/com.apple.xpc.activity2.plist",
]


class XpcActivity2(IOSExtraction):
    """This module extracts information from com.apple.xpc.activity2.plist"""

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
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "activity_base_dates",
            "data": f"Process {record['process']}",
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_process(result["process"])
            if ioc:
                self.log.warning("Found mention of a known process \"%s\"", ioc["value"])
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

    def process_file(self, file_path: str) -> None:
        with open(file_path, "rb") as handle:
            data = plistlib.load(handle)

        for key, value in data.get("ActivityBaseDates").items():
            self.results.append({"process": key, "isodate":convert_datetime_to_iso(value)})

    def run(self) -> None:
        for file_path in self._get_fs_files_from_patterns(XPC_ACTIVITY2_ROOT_PATHS):
            self.file_path = file_path
            self.log.info("Found com.apple.xpc.activity2.plist file at path: %s", self.file_path)
            self.process_file(self.file_path)

        self.log.info("Extracted a total of %d com.apple.xpc.activity2.plist entries", len(self.results))
