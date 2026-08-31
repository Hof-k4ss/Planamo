# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import operator
import os
import re
from typing import Optional, Union

from ..base import IOSExtraction

SMS_ATTACHMENTS_FOLDERS_BACKUP_RELPATH = "Library/SMS/Attachments/*"

SMS_ROOT_PATHS = [
    "private/var/mobile/Library/SMS/Attachments/",
]


class SMSAttachmentsFolder(IOSExtraction):
    """This module extracts all info about SMS/iMessage attachments."""

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
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "sms_attachments_folders",
            "data": f"Empty attachments folder in {record['path']}",
        }

    def _find_suspicious(self) -> None:
        for result in sorted(self.results, key=operator.itemgetter("isodate")):
            self.log.warning("Empty attachments folder : \"%s\". Last modification date %s", result["path"], result["isodate"])

    def check_indicators(self) -> None:
        self._find_suspicious()
        return

    def run(self) -> None:
        if self.is_backup:
            sms_folders = list(self._get_backup_files_from_manifest(SMS_ATTACHMENTS_FOLDERS_BACKUP_RELPATH))
            if len(sms_folders) == 0:
                self.results.append(
                    {
                        "isodate": self._get_file_last_modified_time(SMS_ATTACHMENTS_FOLDERS_BACKUP_RELPATH),
                        "path": "/" + SMS_ROOT_PATHS[0]
                    }
                )
            else:
                for sms_folder in sms_folders:
                    if sms_folder["relative_path"].count("/") == 3:
                        second_level_folders = [sms_folder_match for sms_folder_match in sms_folders if sms_folder_match["relative_path"].startswith(sms_folder["relative_path"]+"/")]
                        if len(second_level_folders) == 0:
                            self.results.append(
                                {
                                    "isodate": self._get_file_last_modified_time("", file_id = sms_folder["file_id"]),
                                    "path": sms_folder["relative_path"]
                                }
                            )
                        else:
                            for second_level_folder in second_level_folders:
                                if second_level_folder["relative_path"].count("/") == 4:
                                    third_level_folders = [sms_folder_match for sms_folder_match in sms_folders if sms_folder_match["relative_path"].startswith(second_level_folder["relative_path"]+"/")]
                                    if len(third_level_folders) == 0:
                                        self.results.append(
                                            {
                                                "isodate": self._get_file_last_modified_time("", file_id = second_level_folder["file_id"]),
                                                "path": second_level_folder["relative_path"]
                                            }
                                        )
            
        elif self.is_fs_dump:
            if self.is_archive:
                sms_folders = [p for p in self.archive_names if re.match("^\/"+SMS_ROOT_PATHS[0]+".+$", p)]
                if len(sms_folders) == 0:
                    self.results.append(
                        {
                            "isodate": self._get_file_last_modified_time(os.path.join(self.target_path, SMS_ROOT_PATHS[0])),
                            "path": "/" + SMS_ROOT_PATHS[0] 
                        }
                    )
                else:
                    for sms_folder in sms_folders:
                        if re.match("^\/"+SMS_ROOT_PATHS[0]+"[^\/]+\/$", sms_folder):
                            second_level_folders = [sms_folder_match for sms_folder_match in sms_folders if re.match("^"+sms_folder+".+$", sms_folder_match)]
                            if len(second_level_folders) == 0:
                                self.results.append(
                                    {
                                        "isodate": self._get_file_last_modified_time(os.path.join(self.target_path, sms_folder)),
                                        "path": sms_folder
                                    }
                                )
                            else:
                                for second_level_folder in second_level_folders:
                                    if re.match(sms_folder+"[^\/]+\/$", second_level_folder):
                                        third_level_folders = [sms_folder_match for sms_folder_match in sms_folders if re.match("^"+second_level_folder+".+$", sms_folder_match)]
                                        if len(third_level_folders) == 0:
                                            self.results.append(
                                                {
                                                    "isodate": self._get_file_last_modified_time(os.path.join(self.target_path, second_level_folder)),
                                                    "path": second_level_folder
                                                }
                                            )
            else:
                root_folder = SMS_ROOT_PATHS[0]
                if os.path.exists(os.path.join(self.target_path, root_folder)):
                    sms_folders = os.listdir(os.path.join(self.target_path, root_folder))
                    if len(sms_folders) == 0:
                        self.results.append(
                            {
                                "isodate": self._get_file_last_modified_time(os.path.join(self.target_path, root_folder)),
                                "path": "/" + root_folder
                            }
                        )
                    else:
                        for sms_folder in sms_folders:
                            second_level_folders = os.listdir(os.path.join(self.target_path, root_folder, sms_folder))
                            if len(second_level_folders) == 0:
                                self.results.append(
                                    {
                                        "isodate": self._get_file_last_modified_time(os.path.join(self.target_path, root_folder, sms_folder)),
                                        "path": os.path.join(root_folder, sms_folder)
                                    }
                                )
                            else:
                                for second_level_folder in second_level_folders:
                                    third_level_folders = os.listdir(os.path.join(self.target_path, root_folder, sms_folder, second_level_folder))
                                    if len(third_level_folders) == 0:
                                        self.results.append(
                                            {
                                                "isodate": self._get_file_last_modified_time(os.path.join(self.target_path, root_folder, sms_folder, second_level_folder)),
                                                "path": os.path.join(root_folder, sms_folder, second_level_folder)
                                            }
                                        )