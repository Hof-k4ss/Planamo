# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional, Union

from mvt.common.utils import convert_unix_to_iso
from .base import AndroidExtraction

INTENT_BLOCKING_DB_PATH = [
    "data/data/com.sec.android.app.sbrowser/databases/intent_blocker.db",
]
class IntentBlocker(AndroidExtraction):
    """This module extracts information from the
    intent_blocker.db database."""

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
        intent_blocker_data = f"The package {record['app_name']} (Package: \'{record['name']}\') has contacted the URL: \'{record['url']}\'. Blocked: \'{record['blocked']}\'"
        records = [
            {
                "timestamp": record["date"],
                "module": self.__class__.__name__,
                "event": "URL_record",
                "data": intent_blocker_data,
            }
        ]
     
        return records

    def check_indicators(self) -> None:
        for result in self.results:
            if result["blocked"] == 1:
                self.log.warning("blocked URL detected: \"%s\"", result["url"])
                self.detected.append(result)


    def process_intent_blocker_db(self, path):
        conn = self._open_sqlite_db(path)
        cur = conn.cursor()

        cur.execute("""
            SELECT 
            * 
            FROM history 
            INNER JOIN package ON history.package_id = package.package_id;
        """)
        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                if headings[index] == "date":
                    entry[headings[index]] = convert_unix_to_iso(float(int(value)/1000))
                else:
                    entry[headings[index]] = value
            self.results.append(entry)
        conn.close()

    def run(self) -> None:
        for file_path in self._get_fs_files_from_patterns(INTENT_BLOCKING_DB_PATH):
            self.log.info("Processing intent_blocker db file at %s", file_path)
            self.process_intent_blocker_db(file_path)

        self.log.info("Extracted a total of %d Intent Blocking records", len(self.results))