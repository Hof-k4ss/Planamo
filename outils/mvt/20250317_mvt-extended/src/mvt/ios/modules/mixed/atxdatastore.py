# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import liblzfse
import logging
import os
import sqlite3
import tempfile
from typing import Optional, Union

from mvt.common.utils import convert_mactime_to_iso, recursive_resolve

from ..base import IOSExtraction

ATXDATASTORE_BACKUP_IDS = "47fc2666c2f803f1fd3185e6b569d32060fa7451"

ATXDATASTORE_ROOT_PATHS = ["private/var/mobile/Library/DuetExpertCenter/_ATXDataStore.db"]


class ATXDataStore(IOSExtraction):
    """This module extracts entries from AtxDataStore.db."""

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
        if record.get("sourceTable", "") == "suggested":
            record["isodate"] = convert_mactime_to_iso(record["ts"])
            return {
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": "suggested",
                "data": f"Suggestion of {record['name']}"
            }
        elif record.get("sourceTable", "") == "messageRecipients":
            record["isodate"] = convert_mactime_to_iso(record["lastDateMessaged"])
            return {
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": "messaged",
                "data": f"Last message sent to {record['recipientName']}"
            }
        elif record.get("sourceTable", "") == "appLaunchSequence":
            record["isodate"] = convert_mactime_to_iso(record["launchDate"])
            return {
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": "app_launch_sequence",
                "data": f"Launch of {record['bundleId']}"
            }
        elif record.get("sourceTable", "") == "appInfo":
            returned = []
            if record.get("installDate", None) and record.get("installDate", "") != 1:
                record["isodate"] = convert_mactime_to_iso(record["installDate"])
                returned.append ({
                    "timestamp": record["isodate"],
                    "module": self.__class__.__name__,
                    "event": "app_info_install",
                    "data": f"Installation of {record['bundleId']}"
                })
            if record.get("lastLaunchDate", None) and record.get("lastLaunchDate", "") != 1:
                record["isodate"] = convert_mactime_to_iso(record["lastLaunchDate"])
                returned.append ({
                    "timestamp": record["isodate"],
                    "module": self.__class__.__name__,
                    "event": "app_info_last_launch_date",
                    "data": f"Last launch date of {record['bundleId']}"
                })
            if record.get("lastSpotlightLaunchDate", None) and record.get("lastSpotlightLaunchDate", "") != 1:
                record["isodate"] = convert_mactime_to_iso(record["lastSpotlightLaunchDate"])
                returned.append ({
                    "timestamp": record["isodate"],
                    "module": self.__class__.__name__,
                    "event": "app_info_last_spotlight_launch_date",
                    "data": f"Last Spotlight launch date of {record['bundleId']}"
                })
            return returned
        elif record.get("sourceTable", "") == "appActionInfo":
            record["isodate"] = convert_mactime_to_iso(record["lastAppActionLaunchDate"])
            return {
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": "app_action_info",
                "data": f"Last app action launch date for {record['appAction']}"
            }
        elif record.get("sourceTable", "") == "anchorOccurrence_parsed":
            record["isodate"] = convert_mactime_to_iso(record["anchorDate"])
            return {
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": "anchor_occurence",
                "data": f"{record['description']} : {record['anchorEventIdentifier']}"
            }
        elif record.get("sourceTable", "") == "alog_parsed":
            returned = []
            if record.get("date", None) and record.get("date", "") != 1:
                record["isodate"] = convert_mactime_to_iso(record["date"])
                returned.append ({
                    "timestamp": record["isodate"],
                    "module": self.__class__.__name__,
                    "event": "alog_date",
                    "data": f"{record['bundleId']} : {record['actionType']}"
                })
            if record.get("appSessionStartDate", None) and record.get("appSessionStartDate", "") != 1:
                record["isodate"] = convert_mactime_to_iso(record["appSessionStartDate"])
                returned.append ({
                    "timestamp": record["isodate"],
                    "module": self.__class__.__name__,
                    "event": "alog_session_start_date",
                    "data": f"{record['bundleId']} : {record['actionType']}"
                })
            if record.get("appSessionEndDate", None) and record.get("appSessionEndDate", "") != 1:
                record["isodate"] = convert_mactime_to_iso(record["appSessionEndDate"])
                returned.append ({
                    "timestamp": record["isodate"],
                    "module": self.__class__.__name__,
                    "event": "alog_session_end_date",
                    "data": f"{record['bundleId']} : {record['actionType']}"
                })
            return returned
        return

    def _find_suspicious_entries(self):
        for result in self.results:
            if result.get("sourceTable", "") == "appInfo":
                    if result.get("bundleId", "") is None or result.get("bundleId", "") == "":
                        self.log.warning("Empty bundleId in table appInfo : %s", result)
                    if result.get("isEnterpriseApp", "") is not None and result.get("isEnterpriseApp", "") != "" and result.get("isEnterpriseApp", "") != 0:
                        self.log.warning("Enterprise app in table appInfo : %s", result)

    def check_indicators(self) -> None:
        self._find_suspicious_entries()
        if not self.indicators:
            return

        for result in self.results:
            for key,value in result.copy().items():
                if isinstance(value, str):
                    if ("tmp" in value or "bd_tool" in value) and result not in self.detected:
                        self.log.warning("Found a suspicious process in AtxDataStore.db (tmp* / bd_tool*) %s : \"%s\"", key, value)

                    ioc = self.indicators.check_process(value)
                    if ioc:
                        result["matched_indicator"] = ioc
                        if  result not in self.detected:
                            self.log.warning("Found a malicious process in AtxDataStore.db %s : \"%s\" ", key, value)
                            self.detected.append(result)
    
    def _process_atxdatastore_backup_file(self, file_path):
        if not os.path.exists(file_path):
            return
        with open(file_path, "rb") as handle:
            atxdatastore_backup_file = handle.read()
        bvx2file = atxdatastore_backup_file[len(atxdatastore_backup_file.split(b"bvx")[0]):]
        decompressed_file = liblzfse.decompress(bvx2file)
        temp_dir = tempfile.TemporaryDirectory()
        temp_file_path = os.path.join(temp_dir.name, "temp")
        with open(temp_file_path, "wb") as f:
            f.write(decompressed_file)
        self._process_atxdatastore_file(temp_file_path)
        temp_dir.cleanup()

    def _process_atxdatastore_file(self, file_path):
        """
        Parse the AtxDataStore.db database
        """
        conn = self._open_sqlite_db(file_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                name
            FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != '_SqliteDatabaseProperties';
        """)
        rows = list(cur)
        for row, in rows:
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM '" + row + "'")
                rows_for_row = list(cur)
            except sqlite3.DatabaseError:
                self.log.warning("AtxDataStore database at path %s is probably malformed, skipping it.", file_path)
                return
            headings = [description[0] for description in cur.description]
            for row_for_row in rows_for_row:
                entry = {}
                for index, value in enumerate(row_for_row):
                    if isinstance(value, (bytes, bytearray)):
                        entry[headings[index]] = recursive_resolve(value)
                    else:
                        entry[headings[index]] = value
                entry["sourceTable"] = row
                self.results.append(entry)

        # Join for anchor*
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT
                    *
                FROM anchorOccurrence, anchorType
                WHERE anchorOccurrence.anchorType = anchorType.name;
            """
            )
        except sqlite3.DatabaseError as e:
            self.log.warning("AtxDataStore database at path %s is probably malformed, skipping it. %s", file_path, e)
            return

        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                entry[headings[index]] = value
            entry["sourceTable"] = "anchorOccurrence_parsed"
            self.results.append(entry)

         # Join for alog*
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT
                    alog.id AS id,
                    alogBundleId.bundleId AS bundleId,
                    alogAction.actionType as actionType,
                    alog.date as date,
                    alog.appSessionStartDate as appSessionStartDate,
                    alog.appSessionEndDate as appSessionEndDate
                FROM alog, alogAction, alogBundleId
                WHERE alogAction.id = alog.actionType AND alogBundleId.id = alog.bundleId
            """
            )
        except sqlite3.DatabaseError as e:
            self.log.warning("AtxDataStore database at path %s is probably malformed, skipping it. %s", file_path, e)
            return

        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                entry[headings[index]] = value
            entry["sourceTable"] = "alog_parsed"
            self.results.append(entry)
        cur.close()
        conn.close()

    def run(self) -> None:
        if self.is_backup:
            atxdatastore_backup_file = self._get_backup_file_from_id(ATXDATASTORE_BACKUP_IDS)
            if atxdatastore_backup_file:
                self.file_path = atxdatastore_backup_file
                self.log.info("Found AtxDataStore database at path: %s", self.file_path)
                self._process_atxdatastore_backup_file(self.file_path)
        elif self.is_fs_dump:
            for atxdatastore_file in self._get_fs_files_from_patterns(ATXDATASTORE_ROOT_PATHS):
                self.file_path = atxdatastore_file
                self.log.info("Found AtxDataStore database at path: %s", self.file_path)
                self._process_atxdatastore_file(self.file_path)

        self.log.info("Extracted a total of %d AtxDataStore entries", len(self.results))
