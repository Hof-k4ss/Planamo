# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import datetime
import logging
import os

from typing import Optional, Union

from mvt.common.utils import recursive_resolve
import mvt.common.ccl_bplist as ccl_bplist

from ..base import IOSExtraction


USERNOTIFICATIONS_REL_PATHS = "Library/UserNotifications/%/%.plist"

USERNOTIFICATIONS_FILE_PATH = [
    "private/var/mobile/Library/UserNotifications/*/*.plist"
]

USERNOTIFICATIONSSERVER_FILE_PATH = [
    "private/var/mobile/Library/UserNotificationsServer/Library.plist"
]


class UserNotifications(IOSExtraction):
    """This module extracts information from the UserNotifications files."""

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
    
    def find_suspicious(self) -> None:
        for record in self.results:
            first_ts = ""
            count = 1
            for key, value in record.items():
                for record_item in value:
                    if isinstance(record_item, dict) and record_item.get("AppNotificationCreationDate") and record_item.get("AppNotificationMessage") and record_item.get("AppNotificationTitle"):
                        ts = datetime.datetime.strptime(record_item["AppNotificationCreationDate"],"%Y-%m-%d %H:%M:%S.%f")
                        if first_ts == "": first_ts = ts
                        diff = abs((first_ts-ts).total_seconds())
                        if diff < 60:
                            if diff != 0.0: count += 1
                        else:
                            if count >= 20:
                                self.log.warning("Received %d notifications from %s in 60 seconds on %s", count, key, datetime.datetime.strftime(first_ts,"%Y-%m-%d %H:%M:%S.%f"))
                            first_ts = ts
                            count = 1
                        if record_item.get("IconApplicationIdentifier") == "com.apple.Preferences" or record_item.get("IconApplicationIdentifier") == "com.apple.findmy" or record_item.get("AppNotificationTitle") == "Blocage (mode Isolement)":
                            self.log.warning("\"%s\" : \"%s\" (by \"%s\") on %s", record_item.get("AppNotificationTitle", ""), record_item.get("AppNotificationMessage", ""), record_item.get("IconApplicationIdentifier", ""), ts)
    
    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            for key in list(result.keys()).copy():
                for ioc in self.indicators.get_iocs("domains"):
                    if ioc["value"] in str(result[key]):
                        result["matched_indicator"] = ioc
                        if result not in self.detected:
                            self.log.warning("Found mention of a malicious domain \"%s\" in \"%s\" file",
                                             ioc["value"], key)
                            self.detected.append(result)
                for ioc in self.indicators.get_iocs("emails"):
                    if ioc["value"] in str(result[key]):
                        result["matched_indicator"] = ioc
                        if result not in self.detected:
                            self.log.warning("Found mention of a known malicious email \"%s\" in \"%s\" file",
                                             ioc["value"], key)
                            self.detected.append(result)

    def serialize(self, record: dict) -> Union[dict, list]:
        entries = []
        for key, value in record.items():
            for record in value:
                if isinstance(record, dict) and record.get("AppNotificationCreationDate") and record.get("AppNotificationMessage") and record.get("AppNotificationTitle"):
                    entries.append({
                        "timestamp": record["AppNotificationCreationDate"],
                        "module": self.__class__.__name__,
                        "event": "push_notification_received",
                        "data": f"Notification from {key}. Title : '{record['AppNotificationTitle']}' and message : '{record['AppNotificationMessage']}'"
                    })
        return(entries)
    
    def _extract_bundle_data(self, handle) -> None:
        plist = ccl_bplist.load(handle)
        ns_keyed_archiver_obj = ccl_bplist.deserialise_NsKeyedArchiver(plist, parse_whole_structure=True)
        return(recursive_resolve(ns_keyed_archiver_obj))

    def _extract_notification_data(self, handle) -> None:
        plist = ccl_bplist.load(handle)
        ns_keyed_archiver_obj = ccl_bplist.deserialise_NsKeyedArchiver(plist, parse_whole_structure=True)
        entries = recursive_resolve(ns_keyed_archiver_obj)
        if entries != {} and entries != [] and entries != "": self.results.append({self.bundle_name : entries})

    def run(self) -> None:

        self.bundle_data = {}

        if self.is_backup:
            for usernotifications_file in self._get_backup_files_from_manifest_pattern(relative_path_pattern=USERNOTIFICATIONS_REL_PATHS):
                usernotifications_file_path = self._get_backup_file_from_id(usernotifications_file["file_id"])
                if not usernotifications_file_path:
                    continue
                self.file_path = usernotifications_file_path
                self.file_name = os.path.basename(self.file_path).rstrip(".plist")
                self.bundle_name = usernotifications_file["domain"] + " / " + usernotifications_file["relative_path"]
                with open(self.file_path, "rb") as handle:
                    self._extract_notification_data(handle)
            
        elif self.is_fs_dump:
            for file_path in self._get_fs_files_from_patterns(USERNOTIFICATIONSSERVER_FILE_PATH):
                self.file_path = file_path
                with open(self.file_path, "rb") as handle:
                    self.bundle_data.update(self._extract_bundle_data(handle))
            
            self.bundle_data = {v: k for k, v in self.bundle_data.items()}

            for file_path in self._get_fs_files_from_patterns(USERNOTIFICATIONS_FILE_PATH):
                self.file_path = file_path
                self.file_name = os.path.basename(self.file_path).rstrip(".plist")
                if not self.file_name.startswith("._"):
                    self.bundle_id = self.file_path.split("/")[-2]
                    self.bundle_name = self.bundle_data[self.bundle_id] if self.bundle_data.get(self.bundle_id) else self.bundle_id
                    with open(self.file_path, "rb") as handle:
                        self._extract_notification_data(handle)

        self.log.info("Extracted information on %d UserNotifications files", len(self.results))
        self.find_suspicious()