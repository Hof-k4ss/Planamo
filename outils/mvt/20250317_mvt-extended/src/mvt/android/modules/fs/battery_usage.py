# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from typing import Optional, Union

from mvt.common.utils import convert_unix_to_iso
from .base import AndroidExtraction

BATTERY_USAGE_DB_PATH = [
    "data/user/0/com.google.android.settings.intelligence/databases/battery-usage-db-v4",
]

class BatteryUsage(AndroidExtraction):
    """This module extracts information from the
    battery-usage-db-v4 database."""

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
        battery_usage_data = f"Package {record['packageName']} ({record['appLabel']}) with hidden flag set at  \'{record['isHidden']}\' has been used in background for {record['backgroundUsageTimeInMs']} ms and for {record['foregroundUsageTimeInMs']} ms in foreground."
        return {
                "timestamp": record["timestamp"],
                "module": self.__class__.__name__,
                "event": "App_Battery_Usage",
                "data": battery_usage_data,
            }

    def check_indicators(self) -> None:
        if not self.indicators:
            return
        for result in self.results:
            ioc = self.indicators.check_app_id(result.get("packageName"))
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
                
            if result.get("percentOfTotal") > 25:
                self.log.warning("Package  %s with AppLabel %s used a suspicious amount of battery", result.get('packageName'), result.get('appLabel'))
                

    def process_battery_usage_db(self, path):
        conn = self._open_sqlite_db(path)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                *
            FROM BatteryState;
        """)
        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                if headings[index] == "timestamp":
                    entry[headings[index]] = convert_unix_to_iso(float(int(value)/1000))
                else:
                    entry[headings[index]] = value
            self.results.append(entry)
        conn.close()

    def run(self) -> None:
        for file_path in self._get_fs_files_from_patterns(BATTERY_USAGE_DB_PATH):
            self.log.info("Processing battery-usage-db-v4 file at %s", file_path)
            self.process_battery_usage_db(file_path)

        self.log.info("Extracted a total of %d battery-usage-db-v4 records", len(self.results))
