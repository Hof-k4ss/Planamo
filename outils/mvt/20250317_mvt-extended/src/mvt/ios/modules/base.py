# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import datetime
import glob
import logging
import os
import shutil
import sqlite3
import subprocess
import tempfile

from io import BytesIO
from mvt.common.utils import trim_prefix
from pathlib import PurePosixPath
from struct import unpack
from typing import Iterator, Optional, Union

from mvt.common.utils import recursive_resolve, convert_datetime_to_iso, convert_unix_to_iso
from mvt.common.module import DatabaseCorruptedError, DatabaseNotFoundError, MVTModule


class IOSExtraction(MVTModule):
    """This class provides a base for all iOS filesystem/backup extraction
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

    def _recover_sqlite_db_if_needed(
        self, file_path: str, forced: bool = False
    ) -> None:
        """Tries to recover a malformed database by running a .clone command.

        :param file_path: Path to the malformed database file.

        """
        # TODO: Find a better solution.
        if not forced:
            conn = self._open_sqlite_db(file_path)
            cur = conn.cursor()

            try:
                recover = False
                cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            except sqlite3.DatabaseError as exc:
                if "database disk image is malformed" in str(exc):
                    recover = True
            finally:
                conn.close()

            if not recover:
                return

        self.log.info(
            "Database at path %s is malformed. Trying to recover...", file_path
        )

        if not shutil.which("sqlite3"):
            raise DatabaseCorruptedError(
                "failed to recover without sqlite3 binary: please install sqlite3!"
            )
        if '"' in file_path:
            raise DatabaseCorruptedError(
                f"database at path '{file_path}' is corrupted. unable to "
                'recover because it has a quotation mark (") in its name'
            )

        bak_path = f"{file_path}.bak"
        shutil.move(file_path, bak_path)

        ret = subprocess.call(
            ["sqlite3", bak_path, f'.clone "{file_path}"'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if ret != 0:
            raise DatabaseCorruptedError("failed to recover database")

        self.log.info("Database at path %s recovered successfully!", file_path)

    def _open_sqlite_db(self, file_path: str) -> sqlite3.Connection:
        if self.is_fs_dump and not self.is_archive:
            temp_dir = tempfile.TemporaryDirectory()

            if os.path.isfile(os.path.join(self.target_path, file_path) + "-shm"):
                shutil.copy(os.path.join(self.target_path, file_path) + "-shm", temp_dir.name)
            if os.path.isfile(os.path.join(self.target_path, file_path) + "-wal"):
                shutil.copy(os.path.join(self.target_path, file_path) + "-wal", temp_dir.name)

            shutil.copy(file_path, temp_dir.name)
            return sqlite3.connect(f"file:{os.path.join(temp_dir.name, file_path)}", uri=True)

        elif self.is_archive:
            try:
                self.archive.extract(trim_prefix(file_path, self.target_path) + "-shm", self.target_path)
            except KeyError:
                pass
            try:
                self.archive.extract(trim_prefix(file_path, self.target_path) + "-wal", self.target_path)
            except KeyError:
                pass
            return sqlite3.connect(f"file:{file_path}")
        
        elif os.path.basename(file_path) == "Manifest.db" or not file_path.startswith(self.target_path):
            return sqlite3.connect(f"file:{file_path}")

        else:
            temp_dir = tempfile.TemporaryDirectory()

            file_id = os.path.basename(file_path)
            metadata = self._get_backup_metadata_from_id(file_id)
            relative_file_path = metadata["RelativePath"]

            potential_shm = [x for x in self._get_backup_files_from_manifest(relative_path=(relative_file_path + "-shm"))]
            if len(potential_shm) > 0:
                if len(potential_shm) > 1:
                    self.log.error("More than one -shm file found for that file %s", relative_file_path)
                else:
                    shutil.copy(os.path.join(self.target_path, potential_shm[0]["file_id"][0:2], potential_shm[0]["file_id"]), temp_dir.name)

            potential_wal = [x for x in self._get_backup_files_from_manifest(relative_path=(relative_file_path + "-wal"))]
            if len(potential_wal) > 0:
                if len(potential_wal) > 1:
                    self.log.error("More than one -wal file found for that file %s", relative_file_path)
                else:
                    shutil.copy(os.path.join(self.target_path, potential_wal[0]["file_id"][0:2], potential_wal[0]["file_id"]), temp_dir.name)

            shutil.copy(file_path, temp_dir.name)
            return sqlite3.connect(f"file:{os.path.join(temp_dir.name, file_path)}", uri=True)

    def _get_backup_files_from_manifest(
        self, relative_path: Optional[str] = None, domain: Optional[str] = None
    ) -> Iterator[dict]:
        """Locate files from Manifest.db.

        :param relative_path: Relative path to use as filter from Manifest.db.
                              (Default value = None)
        :param domain: Domain to use as filter from Manifest.db.
                       (Default value = None)

        """
        manifest_db_path = os.path.join(self.target_path, "Manifest.db")
        if not os.path.exists(manifest_db_path):
            raise DatabaseNotFoundError("unable to find backup's Manifest.db")

        base_sql = "SELECT fileID, domain, relativePath FROM Files WHERE "

        try:
            conn = self._open_sqlite_db(manifest_db_path)
            cur = conn.cursor()
            if relative_path and domain:
                cur.execute(
                    f"{base_sql} relativePath = ? AND domain = ?;",
                    (relative_path, domain),
                )
            else:
                if relative_path:
                    if "*" in relative_path:
                        cur.execute(
                            f"{base_sql} relativePath LIKE ?;",
                            (relative_path.replace("*", "%"),),
                        )
                    else:
                        cur.execute(f"{base_sql} relativePath = ?;", (relative_path,))
                elif domain:
                    cur.execute(f"{base_sql} domain = ?;", (domain,))
        except Exception as exc:
            raise DatabaseCorruptedError(f"failed to query Manifest.db: {exc}") from exc

        for row in cur:
            yield {
                "file_id": row[0],
                "domain": row[1],
                "relative_path": row[2],
            }
    
    def _get_backup_files_from_manifest_pattern(self, relative_path_pattern=None, domain_pattern=None, custom_pattern=None):
        """Locate files from Manifest.db using a glob pattern.

        :param relative_path: Relative path (glob) to use as filter from Manifest.db. (Default value = None)
        :param domain: Domain (glob) to use as filter from Manifest.db. (Default value = None)

        """
        manifest_db_path = os.path.join(self.target_path, "Manifest.db")
        if not os.path.exists(manifest_db_path):
            raise DatabaseNotFoundError("unable to find backup's Manifest.db")

        base_sql = "SELECT fileID, domain, relativePath FROM Files WHERE "

        try:
            conn = self._open_sqlite_db(manifest_db_path)
            cur = conn.cursor()
            if custom_pattern:
                cur.execute(base_sql+custom_pattern)
            else:
                if relative_path_pattern and domain_pattern:
                    cur.execute(f"{base_sql} relativePath LIKE ? AND domain LIKE ?;",
                                ('%'+relative_path_pattern+'%', '%'+domain_pattern+'%'))
                else:
                    if relative_path_pattern:
                        cur.execute(f"{base_sql} relativePath LIKE ?;", ('%'+relative_path_pattern+'%',))
                    elif domain_pattern:
                        cur.execute(f"{base_sql} domain LIKE ?;", ('%'+domain_pattern+'%',))
        except Exception as e:
            raise DatabaseCorruptedError("failed to query Manifest.db: %s", e)

        for row in cur:
            yield {
                "file_id": row[0],
                "domain": row[1],
                "relative_path": row[2],
            }

    @staticmethod
    def _convert_timestamp(timestamp_or_unix_time_int):
        """Older iOS versions stored the manifest times as unix timestamps.

        :param timestamp_or_unix_time_int:

        """
        if isinstance(timestamp_or_unix_time_int, datetime.datetime):
            return convert_datetime_to_iso(timestamp_or_unix_time_int)
        else:
            timestamp = datetime.datetime.utcfromtimestamp(timestamp_or_unix_time_int)
            return convert_datetime_to_iso(timestamp)

    def _get_backup_file_from_id(self, file_id: str) -> Union[str, None]:
        file_path = os.path.join(self.target_path, file_id[0:2], file_id)
        if os.path.exists(file_path):
            return file_path

        return None

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
                    yield os.path.join(self.target_path, trim_prefix(file_match, "/"))

    def _get_file_last_modified_time(self, file_path, file_id = None):
        if self.is_fs_dump:
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
        elif self.is_backup:
            if file_id is not None:
                metadata = self._get_backup_metadata_from_id(file_id)
                return metadata["modified"]
            else:
                file_id = os.path.basename(file_path)
                metadata = self._get_backup_metadata_from_id(file_id)
                return metadata["modified"]


    def _get_backup_metadata_from_id(self, file_id):
        manifest_db_path = os.path.join(self.target_path, "Manifest.db")
        if not os.path.exists(manifest_db_path):
            raise DatabaseNotFoundError("unable to find backup's Manifest.db")

        base_sql = "SELECT file FROM Files WHERE "

        try:
            conn = self._open_sqlite_db(manifest_db_path)
            cur = conn.cursor()
            cur.execute(f"{base_sql} fileID = ?;", (file_id,))
        except Exception as e:
            raise DatabaseCorruptedError("failed to query Manifest.db: %s", e)

        for row in cur:
            file_metadata = recursive_resolve(row[0])
            return {
                "created": self._convert_timestamp(file_metadata["Birth"]),
                "modified": self._convert_timestamp(file_metadata["LastModified"]),
                "size": file_metadata["Size"],
                "RelativePath": file_metadata["RelativePath"]
            }


    def _find_ios_database(
        self, backup_ids: Optional[list] = None, root_paths: Optional[list] = None
    ) -> None:
        """Try to locate a module's database file from either an iTunes
        backup or a full filesystem dump. This is intended only for
        modules that expect to work with a single SQLite database.
        If a module requires to process multiple databases or files,
        you should use the helper functions above.

        :param root_paths: Glob patterns for files to seek in filesystem dump.
                           (Default value = [])
        :param backup_ids: Default value = None)

        """
        file_path = None
        # First we check if the was an explicit file path specified.
        if not self.file_path:
            # If not, we first try with backups.
            # We construct the path to the file according to the iTunes backup
            # folder structure, if we have a valid ID.
            if backup_ids:
                for backup_id in backup_ids:
                    file_path = self._get_backup_file_from_id(backup_id)
                    if file_path:
                        break

            if root_paths:
                # If this file does not exist we might be processing a full
                # filesystem dump (checkra1n all the things!).
                if not file_path or not os.path.exists(file_path):
                    # We reset the file_path.
                    file_path = None
                    for found_path in self._get_fs_files_from_patterns(root_paths):
                        file_path = found_path
                        break

        # If we do not find any, we fail.
        if file_path:
            self.file_path = file_path
        else:
            raise DatabaseNotFoundError("unable to find the module's database file")

        self._recover_sqlite_db_if_needed(self.file_path)
