# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional, Union

from mvt.common.utils import convert_unix_to_iso
from .base import AndroidExtraction

CONTEXT_LOG_PATH = [
    "data/data/com.samsung.android.lool/databases/sm.db",
]
class SMLog(AndroidExtraction):
    """This module extracts information from the
    sm db."""

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
        if record["entry_type"] == "appFreezer":
            sm_log_data = f"Package \'{record['package_name']}\' has been reset (id:\'{record['_id']}\')"
            records = [
                {
                    "timestamp": record["resetTime"],
                    "module": self.__class__.__name__,
                    "event": "Package_Reset",
                    "data": sm_log_data,
                }
            ]
            if record.get("lastUsedTime"):
                sm_log_data = f"Package {record['package']} has been used for the last time" 
                records.append(
                {
                    "timestamp": record["lastUsedTime"],
                    "module": self.__class__.__name__,
                    "event": "Package_last_use",
                    "data": sm_log_data,
                })
            return records

        elif record["entry_type"] == "History":
            history_data = f"Package \'{record['package_name']}\' has sent or received a notification."
            records = [
                {
                    "timestamp": record["notificationTime"],
                    "module": self.__class__.__name__,
                    "event": "History",
                    "data": history_data,
                }
            ]
            return records


        elif record["entry_type"] == "AppIssueHistory":
            app_issue_data = f"Package \'{record['package_name']}\' has encountered a type \'{record['anomaly_type']}\' with action \'{record['action_type']}." 
            records = [
                {
                    "timestamp": record["detect_time"],
                    "module": self.__class__.__name__,
                    "event": "AppIssueHistory",
                    "data": app_issue_data,
                }
            ]
            return records

        elif record["entry_type"] == "Logging":
            logging_data = f"Key: \'{record['key']}\' (id: \'{record['_id']})\' value is: \'{record['value']}\' " 
            records = [
                {
                    "timestamp": record["timeStamp"],
                    "module": self.__class__.__name__,
                    "event": "Logging",
                    "data": logging_data,
                }
            ]
            return records

        elif record["entry_type"] == "MalwareNotified":
            return 

        elif record["entry_type"] == "crash_info":
            crashinfo_data = f"Package \'{record['package_name']}\' has crashed (Type: \'{record['crash_type']}\')" 
            records = [
                {
                    "timestamp": record["crash_time"],
                    "module": self.__class__.__name__,
                    "event": "Package_Crash",
                    "data": crashinfo_data,
                }
            ]
            return records

    def check_indicators(self) -> None:
        if not self.indicators:
            return
        for result in self.results:
            ioc = self.indicators.check_app_id(result.get("package_name"))
            if ioc:
                self.log.warning("Malicious app id detected : %s !", result.get("package_name"))
                result["matched_indicator"] = ioc
                self.detected.append(result)
 
    # parse sm history
    def process_sm_history_file(self, path):
        conn = self._open_sqlite_db(path)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                *
            FROM History;
        """)
        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                if headings[index] == "notificationTime":
                    entry[headings[index]] = convert_unix_to_iso(float(value/1000))
                else:
                    entry[headings[index]] = value
            self.results.append(entry)
            entry["entry_type"] = "History"
        conn.close()

    # parse sm logging
    def process_sm_logging_file(self, path):
        conn = self._open_sqlite_db(path)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                *
            FROM Logging;
        """)
        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                if headings[index] == "timeStamp":
                    entry[headings[index]] = convert_unix_to_iso(float(value/1000))
                else:
                    entry[headings[index]] = value
            self.results.append(entry)
            entry["entry_type"] = "Logging"
        conn.close()

    # parse appFreezer
    def process_sm_appfreezer_file(self, path):
        conn = self._open_sqlite_db(path)
        cur = conn.cursor()
        
        table_exists = cur.execute("""
                SELECT name FROM sqlite_sequence  where name ='AppFreezer';
            """).fetchall()

        if table_exists ==[]:
            return
        else:
            cur.execute("""
                SELECT
                   *
                FROM AppFreezer;
            """)
            rows = list(cur)
            headings = [description[0] for description in cur.description]
            for row in rows:
                entry = {}
                for index, value in enumerate(row):

                    if headings[index] == "resetTime":
                        if value is None:
                            entry[headings[index]] = "1970-01-01 00:00:00"
                        else:
                            entry[headings[index]] = convert_unix_to_iso(float(int(value)/1000))
                    else:
                        entry[headings[index]] = value
                self.results.append(entry)
                entry["entry_type"] = "appFreezer"

        conn.close()

    # parse 
    def process_sm_malware_notified_file(self, path):
        conn = self._open_sqlite_db(path)
        cur = conn.cursor()
        
        table_exists = cur.execute("""
                SELECT name FROM sqlite_sequence  where name ='MalwareNotified';
            """).fetchall()
        
        if table_exists ==[]:
            return
        else:
            
            cur.execute("""
                SELECT
                   *
                FROM MalwareNotified;
            """)
            rows = list(cur)
            headings = [description[0] for description in cur.description]
            for row in rows:
                entry = {}
                for index, value in enumerate(row):

                    entry[headings[index]] = value
                self.results.append(entry)
                entry["entry_type"] = "MalwareNotified"

        conn.close()

    # parse AppIssueHistory
    def process_sm_appissuehistory_file(self, path):
        conn = self._open_sqlite_db(path)
        cur = conn.cursor()
        table_exists = cur.execute("""
                SELECT name FROM sqlite_sequence  where name ='AppIssueHistory';
            """).fetchall()
        
        if table_exists ==[]:
            return
        else:
            
            cur.execute("""
                SELECT
                   *
                FROM AppIssueHistory;
            """)
            rows = list(cur)
            headings = [description[0] for description in cur.description]
            for row in rows:
                entry = {}
                for index, value in enumerate(row):
                    if headings[index] == "timeStamp":
                        entry[headings[index]] = convert_unix_to_iso(float(value/1000))
                    else:

                        entry[headings[index]] = value
                self.results.append(entry)
                entry["entry_type"] =" AppIssueHitory"

        conn.close()


    # parse CrashInfo
    def process_sm_crashinfo_file(self, path):
        conn = self._open_sqlite_db(path)
        cur = conn.cursor()
        
        table_exists = cur.execute("""
                SELECT name FROM sqlite_sequence  where name ='crash_info';
            """).fetchall()
        
        if table_exists ==[]:
            return
        else:
            
            cur.execute("""
                SELECT
                   *
                FROM crash_info;
            """)
            rows = list(cur)
            headings = [description[0] for description in cur.description]
            for row in rows:
                entry = {}
                for index, value in enumerate(row):
                    if headings[index] == "crash_time":
                        entry[headings[index]] = convert_unix_to_iso(float(value/1000))
                    else:

                        entry[headings[index]] = value
                self.results.append(entry)
                entry["entry_type"] ="crash_info"

        conn.close()


    def run(self) -> None:
        for file_path in self._get_fs_files_from_patterns(CONTEXT_LOG_PATH):
            self.log.info("Processing sm file at %s", file_path)
            self.process_sm_appfreezer_file(file_path)
            self.process_sm_history_file(file_path)
            self.process_sm_logging_file(file_path)
            self.process_sm_malware_notified_file(file_path)
            self.process_sm_appissuehistory_file(file_path)
            self.process_sm_crashinfo_file(file_path)

        self.log.info("Extracted a total of %d entries", len(self.results))
