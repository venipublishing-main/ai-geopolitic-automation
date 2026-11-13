import hashlib
import io
from datetime import date

import pytest
from PIL import Image

from src import threads_media as tm

CAPTION = (
    "A tenth suspect was arrested in South Africa on 11 November over an alleged attempt "
    "to join the Russia–Ukraine war. Authorities allege a breach of foreign military "
    "assistance law. Arrest is not conviction.\n\n"
    "#AIGeopolitic #SouthAfrica #Geopolitics #PoliticalAnalysis #NewsBriefing\n\n"
    "The event is factual. The interpretation ideological."
)


def png_bytes(index):
    pic = Image.new("RGB", (1080, 1350), (index * 15, 70, 90))
    result = io.BytesIO()
    pic.save(result, "PNG")
    return result.getvalue()


def archived_episode():
    folder = "1mvKV0f6LFwv8sln8Ps0YD9Ql5f9lLP9H"
    names = [f"Ep145_Slide{i:02d}of10.png" for i in range(1, 11)]
    files = {}
    delivered = {}
    raw = {}
    for i, name in enumerate(names, 1):
        contents = png_bytes(i)
        file_id = "drive_valid_slide_" + str(i)
        digest = hashlib.sha256(contents).hexdigest()
        files[name] = {"Name": name, "ID": file_id, "IsDir": False, "MimeType": "image/png"}
        delivered[name] = {
            "drive_id": file_id, "source_sha256": digest,
            "readback_sha256": digest, "readback_verified": True,
            "dimensions": [1080, 1350],
        }
        raw[name] = contents
    cap_name = "Ep145_CarouselCaption.txt"
    files[cap_name] = {"Name": cap_name, "ID": "valid_caption_drive_123", "IsDir": False}
    delivered[cap_name] = {"drive_id": files[cap_name]["ID"],
                           "sha256": tm.verify_caption(CAPTION), "readback_verified": True}
    raw[cap_name] = CAPTION.encode("utf-8")
    for name in ("Ep145_QC_Completion.json", "Ep145_PUBLISH_HANDOFF.json"):
        files[name] = {"Name": name, "ID": "valid_json_id_" + name, "IsDir": False}
    qc = {"episode": "Ep145", "production_date_sast": "2026-11-13",
          "archive_folder_id": folder, "status": "PRODUCTION COMPLETE — PENDING IAN REVIEW",
          "image_counts": {"carousel": 10, "reel": 6},
          "unresolved_defects": [], "delivered": delivered}
    handoff = {"schema": tm.EXPECTED_HANDOFF_SCHEMA,
               "episode_id": "Ep145", "production_date_sast": "2026-11-13",
               "archive_folder_id": folder, "author": "Sisyphus",
               "status": "PRODUCTION PASSED", "carousel_items": 10,
               "publish_target": "INSTAGRAM_CAROUSEL_TEST_ONLY",
               "unresolved_blockers": [],
               "component_results": {x: "PASS" for x in tm.HANDOFF_COMPONENTS}}
    return folder, files, raw, qc, handoff


def patch_archive(monkeypatch):
    folder, files, raw, qc, handoff = archived_episode()

    def fake_entries(folder_id):
        if folder_id == tm.ARCHIVE_PARENT_ID:
            return [{"Name": "Ep145-13November2026", "ID": folder, "IsDir": True}]
        if folder_id == folder:
            return list(files.values())
        raise AssertionError("unexpected directory access")

    def fake_json(name, folder_id, limit):
        assert folder_id == folder
        return qc if "QC_Completion" in name else handoff

    def fake_rclone(command, path, folder_id, *, limit):
        assert command == "cat" and folder_id == folder
        return raw[path.split(":", 1)[1]]

    monkeypatch.setattr(tm, "_entries", fake_entries)
    monkeypatch.setattr(tm, "_read_json", fake_json)
    monkeypatch.setattr(tm, "safe_rclone", fake_rclone)
    return files, raw, qc, handoff


def test_exact_date_and_folder():
    assert tm.validate_episode("Ep145", "2026-11-13")[2] == "Ep145-13November2026"
    with pytest.raises(tm.ThreadsBlocked):
        tm.validate_episode("Ep145", "20261113")
    for episode in ("latest", "Ep0", "Ep145/foo", "Ep145_Reel"):
        with pytest.raises(tm.ThreadsBlocked):
            tm.validate_episode(episode, "2026-11-13")


def test_canonical_caption_is_under_500_utf8_bytes():
    assert len(CAPTION) == 334
    assert len(CAPTION.encode("utf-8")) == 336
    assert tm.verify_caption(CAPTION)
    with pytest.raises(tm.ThreadsBlocked):
        tm.verify_caption(CAPTION + ("!" * 200))
    with pytest.raises(tm.ThreadsBlocked):
        tm.verify_caption(CAPTION.replace("#AIGeopolitic", "#Random"))


def test_real_qc_schema_and_handoff(monkeypatch):
    _, _, _, handoff = patch_archive(monkeypatch)
    plan, caption, files = tm.read_approved_archive("Ep145", "2026-11-13")
    assert plan["carousel_items"] == 10
    assert plan["approved_for_threads_publishing"] is False
    assert caption == CAPTION
    assert len(files) == 13
    handoff["component_results"]["carousel_10"] = "FAIL"
    with pytest.raises(tm.ThreadsBlocked):
        tm.read_approved_archive("Ep145", "2026-11-13")


def test_stage_converts_only_ten_images(monkeypatch, tmp_path):
    patch_archive(monkeypatch)
    plan, caption, files = tm.read_approved_archive("Ep145", "2026-11-13")
    output = tmp_path / "stage"
    result = tm.stage_archive(plan, caption, files, output)
    assert result["slide_count"] == 10
    assert result["post_target"] == "THREADS_CAROUSEL_ONLY"
    assert len(list(output.glob("*.jpg"))) == 10
    assert len(list(output.glob("*.mp4"))) == 0
    assert (output / "caption.txt").read_text() == CAPTION
    with pytest.raises(tm.ThreadsBlocked):
        tm.stage_archive(plan, caption, files, output)


def test_bad_slide_fails_before_writing(monkeypatch, tmp_path):
    _, raw, _, _ = patch_archive(monkeypatch)
    plan, caption, files = tm.read_approved_archive("Ep145", "2026-11-13")
    raw["Ep145_Slide10of10.png"] = b"corrupted-original"
    output = tmp_path / "stage"
    with pytest.raises(tm.ThreadsBlocked):
        tm.stage_archive(plan, caption, files, output)
    assert not output.exists()


def test_handoff_old_instagram_test_target_never_counts_as_threads_consent(monkeypatch):
    patch_archive(monkeypatch)
    plan, _, _ = tm.read_approved_archive("Ep145", "2026-11-13")
    assert not plan["approved_for_threads_publishing"]

