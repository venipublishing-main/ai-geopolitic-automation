"""No-provider, no-network, no-Meta-POST Reel build and provenance tests."""
from __future__ import annotations

import hashlib
import json
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from src import reel_audio, reel_media as reel

CAPTION = (
    "South Africa reports a tenth arrest. Guilt remains unproven.\n\n"
    "#AIGeopolitic #SouthAfrica #Geopolitics #PoliticalAnalysis #NewsBriefing\n\n"
    "Post is Live!"
)


def test_original_audio_is_deterministic_and_stereo(tmp_path):
    a, b = tmp_path / "a.wav", tmp_path / "b.wav"
    first = reel_audio.write_original_bed(a, duration=0.4, sample_rate=8_000)
    second = reel_audio.write_original_bed(b, duration=0.4, sample_rate=8_000)
    assert first == second
    assert first["external_samples"] is False and first["vocals"] is False
    assert 0 < first["peak_linear"] < 0.5
    with wave.open(str(a), "rb") as wav:
        assert wav.getnchannels() == 2
        assert wav.getframerate() == 8_000
        assert wav.getnframes() == 3_200


def test_reel_render_command_preserves_frames_and_platform_specs(tmp_path):
    frames = [tmp_path / f"ReelFrame{i:02d}of06.png" for i in range(1, 7)]
    cmd = reel.ffmpeg_command(frames, tmp_path / "soundtrack.wav", tmp_path / "Reel.mp4")
    command = " ".join(cmd)
    assert cmd[0] == "ffmpeg"
    assert command.count("-loop 1") == 6
    assert command.count("xfade=transition=fade") == 5
    assert "offset=4.950" in command and "offset=24.750" in command
    assert "-c:v libx264" in command and "-c:a aac" in command
    assert "-pix_fmt yuv420p" in command
    assert "-t 30.000" in command and "-r 30" in command
    assert all(str(frame) in cmd for frame in frames)
    with pytest.raises(reel.ReelBlocked):
        reel.ffmpeg_command(frames[:5], tmp_path / "soundtrack.wav", tmp_path / "Reel.mp4")


def fake_plan():
    return {
        "schema": reel.REEL_SCHEMA,
        "episode": "Ep145", "date_sast": "2026-11-13",
        "archive_folder_id": "1mvKV0f6LFwv8sln8Ps0YD9Ql5f9lLP9H",
        "approved_for_reel_publication": False,
        "reel_caption_sha256": reel.sha(CAPTION.encode()),
        "frames": [{"name": f"ReelFrame{i:02d}of06.png", "sha256": "a" * 64,
                    "drive_id": f"sample-file-{i}", "width": 1080, "height": 1920}
                   for i in range(1, 7)],
    }


def test_exact_six_frame_archive_and_caption_qc(monkeypatch):
    plan = fake_plan()
    listing = [{"Name": "Ep145_ReelCaption.txt", "MimeType": "text/plain", "ID": "captionfile1234"}]
    delivered = {"Ep145_ReelCaption.txt": {
        "drive_id": "captionfile1234", "sha256": reel.sha(CAPTION.encode()),
        "readback_verified": True}}
    for frame in plan["frames"]:
        listing.append({"Name": frame["name"], "MimeType": "image/png", "ID": frame["drive_id"]})
        delivered[frame["name"]] = {
            "drive_id": frame["drive_id"], "source_sha256": frame["sha256"],
            "readback_sha256": frame["sha256"], "readback_verified": True,
            "dimensions": [1080, 1920]}
    qc = {"image_counts": {"reel": 6}, "delivered": delivered}
    monkeypatch.setattr(reel, "read_approved_archive", lambda *args: (
        {"archive_folder_id": plan["archive_folder_id"]}, "carousel", listing))
    monkeypatch.setattr(reel, "_read_json", lambda *args: qc)
    monkeypatch.setattr(reel, "safe_rclone", lambda *args, **kwargs: CAPTION.encode())
    observed, caption = reel.read_reel_archive("Ep145", "2026-11-13")
    assert observed["frame_count"] == 6 and caption == CAPTION
    assert observed["approved_for_reel_publication"] is False
    qc["image_counts"]["reel"] = 5
    with pytest.raises(reel.ReelBlocked):
        reel.read_reel_archive("Ep145", "2026-11-13")


def test_stage_never_overwrites_and_has_no_publish_authority(monkeypatch, tmp_path):
    plan = fake_plan()
    output = tmp_path / reel.output_folder("Ep145", "2026-11-13")
    monkeypatch.setattr(reel, "read_frame", lambda *args: b"accepted-png-bytes")
    def audio(target):
        target.write_bytes(b"mock-original-audio")
        return {"wav_sha256": reel.sha(b"mock-original-audio"), "external_samples": False}
    monkeypatch.setattr(reel, "write_original_bed", audio)
    monkeypatch.setattr(reel, "verify_mp4", lambda *args: {
        "sha256": "b" * 64, "bytes": 100_000, "duration_seconds": 30})
    receipt = reel.stage_reel(plan, CAPTION, output, run_ffmpeg=False)
    assert receipt["status"] == "REVIEW_MP4_READY_NOT_PUBLISHED"
    assert receipt["approved_for_reel_publication"] is False
    assert len(list(output.glob("ReelFrame*"))) == 6
    assert json.loads((output / "stage.json").read_text())["frame_count"] == 6
    with pytest.raises(reel.ReelBlocked, match="already exists"):
        reel.stage_reel(plan, CAPTION, output, run_ffmpeg=False)


def test_invalid_caption_or_drive_frame_is_blocked():
    with pytest.raises(reel.ReelBlocked):
        reel.verify_reel_caption("TEST ONLY: #AIGeopolitic")
    with pytest.raises(reel.ReelBlocked):
        reel.read_frame("../other.png", "1mvKV0f6LFwv8sln8Ps0YD9Ql5f9lLP9H", "a" * 64)
