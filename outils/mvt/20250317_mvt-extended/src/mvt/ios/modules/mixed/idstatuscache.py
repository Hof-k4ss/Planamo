# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import collections
import logging
import plistlib
import re
import sqlite3
from copy import deepcopy
from typing import Optional, Union

from mvt.common.utils import convert_mactime_to_iso, convert_unix_to_iso, convert_mactime_to_iso, recursive_resolve

from ..base import IOSExtraction

IDSTATUSCACHE_BACKUP_IDS = [
    "6b97989189901ceaa4e5be9b7f05fb584120e27b",
]
IDSTATUSCACHE_ROOT_PATHS = [
    "private/var/mobile/Library/Preferences/com.apple.identityservices.idstatuscache.plist",
    "private/var/mobile/Library/IdentityServices/idstatuscache.plist",
]
IDSTATUSCACHE_ROOT_DB_PATHS = [
    "private/var/mobile/Library/IdentityServices/ids-pub-id.db",
]
IDSTATUSCACHE_FIREWALL_DB_PATHS = [
    "private/var/mobile/Library/IdentityServices/ids-firewall-identityservicesd.db",
]
IDSTATUSCACHE_GOSSIP_DB_PATHS = [
    "private/var/mobile/Library/IdentityServices/ids-gossip.db",
]
IDSTATUSCACHE_OTHER_DB_PATHS = [
    "private/var/mobile/Library/IdentityServices/ids.db",
    "private/var/mobile/Library/IdentityServices/ids-a.db",
    "private/var/mobile/Library/IdentityServices/ids-c.db",
]


class IDStatusCache(IOSExtraction):
    """Extracts Apple Authentication information from idstatuscache.plist"""

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
        if record["entry_type"] == "plist":
            return {
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": "lookup",
                "data": f"Lookup of {record['user']} within {record['package']} "
                f"(Status {record['idstatus']})",
            }
        elif record["entry_type"] == "bd":
            user = record["key"].split("-")[1]
            package = record["key"].split("-")[2]
            return {
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": "lookup",
                "data": f"Lookup of {user} within {package} (database)",
            }
        elif record["entry_type"] == "firewall_bd":
            user = record["handle"]
            package = record["service"]
            returned = []
            returned.append({
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": "lookup_last_seen",
                "data": f"Lookup of {user} within {package} (firewall database)",
            })
            returned.append({
                "timestamp": convert_unix_to_iso(record.get("last_modified_date", "")),
                "module": self.__class__.__name__,
                "event": "lookup_last_modified",
                "data": f"Lookup of {user} within {package} (firewall database)",
            })
            return returned
        elif record["entry_type"] == "gossip_bd":
            user = record["prefixedURI"]
            package = record["serviceHint"]
            return {
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": "lookup",
                "data": f"Lookup of {user} within {package} (gossip database)",
            }
        elif record["entry_type"] == "other_bd":
            if not record.get("user"): return
            user = record["user"]
            package = record["package"]
            return {
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": "lookup",
                "data": f"Lookup of {user} within {package} (other database)",
            }
        elif record["entry_type"] == "bd_missing_start":
            return {
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": "ids_pub_id_missing_start",
                "data": f"Begining of a time frame with {record['amount']} missing ids-pub-id{'s' if record['amount'] > 1 else ''}",
            }
        elif record["entry_type"] == "bd_missing_end":
            return {
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": "ids_pub_id_missing_end",
                "data": f"End of a time frame with {record['amount']} missing ids-pub-id{'s' if record['amount'] > 1 else ''}",
            }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        suspicious_email_pattern_1 = re.compile('[a-z\.]+[0-9]{2}@.*')

        for result in self.results:
            if not result.get("entry_type"):
                # For retrocompatibility in check-iocs
                result["entry_type"] = "plist"
            if result["entry_type"] == "plist":
                if result.get("user", "").startswith("mailto:"):
                    email = result["user"][7:].strip("'")
                    ioc = self.indicators.check_email(email)
                    if ioc:
                        result["matched_indicator"] = ioc
                        self.detected.append(result)
                        continue

                if "\\x00\\x00" in result.get("user", ""):
                    self.log.warning(
                        "Found an ID Status Cache entry with suspicious patterns: %s",
                        result.get("user"),
                    )
                    self.detected.append(result)
                
                suspicious_email_pattern_matched = suspicious_email_pattern_1.search(result.get("user"))
                if suspicious_email_pattern_matched:
                    self.log.warning("Found mention of a new suspicious email address \"%s\" in idstatuscache (type %s).",
                                        result.get("user"), result.get("entry_type"))
                    self.detected.append(result)

            else:
                if result["entry_type"] == "bd":
                    user = result["key"].split("-")[1]
                elif result["entry_type"] == "firewall_bd":
                    user = result["handle"]
                elif result["entry_type"] == "gossip_bd":
                    user = result["prefixedURI"]
                elif result["entry_type"] == "other_bd":
                    user = result.get("user", "")
                if user.startswith("mailto:"):
                    email = user[7:].strip("'")
                    ioc = self.indicators.check_email(email)
                    if ioc:
                        result["matched_indicator"] = ioc
                        self.detected.append(result)
                        continue
                
                if "threat-notifications@apple.com" in user:
                    self.log.warning(
                        "Apple warning about state-sponsored attack received on the %s",
                        result.get("isodate"),
                    )

                if "\\x00\\x00" in user:
                    self.log.warning(
                        "Found an ID Status Cache entry with suspicious patterns: %s",
                        user,
                    )
                    self.detected.append(result)

                suspicious_email_pattern_matched = suspicious_email_pattern_1.search(user)
                if suspicious_email_pattern_matched:
                    self.log.warning("Found mention of a new suspicious email address \"%s\" in idstatuscache (type %s).",
                                        user, result.get("entry_type"))
                    self.detected.append(result)

    def _extract_idstatuscache_entries(self, file_path):
        with open(file_path, "rb") as handle:
            file_plist = plistlib.load(handle)

        id_status_cache_entries = []
        for app in file_plist:
            if not isinstance(file_plist[app], dict):
                continue

            for entry in file_plist[app]:
                try:
                    lookup_date = file_plist[app][entry]["LookupDate"]
                    id_status = file_plist[app][entry]["IDStatus"]
                except KeyError:
                    continue

                id_status_cache_entries.append(
                    {
                        "package": app,
                        "user": entry.replace("\x00", "\\x00"),
                        "isodate": convert_mactime_to_iso(lookup_date),
                        "idstatus": id_status,
                        "entry_type": "plist"
                    }
                )

        entry_counter = collections.Counter(
            [entry["user"] for entry in id_status_cache_entries]
        )
        for entry in id_status_cache_entries:
            # Add total count of occurrences to the status cache entry.
            entry["occurrences"] = entry_counter[entry["user"]]
            self.results.append(entry)
    
    def _extract_idstatuscache_firewall_database(self, database_path):
        self._recover_sqlite_db_if_needed(database_path)
        conn = self._open_sqlite_db(database_path)

        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT
                    *
                FROM firewall_record;
            """
            )
        except sqlite3.DatabaseError:
            self.log.warning("IDStatusCache firewall database %s is probably malformed, skipping it.", database_path)
            return

        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                entry[headings[index]] = value

            entry["isodate"] = convert_unix_to_iso(entry.get("last_seen_date", ""))
            entry["entry_type"] = "firewall_bd"
            self.results.append(entry)
        cur.close()
        conn.close()

    def _extract_idstatuscache_gossip_database(self, database_path):
        self._recover_sqlite_db_if_needed(database_path)
        conn = self._open_sqlite_db(database_path)

        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT
                    *
                FROM kvtable;
            """
            )
        except sqlite3.DatabaseError:
            self.log.warning("IDStatusCache database %s is probably malformed, skipping it.", database_path)
            return

        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                entry[headings[index]] = value

            entries = recursive_resolve(entry.get("value", []))
            entry["isodate"] = convert_unix_to_iso(entry.get("date", ""))
            entry["entry_type"] = "gossip_bd"
            if isinstance(entries, list):
                entry.pop("value")
                for entry_item in entries:
                    output_item = deepcopy(entry)
                    if not entry_item.get("serviceHint"): output_item["serviceHint"]=""
                    else: output_item["serviceHint"] = entry_item["serviceHint"]
                    output_item["prefixedURI"] = entry_item["prefixedURI"]
                    self.results.append(output_item)
            else:
                entry["value"] = entries
                self.results.append(entry)
        cur.close()
        conn.close()

    def _extract_idstatuscache_other_database(self, database_path):
        self._recover_sqlite_db_if_needed(database_path)
        conn = self._open_sqlite_db(database_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                name
            FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != '_SqliteDatabaseProperties';
        """)
        rows = list(cur)
        for row, in rows:
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM '" + row + "'")
                rows_for_row = list(cur)
            except sqlite3.DatabaseError:
                self.log.warning("IDStatusCache other database %s is probably malformed, skipping it.", database_path)
                return
            headings = [description[0] for description in cur.description]
            for row_for_row in rows_for_row:
                entry = {}
                for index, value in enumerate(row_for_row):
                    if isinstance(value, (bytes, bytearray)):
                        entry[headings[index]] = recursive_resolve(value)
                    else:
                        entry[headings[index]] = value
                entry["isodate"] = convert_mactime_to_iso(entry.get("date", ""))
                entry["entry_type"] = "other_bd"
                if row == "incoming_message":
                    entry["user"] = entry["from_id"]
                    entry["package"] = entry["topic"]
                elif row == "outgoing_message":
                    if entry["destinations"].get("kIDSDestinationURIURIObject"):
                        entry["user"] = entry["destinations"]["kIDSDestinationURIURIObject"]["prefixedURI"]
                    elif entry["destinations"].get("kURIKey"):
                        entry["user"] = entry["destinations"]["kURIKey"]["prefixedURI"]
                    else:
                        self.log.warning("Unknown destination : %s", entry["destinations"])
                    if entry.get("message_data", {}) is not None and entry.get("message_data", {}).get("s", "") != "":
                        entry["package"] = entry.get("message_data", {}).get("s", "")
                    elif entry.get("data", {}) is not None and isinstance(entry.get("data", {}), dict) and entry.get("data", {}).get("2", {}).get("7", "") != "":
                        entry["package"] = entry.get("data", {}).get("2", {}).get("7", "")
                    elif entry.get("queue_one_identifier", "") != "":
                        entry["package"] = entry["queue_one_identifier"]
                    else:
                        entry["package"] = ""
                        self.log.warning("No package for entry %s", entry)
                else:
                    pass
                entry["sourceTable"] = row
                self.results.append(entry)
        cur.close()
        conn.close()

    def _extract_idstatuscache_database(self, database_path):
        self._recover_sqlite_db_if_needed(database_path)
        conn = self._open_sqlite_db(database_path)

        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT
                    *
                FROM kvtable;
            """
            )
        except sqlite3.DatabaseError:
            self.log.warning("IDStatusCache database %s is probably malformed, skipping it.", database_path)
            return

        rows = list(cur)
        headings = [description[0] for description in cur.description]
        previous_id = 0
        previous_date = "1970-01-01 00:00:00"
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                entry[headings[index]] = value

            entry["value"] = recursive_resolve(entry.get("value", []))
            entry["isodate"] = convert_unix_to_iso(entry.get("date", ""))
            entry["entry_type"] = "bd"
            self.results.append(entry)

            if previous_id > 0:
                missing_amount = entry["ROWID"] - previous_id - 1
                if missing_amount > 0:
                    self.results.append({
                        "missing" : True,
                        "isodate" : previous_date,
                        "amount" : missing_amount,
                        "entry_type" : "bd_missing_start"
                    })

                    self.results.append({
                        "missing" : True,
                        "isodate" : entry["isodate"],
                        "amount" : missing_amount,
                        "type" : "bd_missing_end"
                    })

            previousId = entry["ROWID"]
            previousDate = entry["isodate"]

        cur.close()
        conn.close()

    def run(self) -> None:
        if self.is_backup:
            self._find_ios_database(backup_ids=IDSTATUSCACHE_BACKUP_IDS)
            self.log.info("Found IDStatusCache plist at path: %s", self.file_path)
            self._extract_idstatuscache_entries(self.file_path)
        elif self.is_fs_dump:
            for idstatuscache_path in self._get_fs_files_from_patterns(
                IDSTATUSCACHE_ROOT_PATHS
            ):
                self.file_path = idstatuscache_path
                self.log.info("Found IDStatusCache plist at path: %s", self.file_path)
                self._extract_idstatuscache_entries(self.file_path)
            for new_idstatuscache_path in self._get_fs_files_from_patterns(
                IDSTATUSCACHE_ROOT_DB_PATHS
            ):
                self.file_path = new_idstatuscache_path
                self.log.info("Found IDStatusCache db (new) at path: %s", self.file_path)
                self._extract_idstatuscache_database(self.file_path)
            for firewall_idstatuscache_path in self._get_fs_files_from_patterns(
                IDSTATUSCACHE_FIREWALL_DB_PATHS
            ):
                self.file_path = firewall_idstatuscache_path
                self.log.info("Found IDStatusCache db (firewall) at path: %s", self.file_path)
                self._extract_idstatuscache_firewall_database(self.file_path)
            for gossip_idstatuscache_path in self._get_fs_files_from_patterns(
                IDSTATUSCACHE_GOSSIP_DB_PATHS
            ):
                self.file_path = gossip_idstatuscache_path
                self.log.info("Found IDStatusCache db (gossip) at path: %s", self.file_path)
                self._extract_idstatuscache_gossip_database(self.file_path)
            for other_idstatuscache_path in self._get_fs_files_from_patterns(
                IDSTATUSCACHE_OTHER_DB_PATHS
            ):
                self.file_path = other_idstatuscache_path
                self.log.info("Found IDStatusCache db (other) at path: %s", self.file_path)
                self._extract_idstatuscache_other_database(self.file_path)
            

        self.log.info(
            "Extracted a total of %d ID Status Cache entries", len(self.results)
        )
