import logging
import os
import json

from typing import Optional, Union

from datetime import datetime, timezone

from ..base import IOSExtraction

CRASH_REPORTER_PATHS= [
    "private/var/mobile/Library/Logs/CrashReporter/*.ips*",
    "private/var/mobile/Library/Logs/CrashReporter/*/*.ips*",
    "private/var/mobile/Library/Logs/CrashReporter/DiagnosticLogs/sysdiagnose/*/crashes_and_spins/*.ips*",
    "private/var/mobile/Library/Logs/CrashReporter/DiagnosticLogs/sysdiagnose/*/crashes_and_spins/*/*.ips*",
    "private/var/containers/Shared/SystemGroup/systemgroup.com.apple.osanalytics/DiagnosticReports/*.ips*",
    "private/var/db/analyticsd/*.ips*",
    "private/var/MobileSoftwareUpdate/lastOTA/*.ips*"
]

class CrashReporter(IOSExtraction):
    """This module extracts information from the CrashReporter files."""

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
        return [{
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": f"{record['app_name']}",
            "data": f"{record['app_name']} | App Version : {record['app_version']} | OS Version : {record['os_version']}"
        }]
    
    def check_indicators(self) -> None:
        if not self.indicators:
            return
        for result in self.results:
            ioc = self.indicators.check_process(result["app_name"])
            if ioc:
                result["matched_indicator"] = ioc
                if result not in self.detected:
                    self.log.warning("Found a known malicious crash of \"%s\" at %s", result["app_name"], result["isodate"])
                    self.detected.append(result)
    
    def find_suspicious(self) -> None:
        for result in self.results:
            if result["app_version"] == "" and result["slice_uuid"] == "00000000-0000-0000-0000-000000000000" and result not in self.detected:
                self.log.warning("Found a known suspicious redacted crash of \"%s\" at %s", result["app_name"], result["isodate"])
                self.detected.append(result)
            if result["app_name"] in ("IMTranscoderAgent", "imagent", "MessagesBlastDoorService", "homed", "willowd", "mediaserverd") and not os.path.basename(result["file_path"]).startswith("stacks") and result not in self.detected:
                self.log.warning("Found a known suspicious crash of \"%s\" at %s", result["app_name"], result["isodate"])
                self.detected.append(result)
            if result["is_kern_invalid_address"] and result not in self.detected:
                self.log.info("Found a potential suspicious crash of \"%s\" at %s", result["app_name"], result["isodate"])


    def _extract_ips_data(self) -> None:
        with open(self.file_path, "r", encoding="utf-8") as crash_reporter_file:
            try:
                header = crash_reporter_file.readline()
                parsed_header = json.loads(header)
                content = crash_reporter_file.read()
            except:
                return

        is_kern_invalid_address = False
        if "KERN_INVALID_ADDRESS at 0x00000000000000" in content: is_kern_invalid_address = True
        isodate = datetime.strptime(parsed_header["timestamp"], "%Y-%m-%d %H:%M:%S.%f %z").astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f") if parsed_header.get("timestamp") else "1970-01-01 00:00:00"
        app_name = parsed_header["app_name"] if parsed_header.get("app_name") else ""
        app_version = parsed_header["app_version"] if parsed_header.get("app_version") else ""
        os_version = parsed_header["os_version"] if parsed_header.get("os_version") else ""
        slice_uuid = parsed_header["slice_uuid"] if parsed_header.get("slice_uuid") else ""

        self.results.append({
            "isodate": isodate,
            "app_name": app_name,
            "app_version" : app_version,
            "os_version" : os_version,
            "slice_uuid" : slice_uuid,
            "is_kern_invalid_address" : is_kern_invalid_address,
            "file_path" : self.file_path,
            "type" : "ips"
        })
    
    def _extract_sync_data(self) -> None:
        with open(self.file_path, "r", encoding="utf-8") as crash_reporter_file:
            try:
                header = crash_reporter_file.readline()
                parsed_header = json.loads(header)
                content = crash_reporter_file.readlines()
            except:
                return
        isodate = datetime.strptime(parsed_header["timestamp"], "%Y-%m-%d %H:%M:%S.%f %z").astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f") if parsed_header.get("timestamp") else "1970-01-01 00:00:00"
        os_version = parsed_header["os_version"] if parsed_header.get("os_version") else ""
        slice_uuid = ""
        for line in content:
            parsed_line = json.loads(line)
            if parsed_line.get("message"):
                is_kern_invalid_address = False
                app_name = parsed_line["message"]["process"] if parsed_line.get("message").get("process") else ""
                app_version = parsed_line["message"]["appVersion"] if parsed_line.get("message").get("appVersion") else ""
                is_kern_invalid_address = True if parsed_line.get("message").get("exceptionCodes") and parsed_line["message"]["exceptionCodes"] == "KERN_INVALID_ADDRESS at 0x00000000000000" else False
                self.results.append({
                    "isodate": isodate,
                    "app_name": app_name,
                    "app_version" : app_version,
                    "os_version" : os_version,
                    "slice_uuid" : slice_uuid,
                    "is_kern_invalid_address" : is_kern_invalid_address,
                    "file_path" : self.file_path,
                    "type" : "sync"
                })
    
    def _extract_stacks_data(self) -> None:
        with open(self.file_path, "r", encoding="utf-8") as crash_reporter_file:
            try:
                header = crash_reporter_file.readline()
                parsed_header = json.loads(header)
                content = crash_reporter_file.read()
            except:
                return
        parsed_content = json.loads(content)
        isodate = datetime.strptime(parsed_header["timestamp"], "%Y-%m-%d %H:%M:%S.%f %z").astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f") if parsed_header.get("timestamp") else "1970-01-01 00:00:00"
        slice_uuid = ""
        app_version = ""
        os_version = parsed_header["os_version"] if parsed_header.get("os_version") else ""
        is_kern_invalid_address = False
        if parsed_content.get("processByPid"):
            for process in parsed_content["processByPid"].values():
                app_name = process["procname"] if process.get("procname") else ""
                self.results.append({
                    "isodate": isodate,
                    "app_name": app_name,
                    "app_version" : app_version,
                    "os_version" : os_version,
                    "slice_uuid" : slice_uuid,
                    "is_kern_invalid_address" : is_kern_invalid_address,
                    "file_path" : self.file_path,
                    "type" : "stacks_process_by_pid"
                })
        if parsed_content.get("binaryImages"):
            for binaryImage in parsed_content["binaryImages"]:
                binary_name = binaryImage[0].upper()
                self.results.append({
                    "isodate": isodate,
                    "app_name": binary_name,
                    "app_version" : app_version,
                    "os_version" : os_version,
                    "slice_uuid" : slice_uuid,
                    "is_kern_invalid_address" : is_kern_invalid_address,
                    "file_path" : self.file_path,
                    "type" : "stacks_binary_images"
                })


    def run(self) -> None:
        for file_path in self._get_fs_files_from_patterns(CRASH_REPORTER_PATHS):
            self.file_path = file_path
            if file_path.startswith("stacks") and file_path.endswith(".ips"):
                self._extract_stacks_data()
            elif file_path.endswith(".ips"):
                if os.path.basename(file_path).startswith("panic-full-"):
                    self.log.warning("Panic file ! %s", os.path.basename(file_path))
                self._extract_ips_data()
            elif file_path.endswith(".ips.ca.synced"):
                self._extract_sync_data()

        self.log.info("Parsed %d Crash Files", len(self.results))
        self.find_suspicious()