# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional, Union

from mvt.common.utils import convert_unix_to_iso
from .base import AndroidExtraction

LIBRARY_DB_PATH = [
    "data/user/0/com.android.vending/databases/library.db",
]

class Library(AndroidExtraction):
    """This module extracts information from the
    library.db database."""

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
        library_data = f"App {record['doc_id']} was purchased with the account {record['account']}."
        records = [
            {
                "timestamp": record["purchase_time"],
                "module": self.__class__.__name__,
                "event": "app_purchase",
                "data": library_data,
            }
        ]
     
        return records

    def check_indicators(self) -> None:
        if not self.indicators:
            return
        for result in self.results:
            ioc = self.indicators.check_app_id(result.get("doc_id"))
            if ioc:
                
                result["matched_indicator"] = ioc
                self.detected.append(result)
    
    def process_library_db(self, path):
        conn = self._open_sqlite_db(path)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                *
            FROM ownership;
        """)
        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                if headings[index] == "purchase_time":
                    entry[headings[index]] = convert_unix_to_iso(float(int(value)/1000))
                else:
                    entry[headings[index]] = value
            self.results.append(entry)
        conn.close()

    def run(self) -> None:
        for file_path in self._get_fs_files_from_patterns(LIBRARY_DB_PATH):
            self.log.info("Processing library db file at %s", file_path)
            self.process_library_db(file_path)

        self.log.info("Extracted a total of %d library records", len(self.results))
