import os
import logging
import magic
import re

from typing import Optional, Union

from ..base import IOSExtraction

ATTACHMENTS_ROOT_PATH = ["private/var/mobile/Library/SMS/Attachments/*/*/*/*.gif*"]
ATTACHMENTS_BACKUP_PATTERN = "relativePath LIKE 'Library/SMS/Attachments/%.gif%'"

class Gif(IOSExtraction):
    """ This module search for gif chunks or file with the gif extension that are in fact in the pdf format."""
    
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
        if record["chunk"]:
            event = "gif_chunk"
        elif record["pdf"]:
            event = "gif_pdf"
        else:
            event = "gif"

        return {
            "timestamp": record["modified"],
            "module": self.__class__.__name__,
            "event": event,
            "data": record["file_path"]
        }

    def check_indicators(self) -> None:
        for result in self.results:
            if result["chunk"]:
                self.log.warning("Found a GIF chunk \"%s\"", result["file_path"])
                self.detected.append(result)
            elif result["pdf"]:
                self.log.warning("Found a PDF disguised as a GIF \"%s\"", result["file_path"])
                self.detected.append(result)

    def _extract_fs_data(self) -> None:
        for file_path in self.file_paths:
            gif_chunk = re.search(r'.*.gif-.*$', file_path, re.IGNORECASE)
            if gif_chunk:
                self.results.append({
                    "file_path": os.path.relpath(file_path, self.target_path),
                    "modified": self._get_file_last_modified_time(file_path),
                    "chunk": True,
                    "pdf": False,
                })

        for file_path in self.file_paths:
            if "PDF" in magic.from_file(str(file_path)):
                self.results.append({
                    "file_path": os.path.relpath(file_path, self.target_path),
                    "modified": self._get_file_last_modified_time(file_path),
                    "chunk": False,
                    "pdf": True,
                })
            else:
                self.results.append({
                    "file_path": os.path.relpath(file_path, self.target_path),
                    "modified": self._get_file_last_modified_time(file_path),
                    "chunk": False,
                    "pdf": False,
                })


    def _extract_backup_data(self) -> None:
        found_backup_paths = self._get_backup_files_from_manifest_pattern(custom_pattern=ATTACHMENTS_BACKUP_PATTERN)

        for found_backup_path in found_backup_paths:
            relative_path = found_backup_path["relative_path"]

            gif_chunk = re.search(r'.*.gif-.*$', relative_path, re.IGNORECASE)
            gif = re.search(r'.*.gif$', relative_path, re.IGNORECASE)

            if gif_chunk:
                file_path = self._get_backup_file_from_id(found_backup_path["file_id"])
                self.results.append({
                    "file_path": found_backup_path["domain"]+"-"+found_backup_path["relative_path"],
                    "modified": self._get_file_last_modified_time(file_path),
                    "chunk": True,
                    "pdf": False,
                })

            if gif:
                file_path = self._get_backup_file_from_id(found_backup_path["file_id"])
                if "PDF" in magic.from_file(file_path):
                    self.results.append({
                        "file_path": found_backup_path["domain"]+"-"+found_backup_path["relative_path"],
                        "modified": self._get_file_last_modified_time(file_path),
                        "chunk": False,
                        "pdf": True,
                    })
                else:
                    self.results.append({
                        "file_path": found_backup_path["domain"]+"-"+found_backup_path["relative_path"],
                        "modified": self._get_file_last_modified_time(file_path),
                        "chunk": False,
                        "pdf": False,
                    })

    def run(self) -> None:
        if self.is_fs_dump:
            self.file_paths = self._get_fs_files_from_patterns(ATTACHMENTS_ROOT_PATH)
            self._extract_fs_data()
        elif self.is_backup:
            self._extract_backup_data()

        self.log.info("Parsed information on %d GIF attachments", len(self.results))
