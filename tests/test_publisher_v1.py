"""No-network, no-publishing tests for publisher archive selection and JPEG stage."""
from __future__ import annotations

import hashlib
import io
import json
import subprocess
from datetime import date, datetime, timezone, timedelta

import pytest
from PIL import Image

from src.publisher_archive import (
    Episode, PublisherBlocked, parse_episode_folder, plan_carousel,
    sast_today, select_episode,
)
from src.publisher_cli import evaluate, main, stage_from_plan
from src.publisher_delivery import create_test_deck, test_image as qa_image, to_api_jpeg
from src.publisher_drive import RclonePublisherArchive

TODAY = date(2026, 11, 13)
ARCHIVE_ID = "1ZN-dWSeCFBZ8h3Sy7mmzLDmujRjbdKaM"
EP = Episode(145, TODAY, "Ep145-13November2026", ARCHIVE_ID)
CAPTION = (
    "This is a deliberately synthetic QC fixture, not news.\n"
    "#AIGeopolitic #SouthAfrica #Geopolitics #PoliticalAnalysis #NewsBriefing\n"
    "The event is factual. The interpretation ideological."
)


def png_bytes(dimensions=(1080, 1350)):
    im = Image.new("RGB", dimensions, (247, 244, 235))
    im.paste((50, 40, 30), (20, 20, 400, 100))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def fixture(dimensions=(1080, 1350)):
    raw = png_bytes(dimensions)
    sha = hashlib.sha256(raw).hexdigest()
    caption_sha = hashlib.sha256(CAPTION.encode("utf-8")).hexdigest()
    data = {"episode": EP.episode_id, "production_date_sast": TODAY.isoformat(),
            "archive_url": f"https://drive.google.com/drive/folders/{ARCHIVE_ID}",
            "status": "PRODUCTION COMPLETE — PENDING IAN REVIEW",
            "counts": {"carousel": 10},
            "per_stage_and_per_image_qc": {"captions": {"status": "QC_PASS_PENDING_IAN_REVIEW"}},
            "deliverables": {}}
    files = []
    for index, name in enumerate(EP.slide_names, 1):
        file_id = f"test_image_id_{index:02d}_abcdefghijklmnopqrstuvwxyz"
        files.append({"ID": file_id, "Name": name, "MimeType": "image/png", "IsDir": False})
        data["deliverables"][name] = {"id": file_id, "sha256": sha,
                                      "dimensions": list(dimensions),
                                      "readback_identical": True}
    files.append({"ID": "test_caption_1234567890abcdef", "Name": EP.caption_filename,
                  "IsDir": False, "MimeType": "text/plain"})
    data["deliverables"][EP.caption_filename] = {"id": files[-1]["ID"], "sha256": caption_sha}
    files.append({"ID": "test_qc_completion_12345678", "Name": EP.qc_filename,
                  "IsDir": False, "MimeType": "application/json"})
    data["deliverables"][EP.qc_filename] = {"id": files[-1]["ID"]}
    return data, files, raw


def test_folder_parsing_rejects_invalid_calendar_dates():
    assert parse_episode_folder(EP.name, ARCHIVE_ID) == EP
    assert parse_episode_folder("Ep200-31February2026", ARCHIVE_ID) is None
    assert parse_episode_folder("Ep1-12Unknown2026", ARCHIVE_ID) is None
    assert parse_episode_folder("Ep001-12November2026", "tiny") is None


def test_sast_midnight_boundary_not_utc_day():
    assert sast_today(datetime(2026, 11, 12, 22, 30, tzinfo=timezone.utc)) == date(2026, 11, 13)
    assert sast_today(datetime(2026, 11, 12, 21, 59, tzinfo=timezone.utc)) == date(2026, 11, 12)
    with pytest.raises(PublisherBlocked):
        sast_today(datetime(2026, 11, 13, 0, 0))


def test_exact_sast_day_not_latest_modified():
    old = {"Name": "Ep144-12November2026", "ID": "1abcddefghijklmnop", "IsDir": True,
           "ModTime": "2026-11-13T20:00:00Z"}
    current = {"Name": EP.name, "ID": EP.folder_id, "IsDir": True,
               "ModTime": "2026-11-13T01:00:00Z"}
    assert select_episode([old, current], day=TODAY) == EP
    assert select_episode([old, current], day=TODAY, explicit_episode="Ep144").number == 144


def test_missing_today_does_not_fall_back_to_yesterday():
    with pytest.raises(PublisherBlocked, match="will not fall back"):
        select_episode([{"Name": "Ep144-12November2026",
                         "ID": "1abcddefghijklmnop", "IsDir": True}], day=TODAY)


def test_ambiguous_folders_block():
    with pytest.raises(PublisherBlocked, match="unique"):
        select_episode([{"Name": EP.name, "ID": ARCHIVE_ID, "IsDir": True}] * 2, day=TODAY)


def test_complete_current_archive_generates_pinned_ordered_ten_image_plan():
    qc, files, _ = fixture()
    plan = plan_carousel(EP, files, qc, CAPTION)
    assert plan["episode"] == "Ep145" and plan["slide_count"] == 10
    assert [x["name"] for x in plan["slides"]] == list(EP.slide_names)
    assert all(x["file_id"] and x["source_sha256"] for x in plan["slides"])
    assert plan["release_authorized"] is False and plan["mode"] == "DRY_RUN"


def test_user_reported_manual_episode_is_always_excluded_even_if_qc_says_not_published():
    qc, files, _ = fixture()
    prior = {"excluded_publications": [
        {"episode_id": EP.episode_id, "channel": "instagram",
         "status": "USER_REPORTED_MANUALLY_PUBLISHED"}]}
    with pytest.raises(PublisherBlocked, match="already been manually"):
        plan_carousel(EP, files, qc, CAPTION, manual_history=prior)


@pytest.mark.parametrize("field", [
    "wrong_episode", "wrong_day", "unfinished", "wrong_count", "missing_slide",
    "duplicate_name", "wrong_id", "bad_image_mime", "wrong_dimensions",
    "readback_failed", "bad_sha", "wrong_caption_hash", "wrong_caption",
    "missing_caption_qc", "wrong_archive",
])
def test_missing_or_wrong_qc_blocks(field):
    qc, files, _ = fixture()
    caption = CAPTION
    if field == "wrong_episode":
        qc["episode"] = "Ep999"
    elif field == "wrong_day":
        qc["production_date_sast"] = "2026-11-12"
    elif field == "unfinished":
        qc["status"] = "INCOMPLETE"
    elif field == "wrong_count":
        qc["counts"]["carousel"] = 9
    elif field == "missing_slide":
        files.remove(files[0])
    elif field == "duplicate_name":
        files.append(files[0].copy())
    elif field == "wrong_id":
        files[0]["ID"] = "wrong_image_id_1234567"
    elif field == "bad_image_mime":
        files[0]["MimeType"] = "image/jpeg"
    elif field == "wrong_dimensions":
        qc["deliverables"][EP.slide_names[0]]["dimensions"] = [1080, 1920]
    elif field == "readback_failed":
        qc["deliverables"][EP.slide_names[0]]["readback_identical"] = False
    elif field == "bad_sha":
        qc["deliverables"][EP.slide_names[0]]["sha256"] = "abc"
    elif field == "wrong_caption_hash":
        qc["deliverables"][EP.caption_filename]["sha256"] = "0" * 64
    elif field == "wrong_caption":
        caption = "Other text"
    elif field == "missing_caption_qc":
        qc["per_stage_and_per_image_qc"]["captions"]["status"] = "NOT_REVIEWED"
    elif field == "wrong_archive":
        qc["archive_url"] = "https://drive.google.com/drive/folders/anotherfolder"
    with pytest.raises(PublisherBlocked):
        plan_carousel(EP, files, qc, caption)


@pytest.mark.parametrize("dimensions", [(1080, 1350), (1080, 1440)])
def test_jpeg_delivery_preserves_all_pixels_without_crop(dimensions):
    source = png_bytes(dimensions)
    transformed = to_api_jpeg(source, source_sha256=hashlib.sha256(source).hexdigest(),
                               expected_dimensions=list(dimensions))
    assert len(transformed) < 8 * 1024 * 1024
    with Image.open(io.BytesIO(transformed)) as result:
        assert result.format == "JPEG"
        assert result.size == (1080, 1350)
        assert result.getpixel((result.width // 2, result.height // 2)) == (247, 244, 235)
        if dimensions[1] == 1440:
            # 3:4 portrait downscaled and pillarboxed, NOT cropped.
            assert result.getpixel((2, 2)) == (247, 244, 235)


def test_jpeg_wrong_sha_and_nonpng_rejected():
    raw = png_bytes()
    with pytest.raises(PublisherBlocked):
        to_api_jpeg(raw, source_sha256="0" * 64, expected_dimensions=[1080, 1350])
    with pytest.raises(PublisherBlocked):
        to_api_jpeg(b"not png", source_sha256=hashlib.sha256(b"not png").hexdigest(),
                    expected_dimensions=[1080, 1350])


def test_all_ten_qa_images_are_valid_jpegs(tmp_path):
    manifest = create_test_deck(tmp_path)
    assert manifest["carousel_count"] == 10
    assert len(set(item["sha256"] for item in manifest["images"])) == 10
    for i, item in enumerate(manifest["images"], 1):
        with Image.open(tmp_path / item["filename"]) as im:
            assert im.format == "JPEG" and im.size == (1080, 1350)
        assert item["filename"] == f"TEST_Slide{i:02d}of10.jpg"


def test_cli_test_deck_requires_no_network_or_tokens(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs:
                        (_ for _ in ()).throw(AssertionError("NETWORK CALLED")))
    assert main(["--mode", "test-deck", "--out", str(tmp_path)]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["count"] == 10 and value["published"] is False


class FakeArchive:
    def __init__(self):
        self.qc, self.files, self.raw = fixture()
    def list_folders(self):
        return [{"Name": EP.name, "ID": EP.folder_id, "IsDir": True}]
    def list_files(self, episode):
        assert episode == EP
        return self.files
    def read_json(self, episode, files):
        return self.qc
    def read_caption(self, episode, files):
        return CAPTION
    def read_bytes(self, episode, files, name, file_id, **kwargs):
        assert name in EP.slide_names
        assert file_id == self.qc["deliverables"][name]["id"]
        return self.raw


def test_end_to_end_dry_run_stage_without_meta_post(tmp_path):
    source = FakeArchive()
    plan, caption, episode, files = evaluate(source, for_day=TODAY,
                                             history={"excluded_publications": []})
    delivery = stage_from_plan(source, plan, caption, episode, files, tmp_path)
    assert len(delivery["images"]) == 10
    assert all((tmp_path / EP.episode_id / x["name"]).is_file() for x in delivery["images"])
    assert delivery["mode"] == "STAGED_NOT_PUBLISHED"
    assert delivery["instagram_post_id"] is None
    assert not delivery["public_image_urls"]
    with pytest.raises(PublisherBlocked, match="already exists"):
        stage_from_plan(source, plan, caption, episode, files, tmp_path)


def test_rclone_reader_uses_only_readonly_commands(monkeypatch):
    seen = []
    def fake_run(args, **kwargs):
        seen.append(args)
        assert args[1] == "lsjson" and "--dirs-only" in args
        return subprocess.CompletedProcess(args, 0,
             json.dumps([{"Name": EP.name, "ID": ARCHIVE_ID, "IsDir": True}]))
    monkeypatch.setattr(subprocess, "run", fake_run)
    source = RclonePublisherArchive()
    assert source.list_folders()[0]["ID"] == ARCHIVE_ID
    assert len(seen) == 1
    assert "--drive-root-folder-id" in seen[0]
    assert all("delete" not in arg for arg in seen[0])


def test_missing_rclone_blocks_without_token_leak(monkeypatch):
    def denied(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "rclone", stderr="PRIVATE_OAUTH_TOKEN")
    monkeypatch.setattr(subprocess, "run", denied)
    with pytest.raises(PublisherBlocked) as error:
        RclonePublisherArchive().list_folders()
    assert "PRIVATE_OAUTH_TOKEN" not in str(error.value)
