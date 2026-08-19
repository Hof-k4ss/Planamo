# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os
import logging
import re
import sqlite3
from typing import Optional, Union

from mvt.common.utils import recursive_resolve, trim_prefix, convert_unix_to_iso

from ..base import IOSExtraction

HOMEKIT_BACKUP_ID = ["ebb20ff73819feeaf8b7b15ce2bde7295699ad3e"]
HOMEKIT3_BACKUP_ID = ["e2de31866e030d913242400a88f3293d4d740d28"]

HOMEKIT_PATHS = [
    "private/var/*/Library/homed/datastore.sqlite"
]

HOMEKIT3_PATHS = [
    "private/var/*/Library/homed/datastore3.sqlite"
]


class HomeKit(IOSExtraction):
    """This module extracts information from Homekit files."""

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
        self.emails = []

    def serialize(self, record: dict) -> Union[dict, list]:
        entries = []
        if record.get("isodate"):
            record_type = record["entry_type"]
            if record_type == "record":
                msg = f"Record {record.get('record_name')} with type {record.get('record_type')} (UUID : {record.get('record_uuid')}) was created"
                if record.get("emails"): msg+= f" by {record.get('emails')}"
                if record["record_record"]["RecordCtime"] != record["record_record"]["RecordMtime"]:
                    msg = f"Record {record.get('record_name')} with type {record.get('record_type')} (UUID : {record.get('record_uuid')}) was modified"
                    if record.get("emails"): msg+= f" by {record.get('emails')}"
                    entries.append({
                        "timestamp": record["record_record"]["RecordMtime"],
                        "module": self.__class__.__name__,
                        "event": record_type,
                        "data": msg
                    })
            elif record_type == "xact_block":
                msg = f"Event xact_block : id {record['id']}, data : {record['data']}"
                if record.get("emails"): msg+= f" by {record.get('emails')}"
            elif record_type == "record_v2":
                msg = f"Record {record.get('external_data', {}).get('RecordID', {}).get('RecordName')} with type {record.get('type')} (UUID : {record.get('uuid')}) was created by \"{record.get('external_data', {}).get('ModifiedByDevice', {})}\""
                if record.get("emails"): msg+= f" by {record.get('emails')}"
                if record.get('external_data', {}).get('RecordCtime', {}) != record.get('external_data', {}).get('RecordMtime', {}):
                    msg = f"Record {record.get('external_data', {}).get('RecordID', {}).get('RecordName')} with type {record.get('type')} (UUID : {record.get('uuid')}) was modified by \"{record.get('external_data', {}).get('ModifiedByDevice', {})}\""
                    if record.get("emails"): msg+= f" by {record.get('emails')}"
                    entries.append({
                        "timestamp": record.get('external_data', {}).get('RecordMtime', {}),
                        "module": self.__class__.__name__,
                        "event": record_type,
                        "data": msg
                    })

            entries.append({
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": record_type,
                "data": msg
            })
        return entries
    
    def _trim_mailto_tel(self, to_trim):
        if to_trim == {}: return ""
        if to_trim.startswith("mailto:"):
            return trim_prefix(to_trim, "mailto:")
        elif to_trim.startswith("tel:"):
            return trim_prefix(to_trim, "tel:")
        else:
            return to_trim

    def _get_identifier(self, entry):
        return(entry.get("HM.identifier", {}).get("NS.uuidbytes", {}))

    def _extract_email_from_URI_parent(self, entry):
        if entry == {}: return entry
        prefixedURI = entry.get("HMD.URI", {}).get("prefixedURI", {})
        return(self._trim_mailto_tel(prefixedURI))

    def _extract_email_from_handle(self, handle):
        if handle == {}: return handle
        return(self._extract_email_from_URI_parent(handle.get("HM.internal", {}).get("HM.account", {})))
    
    def _extract_email_from_device_destination(self, device):
        device_destination = device.get("HM.destination", {})
        if "/mailto:" in device_destination: return(device_destination.split("/mailto:")[1])
        elif "/tel:" in device_destination: return(device_destination.split("/tel:")[1])
        else: return device_destination
    
    def _extract_emails_from_account(self, account, is_remote=False):
        emails=[]
        account_identifier = self._get_identifier(account)
        for device in account.get("HM.devices", []):
            device_identifier = self._get_identifier(device)
            for handle in device.get("HM.handles", []):
                handle_email = self._extract_email_from_handle(handle)
                if handle_email not in emails: emails.append(handle_email)
                if is_remote: self.log.warning("%s has a handle to device %s which is tied to HomeKit's remote account %s", handle_email, device_identifier, account_identifier)
                else: self.log.info("%s has a handle to device %s which is tied to HomeKit's account %s", handle_email, device_identifier, account_identifier)
            destination_email = self._extract_email_from_device_destination(device)
            if destination_email not in emails: emails.append(destination_email)
            if is_remote: self.log.warning("%s is listed as a HomeKit's destination for device %s which is tied to HomeKit's remote account %s", destination_email, device_identifier, account_identifier)
            else: self.log.info("%s is listed as a HomeKit's destination for device %s which is tied to HomeKit's account %s", destination_email, device_identifier, account_identifier)
        account_destination = account.get("HM.destination")
        account_destination_email = self._trim_mailto_tel(account_destination)
        if account_destination_email not in emails: emails.append(account_destination_email)
        if is_remote: self.log.warning("%s is listed as a HomeKit's destination for remote account %s", account_destination_email, account_identifier)
        else: self.log.info("%s is listed as a HomeKit's destination for account %s", account_destination_email, account_identifier)
        for handle in account.get("HM.handles"):
            handle_email = self._extract_email_from_URI_parent(handle)
            if handle_email not in emails: emails.append(handle_email)
            if is_remote: self.log.warning("%s has a handle to HomeKit's remote account %s", handle_email, account_identifier)
            else: self.log.info("%s has a handle to HomeKit's account %s", handle_email, account_identifier)
        return(emails)

    def _extract_emails_from_home(self, home, primary_account_email):
        owner_emails = []
        home_id = home.get("homeUUID")
        for user in home.get("users", []):
            userID = user.get("userID", "")
            user_id_email = self._trim_mailto_tel(userID)
            owner_emails.append(user_id_email)
            if user_id_email != primary_account_email:
                self.log.info("%s is registered as a HomeKit user for home %s with primary account %s", user_id_email, home_id, primary_account_email)
            handle_email = self._extract_email_from_URI_parent(user.get("HM.handle", {}))
            if handle_email not in owner_emails:
                owner_emails.append(handle_email)
                self.log.info("%s has a handle to registered HomeKit user %s for home %s with primary account %s", handle_email, user_id_email, home_id, primary_account_email)
            userDisplayName = user.get("userDisplayName", {})
            user_display_name_email = self._trim_mailto_tel(userDisplayName)
            if user_display_name_email not in owner_emails:
                owner_emails.append(user_display_name_email)
                self.log.info("%s is the display name for registered HomeKit user %s for home %s with primary account %s", user_display_name_email, user_id_email, home_id, primary_account_email)
        return(owner_emails)

    def _extract_emails_from_records(self):
        for result in self.results:
            result["emails"] = []
            result_type = result["entry_type"]
            email_regexp = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}")
            r = email_regexp.search(str(result))
            if r:
                result["emails"].append(r.group())

            if result_type == "archive":
                primary_account_email = self._extract_email_from_URI_parent(result.get("value", {}).get("HM.primaryAccountHandle", {}))
                self.log.info("%s is registered as the primary account email", primary_account_email)
                result["emails"].append(primary_account_email)

                for home in result.get("value", {}).get("kHomesDataBlobKey", []):
                    result["emails"].extend(self._extract_emails_from_home(home, primary_account_email))
                
                for remote_account in result.get("value", {}).get("HM.remoteAccounts", []):
                    result["emails"].extend(self._extract_emails_from_account(remote_account, True))

                apple_account = result.get("value", {}).get("HM.appleAccount", {})
                result["emails"].extend(self._extract_emails_from_account(apple_account))

            elif result_type == "xact":
                xact_email = self._trim_mailto_tel(result.get("data", {}).get("idsURI", {}).get("prefixedURI", {}))
                if xact_email!="" and xact_email not in result["emails"]:
                    result["emails"].append(xact_email)
                    self.log.info("%s is appearing in HomeKit's xact data", xact_email)
            
            elif result_type == "xact_block":
                pass
            elif result_type == "record":
                pass 
            else:
                pass
   
    def check_indicators(self) -> None:
        if not self.indicators:
            return

        emails = []
        for result in self.results:
            for email in result.get("emails", []):
                ioc = self.indicators.check_email(email)
                if ioc:
                    self.log.warning("%s is a known malicious email. Seen on %s", email, result.get("isodate", "[missing date]"))
                    self.detected.append(result)
                    continue
            emails.extend(result.get("emails", []))
        emails = sorted(set(filter(lambda email:email != {} and email != "", emails)))
        self.log.info("Mails seen in the HomeKit files : %s", emails)
        

    def find_suspicious(self) -> None:
        #todo
        return
    
    def _process_homekit_file(self: str) -> None:
        conn = self._open_sqlite_db(self.file_path)
        cur = conn.cursor()

        # Get archive data
        try:
            cur.execute("""
                SELECT
                    *
                FROM archive;
            """)
            rows = list(cur)
            headings = [description[0] for description in cur.description]
            for row in rows:
                entry = {}
                for index, value in enumerate(row):
                    entry[headings[index]] = value

                entry["value"] = recursive_resolve(entry.get("value", []))
                entry["entry_type"] = "archive"
                self.results.append(entry)
        except sqlite3.OperationalError as e:
            self.log.warning("Error while reading the archive table: %s", e)

        # Get record data
        cur.execute("""
            SELECT
                record.name as record_name, record.type as record_type, record.uuid as record_uuid,
                record.parent_uuid as record_parent_uuid, record.encoding as record_encoding,
                record.record as record_record, record.data as record_data, store.name as store_name,
                zone_share.root as zone_share_root, zone_share.target as zone_share_target
            FROM record
            JOIN store ON record.store_id = store.id
            JOIN zone_share ON record.share_id = zone_share.id ;
        """)
        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                entry[headings[index]] = value

            entry["record_record"] = recursive_resolve(entry.get("record_record", []))
            entry["record_data"] = recursive_resolve(entry.get("record_data", []))
            entry["entry_type"] = "record"
            entry["isodate"] = entry["record_record"]["RecordCtime"]
            entry["event"] = "creation"
            self.results.append(entry)

        # Get xact data
        cur.execute("""
            SELECT
                *
            FROM xact;
        """)
        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                entry[headings[index]] = value

            entry["data"] = recursive_resolve(entry.get("data", []))
            entry["entry_type"] = "xact"
            self.results.append(entry)

        # Get xact_block data
        cur.execute("""
            SELECT
                *
            FROM xact_block;
        """)
        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                entry[headings[index]] = value

            entry["data"] = recursive_resolve(entry.get("data", []))
            entry["entry_type"] = "xact_block"
            if not entry["data"].get("HM.date"):
                #self.log.warning("Event ID %d (\"%s\") has no date %s", entry["id"], entry["data"]["HM.label"], entry)
                pass
            else:
                entry["isodate"] = entry["data"]["HM.date"]
            entry["event"] = entry["data"]["HM.label"]
            self.results.append(entry)

        cur.close()
        conn.close()
    
    def _process_homekit3_file(self) -> None:
        conn = self._open_sqlite_db(self.file_path)
        cur = conn.cursor()

        # Check if database is wiped

        cur.execute("""
            SELECT 
                name
            FROM sqlite_master;
        """)
        rows = list(cur)
        if rows == []:
            self.log.warning("Empty (no tables) HomeKit 3 database %s. Last modified on %s", self.file_path, self._get_file_last_modified_time(self.file_path))
            return

        # Get record_v2 data
        cur.execute("""
            SELECT
                *
            FROM record_v2;
        """)
        rows = list(cur)
        headings = [description[0] for description in cur.description]
        for row in rows:
            entry = {}
            for index, value in enumerate(row):
                entry[headings[index]] = value

            entry["uuid"] = entry["uuid"].hex()
            entry["parent_uuid"] = entry["parent_uuid"].hex()
            entry["external_data"] = recursive_resolve(entry.get("external_data", {}))
            entry["external_id"] = recursive_resolve(entry.get("external_id", {}))
            entry["model_data"] = recursive_resolve(entry.get("model_data", {}))
            entry["model_schema"] = recursive_resolve(entry.get("model_schema", {}))
            entry["push_data"] = recursive_resolve(entry.get("push_data", {}))
            
            if entry["external_data"] == "" or not entry.get("external_data", {}).get("RecordMtime"):
                #self.log.warning("Event ID %d (\"%s\") has no date %s", entry["id"], entry["data"]["HM.label"], entry)
                pass
            else:
                entry["isodate"] = entry["external_data"]["RecordMtime"]
            entry["entry_type"] = "record_v2"
            self.results.append(entry)

    def run(self) -> None:
        self._find_ios_database(
            backup_ids=HOMEKIT_BACKUP_ID, root_paths=HOMEKIT_PATHS
        )
        self.log.info("Found HomeKit file at path: %s", self.file_path)
        self._process_homekit_file()
        self._extract_emails_from_records()
        
        self.file_path = None
        self._find_ios_database(
            backup_ids=HOMEKIT3_BACKUP_ID, root_paths=HOMEKIT3_PATHS
        )
        self.log.info("Found HomeKit 3 file at path: %s", self.file_path)
        self._process_homekit3_file()

        self.log.info("Extracted a total of %d HomeKit records", len(self.results))