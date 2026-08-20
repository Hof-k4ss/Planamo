# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import re

from typing import Optional, Union
from mvt.common.utils import  convert_unix_to_iso
from .base import AndroidExtraction

APP_USAGE_STATS_PATHS = [
         "data/data/com.google.android.apps.turbo/shared_prefs/app_usage_stats.xml"
]

class AppUsageStats(AndroidExtraction):
    """This module extracts information from the AppUsageStats files."""

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
        pkg_data = f"Package: {record['pkg']}"
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": record['statue'],
            "data": pkg_data,
        }
                    
    def check_indicators(self) -> None:
        if not self.indicators:
            return
        for result in self.results:
            ioc = self.indicators.check_app_id(result.get("pkg"))
            if ioc:
                result["matched_indicator"] = ioc
                self.log.warning("Malicious app_id detected ! %s", result.get("pkg"))
                self.detected.append(result)
                
    def _extract_log_data(self) -> None:
        with open(self.file_path, "r", encoding="utf-8") as handle:
            content = handle.readlines()

        current_entry = {}
        for line in content:
            line = line.strip()
            if re.match(r'((\<string\>)(.*\#)(.*)(\<\/string\>))', line):
                searches = re.search(r'((<string>)(.*\#)(.*)(\<\/string\>))', line)
                
                timestamps = searches.group(4).split(",")
                pkg = searches.group(3).replace("#", "")
                
                for i in range(len(timestamps)):
                    current_entry = {}
                    start = int(timestamps[i])
                    current_entry["isodate"] = convert_unix_to_iso(float(start/1000))
                    current_entry["pkg"] = pkg
                    current_entry["statue"] = "Process Start"
                    self.results.append(current_entry)
                    
        self.results = sorted(self.results, key=lambda entry: entry["isodate"])
        
    def run(self) -> None:
        for AppUsageStats in self._get_fs_files_from_patterns(APP_USAGE_STATS_PATHS):
            self.file_path = AppUsageStats
            self.log.info("Found AppUsageStats file at path: %s", self.file_path)
            self._extract_log_data()
        self.log.info("Extracted information on %d AppUsageStats records", len(self.results))

