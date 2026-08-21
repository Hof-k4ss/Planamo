# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import gzip
import logging
import os
import tempfile

from typing import Optional, Union

from mvt.common.utils import convert_mactime_to_iso, recursive_resolve

from ..base import IOSExtraction

POWERLOGS_PATHS = [
    "private/var/mobile/Library/Logs/CrashReporter/DiagnosticLogs/sysdiagnose/*/logs/powerlogs/*",
    "private/var/mobile/Library/Logs/CrashReporter/powerlog*",
    "private/var/mobile/Library/Logs/CrashReporter/Retired/powerlog*",
    "private/var/containers/Shared/SystemGroup/*/Library/BatteryLife/CurrentPowerlog.PLSQL",
    "private/var/containers/Shared/SystemGroup/*/Library/BatteryLife/Archives/powerlog*",
    "private/var/containers/Shared/SystemGroup/*/Library/BatteryLife/Quarantine/*.PLSQL",
    "private/var/containers/Shared/SystemGroup/*/Library/BatteryLife/UpgradeLogs/*/*/powerlog*",
    "private/var/tmp/powerlog*",
]


class Powerlogs(IOSExtraction):
    """This module extracts information from the powerlog files."""

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
        if record.get("isodate"):
            return {
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": f"powerlogs_{record['source']}",
                "data": f"{str(record)}",
            }

    def _find_suspicious_entries(self) -> None:
        for result in self.results:
            if result.get("source") == "PLProcessMonitorAgent_EventPoint_ProcessExit" or result.get("source") == "PLProcessMonitorAgent_EventBackwardExitHistogram":
                if result.get("ReasonCode") == 254:
                    self.log.info("(Low confidence) Suspicious exit code 254 : at %s from \"%s\"", result["isodate"], result["ProcessName"])
                    if (result not in self.detected) : self.detected.append(result)

    def check_indicators(self) -> None:
        self._find_suspicious_entries()

        if not self.indicators:
            return

        for result in self.results:
            for key,value in result.copy().items():
                if isinstance(value, str):
                    if ("tmp" in value or "bd_tool" in value) and result not in self.detected:
                        self.log.warning("Found a suspicious process in Powerlogs (tmp* / bd_tool*) %s : \"%s\"", key, value)

                    ioc = self.indicators.check_process(value)
                    if ioc:
                        result["matched_indicator"] = ioc
                        if  result not in self.detected:
                            self.log.warning("Found a malicious process in Powerlogs %s : \"%s\" ", key, value)
                            self.detected.append(result)
            if result["source"] == "PLPushAgent_Aggregate_SentPushes":
                topic = result["Topic"]
                count = result["Count"]
                if count is None: continue
                timeInterval = result["timeInterval"]
                if timeInterval / count <= 3 and result not in self.detected:
                        self.log.warning("Sent %d notifications from \"%s\" in %d seconds on %s", count, topic, timeInterval, result["isodate"])
                        self.detected.append(result)
            if result["source"] == "powerlogs_PLPushAgent_Aggregate_SuppressedPushes":
                topic = result["Topic"]
                count = result["Count"]
                if count is None: continue
                timeInterval = result["timeInterval"]
                if timeInterval / count <= 3 and result not in self.detected:
                        self.log.warning("Deleted %d notifications from \"%s\" in %d seconds on %s", count, topic, timeInterval, result["isodate"])
                        self.detected.append(result)
    
    def _uncompress_file(self) -> None:
        with gzip.open(self.file_path, "rb") as f:
            file_content = f.read()
        self.file_path = os.path.join(self.temp_dir.name, self.file_name.rstrip(".PLSQL.gz"))
        with open(self.file_path, "wb") as f:
            f.write(file_content)

    def _extract_log_data(self) -> None:
        
        conn = self._open_sqlite_db(self.file_path)
        cur = conn.cursor()

        alltables = conn.execute("""
        SELECT
            name
        FROM sqlite_master
        WHERE type="table";
        """)

        for table_name in alltables:
            table = '"' + table_name[0] + '"'
            cur.execute("""
                PRAGMA TABLE_INFO({})
            """.format(table))

            headings = [tup[1] for tup in cur.fetchall()]
            rows = cur.execute("""
                SELECT
                    *
                FROM {}
            """.format(table))

            for row in rows:
                i = 0
                rowlist = {}
                while (i < (len(headings))):
                    if headings[i] == "timestamp":
                        rowlist["isodate"] = convert_mactime_to_iso(row[i], from_2001=False)
                    if isinstance(row[i], bytes):
                        rowlist[headings[i]] = recursive_resolve(row[i])
                    else:
                        rowlist[headings[i]] = row[i]
                    i += 1
                rowlist["source"] = table_name[0]
                #if rowlist not in self.results: 
                self.results.append(rowlist)
        conn.close()

    def run(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        for powerloglogpath in self._get_fs_files_from_patterns(POWERLOGS_PATHS):
            self.file_path = powerloglogpath
            self.log.info("Found Powerlog file at path: %s", self.file_path)
            self.file_name = os.path.basename(self.file_path)

            if self.file_name.endswith(".PLSQL.gz"):
                self.log.info("\"%s\" is compressed, uncompressing it ...", self.file_name)
                self._uncompress_file()
            
            elif os.path.isdir(self.file_path):
                continue
        
            elif not(self.file_name.endswith(".PLSQL")):
                self.log.warning("\"%s\" is not compressed, nor a database file. Skipping ...", self.file_name)
                continue
            self._extract_log_data()

        self.temp_dir.cleanup()

        #self.results = sorted(self.results, key=lambda entry: entry["isodate"])
        self.log.info("Extracted a total of %d powerlog records", len(self.results))