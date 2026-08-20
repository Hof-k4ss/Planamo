# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os
import re

from ..base import IOSExtraction


class WebkitBase(IOSExtraction):
    """This class is a base for other WebKit-related modules."""

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_url(result["url"])
            if ioc:
                self.log.warning("Malicious domain %s was visited on %s", result["url"], result["isodate"])
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def _process_webkit_folder(self, root_paths) -> None:
        for found_path in self._get_fs_files_from_patterns(root_paths):
            name_match = re.search(r'(http[^/]+).*$', os.path.basename(found_path))

            if not name_match:
                continue
            
            name = name_match.group(1)
            name = name.replace("http_", "http://")
            name = name.replace("https_", "https://")
            url = name.split("_")[0]

            self.results.append({
                "path": os.path.relpath(found_path, self.target_path),
                "url": url,
                "isodate": self._get_file_last_modified_time(found_path)}
                )