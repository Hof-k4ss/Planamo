# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
import plistlib

from typing import Optional

from ..base import IOSExtraction

UUIDTOBINARYLOCATIONS_FILE_PATH = [
    "private/var/db/spindump/UUIDToBinaryLocations",
    "private/var/mobile/Library/Logs/CrashReporter/DiagnosticLogs/sysdiagnose/*/logs/tailspindb/UUIDToBinaryLocations"
]


class UUIDFiles(IOSExtraction):
    """This module extracts information from the UUIDToBinaryLocations files."""

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
        if not self.indicators:
            return

        for result in self.results:
            for key, value in result.copy().items():
                element = {}
                element["key"] = key
                element["value"] = value
                ioc = self.indicators.check_file_path(value)
                if not ioc:
                    ioc = self.indicators.check_file_path_process(value)
                if ioc:
                    self.log.warning("Found mention of a known malicious process \"%s\" (key : \"%s\") in UUIDToBinaryLocations", value, key)
                    element["matched_indicator"] = ioc
                    self.detected.append(element)

    def _extract_uuidfile_data(self, content) -> None:
        try:
            data = plistlib.loads(content)
            self.results.append(data)
        except Exception as err:
            self.log.warning("Failed to parse UUIDToBinaryLocations file at path %s. Error : %s", self.file_path, err)

    def run(self) -> None:
        for file_path in self._get_fs_files_from_patterns(UUIDTOBINARYLOCATIONS_FILE_PATH):
            self.file_path = file_path
            self.log.info("Found UUIDToBinaryLocations file at path: %s", file_path)
            with open(self.file_path, "rb") as handle:
                if os.path.getsize(self.file_path) == 0:
                    self.log.warning("UUIDToBinaryLocations database at path %s is empty (0 bytes).", self.file_path)
                    continue
                self._extract_uuidfile_data(handle.read())
        self.log.info("Extracted information on %d UUIDToBinaryLocations files", len(self.results))