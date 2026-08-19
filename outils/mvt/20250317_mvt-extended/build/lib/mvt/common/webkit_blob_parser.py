"""WebKit Cache file parser

TODO:
* Manage checksum computation from salt file
* Manage certification chain case (need examples to manage it)
"""
import collections
import datetime
import hashlib
import os
import re
import ssl
import struct
import tempfile

import OpenSSL
from OpenSSL import crypto
import pyasn1.codec.ber.decoder as ber_decoder
import dateutil.parser

ASN_START_RE = re.compile(b"\x31\x82(..)\x30", re.ASCII | re.DOTALL)
CERT_START_RE = re.compile(b"\x04\x82(..)\x30\x82(..)", re.ASCII | re.DOTALL)

class FormatError(Exception):
    ...

class ParsingError(ValueError):
    ...

def debug_hex(data: bytearray) -> str:
    return ":".join(map(lambda x: 32 <= x <= 127 and f" {chr(x)}" or f"{x:02x}",  data))

class CacheFile:
    """Webkit cache file parser.

    Attributes:
        extracted_data [collections.OrderedDict[str,str]]:
            extracted information from cache file
        path [pathlib.Path]: path of the parsed cache file
        content [bytes]: raw content of the cache file
        cursor [int]: cursor used while parsing cache file
        end_cursor [int]: cursor used while parsing cache file (from the end)
        hasher [hashlib.sha1]: current context of file hashing
        asn1_fragment_content: extracted ASN1 content of Certifacte Trust
        certificates: extracted certificates content of Certifacte Trust
        debug_idx [int]: counter for debug pritting

    Recommended usage:
    > cache = CacheFile(<path>)
    > cache.extract()
    > cache.decode_asn1()
    > cache.decode_certificates()
    > cache.extracted_data
    """
    def __init__(self, path, salt=b"") -> None:
        """Create the parser for the file located at `path`.

        Args:
            path [pathlib.Path]: path of the cache file to parse
            salt [bytes]: salt used in the file

        Raises:
            OsError: if file is not readable
        """
        self.path = path
        self.content: bytes = None
        self.cursor = 0
        self.end_cursor = 0
        self.extracted_data = collections.OrderedDict()
        self.asn1_fragment_content = None
        self.certificates = []
        self.hasher = hashlib.sha1()
        self.debug_idx = 0
        self._read()

    def _read(self) -> None:
        """Read content of cache file.

        Raises:
            OsError: if file is not readable
        """
        with open(self.path, "rb") as blob_fd:
            self.content = blob_fd.read()
        self.end_cursor = len(self.content)

    #### Checksum management fonctions

    def get_check_checksum(self) -> (str, str, bool):
        #self.hasher.update(self.content[:-20]) TODO
        result = self.hasher.hexdigest().upper()
        expected = self.decode_digest("sha1")
        return (expected, result, expected == result)

    def update_checksum(self, const_value, value):
        """ Const values are located in `PersistentEncoder.h`
        """
        self.hasher.update(const_value)
        self.hasher.update(value)

    #### Low level cursor management functions

    def read_next(self, length: int) -> bytes:
        """Return `length` bytes after the current cursor in cache file.

        Args:
            length [int]: number of bytes to return

        Raises:
            ValueError: if the extracted contact have not the expected length

        Returns
            bytes: the extracted part of the cache file
        """
        end_cursor = self.cursor+length
        if end_cursor > self.end_cursor:
            error_msg = f"[{self.cursor}:{self.cursor+length}]: fail to extract given {length} length (max cursor is {self.end_cursor})"
            raise ValueError(error_msg)
        retrieved_content = self.content[self.cursor:end_cursor]
        if len(retrieved_content) != length:
            error_msg = f"[{self.cursor}:{self.cursor+length}]: fail to extract given {length} length (produce {retrieved_content})"
            raise ValueError(error_msg)
        return retrieved_content

    def pop_next(self, length: int) -> bytes:
        """Return `length` bytes after the current cursor and move it after.

        Args:
            length [int]: number of bytes to return, move cursor of this length

        Raises:
            ValueError: if the extracted contact have not the expected length

        Returns
            bytes: the extracted part of the cache file
        """
        popped_content = self.read_next(length)
        self.cursor += length
        return popped_content

    @property
    def pending_size(self) -> int:
        """Return `length` of pending available bytes from the cursor to the end of the file

        Returns
            int: length from the cursor to the end of the file
        """
        return len(self.content) - self.cursor

    #### Basic decoding functions

    def decode_bool(self) -> int:
        """Decode the unsigned (short) integer (8 bytes) at the current position.

        Raises:
            ValueError: if there is not enough available size or value is unexpected

        Return:
            int: the extracted integer
        """
        cursor = self.cursor
        boolean = self.pop_next(1)
        const = (3).to_bytes(1, "little")
        self.update_checksum(const, boolean)
        if boolean[0] == 0x00:
            return False
        elif boolean[0] == 0x01:
            return True
        else:
            error_msg = f"[{cursor}]: bad boolean value: {boolean.hex()} ({boolean})"
            raise ValueError(error_msg)

    def decode_u8(self) -> int:
        """Decode the unsigned (short) integer (1 bytes) at the current position.

        Raises:
            ValueError: if there is not enough available size

        Return:
            int: the extracted integer
        """
        data = self.pop_next(1)
        uchar = int.from_bytes(data, "little")
        const = (5).to_bytes(1, "little", signed=False)
        self.update_checksum(const, data)
        return uchar

    def decode_u16(self) -> int:
        """Decode the unsigned (short) integer (2 bytes) at the current position.

        Raises:
            ValueError: if there is not enough available size

        Return:
            int: the extracted integer
        """
        data = self.pop_next(2)
        short = int.from_bytes(data, "little")
        const = (7).to_bytes(2, "little", signed=False)
        self.update_checksum(const, data)
        return short

    def decode_u32(self) -> int:
        """Decode the unsigned (int) integer (4 bytes) at the current position.

        Raises:
            ValueError: if there is not enough available size

        Return:
            int: the extracted integer
        """
        data = self.pop_next(4)
        integer = int.from_bytes(data, "little")
        const = (11).to_bytes(4, "little", signed=False)
        self.update_checksum(const, data)
        return integer

    def decode_u64(self) -> int:
        """Decode the unsigned (long long) integer (8 bytes) at the current position.

        Raises:
            ValueError: if there is not enough available size

        Return:
            int: the extracted integer
        """
        data = self.pop_next(8)
        long_long = int.from_bytes(data, "little")
        const = (13).to_bytes(8, "little", signed=False)
        self.update_checksum(const, data)
        return long_long

    def decode_double(self) -> float:
        """Decode the double (8 bytes) at the current position.

        Raises:
            ValueError: if there is not enough available size

        Return:
            float: the extracted double
        """
        data = self.pop_next(8)
        double = struct.unpack('d', data)[0]
        const = (29).to_bytes(8, "little", signed=False)
        self.update_checksum(const, data)
        return double

    def decode_fixed_len(self, length: int) -> bytes:
        """Extract the given length of raw data from the content

        Raises:
            ValueError: if there is not enough available size

        Return:
            bytes: the extracted bytes
        """
        data = self.pop_next(length)
        const = (101).to_bytes(4, "little", signed=False) # sizeof(uint8_t*) = 4?
        self.update_checksum(const, data)
        return data

    def decode_cstring(self) -> str:
        """Decode the string at the current position.

        Raises:
            ValueError: if there is not enough available size or string size is too big
            UnicodeError: if the extracted bytes cannot be converted to string

        Return:
            str: the extracted string
        """
        length = self.decode_u32()
        if length == 0xffffffff: # max int
            return ""
        if length > self.pending_size:
            error_msg = f"[{self.cursor-4}:{self.cursor}]: bad word len {length} (too big, pending size si {self.pending})"
            raise ValueError(error_msg)
        return self.decode_fixed_len(length).decode()

    def decode_string(self) -> str:
        """Decode the string at the current position.

        Raises:
            ValueError:
              * if there is not enough available size
              * if string size is too big
              * if string type has wrong value
            UnicodeError: if the extracted bytes cannot be converted to string

        Return:
            str: the extracted string
        """
        length = self.decode_u32()
        if length == 0xffffffff: # max int
            return ""
        if length > self.pending_size:
            error_msg = f"[{self.cursor-4}:{self.cursor}]: bad word len {length} (too big, pending size si {self.pending_size})"
            raise ValueError(error_msg)
        if self.decode_bool():
            data = self.decode_fixed_len(length)
            return data.decode()
        else:
            data = self.decode_fixed_len(length)
            return data.decode("utf-16-le") # check between le and be

    def decode_digest(self, algo) -> str:
        """Decode the digest at the current position.

        Raises:
            ValueError: if there is not enough available size

        Return:
            str: the extracted string
        """
        length = {
            "md5": 16,
            "sha1": 20,
            "sha256": 32,
        }.get(algo, None)
        if length is None:
            error_msg = f"{algo} is not recognized. Your program is badly written."
            raise ValueError(error_msg)
        return self.decode_fixed_len(length).hex().upper()

    def decode_timestamp(self) -> datetime.datetime:
        """Decode the timestamp at the current position.

        Raises:
            ValueError: if there is not enough available size of value is not valid for a timestamp

        Return:
            datetime.datetime: the extracted datetime
        """
        data = self.decode_double()
        return datetime.datetime.fromtimestamp(data)

    def decode_field(self, field_type: str, *args, **kwargs) -> "T":
        """Decode the next field according the provided type

        Args:
            field_type: the type of the field to decode
            *args, **kwargs: the argument to transfert to the decoder

        Raises:
            ValueError: if there is not enough available size or field decoding type failed to be decoded
            UnicodeError: if the extracted bytes cannot be converted to string

        Return:
            type: the extracted value (type depends to `field_type`)
        """
        if field_type == "string":
            value = self.decode_string()
        elif field_type == "sha1":
            value = self.decode_digest("sha1")
        elif field_type == "u16":
            value = self.decode_u16()
        elif field_type == "u32":
            value = self.decode_u32()
        elif field_type == "u64":
            value = self.decode_u64()
        elif field_type == "double":
            value = self.decode_double()
        elif field_type == "bool":
            value = self.decode_bool()
        elif field_type == "timestamp":
            value = self.decode_timestamp()
        elif field_type == "vector":
            value = self.decode_vector(*args, **kwargs)
        elif field_type == "hashmap":
            value = self.decode_hash_map(*args, **kwargs)
        elif field_type == "checksum":
            value = self.get_check_checksum()
        else:
            raise TypeError(f"Try to extract inexistant '{field_type}'")
        return value

    def decode_hash_map(self, key_type: str, value_type: str, value_adapter = None) -> "HashMap[K, V]":
        """Decode the hashmap at the current position.

        Args:
            key_type [str]: the keys' type inside the decoded hash map
            value_type: the values' type inside the decoded hash map
            value_adapter [Optional[HashMap[key_type,Func[key_type,value_type]]]]:
                an optional dict that may contains decoded key value
                for each found decoded key value, the dict value is a function
                that convert the value to another one
            *args, **kwargs: the argument to transfert to the decoder

        Raises:
            ValueError: if there is not enough available size or key/value type failed to be decoded
            UnicodeError: if the extracted bytes cannot be converted to string (in case of string type)

        Return:
            `collections.OrderedDict[key_type, value_type]`
        """
        return_dict = collections.OrderedDict()
        dict_size = self.decode_u64()
        for idx in range(dict_size):
            try:
                key = self.decode_field(key_type)
            except ValueError as exc:
                raise ValueError(f"fail to decode hash map key n°{idx + 1}/{dict_size}: {exc}")
            try:
                value = self.decode_field(value_type)
            except ValueError as exc:
                raise ValueError(f"fail to decode hash map value n°{idx + 1}/{dict_size} for key '{key}': {exc}")
            if value_adapter and key in value_adapter:
                try:
                    value = value_adapter[key](value)
                except Exception as exc:
                    raise ValueError(f"fail to convert hash map value n°{idx + 1}/{dict_size} on key '{key}' with value '{value}': {exc}")
            return_dict[key] = value
        return return_dict

    def decode_vector(self, value_type: str) -> "List[V]":
        """Decode the vector at the current position.

        Args:
            value_type: the values' type inside the decoded vector

        Raises:
            ValueError: if there is not enough available size or value type failed to be decoded
            UnicodeError: if the extracted bytes cannot be converted to string (in case of string type)

        Return:
            List[value_type]: the extracted vector
        """
        return_list = list()
        list_size = self.decode_u64()
        for idx in range(list_size):
            try:
                value = self.decode_field(value_type)
            except ValueError as exc:
                raise ValueError(f"fail to decode vector value n°{idx + 1}/{list_size}: {exc}")
            return_list.append(value)
        return return_list

    def store(self, field: "str|List[str]", value) -> None:
        """Store the `value` in `self.extracted_data` attribute.

        Args:
            field [str|List[str]]: the key where the value is stored.
                If field is a string list, nested `collections.OrderedDict` are created to solve the path
        """
        if isinstance(field, str):
            self.extracted_data[field] = value
        else:
            current = self.extracted_data
            for f in field[:-1]:
                if not f in current:
                    current[f] = collections.OrderedDict()
                current = current[f]
            current[field[-1]] = value

    def ensure_string_is(self, expected_word: str) -> None:
        """Ensure that the extracted word at current pos. is the `decode_string`

        Args:
            expected_word [str]: the string value to found

        Raises:
            ValueError: if the word header has wrong format or mismatch with
                `decode_string`
            UnicodeError: if the extracted bytes cannot be converted to string
        """
        start_cursor = self.cursor
        found_word = self.decode_string()
        if found_word != expected_word:
            current_cursor = self.cursor
            self.cursor = start_cursor
            raise ValueError(f"[{start_cursor}:{current_cursor}]: '{found_word}' "
                             f"(found) ≠ '{expected_word}' (expected)")

    def extract_field(self, field: str, field_type: str, *args, **kwargs) -> None:
        """Decode and store the next value of type `field_type` with `field` name.

        Args:
            field [str|List[str]]: the key where the value is stored.
                If field is a string list, nested `collections.OrderedDict` are created to solve the path
            field_type: the type of the field to decode
            *args, **kwargs: the argument to transfert to the decoder

        Raises:
            ValueError: if there is not enough available size or field decoding type failed to be decoded
            UnicodeError: if the extracted bytes cannot be converted to string
        """
        try:
            value = self.decode_field(field_type, *args, **kwargs)
        except ValueError as err:
            raise ValueError(f"While parsing '{field}', {err}") from err
        else:
            self.store(field, value)

    def extract_enum_field(self, field: str, enum_values: "typing.List[typing.Any]") -> None:
        """Decode and store the next enumeration value with `field` name.

        Args:
            field [str|List[str]]: the key where the value is stored.
                If field is a string list, nested `collections.OrderedDict` are created to solve the path
            enums_values: the list of enum value
                field is decoded as `long long` and used as index of `enums_values`

        Raises:
            ValueError: if there is not enough available size or field decoding type failed to be decoded
        """
        try:
            value = self.decode_u64()
        except:
            raise ValueError(f"While parsing '{field}', {err}") from err
        else:
            max_value = len(enum_values)
            if 0 <= value < max_value:
                self.store(field, enum_values[value])
            else:
                raise ValueError(f"While parsing '{field}', get value {value} beyond of {max_value}")

    def extract_debug_field(self, length: int) -> None:
        """Decode an unkwown part of `length` size from the content and record it in different format.

        Args:
            length [int]: the size of the content to extract
        """
        field = f"unknown_{self.debug_idx}"
        self.debug_idx += 1
        content = self.content[self.cursor:self.cursor+length]
        self.extracted_data[field] = content
        self.extracted_data[f"{field}_hex"] = content.hex(":")
        self.extracted_data[f"{field}_len"] = len(content)
        self.cursor += length

    def debug(self):
        """Decode the pending content to parse and record it in different format.

        IMPORTANT: the decoded content is not consummed and can still be parsed
        """
        field = f"unknown_{self.debug_idx}"
        self.debug_idx += 1
        content = self.content[self.cursor:self.end_cursor]
        self.extracted_data[field] = content
        self.extracted_data[f"{field}_hex"] = content.hex(":")
        self.extracted_data[f"{field}_dbg"] = debug_hex(content)
        self.extracted_data[f"{field}_len"] = len(content)

    #### Parsing functions

    def extract(self) -> None:
        """Parse cache file.

        Raises:
            ValueError: if parse of the file fails
        """
        self.extract_metadata()
        base = self.cursor
        self.extract_debug_field(1)
        self.extract_payload(base)
        self.extract_response()
        self.extract_varying_request_headers()
        self.extract_redirection()
        if content := self.content[self.cursor:self.end_cursor]:
            self.extracted_data["pending_unknown"] = content
            self.extracted_data["pending_unknown_hex"] = content.hex(":")
            self.extracted_data["pending_unknown_dbg"] = debug_hex(content)
            self.extracted_data["pending_unknown_len"] = len(content)
        else:
            self.extracted_data["pending_unknown"] = None

    def extract_payload(self, metadata_offset: int) -> None:
        """Extract the payload according to `metadata_offset` and recorded sized

        Args:
            metadata_offset [int]: end position of _metadata_ block in the cache file

        Raises:
            ValueError: if parse of the file fails
        """
        if self.extracted_data["is_body_inline"]:
            content_base = metadata_offset + self.extracted_data["header_size"]
            content_end = content_base + self.extracted_data["content_size"]
            content = self.content[content_base:content_end]
            if content_end == self.end_cursor:
                self.end_cursor = content_base
            self.extracted_data["payload"] = content

    def extract_metadata(self) -> None:
        """Parse `RecordMetadata` field

        See `encodeRecordMetadata` function in `NetworkCacheStorage.cpp`

        Raises:
            ValueError: if headers has unexpected value
        """
        self.extracted_data["path"] = str(self.path)
        self.extract_field("version", "u32")
        if self.extracted_data["version"] != 16:
            if self.extracted_data["version"] > 30:
                raise FormatError(f"This cache program is build for version 16. Encountred version {self.extracted_data['version']}")
            raise ValueError(f"This cache program is build for version 16. Encountred version {self.extracted_data['version']}")
        self.extract_key()
        self.extract_field("timestamp", "timestamp")
        self.extract_field("header_hash", "sha1")
        self.extract_field("header_size", "u64")
        self.extract_field("content_hash", "sha1")
        self.extract_field("content_size", "u64")
        self.extract_field("is_body_inline", "bool")
        self.extract_field("metadata_checksum", "checksum")

    def extract_key(self) -> None:
        """Parse `m_key` field

        See `Cache:makeCacheKey` function in `NetworkCache.cpp`
        See `encodeForPersistence` function in `NetworkCacheCoders.cpp`

        Raises:
            ValueError: if headers has unexpected value
        """
        # Partition
        self.extract_field("domain", "string")
        # Type
        self.ensure_string_is("Resource")
        # Identifier
        self.extract_field("url", "string")
        # Range
        self.extract_field("range", "string")
        # Hash
        self.extract_field("filename", "sha1")
        # Partition hash
        self.extract_field("dirdirname", "sha1")

    def extract_response(self) -> None:
        """Parse `m_response` field

        See `ResponseData` struct in `ResourceResponseBase.h`

        Raises:
            ValueError: if response headers has unexpected value
        """
        self.ensure_string_is(self.extracted_data["url"])
        self.extract_field("mimetype", "string")
        self.extract_field("content_size", "u64")
        self.extract_field("encoding", "string")
        self.extract_field("http_status_text", "string")
        self.extract_field("http_version", "string")
        if not self.extracted_data["http_version"].startswith("HTTP"):
            raise ValueError(f"Wrong protocol: {protocol}")
        self.extract_response_headers()
        self.extract_field("http_status_code", "u16")
        self.extract_field("has_certificate_info", "bool")
        if self.extracted_data["has_certificate_info"]:
            self.extract_certificates_info()
        self.extract_enum_field("response_source", [
            "Unknown",
            "Network",
            "DiskCache",
            "DiskCacheAfterValidation",
            "MemoryCache",
            "MemoryCacheAfterValidation",
            "ServiceWorker",
            "ApplicationCache",
            "DOMCache",
            "InspectorOverride",
        ])
        self.extract_enum_field("response_type", [
            "Basic",
            "Cors",
            "Default",
            "Error",
            "Opaque",
            "Opaqueredirect",
        ])
        self.extract_enum_field("response_tainting", [
            "Basic",
            "Cors",
            "Opaque",
            "Opaqueredirect",
        ])
        self.extract_field("response_is_redirected", "bool")
        self.extract_enum_field("response_usedlegacy_tls", [False, True])
        self.extract_enum_field("response_was_private_relayed", [False, True])
        self.extract_field("response_is_range_requested", "bool")

    def extract_response_headers(self) -> None:
        """Parse response headers of the file.

        Number of responses headers may vary with a well defined structure

        Raises:
            ValueError: if response headers has unexpected value
        """
        self.extract_field("response_headers", "hashmap", "string", "string", HEADERS)
        if content_length := self.extracted_data["response_headers"].get("Content-Length"):
            content_size = self.extracted_data["content_size"]
            self.extracted_data["same-length"] = (content_length == content_size)
        else:
            self.extracted_data["same-length"] = ""

    def extract_varying_request_headers(self) -> None:
        """Parse `m_varyingRequestHeaders` field

        See `Entry::decodeStorageRecord` function in `NetworkCacheEntry.cpp`

        Raises:
            ValueError: if response headers has unexpected value
        """
        self.extract_field("has_varying_request_headers", "bool")
        if self.extracted_data["has_varying_request_headers"]:
            self.extract_field("varying_request_header", "hashmap", "string", "string", HEADERS)

    def extract_redirection(self) -> None:
        """Parse redirection related fields

        See `Entry::decodeStorageRecord` function in `NetworkCacheEntry.cpp`
        See `Coder<WebCore::ResourceRequest>::decodeForPersistence` in `WebCorePersistentCoders.cpp`
        See `ResourceRequestBase.h` for field definition

        Raises:
            ValueError: if response headers has unexpected value
        """
        redirection = self.decode_u8()
        is_redirect = redirection & 0x1 and True or False
        self.extracted_data["redirection_is_redirect"] = is_redirect
        is_private_relayed = redirection & 0x2 and True or False
        self.extracted_data["redirection_is_private_relayed"] = is_private_relayed
        redirect = collections.OrderedDict()
        if is_redirect:
            self.extract_field(["redirect_request", "url"], "string")
            self.extract_field(["redirect_request", "timeout_interval"], "double")
            self.extract_field(["redirect_request", "first_party_cookies"], "string")
            self.extract_field(["redirect_request", "http_method"], "string")
            self.extract_field(["redirect_request", "headers"], "hashmap", "string", "string", HEADERS)
            self.extract_field(["redirect_request", "content_disposition_fallback_array"], "vector", "string")
            self.extract_enum_field(["redirect_request", "cache_policy"], [
                "UseProtocolCachePolicy",
                "ReloadIgnoringCacheData",
                "ReturnCacheDataElseLoad",
                "ReturnCacheDataDontLoad",
                "DoNotUseAnyCache",
                "RefreshAnyCacheData",
            ])
            redirect["allow_cookies"] = self.decode_bool()
            self.extract_enum_field(["redirect_request", "same_site_disposition"], [
                "Unspecified",
                "SameSite",
                "CrossSite",
            ])
            redirect["is_top_site"] = self.decode_bool()
            self.extract_enum_field(["redirect_request", "resource_load_priority"], [
                "VeryLow",
                "Low",
                "Medium",
                "High",
                "VeryHigh",
            ])
            self.extract_enum_field(["redirect_request", "requester"], [
                "Unspecified",
                "Main",
                "XHR",
                "Fetch",
                "Media",
                "Model",
                "ImportScripts",
                "Ping",
                "Beacon",
                "EventSource",
            ])
            self.extract_field(["redirect_request", "is_app_initiated"], "bool")
        self.extract_field("has_max_age_cap", "bool")
        if self.extracted_data["has_max_age_cap"]:
            self.extract_field("max_age_cap", "timestamp")
        self.extract_field("headers_checksum", "checksum")

    def extract_certificates_info(self) -> None:
        """Parse certificate related fields

        See `Coder<WebCore::CertificateInfo>::decodeForPersistence` in `WebCorePersistentCoders.cpp`
        See `decodeSecTrustRef` in `WebCorePersistentCoders.cpp` for Trust certificate
        See `decodeCertificationChain` in `WebCorePersistentCoders.cpp` for CertificateChain (TODO)

        Raises:
            ValueError: if response headers has unexpected value
        """
        self.extract_enum_field("certificate_type", [
            "None",
            "CertificateChain",
            "Trust",
        ])
        if self.extracted_data["certificate_type"] == "CertificateChain":
            print("TODO: certificat en chaîne non implémenté")
            print("VECTOR OF ???")
            self.extract_field("certificate_chain", "vector", "string")
        elif self.extracted_data["certificate_type"] == "Trust":
            self.extract_field("has_certificate_trust", "bool")
            if self.extracted_data["has_certificate_trust"]:
                asn1_length = self.decode_u64()
                asn1_content = self.decode_fixed_len(asn1_length)
                if match := ASN_START_RE.match(asn1_content):
                    content_length = int.from_bytes(match.group(1), "big")
                    if asn1_length < content_length + 4:
                        raise ValueError("ASN1 length ({asn1_length}) is shorter than ASN1 content length ({content_length} + 4 of header)")
                    elif asn1_length > content_length + 4:
                        self.extracted_data["unknown_asn_part"] = asn1_content[content_length + 4:]
                    self.extracted_data["asn1"] = asn1_content
                else:
                    raise ValueError("No ASN1 header in `asn1_content`")

    #### Parsing functions
    def decode_asn1(self) -> None:
        if asn1 := self.extracted_data.get("asn1"):
            decoded_asn1 = ber_decoder.decode(asn1)[0]
            self.asn1_fragment_content = decoded_asn1.prettyPrint()
            #print_asn1_info(decoded_asn1)

    def decode_certificates(self) -> None:
        if asn1 := self.extracted_data.get("asn1"):
            for match in CERT_START_RE.finditer(asn1):
                length = int.from_bytes(match.group(1), "big")
                check_length = int.from_bytes(match.group(2), "big")
                if length != check_length + 4:
                    continue
                start = match.start() + 4
                cert_bytes = asn1[start:start + length]
                try:
                    x509 = crypto.load_certificate(crypto.FILETYPE_ASN1, cert_bytes)
                    cert_pem = crypto.dump_certificate(crypto.FILETYPE_PEM, x509)

                    temp_dir = tempfile.TemporaryDirectory()
                    temp_file_path = os.path.join(temp_dir.name, "temp")
                    with open(temp_file_path, "wb") as f:
                        f.write(cert_pem)
                    self.certificates.append(ssl._ssl._test_decode_cert(temp_file_path))
                    temp_dir.cleanup()
                except OpenSSL.crypto.Error as e:
                    continue
            del self.extracted_data["asn1"]


def print_asn1_info(asn1):
    """Print detail information about provided ASN1 object."""
    position = 0
    while True:
        try:
            print(f"Component By Position #{position}", asn1.getComponentByPosition(position))
        except Exception:
            break
        position += 1
    print("Component Type", asn1.getComponentType())
    print("Effective Tag Set", asn1.getEffectiveTagSet())
    print("Sub Type Spec", asn1.getSubtypeSpec())
    print("Tag Map", asn1.getTagMap())
    print("Tag Set", asn1.getTagSet())
    print("Type Id", asn1.getTypeId())

HEADERS = {
    "Date": dateutil.parser.parse,
    "Content-Length": int,
    "Expires": dateutil.parser.parse,
    "Last-Modified": dateutil.parser.parse,
}

def parse_blob(blob_path):
    cache = CacheFile(blob_path)
    try:
        cache.extract()
    except ValueError as exc:
        error_msg = f"{blob_path}: fail: {exc}. Continuing"
        cache.decode_asn1()
        cache.decode_certificates()
        print(error_msg)
        #raise ParsingError(error_msg, cache.extracted_data)
    cache.decode_asn1()
    cache.decode_certificates()

    entry = cache.extracted_data
    #entry["asn_1"] = cache.asn1_fragment_content
    entry["certificates"] = cache.certificates
    return(entry)
