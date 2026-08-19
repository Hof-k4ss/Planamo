# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
from io import BytesIO
from struct import unpack
from typing import Optional, Union

from mvt.common.utils import convert_unix_to_iso
from .base import AndroidExtraction

class Filesystem(AndroidExtraction):
    """This module extracts creation and modification date of files from a
    full file-system dump.
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
        if record.get("modified"):
            return {
                "timestamp": record["modified"],
                "module": self.__class__.__name__,
                "event": "entry_modified",
                "data": record["path"],
            }
        elif record.get("accessed"):
            return {
                "timestamp": record["accessed"],
                "module": self.__class__.__name__,
                "event": "entry_accessed",
                "data": record["path"],
            }
        elif record.get("changed"):
            return {
                "timestamp": record["changed"],
                "module": self.__class__.__name__,
                "event": "entry_changed",
                "data": record["path"],
            }
        elif record.get("birth"):
            return {
                "timestamp": record["birth"],
                "module": self.__class__.__name__,
                "event": "entry_birth",
                "data": record["path"],
            }

    def check_indicators(self) -> None:
        if not self.indicators:
            return


        for result in self.results:
            if "path" not in result:
                continue

            if result["path"].endswith("/.bash_history"):
                self.log.warning("Presence of a .bash_history file %s (UTC)", result)


            ioc = self.indicators.check_file_path_process(result["path"])
            if ioc:
                self.log.warning("Found known suspicious process name mentioned in file at path \"%s\" matching indicators from \"%s\"",
                    result["path"], ioc["name"])
                result["matched_indicator"] = ioc
                self.detected.append(result)
    
    def run(self) -> None:
        if not self.is_archive:
            for root, dirs, files in os.walk(self.target_path):
                for dir_name in dirs:
                    try:
                        dir_path = os.path.join(root, dir_name)
                        result = {
                            "path": os.path.relpath(dir_path, self.target_path),
                            "modified": self._get_file_last_modified_time(dir_path),
                        }
                    except Exception:
                        continue
                    else:
                        self.results.append(result)

                for file_name in files:
                    try:
                        file_path = os.path.join(root, file_name)
                        result = {
                            "path": os.path.relpath(file_path, self.target_path),
                            "modified": self._get_file_last_modified_time(file_path),
                        }
                    except Exception:
                        continue
                    else:
                        self.results.append(result)
        else:
            archive_members = self.archive_members
            for archive_member in archive_members:
                if self.archive_type == "tar":
                    result = {
                        "path": archive_member.name,
                        "modified": convert_unix_to_iso(archive_member.mtime),
                    }
                    self.results.append(result)
                elif self.archive_type == "zip":
                    extra = BytesIO(archive_member.extra)
                    dhdr, dsz, dflag, mtime, atime, ctime, btime = unpack("<2sHB4I", extra.read(21))
                    result_mtime = {
                        "path": archive_member.filename,
                        "modified": convert_unix_to_iso(mtime),
                    }
                    self.results.append(result_mtime)
                    result_atime = {
                        "path": archive_member.filename,
                        "accessed": convert_unix_to_iso(atime),
                    }
                    self.results.append(result_atime)
                    result_ctime = {
                        "path": archive_member.filename,
                        "changed": convert_unix_to_iso(ctime),
                    }
                    self.results.append(result_ctime)
                    result_btime = {
                        "path": archive_member.filename,
                        "birth": convert_unix_to_iso(btime),
                    }
                    self.results.append(result_btime)
        self.log.info("Processed %d files", len(self.results))
