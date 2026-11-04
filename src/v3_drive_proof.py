"""Authenticated, read-only rclone Drive evidence for active v3 BUILD readiness.

No write-capable rclone command, shell, provider call or publication route exists here.
Never reveal rclone stderr, config paths, OAuth tokens or downloaded image bytes.
"""
from __future__ import annotations

import io
import json
import re
import subprocess
from dataclasses import dataclass, field

from PIL import Image, UnidentifiedImageError

from .production_inputs import DailyDocuments, InputSourceError
from .v3_readiness import V3_PORTRAIT_IDS

# Immutable Drive parents from the 4 November 2026 production canon.
EPISODE_ARCHIVE_PARENT_ID = "1QcCh-qMHOH97ZWdTLULwNygibJcZRb4q"
PANELIST_FOLDER_ID = "1CYYVI5jXH0lgJBPmqP3VqE9mKrbUva5J"
DAILY_OPERATIONS_FOLDER_ID = "1oVynOtXYo0YQCAZ9Mcvhs0OM5lpF_c7J"
V3_DAILY_NATIVE_IDS = {
    "rnd": ("Daily R&D.txt", "1GBvuPF_C4Lna5sZiE5FSthv10J0gmorqdiTnbBgcds4"),
    "slide_design": ("Daily Slide Design.txt", "19PgSfKDLCSZt0YrjVbXDHz-nkN728CxBjkySEh4GVNs"),
}
PANELIST_FILENAMES = {
    "nora": "Nora_CANONICAL_PANELIST.png",
    "diane_sterling": "Diane_Sterling_CANONICAL_PANELIST.png",
    "johan_vosloo": "Johan_Vosloo_CANONICAL_PANELIST.png",
    "kai_patel": "Kai_Patel_CANONICAL_PANELIST.png",
    "thabo_mokoena": "Thabo_Mokoena_CANONICAL_PANELIST.png",
    "amari_ndlovu": "Amari_Ndlovu_CANONICAL_PANELIST.png",
}
ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{10,100}\Z")
REMOTE_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,100}\Z")
ARCHIVE_NAME_PATTERN = re.compile(r"Ep[0-9]{1,6}-[0-9]{1,2}[A-Za-z]+[0-9]{4}\Z")
MAX_PORTRAIT_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 12_000_000


@dataclass
class RcloneV3DriveProof:
    """Authenticated evidence using only rclone lsjson/cat.

    In particular, never use syntactic ID validation as a substitute for
    checking an exact, live Drive ID in its canonical parent directory.
    """
    remote: str = "ai_geopolitic_drive"
    executable: str = "rclone"
    timeout: float = 60
    _list_cache: dict[str, list[dict]] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if not REMOTE_PATTERN.fullmatch(self.remote):
            raise InputSourceError("Drive remote name is invalid.")
        if not self.executable or self.executable.startswith("-"):
            raise InputSourceError("rclone executable is invalid.")
        if self.timeout <= 0:
            raise InputSourceError("Drive verification timeout must be positive.")

    def _run(self, command: list[str], *, binary: bool = False) -> bytes | str:
        if not command or command[0] not in ("lsjson", "cat"):
            raise InputSourceError("Only read-only Drive verification commands are allowed.")
        try:
            completed = subprocess.run(
                [self.executable, *command], check=True, capture_output=True,
                timeout=self.timeout, **({} if binary else {"encoding": "utf-8-sig"}),
            )
            return completed.stdout
        except (OSError, UnicodeError, subprocess.SubprocessError) as exc:
            raise InputSourceError("Authenticated Drive read/verification failed.") from exc

    def _entries(self, folder_id: str, *, directories: bool) -> list[dict]:
        if not ID_PATTERN.fullmatch(folder_id):
            raise InputSourceError("Invalid fixed Drive parent folder ID.")
        cache_key = f"{folder_id}:{'dir' if directories else 'file'}"
        if cache_key not in self._list_cache:
            command = [
                "lsjson", f"{self.remote}:", "--drive-root-folder-id", folder_id,
                "--dirs-only" if directories else "--files-only", "--no-modtime",
            ]
            raw = self._run(command)
            try:
                data = json.loads(raw)
                if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
                    raise ValueError("List response is not an array of objects.")
                if len(data) > 10_000:
                    raise ValueError("Listing exceeded verifier bounds.")
            except (ValueError, TypeError) as exc:
                raise InputSourceError("Malformed authenticated Drive metadata listing.") from exc
            self._list_cache[cache_key] = data
        return self._list_cache[cache_key]


    def read(self) -> DailyDocuments:
        """Read pinned, unique native Daily Ops Docs as UTF-8 TXT exports.

        This is deliberately not a path search: exact Google Drive IDs and
        parent folder are verified before reading the current production state.
        """
        raw = self._run([
            "lsjson", f"{self.remote}:", "--drive-root-folder-id",
            DAILY_OPERATIONS_FOLDER_ID, "--files-only", "--drive-export-formats",
            "txt", "--no-modtime",
        ])
        try:
            listing = json.loads(raw)
            if not isinstance(listing, list) or not all(isinstance(x, dict) for x in listing):
                raise ValueError("Malformed native document listing.")
            if len(listing) > 500:
                raise ValueError("Unexpectedly large Daily Operations listing.")
        except (ValueError, TypeError) as exc:
            raise InputSourceError("Malformed Daily Operations document listing.") from exc

        texts = {}
        for kind, (name, doc_id) in V3_DAILY_NATIVE_IDS.items():
            matches = [x for x in listing if x.get("ID") == doc_id or x.get("Name") == name]
            if (len(matches) != 1 or matches[0].get("ID") != doc_id
                    or matches[0].get("Name") != name or matches[0].get("IsDir") is not False):
                raise InputSourceError("Required canonical Daily Operations document was not verified.")
            content = self._run([
                "cat", f"{self.remote}:{name}", "--drive-root-folder-id",
                DAILY_OPERATIONS_FOLDER_ID, "--drive-export-formats", "txt",
            ])
            if not isinstance(content, str) or not content.strip():
                raise InputSourceError("Daily Operations export returned no UTF-8 text.")
            texts[kind] = content
        return DailyDocuments(texts["rnd"], texts["slide_design"])

    def archive_folder_exists(self, folder_id: str, expected_archive_name: str) -> bool:
        if not isinstance(folder_id, str) or not ID_PATTERN.fullmatch(folder_id):
            return False
        if not isinstance(expected_archive_name, str) or not ARCHIVE_NAME_PATTERN.fullmatch(expected_archive_name):
            return False
        items = self._entries(EPISODE_ARCHIVE_PARENT_ID, directories=True)
        matches = [x for x in items if x.get("ID") == folder_id]
        return (len(matches) == 1 and matches[0].get("Name") == expected_archive_name
                and matches[0].get("IsDir") is True)

    def portrait_asset_exists(self, slug: str, file_id: str) -> bool:
        if slug not in PANELIST_FILENAMES or V3_PORTRAIT_IDS.get(slug) != file_id:
            return False
        entries = self._entries(PANELIST_FOLDER_ID, directories=False)
        target_name = PANELIST_FILENAMES[slug]
        # A filename alone is never sufficient: Drive may allow duplicate names.
        matches = [x for x in entries if x.get("Name") == target_name or x.get("ID") == file_id]
        if len(matches) != 1:
            return False
        entry = matches[0]
        if (entry.get("ID") != file_id or entry.get("Name") != target_name
                or entry.get("MimeType") != "image/png" or entry.get("IsDir") is not False):
            return False
        size = entry.get("Size")
        if type(size) is not int or not (0 < size <= MAX_PORTRAIT_BYTES):
            return False
        # File bytes are read only after the ID, parent and MIME listing matches.
        raw = self._run(["cat", f"{self.remote}:{target_name}", "--drive-root-folder-id",
                         PANELIST_FOLDER_ID], binary=True)
        if not isinstance(raw, bytes) or len(raw) != size or len(raw) > MAX_PORTRAIT_BYTES:
            return False
        try:
            Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
            with Image.open(io.BytesIO(raw)) as image:
                if image.format != "PNG" or image.width < 16 or image.height < 16:
                    return False
                # A mode containing alpha alone does not prove a transparent cutout.
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    return False
                rgba = image.convert("RGBA")
                alpha_min, alpha_max = rgba.getchannel("A").getextrema()
                return alpha_min < 255 and alpha_max > 0
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
            return False
