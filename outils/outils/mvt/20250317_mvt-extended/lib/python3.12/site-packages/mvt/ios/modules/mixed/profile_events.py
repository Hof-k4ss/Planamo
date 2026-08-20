# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import plistlib
from typing import Optional, Union

from mvt.common.utils import convert_datetime_to_iso

from ..base import IOSExtraction

CONF_PROFILES_EVENTS_RELPATH = "Library/ConfigurationProfiles/MCProfileEvents.plist"
CONF_PROFILES_EVENTS_PATH = [
    "private/var/containers/Shared/SystemGroup/systemgroup.com.apple.configurationprofiles/Library/ConfigurationProfiles/MCProfileEvents.plist",
    "private/var/mobile/Library/Logs/CrashReporter/DiagnosticLogs/sysdiagnose/*/logs/MCState/Shared/MCProfileEvents.plist"
]


class ProfileEvents(IOSExtraction):
    """This module extracts events related to the installation of configuration
    profiles.
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
            "timestamp": record.get("timestamp"),
            "module": self.__class__.__name__,
            "event": "profile_operation",
            "data": f"Process {record.get('process')} started operation "
            f"{record.get('operation')} of profile "
            f"{record.get('profile_id')}",
        }
    
    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_process(result.get("process"))
            if ioc:
                self.log.warning("On %s malicious process \"%s\" started operation \"%s\" of profile \"%s\"", result["timestamp"], ioc["value"], result["operation"], result["profile_id"])
                result["matched_indicator"] = ioc
                self.detected.append(result)
            ioc = self.indicators.check_profile(result.get("profile_id"))
            if ioc:
                self.log.warning("On %s process \"%s\" started operation \"%s\" of malicious profile \"%s\"", result["timestamp"], ioc["value"], result["operation"], result["profile_id"])
                result["matched_indicator"] = ioc
                self.detected.append(result)


    def _extract_data(self) -> None:
        with open(self.file_path, "rb") as handle:
            try:
                events_plist = plistlib.load(handle)
            except:
                events_plist = {}

        if "ProfileEvents" not in events_plist: return

        for event in events_plist["ProfileEvents"]:
            key = list(event.keys())[0]
            
            result = {
                "profile_id": key,
                "timestamp": "",
                "operation": "",
                "process": "",
            }

            for key, value in event[key].items():
                key = key.lower()
                if key == "timestamp":
                    result["timestamp"] = str(convert_datetime_to_iso(value))
                else:
                    result[key] = value

            if result not in self.results: 
                self.log.info(
                    'On %s process "%s" started operation "%s" of profile "%s"',
                    result.get("timestamp"),
                    result.get("process"),
                    result.get("operation"),
                    result.get("profile_id"),
                )
                self.results.append(result)

    def run(self) -> None:
        if self.is_backup:
            for events_file in self._get_backup_files_from_manifest(
                relative_path=CONF_PROFILES_EVENTS_RELPATH
            ):
                events_file_path = self._get_backup_file_from_id(events_file["file_id"])
                if not events_file_path:
                    continue
                self.log.info("Found MCProfileEvents.plist file at %s", events_file_path)
                self.file_path = events_file_path
                self._extract_data()

        elif self.is_fs_dump:
            for events_file_path in self._get_fs_files_from_patterns(CONF_PROFILES_EVENTS_PATH):
                self.file_path = events_file_path
                self._extract_data()

        self.log.info("Extracted %d profile events", len(self.results))
