# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import binascii
import contextlib
import gzip
import logging
import ndjson
import os
import struct
import tempfile

from typing import Optional, Union

from ..base import IOSExtraction

FSEVENTS_PATH = [
    "private/var/.fseventsd/*"
]

EVENTMASK = {
    0x00000000: 'None',
    0x00000001: 'FolderEvent',
    0x00000002: 'Mount',
    0x00000004: 'Unmount',
    0x00000020: 'EndOfTransaction',
    0x00000800: 'LastHardLinkRemoved',
    0x00001000: 'HardLink',
    0x00004000: 'SymbolicLink',
    0x00008000: 'FileEvent',
    0x00010000: 'PermissionChange',
    0x00020000: 'ExtendedAttrModified',
    0x00040000: 'ExtendedAttrRemoved',
    0x00100000: 'DocumentRevisioning',
    0x00400000: 'ItemCloned',  # macOS HighSierra
    0x01000000: 'Created',
    0x02000000: 'Removed',
    0x04000000: 'InodeMetaMod',
    0x08000000: 'Renamed',
    0x10000000: 'Modified',
    0x20000000: 'Exchange',
    0x40000000: 'FinderInfoMod',
    0x80000000: 'FolderCreated',
    0x00000008: 'NOT_USED-0x00000008',
    0x00000010: 'NOT_USED-0x00000010',
    0x00000040: 'NOT_USED-0x00000040',
    0x00000080: 'NOT_USED-0x00000080',
    0x00000100: 'NOT_USED-0x00000100',
    0x00000200: 'NOT_USED-0x00000200',
    0x00000400: 'NOT_USED-0x00000400',
    0x00002000: 'NOT_USED-0x00002000',
    0x00080000: 'NOT_USED-0x00080000',
    0x00200000: 'NOT_USED-0x00200000',
    0x00800000: 'NOT_USED-0x00800000'
}

def enumerate_flags(flag, f_map):
    """
    Iterate through record flag mappings and enumerate.
    """
    # Reset string based flags to null
    f_type = []
    f_flag = []
    # Iterate through flags
    for i in f_map:
        if i & flag:
            if f_map[i] == 'FolderEvent' or \
                    f_map[i] == 'FileEvent' or \
                    f_map[i] == 'SymbolicLink' or \
                    f_map[i] == 'HardLink':
                f_type.append(f_map[i])
            else:
                f_flag.append(f_map[i])
    return f_type, f_flag

class FSEventRecord(dict):
    """
    FSEvent record structure.
    """
    def __init__(self, buf, offset, mask_hex):
        """
        """
        # Offset of the record within the fsevent file
        self.file_offset = offset
        # Raw record hex version
        self.header_hex = binascii.b2a_hex(buf)
        # Record wd or event id
        self.wd = struct.unpack("<Q", buf[0:8])[0]
        # Record wd_hex
        wd_buf = bytearray(buf[0:8])
        wd_buf.reverse()
        self.wd_hex = binascii.b2a_hex(wd_buf)
        # Enumerate mask flags, string version
        self.mask = enumerate_flags(
            struct.unpack(">I", buf[8:12])[0],
            EVENTMASK
        )

class FsEventFileHeader():
    """
    FSEvent file header structure.
        Each page within the decompressed begins with DLS1 or DLS2
        It is stored using a byte order of little-endian.
    """

    def __init__(self, buf, filename):
        """
        """
        # Name and path of current source fsevent file
        self.src_fullpath = filename
        # Page header 'DLS1' or 'DLS2'
        # Was written to disk using little-endian
        # Byte stream contains either "1SLD" or "2SLD", reversing order
        self.signature = buf[4] + buf[3] + buf[2] + buf[1]
        # Unknown raw values in DLS header
        # self.unknown_raw = buf[4:8]
        # Unknown hex version
        # self.unknown_hex = buf[4:8].encode("hex")
        # Unknown integer version
        # self.unknown_int = struct.unpack("<I", self.unknown_raw)[0]
        # Size of current DLS page
        self.filesize = struct.unpack("<I", buf[8:12])[0]

class FSEventHandler():
    """
    FSEventHandler iterates through and parses fsevents.
    """

    def __init__(self, src_fullpath, last_modified_date, current_modified_date, log, indicators, detected):
        """
        """

        self.src_fullpath = src_fullpath
        self.last_modified_date = last_modified_date
        self.current_modified_date = current_modified_date
        self.log = log
        self.indicators = indicators
        self.detected = detected
        self.files = []
        self.dls_version = 0
        
        # Begin FSEvent processing

        self.output, self.serialized = self._get_fsevent_files()

    def get_output(self):
        return self.output
    def get_serialized(self):
        return self.serialized

    @contextlib.contextmanager
    def skip_gzip_check(self):
        """
        Context manager that replaces gzip.GzipFile._read_eof with a no-op.
        This is useful when decompressing partial files, something that won't
        work if GzipFile does it's checksum comparison.
        stackoverflow.com/questions/1732709/unzipping-part-of-a-gz-file-using-python/18602286
        """
        _read_eof = gzip._GzipReader._read_eof
        gzip.GzipFile._read_eof = lambda *args, **kwargs: None
        yield
        gzip.GzipFile._read_eof = _read_eof

    def _get_fsevent_files(self):
        """
        get_fsevent_files will iterate through each file in the fsevents dir provided,
        and attempt to decompress the gzip. If it is unable to decompress,
        it will write an entry in the logfile. If successful, the script will
        check for a DLS header signature in the decompress gzip. If found, the contents of
        the gzip will be placed into a buffer and passed to the next phase of processing.
        """
        buf = ""

        # Name of source fsevent file
        self.src_filename = os.path.basename(self.src_fullpath)

        # Attempt to decompress the fsevent archive
        try:
            with self.skip_gzip_check():
                self.files = gzip.GzipFile(self.src_fullpath, "rb")
                buf = self.files.read()
        except Exception as e:
            self.log.warning("Error when parsing %s : %s", self.src_filename, e)
            return None, None

        # If decompress is success, check for DLS headers in the current file
        dls_chk = FSEventHandler.dls_header_search(self, buf, self.src_filename)

        # If check for DLS returns false, write information to logfile
        if dls_chk is False:
            #self.log.debug("Failed to find DLS Header for file %s", self.src_filename)
            # Continue to the next file in the fsevents directory
            return None, None

        # If DLSs were found, pass the decompressed file to be parsed
        output, serialized = FSEventHandler.parse(self, buf)
        return output, serialized

    def dls_header_search(self, buf, f_name):
        """
        Search within the unzipped file
        for all occurrences of the DLS magic header.
        There can be more than one DLS header in an fsevents file.
        The start and end offsets are stored and used for parsing
        the records contained within each DLS page.
        """
        self.file_size = len(buf)
        self.my_dls = []

        raw_file = buf
        dls_count = 0
        start_offset = 0
        end_offset = 0

        while end_offset != self.file_size:
            try:
                start_offset = end_offset
                page_len = struct.unpack("<I", raw_file[start_offset + 8:start_offset + 12])[0]
                end_offset = start_offset + page_len

                if raw_file[start_offset:start_offset + 4] == b'1SLD' or raw_file[start_offset:start_offset + 4] == b'2SLD' or raw_file[start_offset:start_offset + 4] == b'3SLD':
                    self.my_dls.append({'Start Offset': start_offset, 'End Offset': end_offset})
                    dls_count += 1
                else:
                    #self.log.debug("Error in length of page when finding page headers for file %s" % (f_name))
                    break
            except Exception:
                #self.log.debug("Error in length of page when finding page headers for file %s" % (f_name))
                break

        if dls_count == 0:
            # Return false to caller so that the next file will be searched
            return False
        else:
            # Return true so that the DLSs found can be parsed
            return True

    def parse(self, buf):
        """
        Parse the decompressed fsevent log. First
        finding other dates, then iterating through
        eash DLS page found. Then parse records within
        each page.
        """
        # Initialize variables
        pg_count = 0
        output = []
        serialized = []

        # Iterate through DLS pages found in current fsevent file
        for i in self.my_dls:
            # Assign current DLS offsets
            start_offset = self.my_dls[pg_count]['Start Offset']
            end_offset = self.my_dls[pg_count]['End Offset']

            # Extract the raw DLS page from the fsevents file
            raw_page = buf[start_offset:end_offset]

            self.page_offset = start_offset

            # Reverse byte stream to match byte order little-endian
            m_dls_chk = bytearray(raw_page[0:4])
            m_dls_chk.reverse()
            # Assign DLS version based off magic header in page
            if m_dls_chk == b"DLS1":
                self.dls_version = 1
            elif m_dls_chk == b"DLS2":
                self.dls_version = 2
            elif m_dls_chk == b"DLS3":
                self.dls_version = 3
            else:
                self.log.warning("%s: Unknown DLS Version." % (self.src_filename))
                break

            # Pass the raw page + a start offset to find records within page
            output_find_page_records, serialized = FSEventHandler.find_page_records(
                self,
                raw_page,
                start_offset
            )
            output.extend(output_find_page_records)
            # Increment the DLS page count by 1
            pg_count += 1
        self.files.close()
        return output, serialized

    def find_page_records(self, page_buf, page_start_off):
        """
        Input values are starting offset of current page and
        end offset of current page within the current fsevent file
        find_page_records will identify all records within a given page.
        """

        # Initialize variables
        fullpath = ''
        char = ''
        output = []
        serialized = []

        # Start, end offset of first record to be parsed within current DLS page
        start_offset = 12
        end_offset = 13

        len_buf = len(page_buf)

        # Call the file header parser for current DLS page
        try:
            FsEventFileHeader(
                page_buf[:13],
                self.src_fullpath
            )
        except:
            self.log.warning(
                "%s\tError: Unable to parse file header at offset %d\n" % (
                    self.src_filename,
                    page_start_off
                )
            )

        # Account for length of record for different DLS versions
        # Prior to HighSierra
        if self.dls_version == 1:
            bin_len = 13
            rbin_len = 12
        # HighSierra
        elif self.dls_version == 2:
            bin_len = 21
            rbin_len = 20
        # DLS3
        elif self.dls_version == 3:
            bin_len = 25
            rbin_len = 24
        else:
            pass

        # Iterate through the page.
        # Valid record check should be true while parsing.
        # If an invalid record is encounted (occurs in carved gzips)
        # parsing stops for the current file
        while len_buf > start_offset:
            # Grab the first char
            char = page_buf[start_offset:end_offset].hex()

            if char != '00':
                # Replace non-printable char with nothing
                if str(char).lower() == '0d' or str(char).lower() == '0a':
                    self.log.warning('%s\tInfo: non-printable char %s in record fullpath at '
                                       'page offset %d. Parser removed char for reporting '
                                       'purposes.\n' % \
                                       (self.src_filename, char, page_start_off + start_offset))
                    char = ''
                # Append the current char to the full path for current record
                fullpath = fullpath + char
                # Increment the offsets by one
                start_offset += 1
                end_offset += 1
                # Continue the while loop
                continue
            elif char == '00':
                # When 00 is found, then it is the end of fullpath
                # Increment the offsets by bin_len, this will be the start of next full path
                start_offset += bin_len
                end_offset += bin_len

            # Decode fullpath that was stored as hex
            fullpath = bytes.fromhex(fullpath).decode("utf-8").replace('\t', '')
            # Store the record length
            record_len = len(fullpath) + bin_len

            # Account for records that do not have a fullpath
            if record_len == bin_len:
                # Assign NULL as the path
                fullpath = "NULL"

            # Assign raw record offsets #
            r_start = start_offset - rbin_len
            r_end = start_offset

            # Strip raw record from page buffer #
            raw_record = page_buf[r_start:r_end]

            # Strip mask from buffer and encode as hex #
            mask_hex = "0x" + raw_record[8:12].hex()

            # Account for carved files when record end offset
            # occurs after the length of the buffer
            if r_end > len_buf:
                continue

            # Set fs_node_id to empty for DLS version 1
            # Prior to HighSierra
            if self.dls_version == 1:
                fs_node_id = ""
            # Assign file system node id if DLS version is 2
            # Introduced with HighSierra
            if self.dls_version == 2:
                fs_node_id = struct.unpack("<q", raw_record[12:])[0]
            # Assign file system node id if DLS version is 3
            if self.dls_version == 3:
                fs_node_id = struct.unpack("<q", raw_record[12:20])[0]
                unknown = struct.unpack("<i", raw_record[20:24])[0]

            record_off = start_offset + page_start_off

            record = FSEventRecord(raw_record, record_off, mask_hex)

            f_path, f_name = os.path.split(fullpath)
            # Assign our current records attributes
            attributes = {
                'id': record.wd,
                'id_hex': record.wd_hex.decode("ascii") + " (" + str(record.wd) + ")",
                'fullpath': os.path.join("/private/var",fullpath),
                'filename': f_name,
                'type': record.mask[0],
                'flags': record.mask[1],
                'mask': mask_hex,
                'node_id': fs_node_id,
                'record_end_offset': record_off,
                'source': self.src_fullpath,
                'date_not_before': self.last_modified_date,
                'date_not_after': self.current_modified_date,
            }
            output.append(attributes)
            if attributes.get("date_not_before"):
                serialized.append ({
                    "timestamp": attributes["date_not_before"],
                    "module": "FSEvents",
                    "event": "date_not_before",
                    "data": f"Type : {attributes.get('type')}, Flags : {attributes.get('flags')}, Path : {attributes.get('fullpath')}",
                })
            if attributes.get("date_not_after"):
                serialized.append ({
                    "timestamp": attributes["date_not_after"],
                    "module": "FSEvents",
                    "event": "date_not_after",
                    "data": f"Type : {attributes.get('type')}, Flags : {attributes.get('flags')}, Path : {attributes.get('fullpath')}",
                })
            if f_name.startswith("panic-full-"):
                self.log.warning("Panic file ! %s", f_name)
                self.detected.append(attributes)
            if "/.ssh/" in attributes.get("fullpath"):
                self.log.warning("Modification of the .ssh folder : %s between %s and %s", attributes.get("fullpath"), attributes.get("date_not_before"), attributes.get("date_not_after"))
                self.detected.append(attributes)
            if "/no_log" in attributes.get("fullpath"):
                self.log.warning("Modification of a no_log file : %s between %s and %s", attributes.get("fullpath"), attributes.get("date_not_before"), attributes.get("date_not_after"))
                self.detected.append(attributes)
            if "Removed" in attributes.get("flags"):
                if f_name.endswith(".ips") and "/Retired/" not in attributes.get("fullpath"):
                    if not ("Extension-" in f_name or f_name.startswith("pppd-") or f_name.startswith("AppProxy-iOS-") or f_name.startswith("stacks") or f_name.startswith(".") or f_name.startswith("SiriSearchFeedback") or f_name.startswith("WiFiLQMMetrics") or f_name.startswith("DiagnosticRequest_") or f_name.startswith("transparencyd-") or f_name.startswith("LowBatteryLog") or f_name.startswith("JetsamEvent") or ".cpu_resource-" in f_name or ".wakeups_resource-" in f_name or ".diskwrites_resource-" in f_name):
                        self.log.warning("Deletion of an IPS file : %s between %s and %s", attributes.get("fullpath"), attributes.get("date_not_before"), attributes.get("date_not_after"))
                        self.detected.append(attributes)

            if self.indicators:
                ioc = self.indicators.check_file_path(attributes["fullpath"])
                if ioc:
                    self.log.warning("Found a known malicious file name at path: %s", attributes["fullpath"])
                    attributes["matched_indicator"] = ioc
                    self.detected.append(attributes)

                ioc = self.indicators.check_file_path_process(attributes["fullpath"])
                if ioc:
                    self.log.warning("Found known suspicious process name mentioned in file at path \"%s\" matching indicators from \"%s\"",
                        attributes["fullpath"], ioc["name"])
                    attributes["matched_indicator"] = ioc
                    self.detected.append(attributes)

            fullpath = ''
        return output, serialized

class FSEvents(IOSExtraction):
    """This module extracts information from fseventsd files."""

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
        returned = []
        if record.get("date_not_before"):
            returned.append ({
                "timestamp": record["date_not_before"],
                "module": self.__class__.__name__,
                "event": "date_not_before",
                "data": f"Type : {record.get('type')}, Flags : {record.get('flags')}, Path : {record.get('fullpath')}",
            })
        if record.get("date_not_after"):
            returned.append ({
                "timestamp": record["date_not_after"],
                "module": self.__class__.__name__,
                "event": "date_not_after",
                "data": f"Type : {record.get('type')}, Flags : {record.get('flags')}, Path : {record.get('fullpath')}",
            })
        return returned

    def check_indicators(self) -> None:
        if not self.indicators:
            return

    def run(self) -> None:
        if not self.module_options.get("fsevents", None):
            self.log.info("The \"--fsevents\" option was not specified, not running %s module.", self.__class__.__name__)
            return
        self.results = []
        if self.results_path:
            self.tmp_local_path = os.path.join(self.results_path, next(tempfile._get_candidate_names()))
            name = self.get_slug()
            results_file_name = f"{name}.jsonl.gz"
            results_json_path = os.path.join(self.results_path, results_file_name)
            timeline_file_name = f"{name}_timeline.jsonl.gz"
            timeline_json_path = os.path.join(self.results_path, timeline_file_name)
        last_modified_date = "1970-01-01 00:00:00"
        fsevent_paths = list(self._get_fs_files_from_patterns(FSEVENTS_PATH))
        fsevent_paths_without_folder = [val for val in fsevent_paths if not os.path.basename(val) == "fseventsd-uuid"]
        fsevent_paths_sorted = sorted(fsevent_paths_without_folder, key=lambda h: int(os.path.basename(h), 16))
        for fsevent_path in fsevent_paths_sorted:
            self.file_path = fsevent_path
            current_modified_date = self._get_file_last_modified_time(self.file_path)
            if os.path.basename(self.file_path) == "fseventsd-uuid":
                continue
            fseventhandler_instance = FSEventHandler(self.file_path, last_modified_date, current_modified_date, self.log, self.indicators, self.detected)
            fsevent_parsed = fseventhandler_instance.get_output()
            serialized_parsed = fseventhandler_instance.get_serialized()
            if fsevent_parsed and self.results_path:
                with gzip.open(results_json_path, "at") as fh:
                    ndjson.dump(fsevent_parsed, fh)
            else:
                #self.log.debug("%s fsevent file has empty results", fsevent_path)
                pass
            if serialized_parsed and self.results_path:
                with gzip.open(timeline_json_path, "at") as fh:
                    ndjson.dump(serialized_parsed, fh)
            else:
                #self.log.debug("%s fsevent file has empty results", fsevent_path)
                pass
            last_modified_date = current_modified_date
        self.log.info("Parsed %d fseventsd entries", len(fsevent_paths))
