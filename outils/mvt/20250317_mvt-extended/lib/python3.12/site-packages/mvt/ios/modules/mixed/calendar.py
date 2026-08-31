# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import sqlite3
from typing import Optional, Union

from mvt.common.utils import convert_mactime_to_iso

from ..base import IOSExtraction

CALENDAR_BACKUP_IDS = [
    "2041457d5fe04d39d0ab481178355df6781e6858",
]
CALENDAR_ROOT_PATHS = ["private/var/mobile/Library/Calendar/Calendar.sqlitedb"]


class Calendar(IOSExtraction):
    """This module extracts all calendar entries."""

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
        if record["description"]: record["description"] = record["description"].replace("\n", " ").replace("\r", " ")
        if record["location"]: record["location"] = record["location"].replace("\n", " ").replace("\r", " ")
        return {
            "timestamp": record["timestamp"],
            "module": self.__class__.__name__,
            "event": "calendar",
            "data": f"ID : {record['id']}, Entry : {record['summary']}, Description : {record['description']}, Location : {record['location']}, Participant : {record['participant']}, Type of event : {record['type']}",
        }

    def check_indicators(self) -> None:
        for result in self.results:
            participant = result.get("participant_email", result.get("participant", ""))  # support for legacy outputs
            if participant != "" and self.indicators:
                ioc = self.indicators.check_email(participant)
                if ioc:
                    result["matched_indicator"] = ioc
                    self.detected.append(result)
                    continue

            # Custom check for Quadream exploit
            if result["summary"] == "Meeting" and result["description"] == "Notes":
                self.log.warning(
                    "Potential Quadream exploit event identified: %s", result["uuid"]
                )
                self.detected.append(result)

    def _parse_calendar_db(self):
        """
        Parse the calendar database
        """
        conn = self._open_sqlite_db(self.file_path)
        cur = conn.cursor()

        cur.execute(
            """
        SELECT 
            CalendarItem.rowid, 
            CalendarItem.start_date, 
            CalendarItem.end_date, 
            CalendarItem.last_modified, 
            CalendarItem.summary, 
            Location.title, 
            Participant.email,
            CalendarItem.description
        FROM CalendarItem 
        LEFT JOIN Participant ON Participant.owner_id = CalendarItem.ROWID
        LEFT JOIN Location ON CalendarItem.location_id = Location.ROWID
        GROUP BY
            CalendarItem.rowid, 
            CalendarItem.start_date, 
            CalendarItem.end_date, 
            CalendarItem.last_modified, 
            CalendarItem.summary, 
            Location.title, 
            Participant.email,
            CalendarItem.description
        """)
        for row in cur:
            self.results.append({
                "id": row[0],
                "type": "start",
                "timestamp": convert_mactime_to_iso(row[1], True),
                "summary": row[4],
                "location": row[5],
                "participant": row[6],
                "description": row[7]
            })
            self.results.append({
                "id": row[0],
                "type": "end",
                "timestamp": convert_mactime_to_iso(row[2], True),
                "summary": row[4],
                "location": row[5],
                "participant": row[6],
                "description": row[7]
            })
            self.results.append({
                "id": row[0],
                "type": "last_modify_entry",
                "timestamp": convert_mactime_to_iso(row[3], True),
                "summary": row[4],
                "location": row[5],
                "participant": row[6],
                "description": row[7]
            })
        
        cur.close()
        conn.close()

    def run(self) -> None:
        self._find_ios_database(
            backup_ids=CALENDAR_BACKUP_IDS, root_paths=CALENDAR_ROOT_PATHS
        )
        self.log.info("Found calendar database at path: %s", self.file_path)

        self._parse_calendar_db()

        self.log.info("Extracted a total of %d calendar items", len(self.results))

