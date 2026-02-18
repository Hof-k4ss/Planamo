# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
import tarfile
import tempfile

from mvt.common.command import Command
from typing import Optional

from .modules.fs import FS_MODULES
from .modules.mixed import MIXED_MODULES

from .cmd_check_fs import CmdIOSCheckFS

log = logging.getLogger(__name__)


class CmdIOSCheckSysdiagnose(CmdIOSCheckFS):

    name = "check-sysdiagnose"
    modules = FS_MODULES + MIXED_MODULES
    
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

        self.prepare_sysdiagnose_in_sysdiagnose(target_path)
        super().__init__(target_path=self.temp_dir.name, results_path=results_path,
                         ioc_files=ioc_files, module_name=module_name,
                         serial=serial, module_options=module_options, hashes=hashes)

    def prepare_sysdiagnose_in_sysdiagnose(self, target_path):
        if not os.path.exists(target_path):
            log.error("The file %s does not exists", target_path)
            exit(1)
        log.info("Extracting sysdiagnose in temporary directory")
        self.temp_dir = tempfile.TemporaryDirectory()
        fake_sysdiagnose_path = os.path.join(self.temp_dir.name, "private/var/mobile/Library/Logs/CrashReporter/DiagnosticLogs/sysdiagnose/")
        os.makedirs(fake_sysdiagnose_path, exist_ok=True)
        tar = tarfile.open(target_path, "r:gz")
        tar.extractall(fake_sysdiagnose_path)
        tar.close()
        log.info("Launching check-fs on fake directory")