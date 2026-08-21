# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .applications import Applications
from .apps import Apps
from .atxdatastore import ATXDataStore
from .binary_cookies import BinaryCookies
from .calendar import Calendar
from .calls import Calls
from .chrome_favicon import ChromeFavicon
from .chrome_history import ChromeHistory
from .configuration_profiles import ConfigurationProfiles
from .contacts import Contacts
from .crash_reporter_file import CrashReporterFile
from .firefox_favicon import FirefoxFavicon
from .firefox_history import FirefoxHistory
from .gif import Gif
from .global_preferences import GlobalPreferences
from .homekit import HomeKit
from .http_storage import HttpStorage
from .idstatuscache import IDStatusCache
from .interactionc import InteractionC
from .locationd import LocationdClients
from .net_datausage import Datausage
from .osanalytics_addaily import OSAnalyticsADDaily
from .profile_events import ProfileEvents
from .safari_browserstate import SafariBrowserState
from .safari_history import SafariHistory
from .shortcuts import Shortcuts
from .sms import SMS
from .sms_attachments import SMSAttachments
from .sms_attachments_folder import SMSAttachmentsFolder
from .software_updates import SoftwareUpdates
from .tcc import TCC
from .user_notifications import UserNotifications
from .wallet_pkpass import WalletPkpass
from .webkit_resource_load_statistics import WebkitResourceLoadStatistics
from .webkit_session_resource_log import WebkitSessionResourceLog
from .whatsapp import Whatsapp

MIXED_MODULES = [
    Apps,
    Calls,
    ChromeFavicon,
    ChromeHistory,
    Contacts,
    FirefoxFavicon,
    UserNotifications,
    FirefoxHistory,
    Gif,
    IDStatusCache,
    InteractionC,
    LocationdClients,
    OSAnalyticsADDaily,
    Datausage,
    HttpStorage,
    SafariBrowserState,
    SafariHistory,
    TCC,
    SMS,
    SMSAttachments,
    SMSAttachmentsFolder,
    SoftwareUpdates,
    WebkitResourceLoadStatistics,
    WebkitSessionResourceLog,
    Whatsapp,
    ProfileEvents,
    ConfigurationProfiles,
    Shortcuts,
    Applications,
    Calendar,
    GlobalPreferences,
    HomeKit,
    CrashReporterFile,
    BinaryCookies,
    ATXDataStore,
    WalletPkpass
]
