# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import re

from typing import Optional, Union

from mvt.common.utils import convert_datetime_to_iso, convert_lockdowndlog_to_unix, trim_prefix

from ..base import IOSExtraction

LOCKDOWND_LOGS_PATHS = [
    "private/var/logs/*lockdownd.log*",
    "private/var/mobile/Library/Logs/CrashReporter/DiagnosticLogs/sysdiagnose/*/logs/MobileLockdown/*lockdownd.log*"
]


class LockdowndLogs(IOSExtraction):
    """This module extracts information from the lockdownd log files."""

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
            "event": "lockdownd_entry",
            "data": f"(Local Time) {record['message']}",
        }
    
    def _find_suspicious_entries(self) -> None:
        for result in self.results:
            if "[DeveloperModeStatus]" in result["message"] and not "Sprinboard" in result["message"]:
                self.log.warning("A process other than springboard tried to access / edit Developer Mode settings : %s : \"%s\"", result["isodate"], result["message"])
                if (result not in self.detected) : self.detected.append(result)

            if "tmp" in result["message"] or "bd_tool" in result["message"]:
                self.log.warning("Found mention of a suspicious name in lockdownd Logs event (tmp* / bd_tool*) : %s : \"%s\"", result["isodate"], result["message"])
                if (result not in self.detected) : self.detected.append(result)
                    
    def check_indicators(self) -> None:
        self._find_suspicious_entries()

        if not self.indicators:
            return

        for result in self.results:
            for ioc in self.indicators.get_iocs("processes"):
                if ioc["value"] in result["message"]:
                    self.log.warning("Found mention of a known malicious container in lockdownd logs event : %s : \"%s\"", result["isodate"], result["message"])
                    result["matched_indicator"] = ioc
                    if (result not in self.detected) : self.detected.append(result)
                    break
    
    def _extract_log_data(self, content) -> None:
        current_entry = {}
        for line in content.split("\n"):
            line = line.strip()

            if re.match(r'(^[0-9]+/[0-9]+/[0-9]+ [0-9]+:[0-9]+:[0-9]+\.[0-9]+) pid=([0-9]+) (.*)$',line):
                if (current_entry != {} and current_entry not in self.results): 
                    self.results.append(current_entry)
                    current_entry = {}
                searches = re.search(r'(^[0-9]+/[0-9]+/[0-9]+ [0-9]+:[0-9]+:[0-9]+\.[0-9]+) pid=([0-9]+) (.*)$',line)
                isodate = convert_lockdowndlog_to_unix(searches[1])
                current_entry["isodate"] = convert_datetime_to_iso(isodate)
                current_entry["pid"] = int(searches[2])
                current_entry["message"] = searches[3].replace("\r"," ").replace("\n"," ")

            else:
                current_entry["message"] += line.replace("\r"," ").replace("\n"," ")

        if (current_entry != {} and current_entry not in self.results): self.results.append(current_entry)
        self.results = sorted(self.results, key=lambda entry: entry["isodate"])

    def run(self) -> None:
        for lockdowndlogpath in self._get_fs_files_from_patterns(LOCKDOWND_LOGS_PATHS):
            self.file_path = lockdowndlogpath
            self.log.info("Found Lockdownd log file at path: %s", self.file_path)
            with open(self.file_path, "r", encoding="utf-8") as handle:
                self._extract_log_data(handle.read())

        self.log.info("Extracted %d Lockdownd log entries", len(self.results))