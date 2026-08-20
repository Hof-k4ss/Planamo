# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import re

from typing import Optional, Union

from mvt.common.utils import convert_datetime_to_iso, convert_mobilecontainermanagerlog_to_unix, trim_prefix

from ..base import IOSExtraction

MOBILE_INSTALLATION_LOGS_PATHS = [
    "private/var/root/Library/Logs/MobileInstallation/*mobile_installation.log*",
    "private/var/installd/Library/Logs/MobileInstallation/*mobile_installation.log*",
    "private/var/mobile/Library/Logs/CrashReporter/DiagnosticLogs/sysdiagnose/*/logs/MobileInstallation/*mobile_installation.log*"
]


class MobileInstallationLogs(IOSExtraction):
    """This module extracts information from the mobile_installation log files."""

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
        if record.get("operation"):
            return {
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": "mobile_installation_log_" + record["operation"],
                "data": f"(Local Time) {record['message']}",
            }
        else:
            return {
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": "mobile_installation_log_uncategorized",
                "data": f"(Local Time) {record['message']}",
            }

    
    def _find_suspicious_entries(self) -> None:
        for result in self.results:
            if "this is an erase install." in result["message"]:
                self.log.warning("The phone was wiped at : %s (US Pacific Time)", result["isodate"])
            if "tmp" in result["message"] or "bd_tool" in result["message"]:
                self.log.warning("Found mention of a suspicious name in Mobile Installation Logs (tmp* / bd_tool*) : %s : \"%s\"", result["isodate"], result["message"])
                if (result not in self.detected) : self.detected.append(result)
            if result.get("path"):
                if not(result["path"].startswith(("/private/var/mobile/Containers/Data/PluginKitPlugin/", "/private/var/mobile/Containers/Data/Application/", "/private/var/containers/Bundle/Application/", "/private/var/mobile/Containers/Shared/AppGroup/"))):
                    self.log.warning("Found mention of a suspicious path in Mobile Installation Logs : %s : \"%s\"", result["isodate"], result["path"])
                    if (result not in self.detected) : self.detected.append(result)
            if "/binpack/" in result["message"] or "kjc.loader" in result["message"]: 
                    self.log.warning("checkra1n is on the device : %s : \"%s\"", result["isodate"], result["message"])
                    if (result not in self.detected) : self.detected.append(result)
                    continue
            if "Failed to verify code signature of" in result["message"]: 
                    self.log.warning("Unsigned binary on the device : %s : \"%s\"", result["isodate"], result["message"])
                    if (result not in self.detected) : self.detected.append(result)
                    continue
            if "LS registered app" in result["message"] and "ApplicationType = System" in result["message"]: 
                    self.log.warning("System app registered on the device : %s : \"%s\"", result["isodate"], result["message"])
                    if (result not in self.detected) : self.detected.append(result)
                    continue
            if "LS registered app" in result["message"] and "IsDeletable" in result["message"]: 
                    self.log.warning("Undeletable app registered on the device : %s : \"%s\"", result["isodate"], result["message"])
                    if (result not in self.detected) : self.detected.append(result)
                    continue

                    
    def check_indicators(self) -> None:
        self._find_suspicious_entries()

        if not self.indicators:
            return

        for result in self.results:
            if result.get("path"):
                ioc = self.indicators.check_file_path_process(result["path"])
                if ioc:
                    result["matched_indicator"] = ioc
                    if result not in self.detected:
                        self.log.warning("Found mention of a known malicious process \"%s\" in Mobile Installation Logs at %s",
                                            result["path"], result["isodate"])
                        if (result not in self.detected) : self.detected.append(result)
                        continue
            for ioc in self.indicators.get_iocs("processes"):
                if ioc["value"] in result["message"]:
                    self.log.warning("Found mention of a known malicious process in Mobile Installation Logs : %s : \"%s\"", result["isodate"], result["message"])
                    result["matched_indicator"] = ioc
                    if (result not in self.detected) : self.detected.append(result)
                    break
    
    def _extract_log_data(self, content) -> None:
        current_entry = {}
        for line in content.split("\n"):
            line = line.strip()

            if re.match(r'(^[^\[]+ [^\[]+ [0-9]{1,2} [0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2} [0-9]{4}) \[([0-9]+)\] <([^>]+)> \(([^\)]+)\) (.*)$', line):
                if (current_entry != {} and current_entry not in self.results): 
                    self.results.append(current_entry)
                    current_entry = {}

                matchObj = re.search(r"(Install Successful for)", line) # Regex for installed applications
                if matchObj:
                    current_entry["operation"] = "installation"
                    matchObj1 = re.search(r"(?<= for \(Placeholder:)(.*)(?=\))", line) # Regex for bundle id
                    matchObj2 = re.search(r"(?<= for \(Customer:)(.*)(?=\))", line) # Regex for bundle id
                    matchObj3 = re.search(r"(?<= for \(System:)(.*)(?=\))", line) # Regex for bundle id
                    matchObj4 = re.search(r"(?<= for \()(.*)(?=\))", line) # Regex for bundle id
                    if matchObj1:
                        bundle_type = "placeholder"
                        bundleid = matchObj1.group(1)
                    elif matchObj2:
                        bundle_type = "customer"
                        bundleid = matchObj2.group(1)
                    elif matchObj3:
                        bundle_type = "system"
                        bundleid = matchObj3.group(1)
                    elif matchObj4:
                        bundle_type = ""
                        bundleid = matchObj4.group(1)

                    matchObj = re.search(r"(?<=^)(.*)(?= \[[0-9]+\] <)", line) # Regex for timestamp
                    timestamp = matchObj.group(1)
                    current_entry["bundle_type"] = bundle_type
                    current_entry["isodate"] = convert_datetime_to_iso(convert_mobilecontainermanagerlog_to_unix(timestamp))
                    current_entry["message"] = f"Application {bundleid} ({bundle_type}) was installed"
                    continue

                matchObj = re.search(r"(Destroying container with identifier)", line) # Regex for destroyed containers
                if matchObj:
                    current_entry["operation"] = "destroy"
                    matchObj = re.search(r"(?<=identifier )(.*)(?= at )", line) # Regex for bundle id
                    if matchObj:
                        bundleid = matchObj.group(1)
                    matchObj = re.search(r"(?<= at )(.*)(?=$)", line) # Regex for path
                    if matchObj:
                        path = matchObj.group(1)
                        current_entry["path"] = path
                    matchObj = re.search(r"(?<=^)(.*)(?= \[)", line) # Regex for timestamp
                    timestamp = matchObj.group(1)
                    current_entry["isodate"] = convert_datetime_to_iso(convert_mobilecontainermanagerlog_to_unix(timestamp))
                    current_entry["message"] = f"Application {bundleid} was destroyed ({path})"
                    continue

                matchObj = re.search(r"(Data container for)", line) # Regex Moved data containers
                if matchObj:
                    current_entry["operation"] = "move"
                    matchObj = re.search(r"(?<=for )(.*)(?= is now )", line) # Regex for bundle id
                    if matchObj:
                        bundleid = matchObj.group(1)
                    matchObj = re.search(r"(?<= at )(.*)(?=$)", line) # Regex for path
                    if matchObj:
                        path = matchObj.group(1)
                        current_entry["path"] = path
                    matchObj = re.search(r"(?<=^)(.*)(?= \[)", line) # Regex for timestamp
                    timestamp = matchObj.group(1)
                    current_entry["isodate"] = convert_datetime_to_iso(convert_mobilecontainermanagerlog_to_unix(timestamp))
                    current_entry["message"] = f"Application {bundleid} was moved (to {path})"
                    continue

                matchObj = re.search(r"(Made container live for)", line) # Regex for made container
                if matchObj:
                    current_entry["operation"] = "live"
                    matchObj = re.search(r"(?<=for )(.*)(?= at)", line) # Regex for bundle id
                    if matchObj:
                        bundleid = matchObj.group(1)
                    matchObj = re.search(r"(?<= at )(.*)(?=$)", line) # Regex for path
                    if matchObj:
                        path = matchObj.group(1)
                        current_entry["path"] = path
                    matchObj = re.search(r"(?<=^)(.*)(?= \[)", line) # Regex for timestamp
                    timestamp = matchObj.group(1)
                    current_entry["isodate"] = convert_datetime_to_iso(convert_mobilecontainermanagerlog_to_unix(timestamp))
                    current_entry["message"] = f"Application {bundleid} was made live ({path})"
                    continue

                matchObj = re.search(r"(Uninstalling identifier )", line) # Regex for uninstalling container
                if matchObj:
                    current_entry["operation"] = "uninstall"
                    matchObj = re.search(r"(?<=Uninstalling identifier )(.*)", line) # Regex for bundle id
                    if matchObj:
                        bundleid = matchObj.group(1)

                    matchObj = re.search(r"(?<=^)(.*)(?= \[)", line) # Regex for timestamp
                    timestamp = matchObj.group(1)
                    current_entry["isodate"] = convert_datetime_to_iso(convert_mobilecontainermanagerlog_to_unix(timestamp))
                    current_entry["message"] = f"Application {bundleid} was uninstalled"
                    continue
            
                matchObj = re.search(r"(Attempting Delta patch update of )", line) # Regex for Delta patch
                if matchObj:
                    current_entry["operation"] = "update"
                    matchObj = re.search(r"(?<=Attempting Delta patch update of )(.*)(?= from)", line) # Regex for bundle id
                    if matchObj:
                        bundleid = matchObj.group(1)
                    matchObj = re.search(r"(?<= from )(.*)", line) # Regex for path
                    if matchObj:
                        version = matchObj.group(1)
                    matchObj = re.search(r"(?<=^)(.*)(?= \[)", line) # Regex for timestamp
                    timestamp = matchObj.group(1)
                    current_entry["isodate"] = convert_datetime_to_iso(convert_mobilecontainermanagerlog_to_unix(timestamp))
                    current_entry["message"] = f"Application {bundleid} was updated from {version}"
                    continue
                
                searches = re.search(r'(^[^\[]+ [^\[]+ [0-9]{1,2} [0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2} [0-9]{4}) \[([0-9]+)\] <([^>]+)> \(([^\)]+)\) (.*)$',line)
                current_entry["isodate"] = convert_datetime_to_iso(convert_mobilecontainermanagerlog_to_unix(searches[1]))
                #current_entry["?"] = int(searches[2]) // TODO : check value
                #current_entry["loglevel"] = searches[3]
                #current_entry["?"] = searches[4] // TODO : check value
                current_entry["message"] = trim_prefix(searches[5],"-").replace("\r"," ").replace("\n"," ")

            else:
                current_entry["message"] += line.replace("\r"," ").replace("\n"," ")

        if (current_entry != {} and current_entry not in self.results): self.results.append(current_entry)
        self.results = sorted(self.results, key=lambda entry: entry["isodate"])

    def run(self) -> None:
        for mobileinstallationlogpath in self._get_fs_files_from_patterns(MOBILE_INSTALLATION_LOGS_PATHS):
            self.file_path = mobileinstallationlogpath
            self.log.info("Found MobileInstallation log file at path: %s", self.file_path)
            with open(self.file_path, "r", encoding="utf-8") as handle:
                self._extract_log_data(handle.read())
        self.log.info("Extracted information on %d MobileInstallation log records", len(self.results))

