"""Authenticated read-only Google Drive source for the publisher.

Selects EXACTLY the intended SAST episode inside the fixed archive parent.
Never uses 'latest modified' ordering, writes to Drive, or publishes.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass

from .publisher_archive import ARCHIVE_PARENT_ID, Episode, PublisherBlocked

MAX_LIST = 1000
DRIVE_ID = re.compile(r"[A-Za-z0-9_-]{10,100}\Z")
REMOTE = re.compile(r"[A-Za-z0-9_-]{1,100}\Z")


@dataclass(frozen=True)
class RclonePublisherArchive:
    remote: str = "ai_geopolitic_drive"
    executable: str = "rclone"
    timeout: int = 60

    def __post_init__(self):
        if not REMOTE.fullmatch(self.remote) or not self.executable or self.executable.startswith("-"):
            raise PublisherBlocked("Invalid rclone remote or executable name.")
        if self.timeout <= 0:
            raise PublisherBlocked("Invalid rclone timeout.")

    @classmethod
    def from_environment(cls):
        return cls(os.environ.get("AI_GEOPOLITIC_DRIVE_REMOTE", "ai_geopolitic_drive"),
                   os.environ.get("AI_GEOPOLITIC_RCLONE", "rclone"))

    def _run(self, cmd: list[str], *, binary: bool = False) -> str | bytes:
        if cmd[0] not in ("lsjson", "cat"):
            raise PublisherBlocked("Publisher archive only permits rclone read operations.")
        try:
            p = subprocess.run([self.executable, *cmd], check=True, capture_output=True,
                               timeout=self.timeout,
                               **({} if binary else {"encoding": "utf-8-sig"}))
        except (OSError, UnicodeError, subprocess.SubprocessError) as exc:
            # OAuth tokens and account details can be present in rclone stderr.
            raise PublisherBlocked("Cannot read authenticated Google Drive archive.") from exc
        return p.stdout

    def list_entries(self, folder_id: str, *, folders: bool) -> list[dict]:
        if not DRIVE_ID.fullmatch(folder_id):
            raise PublisherBlocked("Invalid archive parent folder ID.")
        raw = self._run(["lsjson", f"{self.remote}:", "--drive-root-folder-id",
                         folder_id, "--dirs-only" if folders else "--files-only",
                         "--no-modtime"])
        try:
            data = json.loads(raw)
            if not isinstance(data, list) or len(data) > MAX_LIST or not all(
                isinstance(x, dict) for x in data
            ):
                raise ValueError("Bad Drive metadata.")
            return data
        except (ValueError, TypeError) as exc:
            raise PublisherBlocked("Authenticated Drive archive listing is malformed.") from exc

    def list_folders(self) -> list[dict]:
        return self.list_entries(ARCHIVE_PARENT_ID, folders=True)

    def list_files(self, episode: Episode) -> list[dict]:
        return self.list_entries(episode.folder_id, folders=False)

    def read_bytes(self, episode: Episode, files: list[dict], name: str,
                   file_id: str, *, max_bytes: int) -> bytes:
        """Cross-check the listed ID and filename before each bounded file read."""
        if not DRIVE_ID.fullmatch(file_id) or not (0 < max_bytes <= 50_000_000):
            raise PublisherBlocked("Invalid asset ID or download bound.")
        matches = [x for x in files if x.get("Name") == name or x.get("ID") == file_id]
        if len(matches) != 1 or matches[0].get("ID") != file_id or matches[0].get("Name") != name:
            raise PublisherBlocked("Drive file identity is missing or ambiguous.")
        raw = self._run(["cat", f"{self.remote}:{name}", "--drive-root-folder-id",
                         episode.folder_id, "--count", str(max_bytes + 1)], binary=True)
        if not isinstance(raw, bytes) or len(raw) == 0 or len(raw) > max_bytes:
            raise PublisherBlocked("Archived asset download is missing or exceeds byte limit.")
        return raw

    def read_json(self, episode: Episode, files: list[dict]) -> dict:
        matches = [x for x in files if x.get("Name") == episode.qc_filename]
        if len(matches) != 1:
            raise PublisherBlocked("Episode has no unique QC completion record.")
        raw = self.read_bytes(episode, files, episode.qc_filename,
                              matches[0]["ID"], max_bytes=2_000_000)
        try:
            data = json.loads(raw.decode("utf-8-sig"))
            if not isinstance(data, dict):
                raise ValueError("QC root must be object.")
            return data
        except (UnicodeError, ValueError) as exc:
            raise PublisherBlocked("QC completion record is invalid JSON.") from exc

    def read_caption(self, episode: Episode, files: list[dict]) -> str:
        matches = [x for x in files if x.get("Name") == episode.caption_filename]
        if len(matches) != 1:
            raise PublisherBlocked("Episode has no unique carousel-caption file.")
        raw = self.read_bytes(episode, files, episode.caption_filename,
                              matches[0]["ID"], max_bytes=16_000)
        try:
            return raw.decode("utf-8")
        except UnicodeError as exc:
            raise PublisherBlocked("Archived carousel caption is not UTF-8.") from exc
