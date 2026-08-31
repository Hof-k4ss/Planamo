# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.common.webkit_blob_parser import parse_blob
from mvt.common.utils import convert_datetime_to_iso, trim_prefix

from typing import Union

from ..base import IOSExtraction

WEBKIT_BLOB_ROOT_PATHS = [
    "private/var/*/Library/Caches/*/WebKit/NetworkCache/Version*/Records/*/Resource/*",
    "private/var/*/Library/Caches/*/WebKit/NetworkCache/Version*/Blobs/*",
]

class WebKitBlob(IOSExtraction):
    """This class parses request / response blobs."""

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for item in self.results:
            if item["process"] == "com.apple.imtranscoding.IMTranscoderAgent":
                self.log.warning("Malicious process %s visited %s on %s", item["process"], item["isodate"], item["domain"])
                item["matched_indicator"] = "com.apple.imtranscoding.IMTranscoderAgent"
                self.detected.append(item)

            ioc = self.indicators.check_process(item["process"])
            if ioc:
                self.log.warning("Malicious process %s visited %s on %s", item["process"], item["isodate"], item["domain"])
                item["matched_indicator"] = ioc
                self.detected.append(item)

            ioc = self.indicators.check_url(item["url"])
            if ioc:
                self.log.warning("Malicious url %s was visited on %s by %s", item["url"], item["isodate"], item["process"])
                item["matched_indicator"] = ioc
                self.detected.append(item)

    def serialize(self, record: dict) -> Union[dict, list]:
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "webkit-blob",
            "data": f"WebKit blob ({record['path']}) recorded a visit to {record['url']}",
        }
    
    def _parse_webkit_data(self) -> None:
        try:
            entry = parse_blob(self.file_path)
        except Exception as e:
            self.log.error(e)
            return
        entry["path"] = trim_prefix(entry["path"], self.target_path)
        entry["process"] = trim_prefix(self.file_path, self.target_path).split("/")[5]
        entry["isodate"] = convert_datetime_to_iso(entry.get("timestamp", ""))
        self.results.append(entry)
                
    def run(self) -> None:
        for file_path in self._get_fs_files_from_patterns(WEBKIT_BLOB_ROOT_PATHS):
            self.file_path = file_path
            self._parse_webkit_data()
        self.log.info("Extracted a total of %d WebKit records",
                      len(self.results))
