# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import logging

from typing import Optional

from ..base import IOSExtraction

PS_FILE_PATH = [
    "private/var/mobile/Library/Logs/CrashReporter/DiagnosticLogs/sysdiagnose/*/ps.txt"
]


class Process(IOSExtraction):
    """This module extracts information from the ps.txt files."""

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
            for ioc in self.indicators.get_iocs("processes"):
                executable_path = "/" + "/".join(result.split("/")[1:])
                if (ioc["value"] in result or self.indicators.check_file_path(executable_path)) and result not in self.detected:
                    self.log.warning("Found mention of a known malicious process \"%s\" in ps.txt", result)
                    self.detected.append(result)

    def _extract_ps_data(self, content) -> None:
        self.results += content

    def run(self) -> None:
        for file_path in self._get_fs_files_from_patterns(PS_FILE_PATH):
            self.file_path = file_path
            self.log.info("Found ps.txt file at path: %s", file_path)
            with open(self.file_path, "r", encoding="utf-8") as handle:
                self._extract_ps_data(handle.read().splitlines())
                
        self.log.info("Extracted information on %d ps.txt entries", len(self.results))