"""Offline regression coverage for the read-only authenticated Drive R1b boundary."""
from __future__ import annotations

import io
import json
import subprocess
from datetime import date

import pytest
from PIL import Image

from src.production_inputs import InputSourceError
from src.v3_drive_proof import (
    DAILY_OPERATIONS_FOLDER_ID, V3_DAILY_NATIVE_IDS,
    EPISODE_ARCHIVE_PARENT_ID, PANELIST_FILENAMES, PANELIST_FOLDER_ID,
    RcloneV3DriveProof,
)
from src.v3_drive_readiness import main, verify_authenticated
from src.v3_readiness import V3_PORTRAIT_IDS
from test_v3_readiness import v3_fixture

ARCHIVE_ID = "1j7gPq91u5V-QSfTnHJwsxEl6rFEbr4Kb"
ARCHIVE_NAME = "Ep136-4November2026"
TODAY = date(2026, 11, 4)


def png_bytes(*, transparent: bool = True) -> bytes:
    im = Image.new("RGBA", (64, 64), (30, 60, 90, 255))
    if transparent:
        im.putpixel((0, 0), (0, 0, 0, 0))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


class FakeReadOnlyRclone:
    """Three authenticated parent listings plus native text and PNG reads."""
    def __init__(self, *, image: bytes | None = None):
        self.image = image if image is not None else png_bytes()
        self.calls = []
        self.archive_list = [
            {"ID": ARCHIVE_ID, "Name": ARCHIVE_NAME, "IsDir": True},
        ]
        self.portraits = [
            {"ID": file_id, "Name": PANELIST_FILENAMES[slug], "IsDir": False,
             "MimeType": "image/png", "Size": len(self.image)}
            for slug, file_id in V3_PORTRAIT_IDS.items()
        ]
        docs = v3_fixture()
        self.documents = {
            "Daily R&D.txt": docs.rnd.replace("fixture_v3_archive", ARCHIVE_ID),
            "Daily Slide Design.txt": docs.slide_design.replace("fixture_v3_archive", ARCHIVE_ID),
        }
        self.daily_list = [
            {"ID": native_id, "Name": name, "IsDir": False, "MimeType": "text/plain"}
            for name, native_id in V3_DAILY_NATIVE_IDS.values()
        ]
        self.error = None

    def __call__(self, args, **kwargs):
        self.calls.append((args, kwargs))
        assert args[0] == "rclone"
        assert "shell" not in kwargs
        assert kwargs.get("check") is True
        assert kwargs.get("capture_output") is True
        assert kwargs.get("timeout") == 60
        assert args[1] in ("lsjson", "cat")
        if self.error is not None:
            raise self.error
        assert "--drive-root-folder-id" in args
        parent = args[args.index("--drive-root-folder-id") + 1]
        if args[1] == "lsjson":
            assert args[2] == "ai_geopolitic_drive:"
            if "--dirs-only" in args:
                assert parent == EPISODE_ARCHIVE_PARENT_ID
                value = self.archive_list
            elif parent == DAILY_OPERATIONS_FOLDER_ID:
                assert "--files-only" in args
                assert "--drive-export-formats" in args
                value = self.daily_list
            else:
                assert "--files-only" in args
                assert parent == PANELIST_FOLDER_ID
                value = self.portraits
            return subprocess.CompletedProcess(args, 0, json.dumps(value))
        assert args[1] == "cat"
        assert args[2].startswith("ai_geopolitic_drive:")
        if parent == DAILY_OPERATIONS_FOLDER_ID:
            assert "--drive-export-formats" in args
            name = args[2].split(":", 1)[1]
            assert name in self.documents
            assert kwargs.get("encoding") == "utf-8-sig"
            return subprocess.CompletedProcess(args, 0, self.documents[name])
        assert parent == PANELIST_FOLDER_ID
        assert args[2].endswith(".png")
        assert "encoding" not in kwargs
        return subprocess.CompletedProcess(args, 0, self.image)


def verifier(monkeypatch, *, image: bytes | None = None):
    fake = FakeReadOnlyRclone(image=image)
    monkeypatch.setattr(subprocess, "run", fake)
    return RcloneV3DriveProof(), fake


def test_archive_requires_exact_id_folder_name_type_and_parent(monkeypatch):
    proof, fake = verifier(monkeypatch)
    assert proof.archive_folder_exists(ARCHIVE_ID, ARCHIVE_NAME)
    assert not proof.archive_folder_exists(ARCHIVE_ID, "Ep135-3November2026")
    assert not proof.archive_folder_exists("1invalidfolderid", ARCHIVE_NAME)
    assert not proof.archive_folder_exists(ARCHIVE_ID, "other-folder")
    assert len(fake.calls) == 1  # per-run read-only listing cache
    fake.archive_list[0]["IsDir"] = False
    assert not RcloneV3DriveProof().archive_folder_exists(ARCHIVE_ID, ARCHIVE_NAME)


def test_all_six_exact_portrait_ids_have_png_bytes_and_real_transparency(monkeypatch):
    proof, fake = verifier(monkeypatch)
    for slug, file_id in V3_PORTRAIT_IDS.items():
        assert proof.portrait_asset_exists(slug, file_id)
    assert not proof.portrait_asset_exists("nora", V3_PORTRAIT_IDS["kai_patel"])
    assert not proof.portrait_asset_exists("made_up", V3_PORTRAIT_IDS["nora"])
    assert sum(args[1] == "lsjson" for args, _ in fake.calls) == 1
    assert sum(args[1] == "cat" for args, _ in fake.calls) == 6


@pytest.mark.parametrize("tamper", ["id", "name", "mime", "isdir", "size", "duplicate", "missing"])
def test_wrong_identity_or_metadata_blocks_without_reading_image(monkeypatch, tamper):
    proof, fake = verifier(monkeypatch)
    entry = fake.portraits[0]
    if tamper == "id":
        entry["ID"] = V3_PORTRAIT_IDS["kai_patel"]
    elif tamper == "name":
        entry["Name"] = "Nora_REPLACEMENT.png"
    elif tamper == "mime":
        entry["MimeType"] = "image/jpeg"
    elif tamper == "isdir":
        entry["IsDir"] = True
    elif tamper == "size":
        entry["Size"] = 0
    elif tamper == "duplicate":
        fake.portraits.append(entry.copy())
    else:
        fake.portraits.remove(entry)
    assert not proof.portrait_asset_exists("nora", V3_PORTRAIT_IDS["nora"])
    assert all(args[1] != "cat" for args, _ in fake.calls)


@pytest.mark.parametrize("image", [png_bytes(transparent=False), b"not a PNG"])
def test_opaque_or_corrupt_png_blocks(monkeypatch, image):
    proof, _ = verifier(monkeypatch, image=image)
    assert not proof.portrait_asset_exists("nora", V3_PORTRAIT_IDS["nora"])


def test_wrong_image_length_blocks(monkeypatch):
    proof, fake = verifier(monkeypatch)
    fake.portraits[0]["Size"] += 1
    assert not proof.portrait_asset_exists("nora", V3_PORTRAIT_IDS["nora"])


def test_read_failure_blocks_without_leaking_rclone_stderr(monkeypatch):
    proof, fake = verifier(monkeypatch)
    fake.error = subprocess.CalledProcessError(1, "rclone", stderr="PRIVATE_TOKEN_CONTENT")
    with pytest.raises(InputSourceError) as error:
        proof.archive_folder_exists(ARCHIVE_ID, ARCHIVE_NAME)
    assert "PRIVATE_TOKEN_CONTENT" not in str(error.value)


def test_malformed_remote_listing_blocks(monkeypatch):
    proof, _ = verifier(monkeypatch)
    monkeypatch.setattr(subprocess, "run", lambda args, **kwargs:
                        subprocess.CompletedProcess(args, 0, "{malformed"))
    with pytest.raises(InputSourceError):
        proof.archive_folder_exists(ARCHIVE_ID, ARCHIVE_NAME)


def test_pinned_native_daily_documents_are_exported_by_exact_id(monkeypatch):
    proof, fake = verifier(monkeypatch)
    docs = proof.read()
    assert "Ep136" in docs.rnd
    assert "DESIGN INTEGRITY GATE: PASS" in docs.slide_design
    assert any(args[1] == "lsjson" and DAILY_OPERATIONS_FOLDER_ID in args
               for args, _ in fake.calls)
    assert sum(args[1] == "cat" for args, _ in fake.calls) == 2


@pytest.mark.parametrize("tamper", ["id", "name", "duplicate", "missing"])
def test_native_document_ambiguous_or_wrong_identity_blocks_before_read(monkeypatch, tamper):
    proof, fake = verifier(monkeypatch)
    entry = fake.daily_list[0]
    if tamper == "id":
        entry["ID"] = V3_DAILY_NATIVE_IDS["slide_design"][1]
    elif tamper == "name":
        entry["Name"] = "Daily R&D REPLACEMENT.txt"
    elif tamper == "duplicate":
        fake.daily_list.append(entry.copy())
    else:
        fake.daily_list.remove(entry)
    with pytest.raises(InputSourceError):
        proof.read()
    assert all(args[1] != "cat" for args, _ in fake.calls)


def test_runtime_wires_real_callbacks_and_returns_metadata_only(monkeypatch, capsys):
    proof, fake = verifier(monkeypatch)
    result = verify_authenticated(proof, proof, production_date=TODAY)
    assert result.ready
    assert len(result.manifest["slides"]) == 10
    assert all(args[1] in ("lsjson", "cat") for args, _ in fake.calls)
    monkeypatch.setattr("src.v3_drive_readiness.current_production_date", lambda: TODAY)
    assert main(["--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["slide_count"] == 10
    assert output["generation_performed"] is False
    assert output["publishing_performed"] is False
    assert "SYNTHETIC V3 CONTRACT REGRESSION" not in json.dumps(output)


def test_missing_rclone_credentials_fails_closed(monkeypatch, capsys):
    monkeypatch.setattr(subprocess, "run", lambda args, **kwargs:
                        (_ for _ in ()).throw(FileNotFoundError("private executable path")))
    assert main(["--json"]) == 1
    value = json.loads(capsys.readouterr().out)
    assert value["build"] == "BLOCKED"
    assert value["blockers"][0]["code"] == "INPUT_SOURCE_UNAVAILABLE"
    assert "private executable path" not in json.dumps(value)


def test_invalid_remote_name_is_rejected_without_shell_or_network():
    with pytest.raises(InputSourceError):
        RcloneV3DriveProof(remote="drive:evil")
