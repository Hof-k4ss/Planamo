# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/


import logging
import os
import plistlib

from typing import Optional

from mvt.common.utils import convert_unix_to_iso

from ..base import IOSExtraction

SOFTWAREUPDATESERVICESD_BACKUP_IDS = [
    "b2360ab334042795fbf866b746141b8aa6640fb9",
]
SOFTWAREUPDATESERVICESD_ROOT_PATH = [
    "private/var/mobile/Library/Preferences/com.apple.softwareupdateservicesd.plist",
]


class SoftwareUpdates(IOSExtraction):
    """Extracts information about the auto-update status of the device, and potentially the date of the disabling of that feature"""

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

    def check_indicators(self) -> None:
        for result in self.results:
            if result.get("SUAutomaticUpdateV2Enabled") == False:
                self.detected.append(result)
                self.log.warning("Auto-updates are disabled. The last time the configuration file was edited is : %s", result["modified"])

    def _extract_softwareupdateservicesd_entries(self, file_path) -> None:
        with open(file_path, "rb") as handle:
            file_plist = plistlib.load(handle)
        file_plist["modified"] = self._get_file_last_modified_time(file_path)
        self.results.append(file_plist)

    def run(self) -> None:

        if self.is_backup:
            self._find_ios_database(backup_ids=SOFTWAREUPDATESERVICESD_BACKUP_IDS)
            self.log.info("Found com.apple.softwareupdateservicesd plist at path: %s", self.file_path)
            self._extract_softwareupdateservicesd_entries(self.file_path)
        elif self.is_fs_dump:
            for softwareupdateservicesd_path in self._get_fs_files_from_patterns(SOFTWAREUPDATESERVICESD_ROOT_PATH):
                self.file_path = softwareupdateservicesd_path
                self.log.info("Found com.apple.softwareupdateservicesd plist at path: %s", self.file_path)
                self._extract_softwareupdateservicesd_entries(self.file_path)

        self.log.info("Extracted a total of %d com.apple.softwareupdateservicesd entry", len(self.results))
