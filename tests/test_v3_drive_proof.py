"""No-network proof for the authenticated Drive R1b boundary."""
from __future__ import annotations

import io
import json
import subprocess
from datetime import date

import pytest
from PIL import Image

from src.production_inputs import InputSourceError, MemoryInput, RcloneDriveInput
from src.v3_drive_proof import (
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
    """Emulates two authenticated parent lists and explicit image-byte reads."""
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
            else:
                assert "--files-only" in args
                assert parent == PANELIST_FOLDER_ID
                value = self.portraits
            return subprocess.CompletedProcess(args, 0, json.dumps(value))
        assert args[1] == "cat"
        assert parent == PANELIST_FOLDER_ID
        assert args[2].startswith("ai_geopolitic_drive:")
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
    assert len(fake.calls) == 1  # per-read immutable snapshot
    fake.archive_list[0]["IsDir"] = False
    assert not RcloneV3DriveProof().archive_folder_exists(ARCHIVE_ID, ARCHIVE_NAME)


def test_all_six_exact_portrait_ids_have_png_bytes_and_real_transparency(monkeypatch):
    proof, fake = verifier(monkeypatch)
    for slug, file_id in V3_PORTRAIT_IDS.items():
        assert proof.portrait_asset_exists(slug, file_id)
    assert not proof.portrait_asset_exists("nora", V3_PORTRAIT_IDS["kai_patel"])
    assert not proof.portrait_asset_exists("made_up", V3_PORTRAIT_IDS["nora"])
    # Exactly one list request plus one read per assigned portrait.
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
    proof, fake = verifier(monkeypatch)
    def broken(args, **kwargs):
        return subprocess.CompletedProcess(args, 0, "{malformed")
    monkeypatch.setattr(subprocess, "run", broken)
    with pytest.raises(InputSourceError):
        proof.archive_folder_exists(ARCHIVE_ID, ARCHIVE_NAME)


def test_runtime_wires_real_callbacks_and_returns_metadata_only(monkeypatch, capsys):
    proof, fake = verifier(monkeypatch)
    docs = v3_fixture()
    # This fixture uses a deliberately synthetic archive ID. Substitute only
    # the declared identity; the JSON and two human document IDs must agree.
    design = docs.slide_design.replace("fixture_v3_archive", ARCHIVE_ID)
    rnd = docs.rnd.replace("fixture_v3_archive", ARCHIVE_ID)
    result = verify_authenticated(MemoryInput(rnd, design), proof, production_date=TODAY)
    assert result.ready
    assert len(result.manifest["slides"]) == 10
    assert all(args[1] in ("lsjson", "cat") for args, _ in fake.calls)

    monkeypatch.setattr(RcloneDriveInput, "from_environment", classmethod(
        lambda cls: RcloneDriveInput("ai_geopolitic_drive", "Control/Daily R&D.txt",
                                    "Control/Daily Slide Design.txt")
    ))
    monkeypatch.setattr(RcloneDriveInput, "read", lambda self: type(docs)(rnd, design))
    # CLI uses real current SAST day; deterministic tests inject it at the function.
    # Here only verify that the summary never includes raw slide copy.
    if date.today() == TODAY:
        assert main(["--json"]) == 0
        output = json.loads(capsys.readouterr().out)
        assert output["slide_count"] == 10
        assert output["generation_performed"] is False
        assert "SYNTHETIC V3 CONTRACT REGRESSION" not in json.dumps(output)


def test_no_env_paths_means_closed_cli(monkeypatch, capsys):
    monkeypatch.delenv("AI_GEOPOLITIC_RND_PATH", raising=False)
    monkeypatch.delenv("AI_GEOPOLITIC_SLIDE_DESIGN_PATH", raising=False)
    assert main(["--json"]) == 1
    value = json.loads(capsys.readouterr().out)
    assert value["build"] == "BLOCKED"
    assert value["blockers"][0]["code"] == "INPUT_SOURCE_UNAVAILABLE"


def test_invalid_remote_name_is_rejected_without_shell_or_network():
    with pytest.raises(InputSourceError):
        RcloneV3DriveProof(remote="drive:evil")
