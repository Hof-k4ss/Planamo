# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import glob
import logging
import os
import sqlite3

from io import BytesIO
from mvt.common.utils import trim_prefix
from pathlib import PurePosixPath
from struct import unpack
from typing import Iterator, Optional

from mvt.common.utils import convert_unix_to_iso
from mvt.common.module import MVTModule


class AndroidExtraction(MVTModule):
    """This class provides a base for all Android filesystem/backup extraction
    modules."""

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

        self.is_backup = False
        self.is_fs_dump = False

    def _open_sqlite_db(self, file_path: str) -> sqlite3.Connection:
        if self.is_archive:
            return sqlite3.connect(f"file:{file_path}")
        else:
            return sqlite3.connect(f"file:{file_path}?immutable=1", uri=True)

    def _get_fs_files_from_patterns(self, root_paths: list) -> Iterator[str]:
        if self.is_archive:
            yield from self._copy_fs_files_from_patterns(root_paths)
        else:
            for root_path in root_paths:
                for found_path in glob.glob(os.path.join(self.target_path, root_path), recursive=True):
                    if not os.path.exists(found_path):
                        continue

                    yield found_path

    def _copy_fs_files_from_patterns(self, root_paths: list) -> Iterator[str]:
        for root_path in root_paths:
            file_matches = list(set([p for p in self.archive_names if PurePosixPath(p).match(root_path)]))
            if len(file_matches) != 0:
                for file_match in file_matches:
                    self.archive.extract(file_match, self.target_path)
                    if file_match.endswith(".db") or file_match.endswith(".sqlite") or file_match.endswith(".sqlite3") or file_match.endswith(".sqlitedb") or file_match.endswith(".storedata") or file_match.endswith(".PLSQL") or file_match.endswith(".CESQL") or file_match.endswith(".EPSQL") or file_match.endswith(".sql") or file_match.endswith(".sql3")  or file_match.endswith(".localstorage"):
                        try:
                            self.archive.extract(file_match + "-shm", self.target_path)
                        except KeyError:
                            pass
                        try:
                            self.archive.extract(file_match + "-wal", self.target_path)
                        except KeyError:
                            pass
                    yield os.path.join(self.target_path, trim_prefix(file_match, "/"))

    def _get_file_last_modified_time(self, file_path):
        if self.is_archive:
            file_path = trim_prefix(file_path, self.target_path)
            if self.archive_type == "tar":
                archive_member = self.archive.getmember(trim_prefix(file_path, "/"))
                return(convert_unix_to_iso(archive_member.mtime))
            elif self.archive_type == "zip":
                archive_member = self.archive.getinfo(file_path)
                extra = BytesIO(archive_member.extra)
                dhdr, dsz, dflag, mtime, atime, ctime, btime = unpack("<2sHB4I", extra.read(21))
                return(convert_unix_to_iso(mtime))
        else:
            return(convert_unix_to_iso(os.stat(file_path).st_mtime))
