# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.common.utils import recursive_resolve, trim_prefix

import logging
import os
import sqlite3
from typing import Optional, Union

from ..base import IOSExtraction

CACHE_DB_PATH = [
    "**/Cache.db",
]

class CacheFiles(IOSExtraction):

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
        records = []
        for item in self.results[record]:
            records.append({
                "timestamp": item["isodate"],
                "module": self.__class__.__name__,
                "event": "cache_response",
                "data": f"{record} recorded visit to URL {item['url']}"
            })

        return records

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        self.detected = {}
        for key, values in self.results.items():
            try:
                process_name = key.split("Library/Caches/")[1].split("/")[0]
            except:
                process_name = key
            for value in values:
                ioc = self.indicators.check_url(value["url"])
                if  not ioc :
                    ioc = self.indicators.check_process(process_name)
                if ioc :
                    value["matched_indicator"] = ioc
                    self.log.warning("Process \"%s\"'s cache recorded a visit to %s on %s", process_name, value["url"], value["isodate"])
                    if key not in self.detected:
                        self.detected[key] = [value, ]
                    else:
                        self.detected[key].append(value)

    def _process_cache_file(self, file_path):

        conn = self._open_sqlite_db(file_path)
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT
                    *
                FROM cfurl_cache_response
                LEFT JOIN
                    cfurl_cache_receiver_data
                    ON cfurl_cache_response.entry_ID = cfurl_cache_receiver_data.entry_ID
                LEFT JOIN
                    cfurl_cache_blob_data
                    ON cfurl_cache_response.entry_ID = cfurl_cache_blob_data.entry_ID
            """)
        except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
            self.log.warning("File %s is probably malformed, skipping it : %s", trim_prefix(file_path, self.target_path), e)
            return

        key_name = os.path.relpath(file_path, self.target_path)
        if key_name not in self.results:
            self.results[key_name] = []

        for row in cur:
            entry = {}

            cfurl_cache_response_entry_id = row[0]
            cfurl_cache_response_version = row[1]
            cfurl_cache_response_hash_value = row[2]
            cfurl_cache_response_storage_policy = row[3]
            cfurl_cache_response_request_key = row[4]
            cfurl_cache_response_time_stamp = row[5]
            cfurl_cache_response_partition = row[6]

            cfurl_cache_receiver_data_entry_id = row[7]
            cfurl_cache_receiver_data_isdataonfs = row[8]
            
            cfurl_cache_receiver_data_receiver_data_bplist = row[9]
            cfurl_cache_receiver_data_receiver_data = recursive_resolve(cfurl_cache_receiver_data_receiver_data_bplist)

            cfurl_cache_blob_data_entry_id = row[10]
            cfurl_cache_blob_data_response_object_bplist = row[11]
            cfurl_cache_blob_data_response_object = recursive_resolve(cfurl_cache_blob_data_response_object_bplist)

            cfurl_cache_blob_data_request_object_bplist = row[12]
            cfurl_cache_blob_data_request_object = recursive_resolve(cfurl_cache_blob_data_request_object_bplist)

            cfurl_cache_blob_data_proto_props_bplist = row[13]
            cfurl_cache_blob_data_proto_props = recursive_resolve(cfurl_cache_blob_data_proto_props_bplist)

            cfurl_cache_blob_data_user_info = row[14]

            entry["entry_id"] = cfurl_cache_response_entry_id
            entry["version"] = cfurl_cache_response_version
            entry["hash_value"] = cfurl_cache_response_hash_value
            entry["storage_policy"] = cfurl_cache_response_storage_policy
            entry["url"] = cfurl_cache_response_request_key
            entry["isodate"] = cfurl_cache_response_time_stamp
            entry["partition"] = cfurl_cache_response_partition
            entry["isdataonfs"] = cfurl_cache_receiver_data_isdataonfs
            entry["receiver_data"] = cfurl_cache_receiver_data_receiver_data
            entry["request_object"] = cfurl_cache_blob_data_request_object
            entry["response_object"] = cfurl_cache_blob_data_response_object
            entry["proto_props"] = cfurl_cache_blob_data_proto_props
            entry["user_info"] = cfurl_cache_blob_data_user_info

            self.results[key_name].append(entry)

    def run(self) -> None:
        self.results = {}
        for cache_file in self._get_fs_files_from_patterns(CACHE_DB_PATH):
            self._process_cache_file(cache_file)
        self.log.info("Processed %d cache files", len(self.results))
