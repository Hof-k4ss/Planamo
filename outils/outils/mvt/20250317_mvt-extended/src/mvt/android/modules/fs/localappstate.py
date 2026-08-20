# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional, Union

from mvt.common.utils import convert_unix_to_iso
from .base import AndroidExtraction

LOCALAPPSTATE_DB_PATH = [
    "data/data/com.android.vending/databases/localappstate.db",
]
class LocalAppState(AndroidExtraction):
    """This module extracts information from the
    localappstate.db database."""

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
        appstate_data = f"Package {record['package_name']} (owner: {record['account']}) state has changed. Reason: {record['install_reason']}"
        records = [
            {
                "timestamp": record["delivery_data_timestamp_ms"],
                "module": self.__class__.__name__,
                "event": "app_state_delivery_data",
                "data": appstate_data,
            }
        ]

        if record.get("last_update_timestamp_ms"):
            records.append(
            {
                "timestamp": record["last_update_timestamp_ms"],
                "module": self.__class__.__name__,
                "event": "app_state_last_update",
                "data": appstate_data,
            })
     
        return records

    def check_indicators(self) -> None:
        # TODO
        if not self.indicators:
            return
    
    def process_localappstate_db(self, path):
        print(path)
        conn = self._open_sqlite_db(path)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                *
            FROM appstate;
        """)
        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                if headings[index] == "delivery_data_timestamp_ms" or headings[index] == "last_update_timestamp_ms":
                    entry[headings[index]] = convert_unix_to_iso(float(int(value)/1000))
                else:
                    entry[headings[index]] = value
            self.results.append(entry)
        conn.close()

    def run(self) -> None:
        for file_path in self._get_fs_files_from_patterns(LOCALAPPSTATE_DB_PATH):
            self.log.info("Processing localappstate.db database at %s", file_path)
            self.process_localappstate_db(file_path)

        self.log.info("Extracted a total of %d localappstate entries", len(self.results))
