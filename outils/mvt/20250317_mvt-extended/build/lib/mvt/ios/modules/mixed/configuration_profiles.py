# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
import plistlib
from base64 import b64encode
from typing import Optional, Union

from mvt.common.utils import convert_datetime_to_iso

from ..base import IOSExtraction

CONF_PROFILES_DOMAIN = "SysSharedContainerDomain-systemgroup.com.apple.configurationprofiles"
CONF_PROFILES_PATH = [
    "private/var/containers/Shared/SystemGroup/systemgroup.com.apple.configurationprofiles/Library/ConfigurationProfiles/*",
    "private/var/containers/Shared/SystemGroup/systemgroup.com.apple.configurationprofiles/Library/ConfigurationProfiles/*/*",
    "private/var/mobile/Library/Logs/CrashReporter/DiagnosticLogs/sysdiagnose/*/logs/MCState/Shared/*",
    "private/var/mobile/Library/Logs/CrashReporter/DiagnosticLogs/sysdiagnose/*/logs/MCState/Shared/*/*",
]

class ConfigurationProfiles(IOSExtraction):
    """This module extracts the full plist data from configuration profiles."""

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
        if record.get("matched") == "setting":
            return {
                "timestamp": convert_datetime_to_iso(record["timestamp"]),
                "module": self.__class__.__name__,
                "event": "configuration_profile_setting_" + record["event"],
                "data": f"Modification of {record['setting']} by {record['process']} to {record['event']} ({record['key']})"
            }

        returned = []
        for settings_class in record["plist"].keys():
            if isinstance(record["plist"].get(settings_class), dict) and record["plist"].get(settings_class).get("restrictedBool"):
                for setting, entry in record["plist"].get(settings_class).get("restrictedBool").items():
                    if entry:
                        for key in entry.keys():
                            if not isinstance(entry.get(key), dict): continue
                            process = entry.get(key).get("process")
                            event = entry.get(key).get("event")
                            timestamp = entry.get(key).get("timestamp")                            
                            returned.append({
                                "timestamp": convert_datetime_to_iso(timestamp),
                                "module": self.__class__.__name__,
                                "event": "configuration_profile_setting_" + event,
                                "data": f"Modification of {setting} by {process} to {event} ({key})"
                            })

        if not record.get("install_date"): return returned

        payload_name = record['plist'].get('PayloadDisplayName')
        payload_description = record['plist'].get('PayloadDescription')
        returned.append({
            "timestamp": record["install_date"],
            "module": self.__class__.__name__,
            "event": "configuration_profile_install",
            "data": f"{record['plist']['PayloadType']} installed: {record['plist']['PayloadUUID']} "
                    f"- {payload_name}: {payload_description}"
        })
        return(returned)

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            for settings_class in result["plist"].keys():
                if settings_class == "restrictedBool":
                    for setting, entry in result["plist"].get(settings_class).items():
                        for key in entry.keys():
                            if key == "value" and setting in ["allowAppAnalytics", "allowDiagnosticSubmissionModification", "allowHandWashingDataSubmission", "allowHealthDataSubmission", "allowHealthDataSubmission2", "allowDiagnosticSubmission", "allowWheelchairDataSubmission"]:
                                    if entry[key]:
                                        self.log.info("\"%s\" is set to \"%s\"", setting, entry[key])
                                    else:
                                        self.log.warning("\"%s\" is set to \"%s\"", setting, entry[key])

                if isinstance(result["plist"].get(settings_class), dict) and result["plist"].get(settings_class).get("restrictedBool"):
                    for setting, entry in result["plist"].get(settings_class).get("restrictedBool").items():
                        if entry:
                            for key in entry.keys():
                                if not isinstance(entry.get(key), dict): continue
                                process = entry.get(key).get("process")
                                event = entry.get(key).get("event")
                                timestamp = entry.get(key).get("timestamp")
                                ioc = self.indicators.check_process(process)
                                if ioc:
                                    self.log.warning("Malicious modification of \"%s\" by \"%s\" to \"%s\" at %s (%s)", setting, process, event, timestamp, key)
                                    detected_match = {"matched": "setting", "setting": setting, "process": process, "event": event, "timestamp": timestamp, "key": key}
                                    self.detected.append(detected_match)
                                if process == "unknown":
                                    self.log.warning("Suspicious modification of \"%s\" by \"%s\" to \"%s\" at %s (%s)", setting, process, event, timestamp, key)
                                    detected_match = {"matched": "setting", "setting": setting, "process": process, "event": event, "timestamp": timestamp, "key": key}
                                    self.detected.append(detected_match)
                                if setting in ["allowAppAnalytics", "allowDiagnosticSubmissionModification", "allowHandWashingDataSubmission", "allowHealthDataSubmission", "allowHealthDataSubmission2", "allowDiagnosticSubmission", "allowWheelchairDataSubmission"] and process not in ["com.apple.DataMigrator", "com.apple.iad-cloudkit", "com.apple.purplebuddy", "com.apple.Preferences", "com.apple.Health", "MCMigrator.UpdateClientRestrictions", "MCMigrator.UpdateProfileRestrictions", "MCMigrator.ApplyImpliedSettings", "MCRestrictionManagerWriter.RecomputeEffectiveUserSettings"]:
                                    self.log.warning("Suspicious modification of \"%s\" by \"%s\" to \"%s\" at %s (%s)", setting, process, event, timestamp, key)
                                    detected_match = {"matched": "setting", "setting": setting, "process": process, "event": event, "timestamp": timestamp, "key": key}
                                    self.detected.append(detected_match)

            if result["plist"].get("PayloadUUID"):
                payload_content = result["plist"]["PayloadContent"][0]

                # Alert on any known malicious configuration profiles in the
                # indicator list.
                ioc = self.indicators.check_profile(result["plist"]["PayloadUUID"])
                if ioc:
                    self.log.warning("Found a known malicious configuration "
                                     "profile \"%s\" with UUID %s",
                                     result['plist']['PayloadDisplayName'],
                                     result['plist']['PayloadUUID'])
                    result["matched_indicator"] = ioc
                    self.detected.append(result)
                    continue

                # Highlight suspicious configuration profiles which may be used
                # to hide notifications.
                if payload_content["PayloadType"] in ["com.apple.notificationsettings"]:
                    self.log.warning("Found a potentially suspicious configuration profile "
                                     "\"%s\" with payload type %s",
                                     result['plist']['PayloadDisplayName'],
                                     payload_content['PayloadType'])
                    self.detected.append(result)
                    continue

    def _extract_data(self) -> None:
        if (os.path.isdir(self.file_path)): return

        with open(self.file_path, "rb") as handle:
            try:
                conf_plist = plistlib.load(handle)
            except Exception as e:
                self.log.warning(e)
                conf_plist = {}

        # TODO: Tidy up the following code hell.

        if "IdentityPersistentRef" in conf_plist:
            conf_plist["IdentityPersistentRef"] = b64encode(conf_plist["IdentityPersistentRef"])

        if "EASAccountCertificatePersistentID" in conf_plist:
            conf_plist["EASAccountCertificatePersistentID"] = b64encode(conf_plist["EASAccountCertificatePersistentID"])

        if "OTAProfileStub" in conf_plist:
                if "SignerCerts" in conf_plist["OTAProfileStub"]:
                    conf_plist["OTAProfileStub"]["SignerCerts"] = [b64encode(x) for x in conf_plist["OTAProfileStub"]["SignerCerts"]]
                if "PayloadContent" in conf_plist["OTAProfileStub"]:
                    if "EnrollmentIdentityPersistentID" in conf_plist["OTAProfileStub"]["PayloadContent"]:
                        conf_plist["OTAProfileStub"]["PayloadContent"]["EnrollmentIdentityPersistentID"] = b64encode(conf_plist["OTAProfileStub"]["PayloadContent"]["EnrollmentIdentityPersistentID"])

        if "SignerCerts" in conf_plist:
            conf_plist["SignerCerts"] = [b64encode(x) for x in conf_plist["SignerCerts"]]

        if "PushTokenDataSentToServerKey" in conf_plist:
            conf_plist["PushTokenDataSentToServerKey"] = b64encode(conf_plist["PushTokenDataSentToServerKey"])
        if "LastPushTokenHash" in conf_plist:
            conf_plist["LastPushTokenHash"] = b64encode(conf_plist["LastPushTokenHash"])
        if "PayloadContent" in conf_plist:
            for content_entry in range(len(conf_plist["PayloadContent"])):
                if "PERSISTENT_REF" in conf_plist["PayloadContent"][content_entry]:
                    conf_plist["PayloadContent"][content_entry]["PERSISTENT_REF"] = b64encode(conf_plist["PayloadContent"][content_entry]["PERSISTENT_REF"])
                if "IdentityPersistentRef" in conf_plist["PayloadContent"][content_entry]:
                    conf_plist["PayloadContent"][content_entry]["IdentityPersistentRef"] = b64encode(conf_plist["PayloadContent"][content_entry]["IdentityPersistentRef"])
                if "EASAccountCertificatePersistentID" in conf_plist["PayloadContent"][content_entry]:
                    conf_plist["PayloadContent"][content_entry]["EASAccountCertificatePersistentID"] = b64encode(conf_plist["PayloadContent"][content_entry]["EASAccountCertificatePersistentID"])

        if "SupervisorHostCertificates" in conf_plist:
            for content_entry in range(len(conf_plist["SupervisorHostCertificates"])):
                if b"Grayshift" in conf_plist["SupervisorHostCertificates"][content_entry]:
                    self.log.warning("Dumped with Grayshift")
                else:
                    self.log.warning(conf_plist["SupervisorHostCertificates"][content_entry])
                conf_plist["SupervisorHostCertificates"][content_entry] = b64encode(conf_plist["SupervisorHostCertificates"][content_entry])

        entry = {
            "file_path": self.file_path,
            "plist": conf_plist,
        }
        if conf_plist.get("InstallDate"): entry["install_date"] = convert_datetime_to_iso(conf_plist.get("InstallDate"))
        if entry not in self.results: self.results.append(entry)

    def run(self) -> None:
        if self.is_backup:
            for conf_file in self._get_backup_files_from_manifest(
                    domain=CONF_PROFILES_DOMAIN):
                conf_rel_path = conf_file["relative_path"]

                # Filter out all configuration files that are not configuration
                # profiles.
                if not conf_rel_path:
                    continue

                conf_file_path = self._get_backup_file_from_id(conf_file["file_id"])
                if not conf_file_path:
                    self.log.debug(
                        "Missing file %s in backup (%s)",
                        conf_file["file_id"],
                        conf_file["relative_path"],
                    )
                    continue
                self.file_path = conf_file_path
                self._extract_data()

        elif self.is_fs_dump:
            for conf_file in self._get_fs_files_from_patterns(CONF_PROFILES_PATH):
                self.file_path = conf_file
                self._extract_data()
        self.log.info("Extracted details about %d configuration profiles",
                      len(self.results))