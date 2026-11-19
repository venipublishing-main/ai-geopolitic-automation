"""No-network tests for the selected public Reel staging path."""

import hashlib
import json
from pathlib import Path

import pytest

from src import video_media as vm
from src.reel_media import ReelBlocked, SONORA_MASTER_SHA256

CAPTION = ("Verified news update from the world's trade networks.\n\n"
           "#APEC #Shenzhen #GlobalTrade #SupplyChains #AIGeopolitic\n\n"
           "The event is factual. The interpretation ideological.\n")


def fake_plan():
    return {
        "episode": "Ep151", "date_sast": "2026-11-19", "archive_folder_id": "A" * 25,
        "approved_for_reel_publication": False, "carousel_handoff_passed": True,
        "frame_count": 6, "reel_caption_sha256": hashlib.sha256(CAPTION.encode()).hexdigest(),
        "approved_audio_sha256": SONORA_MASTER_SHA256,
        "frames": [{"name": f"ReelFrame{i:02d}of06.png", "drive_id": "B" * 25,
                    "sha256": f"{i:064x}", "width": 1080, "height": 1920}
                   for i in range(1, 7)],
    }


def test_stage_contains_one_approved_video_and_caption_no_source_images(monkeypatch, tmp_path):
    monkeypatch.setattr(vm, "verified_sonora_master", lambda target=None: (
        target.write_bytes(b"locked soundtrack") if target is not None else None,
        {"sha256": SONORA_MASTER_SHA256, "master_id": "approved-VS001-B"}
    )[1])
    monkeypatch.setattr(vm, "read_frame", lambda *args: b"verified-original-frame")
    monkeypatch.setattr(vm, "make_flare_overlay", lambda target: {
        "animation_pattern": "flare_frames/flare_%02d.png"})
    monkeypatch.setattr(vm, "ffmpeg_command", lambda frames, audio, flare, mp4, **kwargs: [
        "mockffmpeg", str(mp4)])
    generated = b"mock-mp4" * 25000

    def fake_run(command, **kwargs):
        assert command[0] == "mockffmpeg"
        assert kwargs["check"] and kwargs["timeout"] == 1200
        Path(command[1]).write_bytes(generated)

    monkeypatch.setattr(vm.subprocess, "run", fake_run)
    monkeypatch.setattr(vm, "verify_mp4", lambda path: {
        "width": 1080, "height": 1920, "fps": 30, "duration_seconds": 18.0,
        "video_codec": "h264", "audio_codec": "aac", "bytes": len(generated),
        "sha256": hashlib.sha256(generated).hexdigest()})
    out = tmp_path / "publisher_media/video-ep151-20261119"
    rec = vm.stage_video(fake_plan(), CAPTION, out)
    assert sorted(p.name for p in out.iterdir()) == ["caption.txt", "reel.mp4", "stage.json"]
    assert (out / "caption.txt").read_bytes() == CAPTION.encode()
    assert (out / "reel.mp4").read_bytes() == generated
    assert rec["video_variant"] == "C_Stronger"
    assert rec["published"] is False and rec["status"] == "STAGED_NOT_PUBLISHED"
    assert rec["audio_master_sha256"] == SONORA_MASTER_SHA256
    assert json.loads((out / "stage.json").read_text()) == rec
    with pytest.raises(ReelBlocked, match="already exists"):
        vm.stage_video(fake_plan(), CAPTION, out)


def test_fail_closed_on_invalid_sources_before_render(monkeypatch, tmp_path):
    good = fake_plan()
    bad = dict(good, approved_audio_sha256="0" * 64)
    with pytest.raises(ReelBlocked):
        vm.stage_video(bad, CAPTION, tmp_path / "somewhere")
    with pytest.raises(ReelBlocked, match="QC"):
        vm.stage_video(dict(good, frame_count=5), CAPTION, tmp_path / "somewhere")
    with pytest.raises(ReelBlocked, match="QC"):
        vm.stage_video(good, CAPTION + "Changed", tmp_path / "somewhere")


def test_stage_folder_exact_episode_and_date():
    assert vm.output_folder("Ep151", "2026-11-19").as_posix() == (
        "publisher_media/video-ep151-20261119")
    with pytest.raises(ValueError):
        vm.output_folder("newest", "2026-11-19")


def test_shared_stage_can_only_be_reused_for_identical_drive_qc(monkeypatch, tmp_path):
    plan = fake_plan()
    folder = tmp_path / "publisher_media/video-ep151-20261119"
    folder.mkdir(parents=True)
    video = b"mock-mp4" * 25000
    (folder / "reel.mp4").write_bytes(video)
    (folder / "caption.txt").write_text(CAPTION)
    details = {"width": 1080, "height": 1920, "fps": 30, "duration_seconds": 18.0,
               "video_codec": "h264", "audio_codec": "aac", "bytes": len(video),
               "sha256": hashlib.sha256(video).hexdigest()}
    receipt = {"schema": vm.STAGE_SCHEMA, "episode": plan["episode"],
               "date_sast": plan["date_sast"], "archive_folder_id": plan["archive_folder_id"],
               "source_frames": plan["frames"], "caption_sha256": plan["reel_caption_sha256"],
               "audio_master_sha256": SONORA_MASTER_SHA256,
               "video_variant": "C_Stronger", "status": "STAGED_NOT_PUBLISHED",
               "published": False, "video": {"name": "reel.mp4", **details}}
    (folder / "stage.json").write_text(json.dumps(receipt))
    monkeypatch.setattr(vm, "verify_mp4", lambda path: dict(details))
    assert vm.verify_reusable_stage(plan, CAPTION, folder) == receipt
    with pytest.raises(ReelBlocked, match="differs"):
        vm.verify_reusable_stage(dict(plan, frames=[]), CAPTION, folder)
    (folder / "reel.mp4").write_bytes(video + b"corrupt")
    monkeypatch.setattr(vm, "verify_mp4", lambda path: dict(details, bytes=path.stat().st_size))
    with pytest.raises(ReelBlocked, match="checksum"):
        vm.verify_reusable_stage(plan, CAPTION, folder)
