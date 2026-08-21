# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import glob
import logging
import os
import sys
import tarfile
import tempfile
import zipfile
from pathlib import PurePosixPath
from typing import Optional

from mvt.common.command import Command

from .modules.fs import FS_MODULES
from .modules.mixed import MIXED_MODULES

log = logging.getLogger(__name__)

SYSDIAGNOSE_PATH = "private/var/mobile/Library/Logs/CrashReporter/DiagnosticLogs/sysdiagnose/sysdiagnose_*.tar.gz"

class CmdIOSCheckFS(Command):
    def __init__(
        self,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        ioc_files: Optional[list] = None,
        module_name: Optional[str] = None,
        serial: Optional[str] = None,
        module_options: Optional[dict] = None,
        hashes: bool = False,
    ) -> None:
        super().__init__(
            target_path=target_path,
            results_path=results_path,
            ioc_files=ioc_files,
            module_name=module_name,
            serial=serial,
            module_options=module_options,
            hashes=hashes,
            log=log,
        )

        self.name = "check-fs"
        self.modules = FS_MODULES + MIXED_MODULES
        self.is_archive = False
        if os.path.isfile(self.target_path):
            if (self.target_path.endswith(".gz") or self.target_path.endswith(".bz2") or self.target_path.endswith(".xz") or self.target_path.endswith(".tar")):
                if not tarfile.is_tarfile(self.target_path):
                    self.log.critical("Tar file %s seems corrupted.", self.target_path)
                    sys.exit(1)
                self.archive_type = "tar"
                self.archive = tarfile.open(self.target_path, "r")
                self.archive_names = self.archive.getnames()
                self.archive_members = self.archive.getmembers()
            elif (self.target_path.endswith(".zip")):
                if not zipfile.is_zipfile(self.target_path):
                    self.log.critical("ZIP file %s seems corrupted.", self.target_path)
                    sys.exit(1)
                self.archive_type = "zip"
                self.archive = zipfile.ZipFile(self.target_path, mode="r")
                self.archive_names = self.archive.namelist()
                self.archive_members = self.archive.infolist()
            else:
                self.log.critical("Unrecognized file %s. Supported archive types are .zip and tar files.", self.target_path)
                sys.exit(1)
            self.is_archive = True
            self.temp_archive_dir = tempfile.TemporaryDirectory()
        self.prepare_sysdiagnose_in_fs()
        
        
    def prepare_sysdiagnose_in_fs(self):
        if self.is_archive:
            file_matches = [p for p in self.archive_names if PurePosixPath(p).match(SYSDIAGNOSE_PATH)]
            if (len(file_matches) != 0):
                for file_match in file_matches:
                    self.archive.extract(file_match, self.temp_archive_dir.name)
                    output_file = os.path.join(self.temp_archive_dir.name, file_match)
                    tar = tarfile.open(output_file, "r:gz")
                    tar.extractall(os.path.dirname(output_file))
                    tar.close()
        else:
            for found_path in glob.glob(os.path.join(self.target_path,
                                                                    SYSDIAGNOSE_PATH)):
                tar = tarfile.open(found_path, "r:gz")
                tar.extractall(os.path.dirname(found_path))
                tar.close() 
            
    def module_init(self, module):
        module.is_fs_dump = True
        module.is_archive = self.is_archive
        if self.is_archive:
            module.archive = self.archive
            module.archive_names = self.archive_names
            module.archive_members = self.archive_members
            module.archive_type = self.archive_type
            module.target_path = self.temp_archive_dir.name