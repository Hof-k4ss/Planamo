# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional, Union

from mvt.common.utils import convert_unix_to_iso
from .base import AndroidExtraction

DOWNLOADS_DB_PATH = [
    "data/user/0/com.android.providers.downloads/databases/downloads.db",
    "data/data/com.android.providers.downloads/databases/downloads.db",
]
class Downloads(AndroidExtraction):
    """This module extracts information from the
    downloads.db database."""

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
        text = record['uri']
        downloads_data = f"The file {record['_data']} ({record['total_bytes']} bytes) with MimeType {record['mimetype']} downloaded from {record['uri']} has been last modified."
        records = [
            {
                "timestamp": record["lastmod"],
                "module": self.__class__.__name__,
                "event": "Downloaded_File_last_modification",
                "data": downloads_data,
            }
        ]
     
        return records

    def check_indicators(self) -> None:
        
        if not self.indicators:
            return

        for result in self.results:
            download_links = result.get("links", "")
            
            if self.indicators.check_url(download_links):
                self.detected.append(result)
    
    def process_download_db(self, path):
        conn = self._open_sqlite_db(path)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                *
            FROM downloads;
        """)
        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                if headings[index] == "lastmod":
                    entry[headings[index]] = convert_unix_to_iso(float(int(value)/1000))
                else:
                    entry[headings[index]] = value

            # Extract links from the uri.
            entry["links"] = entry.get("uri", "")
            self.results.append(entry)
        conn.close()

    def run(self) -> None:
        for file_path in self._get_fs_files_from_patterns(DOWNLOADS_DB_PATH):
            self.log.info("Processing downloads.db database at %s", file_path)
            self.process_download_db(file_path)

        self.log.info("Extracted a total of %d downloads records", len(self.results))
