# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from typing import Optional, Union

from mvt.common.utils import convert_unix_to_iso
from .base import AndroidExtraction

ANOMALY_DB_PATH = [
    "data/user/0/com.sec.android.sdhms/databases/anomaly.db",
]

class Anomaly(AndroidExtraction):
    """This module extracts information from the
    anomaly database."""

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
        anomaly_data = f"reason: {record['reason']}"
        records = [
            {
                "timestamp": record["time"],
                "module": self.__class__.__name__,
                "event": "config_history",
                "data": anomaly_data,
            }
        ]
     
        return records

    def check_indicators(self) -> None:
        # TODO
        return
    
    def process_anomaly_db(self, path):
        conn = self._open_sqlite_db(path)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                *
            FROM config_history;
        """)

        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                if headings[index] == "time":
                    entry[headings[index]] = convert_unix_to_iso(float(value/1000))
                else:
                    entry[headings[index]] = value
            self.results.append(entry)
        conn.close()

    def run(self) -> None:
        for file_path in self._get_fs_files_from_patterns(ANOMALY_DB_PATH):
            self.log.info("Processing anomaly database file at %s", file_path)
            self.process_anomaly_db(file_path)

        self.log.info("Extracted a total of %d anomaly entries", len(self.results))
