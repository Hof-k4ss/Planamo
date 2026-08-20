# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional, Union

from mvt.common.utils import check_for_links, convert_unix_to_iso
from .base import AndroidExtraction

SMS_DB_PATH = [
    "data/user/0/com.android.providers.telephony/databases/mmssms.db",
    "data/user_de/0/com.android.providers.telephony/databases/mmssms.db",
    "data/data/com.android.providers.telephony/databases/mmssms.db",
]
class SMS(AndroidExtraction):
    """This module extracts information from the
    sms.db database."""

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
        text = record["body"].replace("\n", "\\n")
        sms_data = f"{record['creator']}: {record['_id']} \"{text}\" from {record['address']} ({record['service_center']})"
        records = [
            {
                "timestamp": record["date"],
                "module": self.__class__.__name__,
                "event": "sms_received",
                "data": sms_data,
            }
        ]
        # If the message was sent, we add an extra event.
        if record.get("date_sent"):
            records.append(
            {
                "timestamp": record["date_sent"],
                "module": self.__class__.__name__,
                "event": "sms_emitted",
                "data": sms_data,
            })
        return records

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for message in self.results:
            if "body" not in message:
                continue

            message_links = message.get("links", [])
            if message_links == []:
                message_links = check_for_links(message.get("text", ""))
                
            if self.indicators.check_urls(message_links):
                self.detected.append(message)
    
    def process_sms_file(self, path):
        conn = self._open_sqlite_db(path)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                *
            FROM sms;
        """)
        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                if headings[index] == "date" or headings[index] == "date_sent":
                    entry[headings[index]] = convert_unix_to_iso(float(value/1000))
                else:
                    entry[headings[index]] = value

            # Extract links from the SMS message.
            message_links = check_for_links(entry.get("body", ""))
            entry["links"] = message_links

            self.results.append(entry)
            
        conn.close()

    def run(self) -> None:
        for file_path in self._get_fs_files_from_patterns(SMS_DB_PATH):
            self.log.info("Processing SMS file at %s", file_path)
            self.process_sms_file(file_path)

        self.log.info("Extracted a total of %d SMS & MMS messages", len(self.results))
