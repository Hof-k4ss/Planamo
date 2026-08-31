# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .analytics import Analytics
from .cache_files import CacheFiles
from .crash_reporter import CrashReporter
from .filesystem import Filesystem
from .fsevents import FSEvents
from .imtranscoderagent import IMTranscoderAgent
from .knowledge_c import KnowledgeC
from .launchd import LaunchdLogs
from .lockdownd import LockdowndLogs
from .mobile_container_manager import MobileContainerManager
from .mobile_container_manager_logs import MobileContainerManagerLogs
from .mobile_installation_logs import MobileInstallationLogs
from .net_netusage import Netusage
from .powerlogs import Powerlogs
from .ps import Process
from .safari_favicon import SafariFavicon
from .security_sysdiagnose import SecuritySysdiagnose
from .shutdownlog import ShutdownLog
from .spotlight import SpotlightFolder
from .uuidfiles import UUIDFiles
from .version_history import IOSVersionHistory
from .webkit_blob import WebKitBlob
from .webkit_indexeddb import WebkitIndexedDB
from .webkit_localstorage import WebkitLocalStorage
from .webkit_safariviewservice import WebkitSafariViewService
from .xpc_activity2 import XpcActivity2

FS_MODULES = [
    Analytics,
    CacheFiles,
    CrashReporter,
    Filesystem,
    FSEvents,
    IMTranscoderAgent,
    IOSVersionHistory,
    KnowledgeC,
    LaunchdLogs,
    LockdowndLogs,
    MobileContainerManager,
    MobileContainerManagerLogs,
    MobileInstallationLogs,
    Netusage,
    Powerlogs,
    Process,
    SafariFavicon,
    SecuritySysdiagnose,
    ShutdownLog,
    SpotlightFolder,
    UUIDFiles,
    WebKitBlob,
    WebkitIndexedDB,
    WebkitLocalStorage,
    WebkitSafariViewService,
    XpcActivity2
]
