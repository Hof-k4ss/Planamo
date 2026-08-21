# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import re
import logging
from typing import Optional, Union

from mvt.common.utils import convert_mactime_to_iso

from ..base import IOSExtraction

SHUTDOWN_LOG_PATH = [
    "private/var/db/diagnostics/shutdown.log",
    "private/var/mobile/Library/Logs/CrashReporter/DiagnosticLogs/sysdiagnose/*/system_logs.logarchive/Extra/shutdown.log"
]


class ShutdownLog(IOSExtraction):
    """This module extracts processes information from the shutdown log file."""

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
            "event": "shutdown",
            "data": f"Client {record['client']} with PID {record['pid']} "
            "was running when the device was shut down",
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        suspicious_process_pattern_1 = re.compile('^/[0-9A-F\-]{36}$')
        suspicious_process_pattern_2 = re.compile('^(/private)?/var/db/com.apple.xpc.roleaccountd.staging/(?!com.apple.MobileSoftwareUpdate)(?!com.apple.dt.instruments.dtsecurity).*/[0]{36}$')
        suspicious_process_pattern_3 = re.compile('^(/private)?/var/db/com.apple.xpc.roleaccountd.staging/(?!com.apple.MobileSoftwareUpdate)(?!com.apple.dt.instruments.dtsecurity).*/[0-9A-F\-]{36}$')
        suspicious_process_pattern_4 = re.compile('^(/private)?/var/tmp/.*$')

        for result in self.results:
            ioc = self.indicators.check_file_path(result["client"])
            if ioc:
                result["matched_indicator"] = ioc
                if result not in self.detected:
                    self.log.warning("Found mention of a known malicious process \"%s\" in shutdown.log at %s",
                                        result["client"], result["isodate"])
                    self.detected.append(result)
                    continue

            ioc = self.indicators.check_file_path_process(result["client"])
            if ioc:
                result["matched_indicator"] = ioc
                if result not in self.detected:
                    self.log.warning("Found mention of a known malicious process \"%s\" in shutdown.log at %s",
                                        result["client"], result["isodate"])
                    self.detected.append(result)
                    continue

            suspicious_process_pattern_matched = suspicious_process_pattern_1.search(result["client"])
            if suspicious_process_pattern_matched and result not in self.detected:
                self.log.warning("Found mention of a new malicious client \"%s\" in shutdown.log at %s",
                                    result["client"], result["isodate"])
                self.detected.append(result)

            suspicious_process_pattern_matched = suspicious_process_pattern_2.search(result["client"])
            if suspicious_process_pattern_matched and result not in self.detected:
                self.log.warning("Found mention of a new malicious client \"%s\" in shutdown.log at %s",
                                    result["client"], result["isodate"])
                self.detected.append(result)

            suspicious_process_pattern_matched = suspicious_process_pattern_3.search(result["client"])
            if suspicious_process_pattern_matched and result not in self.detected:
                self.log.warning("Found mention of a suspicious client \"%s\" in shutdown.log at %s",
                                    result["client"], result["isodate"])

            suspicious_process_pattern_matched = suspicious_process_pattern_4.search(result["client"])
            if suspicious_process_pattern_matched and result not in self.detected:
                self.log.warning("Found mention of a suspicious client \"%s\" in shutdown.log at %s",
                                    result["client"], result["isodate"])


    def process_shutdownlog(self, content):
        current_processes = []
        recent_processes = []
        times_delayed = 0
        delay = 0.0
        for line in content.split("\n"):
            line = line.strip()

            if line.startswith("remaining client pid:"):
                current_processes.append(
                    {
                        "pid": line[line.find("pid: ") + 5 : line.find(" (")],
                        "client": line[line.find("(") + 1 : line.find(")")],
                        "delay": delay,
                        "times_delayed": times_delayed,
                    }
                )
            elif line.startswith("After "):
                # Consider the previous processes
                # End of the current processes
                for p in current_processes:
                    recent_processes.append(p)
                delay += float(line.split(" ")[1][:-2])
                times_delayed += 1
                current_processes = []
            elif line.startswith("SIGTERM: "):
                for p in current_processes:
                    recent_processes.append(p)

                try:
                    mac_timestamp = int(line[line.find("[") + 1 : line.find("]")])
                except ValueError:
                    try:
                        start = line.find(" @") + 2
                        mac_timestamp = int(line[start : start + 10])
                    except Exception:
                        mac_timestamp = 0

                isodate = convert_mactime_to_iso(mac_timestamp, from_2001=False)

                for process in recent_processes:
                    self.results.append(
                        {
                            "isodate": isodate,
                            "pid": process["pid"],
                            "client": process["client"],
                            "delay": process["delay"],
                            "times_delayed": process["times_delayed"],
                        }
                    )

                current_processes = []
                recent_processes = []
                times_delayed = 0
                delay = 0.0

        self.results = sorted(self.results, key=lambda entry: entry["isodate"])

    def run(self) -> None:
        for file_path in self._get_fs_files_from_patterns(SHUTDOWN_LOG_PATH):
            self.file_path = file_path
            self.log.info("Found shutdown log at path: %s", self.file_path)
            with open(self.file_path, "r", encoding="utf-8") as handle:
                self.process_shutdownlog(handle.read())
                
        self.log.info("Extracted information on %d shutdown log entries", len(self.results))
