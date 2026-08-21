from .anomaly import Anomaly
from .app_usage_stats import AppUsageStats
from .adb_key import AdbKeys
from .battery_usage import BatteryUsage
from .contextlog import ContextLog
from .data_usage import DataUsage
from .downloads import Downloads
from .forced_app_standby import ForcedAppStandby
from .filesystem import Filesystem
from .frosting import Frosting
from .intent_blocking import IntentBlocker
from .library import Library 
from .localappstate import LocalAppState
from .notification import Notification
from .package_verification import PackageVerification
from .prefetch import Prefetch
from .sm import SMLog
from .smart_protect import SmartProtect
from .sms import SMS
from .snet_files_info import Snet
from .ssrm_heating import SSRMHeatingLogs
from .thermal_log import ThermalLog

FS_MODULES = [AdbKeys,
        AppUsageStats,
        Anomaly,
        BatteryUsage,
        ContextLog,
        DataUsage,
        Downloads,
        Filesystem,
        ForcedAppStandby,
        Frosting,
        IntentBlocker,
        LocalAppState,
        Library,
        Notification,
        PackageVerification,
        Prefetch,
        SMLog,
        SmartProtect,
        SMS,
        Snet,
        SSRMHeatingLogs,
        ThermalLog,
]
