# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from typing import Optional, Union

from mvt.common.utils import  convert_unix_to_iso
from mvt.common.ccl_abx import parse_abx
from .base import AndroidExtraction

ADB_TEMP_KEYS_PATHS = [
         "data/misc/adb/adb_temp_keys.xml"
]

class AdbKeys(AndroidExtraction):  

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
        adb_connection_data = f"ADB connection from {record.get('user', '')} with key {record.get('key', '')}"
        return {
            "timestamp": record["timestamp"],
            "module": self.__class__.__name__,
            "event": "adb_connection",
            "data": adb_connection_data,
        }
                    
    def check_indicators(self) -> None:
        for result in self.results:
            self.log.warning("ADB connection from user \"%s\" with key \"%s\"", result.get('user', ''), result.get('key', ''))
            self.detected.append(result)
                
    def _extract_log_data(self) -> None:
        content = parse_abx(self.file_path)
        keys = content.get("keyStore", {}).get("adbKey", {})
        for key in keys:
            current_entry = {}
            identifier = keys["@key"]
            if " " in identifier:
                identifier= identifier.split(" ")
                current_entry["timestamp"] = convert_unix_to_iso(float(keys["@lastConnection"])/1000)
                current_entry["user"] = identifier[1]
                current_entry["key"] = identifier[0]
            else:
                current_entry["timestamp"] = convert_unix_to_iso(float(keys["@lastConnection"])/1000)
                current_entry["user"] = "None"
                current_entry["key"] = key
            self.results.append(current_entry)
                    
        self.results = sorted(self.results, key=lambda entry: entry["timestamp"])
        
    def run(self) -> None:
        for adb_temp_keys in self._get_fs_files_from_patterns(ADB_TEMP_KEYS_PATHS):
            self.file_path = adb_temp_keys
            self.log.info("Found adb_temp_keys file at path: %s", self.file_path)
            self._extract_log_data()
        self.log.info("Extracted information on %d adb_temp_keys records", len(self.results))

