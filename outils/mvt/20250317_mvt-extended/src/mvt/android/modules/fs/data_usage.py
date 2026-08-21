# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import locale
import logging
import datetime

from typing import Optional, Union
from .base import AndroidExtraction

DATA_USAGE_DB_PATH = [
    "data/data/com.android.vending/databases/data_usage.db",
]
class DataUsage(AndroidExtraction):
    """This module extracts information from the
    data_usage.db database."""

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
        data_usage_data = f"Package {record['package_name']} made a network connection of type {record['connection_type']}."
        records = [
            {
                "timestamp": record["date"],
                "module": self.__class__.__name__,
                "event": "package_data_usage",
                "data": data_usage_data,
            }
        ]
     
        return records

    def check_indicators(self) -> None:
        # TODO
        if not self.indicators:
            return
    
    def process_data_usage_db(self, path):
        conn = self._open_sqlite_db(path)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                *
            FROM app_data_usage;
        """)
        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                if headings[index] == "date":
                    locale.setlocale(locale.LC_ALL, "C")
                    value = datetime.datetime.strptime(value, "%Y-%m-%d")
                    entry[headings[index]] = value.strftime("%Y-%m-%d %H:%M:%S.%f")
                else:
                    entry[headings[index]] = value
            self.results.append(entry)
        conn.close()

    def run(self) -> None:
        for file_path in self._get_fs_files_from_patterns(DATA_USAGE_DB_PATH):
            self.log.info("Processing data_usage database at %s", file_path)
            self.process_data_usage_db(file_path)

        self.log.info("Extracted a total of %d data_usage records", len(self.results))
