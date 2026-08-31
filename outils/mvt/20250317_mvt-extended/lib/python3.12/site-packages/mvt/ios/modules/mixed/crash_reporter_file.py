# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import datetime
import logging
import plistlib
from typing import Optional, Union

from mvt.common.utils import convert_datetime_to_iso

from ..base import IOSExtraction

CRASH_REPORTER_BACKUP_IDS = ["5c5d55b29327a8b1bbcf63bf99c6a9faeca7448d"]
CRASH_REPORTER_ROOT_PATHS = [
    "private/var/root/Library/Preferences/com.apple.CrashReporter.plist",
]


class CrashReporterFile(IOSExtraction):
    """This module extracts data from com.apple.CrashReporter.plist."""

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
        if record.get("isodate"):
            return {
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": "last_crash_reported",
                "data": record,
            }

    def find_suspicious(self) -> None:
        for entry in self.results:
            if entry.get("urgentSubmissionCount", 0) != 0:
                self.log.warning("urgentSubmissionCount is %s. Last edited %s", entry["urgentSubmissionCount"], entry["isodate"])
                self.detected.append(entry)

    def process_file(self, file_path: str) -> None:
        with open(file_path, "rb") as handle:
            data = plistlib.load(handle)
        if data.get("urgentSubmissionCount", 0) != 0:
            isodate = datetime.datetime(1970, 1, 1) + datetime.timedelta(days=data.get("urgentSubmissionDay", 0))
            data["isodate"] = convert_datetime_to_iso(isodate)
        self.results.append(data)

    def run(self) -> None:
        self._find_ios_database(
            backup_ids=CRASH_REPORTER_BACKUP_IDS,
            root_paths=CRASH_REPORTER_ROOT_PATHS,
        )
        self.log.info("Found com.apple.CrashReporter.plist file at path: %s", self.file_path)

        self.process_file(self.file_path)

        self.find_suspicious()

        self.log.info("Extracted a total of %d entries", len(self.results))
