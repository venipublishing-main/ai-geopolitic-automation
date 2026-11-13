"""Instagram staging must remain exact-archive, independent, and non-posting."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from src import instagram_media as module

CAPTION = (
    "South Africa's latest inquiry raises important questions for public debate. "
    "#AIGeopolitic #SouthAfrica #Geopolitics #PoliticalAnalysis #NewsBriefing\n\n"
    "The event is factual. The interpretation ideological."
)


def fake_plan() -> tuple[dict, str, list[dict]]:
    slides = []
    inventory = []
    for i in range(1, 11):
        name = f"Ep145_Slide{i:02d}of10.png"
        slides.append({"name": name, "id": f"drivefiletestsource{i:02d}",
                       "sha256": f"{i:064x}", "dimensions": [1080, 1350]})
        inventory.append({"Name": name, "ID": f"drivefiletestsource{i:02d}",
                          "MimeType": "image/png"})
    plan = {"schema": "ai-geopolitic.threads.archive-plan.v1",
            "episode": "Ep145", "date_sast": "2026-11-13",
            "archive_folder_id": "drivefolderexact01",
            "caption_sha256": hashlib.sha256(CAPTION.encode()).hexdigest(),
            "slides": slides, "carousel_items": 10,
            "production_passed": True, "approved_for_threads_publishing": False}
    return plan, CAPTION, inventory


def test_instagram_plan_reuses_canonical_pass_but_not_threads_publish_permission():
    plan, caption, inventory = fake_plan()
    module.validate_plan(plan, caption, inventory)
    assert module.output_folder("Ep145", "2026-11-13") == Path(
        "publisher_media/instagram-ep145-20261113"
    )
    for key, value in (("production_passed", False),
                       ("approved_for_threads_publishing", True),
                       ("carousel_items", 9)):
        changed = dict(plan, **{key: value})
        with pytest.raises(module.InstagramStageBlocked):
            module.validate_plan(changed, caption, inventory)


def test_instagram_stage_is_review_only_with_independent_manifest(tmp_path, monkeypatch):
    plan, caption, inventory = fake_plan()
    requested = []

    def source_reader(command, name, folder, *, limit):
        requested.append((command, name, folder, limit))
        return name.encode()

    def convert(raw, digest, dimensions):
        assert digest in {item["sha256"] for item in plan["slides"]}
        assert dimensions == [1080, 1350]
        return b"JPEG / REVIEW ONLY: " + raw

    monkeypatch.setattr(module, "safe_rclone", source_reader)
    monkeypatch.setattr(module, "_jpeg_from_png", convert)
    folder = tmp_path / "instagram-ep145-20261113"
    receipt = module.stage(plan, caption, inventory, folder)
    assert receipt["status"] == "STAGED_FOR_REVIEW_NOT_PUBLISHED"
    assert receipt["post_target"] == "INSTAGRAM_CAROUSEL_ONLY"
    assert receipt["ai_info_required"] is True
    assert receipt["approved_for_publication"] is False
    assert receipt["published"] is False
    assert len(receipt["media"]) == 10
    assert receipt["media"][0]["name"] == "Slide01of10.jpg"
    assert receipt["media"][-1]["name"] == "Slide10of10.jpg"
    assert (folder / "caption.txt").read_bytes() == caption.encode()
    assert (folder / "stage.json").is_file()
    assert len(requested) == 10
    assert all(command == "cat" and folder_id == plan["archive_folder_id"]
               for command, _, folder_id, _ in requested)


def test_bad_caption_or_duplicate_source_blocks_before_download(tmp_path, monkeypatch):
    plan, caption, inventory = fake_plan()
    monkeypatch.setattr(module, "safe_rclone", lambda *args, **kwargs: pytest.fail(
        "No Drive download allowed after failed preflight"
    ))
    with pytest.raises(module.InstagramStageBlocked):
        module.stage(plan, caption + " tampered", inventory, tmp_path / "bad")
    duplicate = dict(plan, slides=[dict(x) for x in plan["slides"]])
    duplicate["slides"][5]["sha256"] = duplicate["slides"][4]["sha256"]
    with pytest.raises(module.InstagramStageBlocked):
        module.stage(duplicate, caption, inventory, tmp_path / "duplicate")


def test_existing_stage_is_not_overwritten(tmp_path, monkeypatch):
    plan, caption, inventory = fake_plan()
    folder = tmp_path / "existing"
    folder.mkdir()
    (folder / "user-data.txt").write_text("preserve")
    monkeypatch.setattr(module, "safe_rclone", lambda *args, **kwargs: pytest.fail(
        "Existing stage must be rejected before Drive access"
    ))
    with pytest.raises(module.InstagramStageBlocked):
        module.stage(plan, caption, inventory, folder)
    assert (folder / "user-data.txt").read_text() == "preserve"


def test_partial_stage_rolls_back_without_touching_other_outputs(tmp_path, monkeypatch):
    plan, caption, inventory = fake_plan()
    count = 0

    def mock_read(*args, **kwargs):
        nonlocal count
        count += 1
        if count == 3:
            raise module.InstagramStageBlocked("Source image third read failed")
        return str(count).encode()

    monkeypatch.setattr(module, "safe_rclone", mock_read)
    monkeypatch.setattr(module, "_jpeg_from_png", lambda raw, digest, dimensions: b"JPG" + raw)
    keep = tmp_path / "unrelated.txt"
    keep.write_text("keep")
    with pytest.raises(module.InstagramStageBlocked):
        module.stage(plan, caption, inventory, tmp_path / "failed")
    assert keep.read_text() == "keep"
    assert list(tmp_path.iterdir()) == [keep]
