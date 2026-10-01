"""I/O adapters; validation never invokes these adapters itself."""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol


@dataclass(frozen=True)
class DailyDocuments:
    rnd: str
    slide_design: str


class ProductionInput(Protocol):
    def read(self) -> DailyDocuments: ...


class InputSourceError(ValueError):
    pass


@dataclass(frozen=True)
class MemoryInput:
    rnd: str
    slide_design: str

    def read(self) -> DailyDocuments:
        return DailyDocuments(self.rnd, self.slide_design)


@dataclass(frozen=True)
class LocalFileInput:
    rnd_path: Path
    slide_design_path: Path

    def read(self) -> DailyDocuments:
        try:
            return DailyDocuments(self.rnd_path.read_text(encoding="utf-8-sig"),
                                  self.slide_design_path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError) as exc:
            raise InputSourceError("Cannot read UTF-8 daily input files.") from exc


@dataclass(frozen=True)
class RcloneDriveInput:
    remote: str
    rnd_path: str
    slide_design_path: str
    executable: str = "rclone"
    timeout: float = 60

    @classmethod
    def from_environment(cls) -> RcloneDriveInput:
        rnd = os.environ.get("AI_GEOPOLITIC_RND_PATH", "")
        design = os.environ.get("AI_GEOPOLITIC_SLIDE_DESIGN_PATH", "")
        if not rnd or not design:
            raise InputSourceError("Set AI_GEOPOLITIC_RND_PATH and AI_GEOPOLITIC_SLIDE_DESIGN_PATH.")
        return cls(os.environ.get("AI_GEOPOLITIC_DRIVE_REMOTE", "ai_geopolitic_drive"),
                   rnd, design, os.environ.get("AI_GEOPOLITIC_RCLONE", "rclone"))

    def _run(self, args: list[str]) -> str:
        try:
            result = subprocess.run([self.executable, *args], check=True, capture_output=True,
                                    encoding="utf-8-sig", timeout=self.timeout)
            return result.stdout
        except (OSError, UnicodeError, subprocess.SubprocessError) as exc:
            # Do not expose rclone stderr, which can contain account/config details.
            raise InputSourceError("Drive read failed; check rclone configuration, access and paths.") from exc

    def _read_document(self, path: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", self.remote):
            raise InputSourceError("Drive remote must be a configured rclone remote name.")
        parts = PurePosixPath(path).parts
        if not path or path.startswith(("/", "-")) or ":" in path or ".." in parts or "\\" in path:
            raise InputSourceError("Drive paths must be relative POSIX paths within the remote.")
        parent, _, name = path.rpartition("/")
        # rclone cat can concatenate same-name files: detect ambiguity before reading.
        raw = self._run(["lsjson", f"{self.remote}:{parent}", "--files-only", "--drive-export-formats", "txt"])
        try:
            entries = json.loads(raw)
            if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
                raise ValueError("Invalid listing")
            matches = [entry for entry in entries if entry.get("Name") == name]
            if len(matches) != 1:
                raise ValueError("Missing or ambiguous document")
        except (ValueError, TypeError) as exc:
            raise InputSourceError("Drive document path must resolve to exactly one exported file.") from exc
        return self._run(["cat", f"{self.remote}:{path}", "--drive-export-formats", "txt"])

    def read(self) -> DailyDocuments:
        return DailyDocuments(self._read_document(self.rnd_path), self._read_document(self.slide_design_path))
