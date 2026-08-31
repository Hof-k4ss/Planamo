# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import plistlib
from typing import Optional

from ..base import IOSExtraction

IMTRANSCODERAGENTPLIST_ROOT_PATHS = [
    "private/var/mobile/Library/Preferences/com.apple.imtranscoding.IMTranscoderAgent.plist",
]

class IMTranscoderAgent(IOSExtraction):
    """This module parses the com.apple.imtranscoding.IMTranscoderAgent.plist.


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

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            for key, value in result.copy().items():
                for ioc in self.indicators.get_iocs("processes"):
                    if ioc["value"] in str(key) or ioc["value"] in str(value):
                        self.log.warning("Found mention of a known malicious process : %s in %s", ioc["value"], key)
                        result["matched_indicator"] = ioc
                        self.detected.append(result)
                        break

    def run(self) -> None:
        for file_path in self._get_fs_files_from_patterns(IMTRANSCODERAGENTPLIST_ROOT_PATHS):
            self.file_path = file_path
            self.log.info("Found com.apple.imtranscoding.IMTranscoderAgent.plist at path: %s", self.file_path)

            with open(self.file_path, "rb") as handle:
                imtranscoderagent_plist = plistlib.load(handle)
                self.results.append(imtranscoderagent_plist)

            self.log.info("Extracted a total of %d IMTranscoderAgent items", len(self.results))
