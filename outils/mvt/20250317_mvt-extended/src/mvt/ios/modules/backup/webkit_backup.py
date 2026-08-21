# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import re

from typing import Optional, Union

from ..base import IOSExtraction

WEBKIT_REL_PATHS = "Library/WebKit/WebsiteData/"

class WebKitBackup(IOSExtraction):
    """This module extracts information from the WebKit files."""

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
            "timestamp": record["modified"],
            "module": self.__class__.__name__,
            "event": "webkit_backup",
            "data": f"URL {record['url']} was visited",
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_url(result["url"])
            if ioc:
                self.log.warning("Malicious domain %s was visited on %s", result["url"], result["modified"])
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def _extract_ps_data(self, content):
        self.results += content

    def run(self) -> None:
        found_backup_paths = self._get_backup_files_from_manifest_pattern(relative_path_pattern=WEBKIT_REL_PATHS)
        for found_backup_path in found_backup_paths:
            found_path = found_backup_path["relative_path"]

            name_match = re.match(r'^Library/WebKit/WebsiteData/.*(http[^/]+).*$', found_path)

            if not name_match:
                continue
            
            name = name_match.group(1)
            name = name.replace("http_", "http://")
            name = name.replace("https_", "https://")
            url = name.split("_")[0]

            backup_metadata = self._get_backup_metadata_from_id(found_backup_path["file_id"])
            
            entry = {
                "folder": found_path,
                "url": url
            }
            entry.update(backup_metadata)

            self.results.append(entry)
        self.log.info("Extracted a total of %d WebKit records",
                      len(self.results))