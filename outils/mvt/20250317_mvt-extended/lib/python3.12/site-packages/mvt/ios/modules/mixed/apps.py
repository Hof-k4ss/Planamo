# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import base64
import datetime
import glob
import json
import logging
import os
import plistlib
import struct

from typing import Optional, Union

from mvt.common.module import DatabaseNotFoundError

from ..base import IOSExtraction

APPS_PATHS = [
    "private/var/containers/Bundle/Application/*"
]

APPS_ARCHIVE_PATHS = [
    "private/var/containers/Bundle/Application/*/iTunesMetadata.plist",
    "private/var/containers/Bundle/Application/*/*.app/SC_Info/*.sinf"
]

# Source : https://archive.ph/PNfJ5 & https://github.com/KJCracks/Clutch/blob/master/Clutch/scinfo.m
end_blobs_int = [ "asdt", "key "] # names which should stop the processing
end_blobs_str = ["frma", "name"] # names which should stop the processing
end_blobs_blob = ["schm", "user", "crdt", "iviv", "priv", "sign", "UUID"] # names which should stop the processing
sinf_kval_items = [b"veID", b"plat", b"aver", b"tran", b"sing", b"song", b"tool", b"medi", b"mode", b"hi32"] # sinf_kval structures

class Apps(IOSExtraction):
    """This module extracts information about the apps installed on the device."""

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
        application_name = list(record.keys())[0]
        application_data = record[application_name]
        application_data_username = f"{application_data.get('SC_info').get('sinf').get('schi').get('name')}" if application_data.get('SC_info') and application_data.get('SC_info').get('sinf') and application_data.get('SC_info').get('sinf').get('schi') else ""       
        purchase_date = application_data.get('ItunesMetadata').get('com.apple.iTunesStore.downloadInfo').get('purchaseDate') if application_data.get('ItunesMetadata') and application_data.get('ItunesMetadata').get('com.apple.iTunesStore.downloadInfo') else "1970-01-01 00:00:00"
        apple_id = application_data.get('ItunesMetadata').get('com.apple.iTunesStore.downloadInfo').get('accountInfo').get('AppleID') if application_data.get('ItunesMetadata') and application_data.get('ItunesMetadata').get('com.apple.iTunesStore.downloadInfo') and application_data.get('ItunesMetadata').get('com.apple.iTunesStore.downloadInfo').get('accountInfo') else None
        item_name = application_data.get('ItunesMetadata').get('itemName') if application_data.get('ItunesMetadata') else ""
        bundle_short_version_string = application_data.get('ItunesMetadata').get('bundleShortVersionString') if application_data.get('ItunesMetadata') else ""
        artist_name = application_data.get('ItunesMetadata').get('artistName') if application_data.get('ItunesMetadata') else ""
        source_app = application_data.get('ItunesMetadata').get('sourceApp') if application_data.get('ItunesMetadata') else ""
        
        return {
            "timestamp": purchase_date,
            "module": self.__class__.__name__,
            "event": "app_purchased",
            "data": f"User \"{apple_id}\" ({application_data_username}) purchased \"{item_name}\" ({application_name}) version {bundle_short_version_string} from \"{artist_name}\" using \"{source_app}\"",
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            application_name = list(result.keys())[0]

            ioc = self.indicators.check_process(application_name)
            if ioc:
                self.log.warning("Malicious app is installed %s", application_name)
                result["matched_indicator"] = ioc
                self.detected.append(result)
            if application_name.startswith("tmp") or application_name.startswith("bd_tool"):
                self.log.warning("Found mention of a very suspicious application (named tmp* / bd_tool*) : \"%s\"", application_name)
                self.detected.append(result)

    def find_suspicious(self) -> None:
        if self.results_path is not None:
            mobile_container_manager_output_path = os.path.join(self.results_path, "mobile_container_manager.json")
            if os.path.exists(mobile_container_manager_output_path):
                application_names = []
                for record in self.results:
                    application_names.append(list(record.keys())[0])
                with open(mobile_container_manager_output_path, "r") as file_handle:
                    data = json.load(file_handle)
                for record in data:
                    code_signing_id_text = record.get("code_signing_id_text")
                    found = False
                    for application_name in application_names:
                        if application_name in code_signing_id_text:
                            found = True
                    if not found and not code_signing_id_text.startswith("com.apple."):
                        self.log.warning("Mobile Container Manager code_signing_id_text not in Apps : \"%s\"", code_signing_id_text) 

        for record in self.results:
            application_name = list(record.keys())[0]
            application_data = record[application_name]
            application_data_username = f"{application_data.get('SC_info').get('sinf').get('schi').get('name')}" if application_data.get('SC_info') and application_data.get('SC_info').get('sinf') and application_data.get('SC_info').get('sinf').get('schi') else None
            song = application_data.get('SC_info').get('sinf').get('schi').get('righ').get('song') if application_data.get('SC_info') and application_data.get('SC_info').get('sinf') and application_data.get('SC_info').get('sinf').get('schi') and application_data.get('SC_info').get('sinf').get('schi').get('righ') else None
            tool = application_data.get('SC_info').get('sinf').get('schi').get('righ').get('tool') if application_data.get('SC_info') and application_data.get('SC_info').get('sinf') and application_data.get('SC_info').get('sinf').get('schi') and application_data.get('SC_info').get('sinf').get('schi').get('righ') else None
            key = application_data.get('SC_info').get('sinf').get('schi').get('righ').get('key') if application_data.get('SC_info') and application_data.get('SC_info').get('sinf') and application_data.get('SC_info').get('sinf').get('schi') and application_data.get('SC_info').get('sinf').get('schi').get('righ') else None
            purchase_date = application_data.get('ItunesMetadata').get('com.apple.iTunesStore.downloadInfo').get('purchaseDate') if application_data.get('ItunesMetadata') and application_data.get('ItunesMetadata').get('com.apple.iTunesStore.downloadInfo') else None
            apple_id = application_data.get('ItunesMetadata').get('com.apple.iTunesStore.downloadInfo').get('accountInfo').get('AppleID') if application_data.get('ItunesMetadata') and application_data.get('ItunesMetadata').get('com.apple.iTunesStore.downloadInfo') and application_data.get('ItunesMetadata').get('com.apple.iTunesStore.downloadInfo').get('accountInfo') else None
            source_app = application_data.get('ItunesMetadata').get('sourceApp') if application_data.get('ItunesMetadata') else None
            item_name = application_data.get('ItunesMetadata').get('itemName') if application_data.get('ItunesMetadata') else None
            item_id = application_data.get('ItunesMetadata').get('itemId') if application_data.get('ItunesMetadata') else None
            software_version_bundle_id = application_data.get('ItunesMetadata').get('softwareVersionBundleId') if application_data.get('ItunesMetadata') else None
            bundle_version = application_data.get('ItunesMetadata').get('bundleVersion') if application_data.get('ItunesMetadata') else None
            bundle_short_version_string = application_data.get('ItunesMetadata').get('bundleShortVersionString') if application_data.get('ItunesMetadata') else None
            device_based_vpp = application_data.get('ItunesMetadata').get('DeviceBasedVPP') if application_data.get('ItunesMetadata') else None
            artist_name = application_data.get('ItunesMetadata').get('artistName') if application_data.get('ItunesMetadata') else None
            is_auto_download = application_data.get('ItunesMetadata').get('is-auto-download') if application_data.get('ItunesMetadata') else None
            is_factory_install = application_data.get('ItunesMetadata').get('isFactoryInstall') if application_data.get('ItunesMetadata') else None
            launch_prohibited = application_data.get('ItunesMetadata').get('launchProhibited') if application_data.get('ItunesMetadata') else None
            release_date = application_data.get('ItunesMetadata').get('releaseDate') if application_data.get('ItunesMetadata') else None
            
            logging_phrase = f"On {purchase_date}, user \"{apple_id}\" ({application_data_username}) purchased \"{item_name}\" ({application_name}) version {bundle_short_version_string} from \"{artist_name}\" using \"{source_app}\""

            if source_app and source_app != "com.apple.AppStore":
                self.log.info(f"Install not from the app store - {logging_phrase}")

            if application_data.get("SC_info") and application_data.get("SC_info").get("UUID") and source_app and not source_app in ["com.apple.dmd", "dmd"]:
                self.log.warning(f"UUID and install not from dmd - {logging_phrase}")
                self.detected.append(record)

            if purchase_date and purchase_date == "" and source_app and not source_app in ["com.apple.dmd", "dmd"]:
                self.log.warning(f"No purchaseDate and install not from dmd - {logging_phrase}")
                self.detected.append(record)

            if song and item_id and song != item_id:
                self.log.warning(f"Mismatch between song and itemId - {logging_phrase}")
                self.detected.append(record)

            if application_name and software_version_bundle_id and application_name != software_version_bundle_id:
                self.log.warning(f"Mismatch between application name and softwareVersionBundleId - {logging_phrase}")
                self.detected.append(record)

            if apple_id is None and device_based_vpp is not None and not device_based_vpp:
                self.log.warning(f"No AppleID and DeviceBasedVPP is set to False - {logging_phrase}")
                self.detected.append(record)

            if bundle_short_version_string == "1.0.0" or bundle_version == "1.0.0":
                self.log.warning(f"Version 1.0.0 - {logging_phrase}")
                self.detected.append(record)
            
            if is_auto_download:
                self.log.warning(f"Auto download - {logging_phrase}")
                self.detected.append(record)

            if is_factory_install:
                self.log.warning(f"Factory install - {logging_phrase}")
                self.detected.append(record)

            if launch_prohibited:
                self.log.warning(f"Launch prohibited - {logging_phrase}")
                self.detected.append(record)

            if purchase_date and purchase_date != "" and release_date and release_date != "":
                datetime_purchase_date = datetime.datetime.strptime(purchase_date, "%Y-%m-%dT%H:%M:%SZ")
                datetime_release_date = datetime.datetime.strptime(release_date, "%Y-%m-%dT%H:%M:%SZ")
                if datetime_purchase_date < datetime_release_date:
                    self.log.warning(f"Purchase date sooner than release date - {logging_phrase}")
                    self.detected.append(record)

            if application_data.get("SC_info") and application_data.get("SC_info").get("sinf") and (key == 1 or tool == 1345598006):
                self.log.warning(f"Potential Clutch usage - {logging_phrase}")
                self.detected.append(record)

    def scinfo_recursive_unpack(self, scinfo):
        returned_value = {}

        if scinfo == b"":
            # if we are reading an empty scinfo, return
            return returned_value

        if any(scinfo.startswith(returned_sinf_kval_item := sinf_kval_item) for sinf_kval_item in sinf_kval_items):
            # if we match any of the sinf_kval, from sinf.schi.righ.*
            returned_sinf_kval_item = returned_sinf_kval_item.decode("utf8")
            read_value = scinfo[4:8] # we read 32 bits (the value)
            try:
                returned_value[returned_sinf_kval_item] = int(struct.unpack(">L", read_value)[0]) # we only read ints in sinf.schi.righ.*
            except:
                returned_value[returned_sinf_kval_item] = read_value
            if returned_sinf_kval_item == "mode":
                if not scinfo[8:].startswith(b'hi32'):
                    returned_value["padding"] = base64.b64encode(scinfo[8:]).decode("utf8") # we read the padding + extra unknown bytes
            elif returned_sinf_kval_item == "hi32":
                    returned_value["padding"] = base64.b64encode(scinfo[8:]).decode("utf8") # we read the padding + extra unknown bytes
            else:
                returned_value.update(self.scinfo_recursive_unpack(scinfo[8:])) # we move to the next bytes
            return(returned_value)

        try:
            # we try to decode a sinf_atom
            size, name = struct.unpack(">L4s", scinfo[0:8])
            name = name.decode("utf8")
        except:
            self.log.warning("We were unable to decode a scinfo")
            return(scinfo)
        if (name in end_blobs_int or name in end_blobs_str or name in end_blobs_blob):
                # if the name if the name of an end blob, we don't need to recursively handle it
                # UUID is an end node because it's format could not be reversed
                read_value = scinfo[8:size] # we read the value
                if name in end_blobs_int: returned_value[name] = int(struct.unpack(">L", read_value)[0]) # we unpack and convert to int
                elif name in end_blobs_str: returned_value[name] = read_value.rstrip(b"\x00").decode("utf8") # we decode strings and strip padding
                elif name in end_blobs_blob: returned_value[name] = base64.b64encode(read_value).decode("utf8") # we base64-encode bytes
                returned_value.update(self.scinfo_recursive_unpack(scinfo[size:])) # we move to the next bytes
                return(returned_value)
        else:
            # we are handling sinf, schi, righ, which are sinf_atom or array of sinf_kval
            blob = struct.unpack(">%dc" % (size - 8), scinfo[8:size]) # we read the value
            new_blob = b"".join(blob) # we join the tuple into a bytearray
            returned_value[name] = self.scinfo_recursive_unpack(new_blob) # we recursively handle the value
            returned_value.update(self.scinfo_recursive_unpack(scinfo[size:])) # we move to the next bytes
            return(returned_value)

    def run(self) -> None:
        if self.is_backup:
            info_path = os.path.join(self.target_path, "Info.plist")
            if not os.path.exists(info_path):
                raise DatabaseNotFoundError("No Info.plist at backup path, unable to extract apps "
                                            "information")

            with open(info_path, "rb") as handle:
                info = plistlib.load(handle)
            applications = info.get("Applications")
            if applications:
                for application_name, application_data in applications.items():
                    application = {}
                    sc_info = application_data.get("ApplicationSINF")
                    if sc_info:
                        sc_info_parsed = self.scinfo_recursive_unpack(sc_info)
                        application["SC_info"] = sc_info_parsed

                    itunes_metadata_plist = application_data.get("iTunesMetadata")
                    if itunes_metadata_plist:
                        itunes_metadata = plistlib.loads(itunes_metadata_plist)
                        application["ItunesMetadata"] = itunes_metadata

                    self.results.append({application_name:application})
            else:
                self.log.warning("It seems no applications are installed")

        elif self.is_fs_dump:
            if self.is_archive: all(self._copy_fs_files_from_patterns(APPS_ARCHIVE_PATHS))
            for app_path in self._get_fs_files_from_patterns(APPS_PATHS):
                application = {}
                itunes_metadata_plist_file = os.path.join(self.target_path, app_path, "iTunesMetadata.plist")
                if not os.path.exists(itunes_metadata_plist_file):
                    app_names = glob.glob(os.path.join(self.target_path, app_path, "*.app"))
                    for app_name in app_names:
                        self.log.info(f"Application {app_name} has no iTunesMetadata.plist")
                    continue
                with open(itunes_metadata_plist_file, "rb") as handle:
                    itunes_metadata = plistlib.load(handle)
                application["ItunesMetadata"] = itunes_metadata
                bundle_id = itunes_metadata.get("softwareVersionBundleId", "Unknown")
                if bundle_id == "Unknown":
                    self.log.warning("Missing bundle_id : %s", application)
                SC_info_files = glob.glob(os.path.join(self.target_path, app_path, "*.app", "SC_Info", "*.sinf"))
                for SC_info in SC_info_files:
                    with open(SC_info, "rb") as sc_info_handle:
                        sc_info_parsed = self.scinfo_recursive_unpack(sc_info_handle.read())
                        application["SC_info"] = sc_info_parsed
                self.results.append({bundle_id:application})
        self.log.info("Extracted a total of %d applications",
                      len(self.results))
        self.find_suspicious()