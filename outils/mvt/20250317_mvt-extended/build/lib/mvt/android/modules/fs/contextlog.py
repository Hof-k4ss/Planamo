# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional, Union

from mvt.common.utils import convert_unix_to_iso
from .base import AndroidExtraction

CONTEXT_LOG_PATH = [
    "data/data/com.samsung.android.providers.context/databases/ContextLog.db",
]
class ContextLog(AndroidExtraction):
    """This module extracts information from the
    contexLog db."""

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
        if record["entry_type"] == "use_app":
            records = [
                {
                    "timestamp": record["starttime"],
                    "module": self.__class__.__name__,
                    "event": "sub_app_started",
                    "data": f"Package {record['app_id']} with sub app {record['app_sub_id']} started.",
                }
            ]
            if record.get("stoptime"):
                records.append(
                {
                    "timestamp": record["stoptime"],
                    "module": self.__class__.__name__,
                    "event": "sub_app_stopped",
                    "data": f"Package {record['app_id']} with sub app {record['app_sub_id']} stopped." ,
                })
            return records

        elif record["entry_type"] == "manage_app":
            records = [
                {
                    "timestamp": record["timestamp"],
                    "module": self.__class__.__name__,
                    "event": "app_management",
                    "data": f"Package  {record['installed_app_id']}  with id \'{record['_id']}\' has been {record['verification']}.",
                }
            ]
            return records

    def check_indicators(self) -> None:
        if not self.indicators:
            return
        for result in self.results:
            ioc = self.indicators.check_app_id(result.get("doc_id"))
            if ioc:
                self.log.warning("Malicious app id detected : %s", result.get("doc_id"))
                result["matched_indicator"] = ioc
                self.detected.append(result)
 
    # parse use_app
    def process_context_log_file(self, path):
        conn = self._open_sqlite_db(path)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                *
            FROM use_app;
        """)
        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                if headings[index] == "starttime" or headings[index] == "stoptime":
                    entry[headings[index]] = convert_unix_to_iso(float(value/1000))
                else:
                    entry[headings[index]] = value
            self.results.append(entry)
            entry["entry_type"] = "use_app"
        conn.close()

    # parse manage_app
    def process_manage_app_file(self, path):
        conn = self._open_sqlite_db(path)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                *
            FROM manage_app;
        """)
        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                if headings[index] == "timestamp":
                    if value is None:
                        entry[headings[index]] = "1970-01-01 00:00:00"
                    else:
                        entry[headings[index]] = convert_unix_to_iso(float(value/1000))
                else:
                    entry[headings[index]] = value
            self.results.append(entry)
            entry["entry_type"] = "manage_app"

        conn.close()


    def run(self) -> None:
        for file_path in self._get_fs_files_from_patterns(CONTEXT_LOG_PATH):
            self.log.info("Processing ContextLog file at %s", file_path)
            self.process_context_log_file(file_path)
            self.process_manage_app_file(file_path)

        self.log.info("Extracted a total of %d entries", len(self.results))
