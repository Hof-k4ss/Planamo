# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .backup_info import BackupInfo
from .manifest import Manifest
from .webkit_backup import WebKitBackup

BACKUP_MODULES = [BackupInfo, Manifest, WebKitBackup]
