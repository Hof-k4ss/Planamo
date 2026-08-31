# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional, Union

from mvt.common.utils import convert_unix_to_iso
from .base import AndroidExtraction

THERMAL_DB_PATH = [
    "data/user/0/com.sec.android.sdhms/databases/thermal_log",
]
class ThermalLog(AndroidExtraction):
    """This module extracts information from the
    thermal_log file."""

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
        self.results = []
    
    def serialize(self, record: dict) -> Union[dict, list]:
        if record["entry_type"] == "netstat":
            thermal_netstat_data = f"Package {record['package_name']} with UID {record['uid']} used {record['net_usage']} bytes of data."
            records = [
                {
                    "timestamp": record["start_time"],
                    "module": self.__class__.__name__,
                    "event": "netstat_package_started",
                    "data": thermal_netstat_data,
                }
            ]
            if record.get("end_time"):
                records.append(
                {
                    "timestamp": record["end_time"],
                    "module": self.__class__.__name__,
                    "event": "netstat_package_stopped",
                    "data": thermal_netstat_data,
                })
            return records

        elif record["entry_type"] == "cpustat":
            thermal_cpustat_data = f"Process {record['process_name']} with PID {record['pid']} launched with UID {record['uid']} has an uptime of {record['uptime']} milliseconds."
            records = [
                {
                    "timestamp": record["start_time"],
                    "module": self.__class__.__name__,
                    "event": "cpustat_process_started",
                    "data": thermal_cpustat_data,
                }
            ]
            if record.get("end_time"):
                records.append(
                {
                    "timestamp": record["end_time"],
                    "module": self.__class__.__name__,
                    "event": "cpustat_process_end",
                    "data": thermal_cpustat_data,
                })
            return records

    def check_indicators(self) -> None:
        # TODO
        return
    
    # parse NetStat
    def process_netstat_thermal_file(self, path):
        conn = self._open_sqlite_db(path)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                *
            FROM NETSTAT;
        """)
        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                if headings[index] == "start_time" or headings[index] == "end_time":
                    entry[headings[index]] = convert_unix_to_iso(float(value/1000))
                else:
                    entry[headings[index]] = value
            self.results.append(entry)
            entry["entry_type"] = "netstat"
        conn.close()

    # parse CPUSTAT
    def process_cpustat_thermal_file(self, path):
        conn = self._open_sqlite_db(path)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                *
            FROM CPUSTAT;
        """)
        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                if headings[index] == "start_time" or headings[index] == "end_time":
                    entry[headings[index]] = convert_unix_to_iso(float(value/1000))
                else:
                    entry[headings[index]] = value
            self.results.append(entry)
            entry["entry_type"] = "cpustat"
        conn.close()

    def run(self) -> None:
        for file_path in self._get_fs_files_from_patterns(THERMAL_DB_PATH):
            self.log.info("Processing thermal_log file at %s", file_path)
            self.process_netstat_thermal_file(file_path)
            self.process_cpustat_thermal_file(file_path)

        self.log.info("Extracted a total of %d entries", len(self.results))
