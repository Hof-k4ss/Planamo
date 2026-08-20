# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import re
from typing import Optional, Union

from mvt.common.utils import trim_prefix
from .base import AndroidExtraction

SSRM_HEATING_LOGS_PATHS = [
         "data/user/0/com.sec.android.sdhms/ssrm_heating.log",
         "data/system/ssrm_heating.log"
]


class SSRMHeatingLogs(AndroidExtraction):
    """This module extracts information from the ssrm_heating log files."""

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
            "event": record['entry_type'],
            "data": record['message'],
        }
                    
    def check_indicators(self) -> None:
        #TODO
        return


    
    def _extract_log_data(self) -> None:
        with open(self.file_path, "r", encoding="utf-8") as handle:
            content = handle.readlines()

        current_entry = {}
        for line in content:
            
            line = line.strip()
            
            if re.match(r'(^[0-9]{4}\-[0-9]{2}\-[0-9]{2} [0-9]{2}\:[0-9]{2}\:[0-9]{2})', line):
                if (current_entry != {} and current_entry not in self.results): 
                    self.results.append(current_entry)
                current_entry = {}
                searches = re.search(r'(^[0-9]{4}\-[0-9]{2}\-[0-9]{2} [0-9]{2}\:[0-9]{2}\:[0-9]{2}) (\[[A-Z]{3}\]) (.*)$',line)
                isodate = searches.group(1)
                entry_type = searches.group(2)
                
                current_entry["isodate"] = isodate
                current_entry["entry_type"]  = entry_type
                current_entry["message"] = trim_prefix(searches[3],"-").replace("\r"," ").replace("\n"," ")
                
            else:
                current_entry["message"] += line

        self.results = sorted(self.results, key=lambda entry: entry["isodate"])
        

    def run(self) -> None:
        for ssrmheatinglogpath in self._get_fs_files_from_patterns(SSRM_HEATING_LOGS_PATHS):
            self.file_path = ssrmheatinglogpath
            self.log.info("Found SSRM_Heating log file at path: %s", self.file_path)
            self._extract_log_data()
        self.log.info("Extracted information on %d SSRM Heating log records", len(self.results))

