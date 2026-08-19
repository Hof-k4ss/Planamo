# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
import sqlite3

from typing import Optional, Union

from mvt.common.utils import convert_mactime_to_iso

from ..base import IOSExtraction

HTTP_STORAGE_REL_PATHS = "/httpstorages.sqlite"
HTTP_STORAGE_ROOT_PATHS = [
    "private/var/*/Library/HTTPStorages/*/httpstorages.sqlite",
    "private/var/mobile/Containers/Data/*/*/Library/HTTPStorages/*/httpstorages.sqlite"
]


class HttpStorage(IOSExtraction):
    """This module extracts all entries from httpstorages.sqlite dabatases


    """

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
        return {
            "timestamp": record["creation_time"],
            "module": self.__class__.__name__,
            "event": "alt_entry",
            "data": f"Entry in {record['file']} for {record['host']} port {record['port']}",
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_url(result["host"])
            
            if not ioc:
                ioc = self.indicators.check_url(result["alternateHost"])
            
            if ioc:
                self.log.warning("Malicious entry in \"%s\" for \"%s\" or \"%s\" at %s, port %s", result["file"], result["host"], result["alternateHost"], result["creation_time"], result["port"])
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def _process_http_storage_db(self, http_storage_path) -> None:
        if (os.stat(http_storage_path).st_size == 0): return
        self._recover_sqlite_db_if_needed(http_storage_path)
        conn = self._open_sqlite_db(http_storage_path)
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT
                    *
                FROM alt_services;
            """)

        except sqlite3.OperationalError:
            return
        except sqlite3.DatabaseError:
            self.log.warning("File %s is probably malformed, skipping it.", http_storage_path)
            return

        for row in cur:
            entry = {
                "file": os.path.relpath(http_storage_path, self.target_path),
                "partition": row[0],
                "host": row[1],
                "alternateHost": row[2],
                "port": row[3],
                "alternatePort": row[4],
                "type": row[5],
                "creation_time": convert_mactime_to_iso(row[6], from_2001=False),
                "expires_time": convert_mactime_to_iso(row[7], from_2001=False)
            }
            if entry not in self.results: self.results.append(entry)

        cur.close()
        conn.close()

    def run(self) -> None:
        if self.is_backup:
            for http_storage_file in self._get_backup_files_from_manifest_pattern(relative_path_pattern=HTTP_STORAGE_REL_PATHS):
                http_storage = self._get_backup_file_from_id(http_storage_file["file_id"])
                if not http_storage:
                    continue

                self._process_http_storage_db(http_storage)
        elif self.is_fs_dump:
            for http_storage in self._get_fs_files_from_patterns(HTTP_STORAGE_ROOT_PATHS):
                self._process_http_storage_db(http_storage)

        self.log.info("Extracted a total of %d http storage records", len(self.results))