# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import base64
import logging
import sqlite3

from typing import Optional, Union

from mvt.common.utils import recursive_resolve, convert_mactime_to_iso

from ..base import IOSExtraction

KNOWLEDGEC_FILE_PATH = [
    "private/var/mobile/Library/CoreDuet/Knowledge/knowledgeC.db"
]


class KnowledgeC(IOSExtraction):
    """This module extracts information from the knowledgeC.db file."""

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
        entries = []
        if record.get("ZOBJECT.ZSTARTDATE") and record.get("ZOBJECT.ZENDDATE") and record.get("ZOBJECT.ZCREATIONDATE"):
            zvaluestring = " : '"+record['ZOBJECT.ZVALUESTRING']+"'" if record.get("ZOBJECT.ZVALUESTRING") else ""
            entries.append({
                "timestamp": record["ZOBJECT.ZCREATIONDATE"],
                "module": self.__class__.__name__,
                "event": "entry creation",
                "data": f"Event ID {record['ZOBJECT.Z_PK']}. {record['ZOBJECT.ZSTREAMNAME']}{zvaluestring}"
            })
            entries.append({
                "timestamp": record["ZOBJECT.ZSTARTDATE"],
                "module": self.__class__.__name__,
                "event": "entry started",
                "data": f"Event ID {record['ZOBJECT.Z_PK']}. {record['ZOBJECT.ZSTREAMNAME']}{zvaluestring}"
            })
            entries.append({
                "timestamp": record["ZOBJECT.ZENDDATE"],
                "module": self.__class__.__name__,
                "event": "entry ended",
                "data": f"Event ID {record['ZOBJECT.Z_PK']}. {record['ZOBJECT.ZSTREAMNAME']}{zvaluestring}"
            })
        return(entries)

    def _extract_notification_data(self) -> None:
        conn = self._open_sqlite_db(self.file_path)
        cur = conn.cursor()
        
        headings = []

        for table_name in ["ZOBJECT", "ZSTRUCTUREDMETADATA", "ZSOURCE"]:
            table = '"' + table_name + '"'
            cur.execute("""
                PRAGMA TABLE_INFO({})
            """.format(table))
            headings += [table_name+"."+tup[1] for tup in cur.fetchall()]
        
        rows = cur.execute("""
            SELECT
                *
            FROM ZOBJECT
            LEFT JOIN
                ZSTRUCTUREDMETADATA
                ON ZOBJECT.ZSTRUCTUREDMETADATA = ZSTRUCTUREDMETADATA.Z_PK
            LEFT JOIN
                ZSOURCE
                ON ZOBJECT.ZSOURCE = ZSOURCE.Z_PK;
        """)

        for row in rows:
            i = 0
            rowlist = {}
            while (i < (len(headings))):
                if headings[i] in  ("ZOBJECT.ZSTARTDATE", "ZOBJECT.ZENDDATE", "ZOBJECT.ZCREATIONDATE"):
                    rowlist[headings[i]] = convert_mactime_to_iso(row[i], from_2001=True)
                elif isinstance(row[i], bytes):
                    if headings[i] in ("ZSTRUCTUREDMETADATA.Z_DKINTENTMETADATAKEY__SERIALIZEDINTERACTION", "ZSTRUCTUREDMETADATA.Z_DKBEHAVIORALRULEFEATURESMETADATAKEY__FEATUREDICT", "ZSTRUCTUREDMETADATA.Z_DKSHARESHEETFEEDBACKMETADATAKEY__MODELSUGGESTIONPROXIES", "ZSTRUCTUREDMETADATA.Z_DKSHARESHEETFEEDBACKMETADATAKEY__ATTACHMENTS", "ZSTRUCTUREDMETADATA.Z_DKFAMILYPREDICTIONMETADATAKEY__SUGGESTIONS", "ZSTRUCTUREDMETADATA.Z_DKSHARESHEETFEEDBACKMETADATAKEY__LOCATIONUUIDS"):
                        rowlist[headings[i]] = recursive_resolve(row[i])
                    else:
                        rowlist[headings[i]] = base64.b64encode(row[i])
                elif row[i] is not None:
                    rowlist[headings[i]] = row[i]
                i += 1
            self.results.append(rowlist)

        cur.close()
        conn.close()

    def run(self) -> None:
        for file_path in self._get_fs_files_from_patterns(KNOWLEDGEC_FILE_PATH):
            self.file_path = file_path
            self.log.info("Found knowledgeC.db file at path: %s", file_path)
            self._extract_notification_data()

        self.log.info("Extracted %d knowledgeC entries", len(self.results))