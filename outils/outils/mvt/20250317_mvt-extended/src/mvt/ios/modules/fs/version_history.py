# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import datetime
import json
import logging
import re

from mvt.common.utils import convert_datetime_to_iso, trim_prefix
from mvt.ios.versions import find_version_by_build
from typing import Optional, Union

from ..base import IOSExtraction
from .analytics import Analytics

IOS_ANALYTICS_JOURNAL_PATHS = [
    "private/var/db/analyticsd/Analytics-Journal-*.ips",
    "private/var/mobile/Library/Logs/CrashReporter/Analytics-Journal-*.ips*"
]

MOBILEACTIVATIOND_LOG_PATHS = [
    "private/var/mobile/Library/Logs/mobileactivationd/mobileactivationd.log.*",
    "private/var/mobile/Library/Logs/CrashReporter/DiagnosticLogs/sysdiagnose/*/logs/MobileActivation/mobileactivationd.log.*"
    ""
]

class IOSVersionHistory(IOSExtraction):
    """This module extracts iOS update history from Analytics Journal log files and mobileactivationd log files."""

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
        if record["source"] == "analytics_journal":
            return {
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": "ios_version_analytics_journal",
                "data": f"Recorded iOS version {record['os_version']}",
            }
        elif record["source"] == "analytics_database":
            return {
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": "ios_version_analytics_database",
                "data": f"Recorded iOS version {record['os_version']}",
            }
        elif record["source"] == "mobileactivationd":
            if record.get("message"):
                return {
                    "timestamp": record["isodate"],
                    "module": self.__class__.__name__,
                    "event": "ios_version_mobileactivationd",
                    "data": f"(Local Time) Recorded iOS upgrade : {record['message']}",
                }
            version_from = find_version_by_build(record['from_build'])
            version_to = find_version_by_build(record['to_build'])
            return {
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": "ios_version_mobileactivationd",
                "data": f"(Local Time) Recorded iOS upgrade from {version_from if version_from else record['from_build']} to {version_to if version_to else record['to_build']}",
            }
        elif record["source"] == "mobileactivationd_estimate":
            version_from = find_version_by_build(record['from_build'])
            version_to = find_version_by_build(record['to_build'])
            return {
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": "ios_version_mobileactivationd",
                "data": f"(Local Time) Recorded iOS upgrade from {version_from if version_from else record['from_build']} to {version_to if version_to else record['to_build']} between {record['isodate_from']} and {record['isodate']}",
            }


    def _extract_from_analytics(self):

        anl = Analytics(target_path=self.target_path, log=self.log)
        anl.process_analytics_dbs()

        dt_format = "%Y-%m-%d %H:%M:%S.%f"

        builds = {}
        for result in anl.results:
            build = result.get("build")
            if not build:
                continue

            isodate = result.get("isodate", None)
            if not isodate:
                continue

            if build not in builds.keys():
                builds[build] = isodate
                continue

            result_dt = datetime.strptime(isodate, dt_format)
            cur_dt = datetime.strptime(builds[build], dt_format)

            if result_dt < cur_dt:
                builds[build] = isodate

        for build, isodate in builds.items():
            version = find_version_by_build(build)

            self.results.append({
                "source": "analytics_database",
                "isodate": isodate,
                "os_version": version
            })

    def _extract_from_mobileactivationd(self):
        last_build = ""
        last_boot_time = ""
        ordered_paths = sorted(list(self._get_fs_files_from_patterns(MOBILEACTIVATIOND_LOG_PATHS)), reverse=True)
        for found_path in ordered_paths:
            with open(found_path, "r", encoding="utf-8") as mobileactivationd_log:
                lines = mobileactivationd_log.readlines()
            for line in lines:
                if re.match(r'^[^ ]+\s+[^ ]+\s+[0-9]+\s+[0-9]+:[0-9]+:[0-9]+ [0-9]+ \[[0-9]+\] <[^>]+> \([^)]+\) .*$', line):
                    match = re.search(r'(?P<day>[^ ]+)\s+(?P<month>[^ ]+)\s+(?P<dom>[0-9]+)\s+(?P<hour>[0-9]+):(?P<minutes>[0-9]+):(?P<seconds>[0-9]+) (?P<year>[0-9]+) \[(?P<id>[0-9]+)\] <(?P<level>[^>]+)> \((?P<hexid>[^)]+)\) (?P<message>.*)', line)
                    if match:
                        message = match.group("message")
                        if ("perform_data_migration" in message):
                            
                            entry = {}
                            message_stripped = trim_prefix(message, "MA: perform_data_migration: Upgrade from ")
                            matched_versions = re.search(r'(?P<from>.*)to\s+(?P<to>.*)detected', message_stripped)


                            try:
                                from_build = matched_versions.group("from")[:-1]
                                to_build = matched_versions.group("to")[:-1]
                            except:
                                from_build = None
                                to_build = None

                            datetime_string = match.group("day") + " " + match.group("month") + " " + match.group("dom") + " " + match.group("hour") + ":" + match.group("minutes") + ":" + match.group("seconds") + " " + match.group("year")
                            timestamp = datetime.datetime.strptime(datetime_string, "%a %b %d %H:%M:%S %Y")
                            entry["isodate"] = convert_datetime_to_iso(timestamp)
                            entry["source"] = "mobileactivationd"

                            if not from_build and not to_build:
                                entry["message"] = message
                            else:
                                entry["from_build"] = from_build
                                entry["to_build"] = to_build

                            self.results.append(entry)
                        
                        elif ("build_version: " in message):
                            
                            entry = {}
                            build = trim_prefix(message, "MA: main: build_version: ")
                            datetime_string = match.group("day") + " " + match.group("month") + " " + match.group("dom") + " " + match.group("hour") + ":" + match.group("minutes") + ":" + match.group("seconds") + " " + match.group("year")
                            boot_time = datetime.datetime.strptime(datetime_string, "%a %b %d %H:%M:%S %Y")

                            if last_build == "": last_build = build
                            if build != last_build:
                                entry["from_build"] = last_build
                                entry["to_build"] = build
                                entry["isodate_from"] = convert_datetime_to_iso(last_boot_time)
                                entry["isodate"] = convert_datetime_to_iso(boot_time)
                                entry["source"] = "mobileactivationd_estimate"
                                self.results.append(entry)
                                last_build = build
                            last_boot_time = boot_time

                else:
                    #self.results[-1]["message"] += line.replace("\n","").replace("\r","").replace("\t","")
                    continue

    def run(self) -> None:
        for found_path in self._get_fs_files_from_patterns(IOS_ANALYTICS_JOURNAL_PATHS):
            with open(found_path, "r", encoding="utf-8") as analytics_log:
                log_line = json.loads(analytics_log.readline().strip())

                timestamp = datetime.datetime.strptime(
                    log_line["timestamp"], "%Y-%m-%d %H:%M:%S.%f %z"
                )
                timestamp_utc = timestamp.astimezone(datetime.timezone.utc)
                self.results.append(
                    {
                        "source": "analytics_journal",
                        "isodate": convert_datetime_to_iso(timestamp_utc),
                        "os_version": log_line["os_version"],
                    }
                )

        self._extract_from_mobileactivationd()

        self.results = sorted(self.results, key=lambda entry: entry["isodate"])
        self.log.info("Extracted a total of %d version history records", len(self.results))
