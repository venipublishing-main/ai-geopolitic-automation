"""No-provider, no-network, no-Meta-POST Reel build and provenance tests."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
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


def test_original_flare_is_deterministic_and_transparent(tmp_path):
    a, b = tmp_path / "flare-a.png", tmp_path / "flare-b.png"
    first, second = reel.make_flare_overlay(a), reel.make_flare_overlay(b)
    assert first == second
    assert first["edits_preset_exact"] is False
    with Image.open(a) as picture:
        assert picture.size == (1080, 1920)
        assert picture.mode == "RGBA"
        assert picture.getpixel((0, 0))[3] == 0
        assert picture.getpixel((540, 959))[3] > 0


def test_reel_render_command_preserves_frames_and_platform_specs(tmp_path):
    frames = [tmp_path / f"ReelFrame{i:02d}of06.png" for i in range(1, 7)]
    cmd = reel.ffmpeg_command(frames, tmp_path / "soundtrack.wav",
                              tmp_path / "flare.png", tmp_path / "Reel.mp4")
    command = " ".join(cmd)
    assert cmd[0] == "ffmpeg" and command.count("-loop 1") == 7
    assert command.count("xfade=transition=fade") == 5
    assert "offset=2.850" in command and "offset=14.850" in command
    assert command.count("overlay=x=0:y=0") == 5
    assert "fade=t=in:st=0:d=0.250" in command
    assert "fade=t=out:st=17.650:d=0.350" in command
    assert "format=yuva420p,split=5" in command
    assert "-b:a 128k" in command
    assert "zoompan" not in command and "scale=" not in command
    assert "-c:v libx264" in command and "-c:a aac" in command
    assert "-pix_fmt yuv420p" in command
    assert "-t 18.000" in command and "-r 30" in command
    assert all(str(frame) in cmd for frame in frames)
    with pytest.raises(reel.ReelBlocked):
        reel.ffmpeg_command(frames[:5], tmp_path / "soundtrack.wav",
                            tmp_path / "flare.png", tmp_path / "Reel.mp4")


def test_ffmpeg_executes_18_second_flare_edit_on_small_synthetic_inputs(tmp_path):
    """An actual codec/filter smoke test without touching an accepted episode."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg and ffprobe are required for the integration check")
    frames = []
    for i in range(1, 7):
        path = tmp_path / f"frame{i}.png"
        Image.new("RGB", (216, 384), (i * 25, 35, 75)).save(path)
        frames.append(path)
    flare = tmp_path / "flare.png"
    # Same RGBA input contract as the full-resolution authored overlay.
    Image.new("RGBA", (216, 384), (255, 235, 180, 120)).save(flare)
    wav = tmp_path / "audio.wav"
    reel_audio.write_original_bed(wav, duration=18.0, sample_rate=8_000)
    output = tmp_path / "review.mp4"
    run = subprocess.run(reel.ffmpeg_command(frames, wav, flare, output),
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr[-2_000:]
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                            str(output)], check=True, capture_output=True, text=True)
    assert abs(float(probe.stdout.strip()) - 18.0) < 0.35


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
    def audio(target, *, duration):
        target.write_bytes(b"mock-original-audio")
        return {"wav_sha256": reel.sha(b"mock-original-audio"), "external_samples": False,
                "duration_seconds": duration}
    monkeypatch.setattr(reel, "write_original_bed", audio)
    monkeypatch.setattr(reel, "verify_mp4", lambda *args: {
        "sha256": "b" * 64, "bytes": 100_000, "duration_seconds": 18})
    receipt = reel.stage_reel(plan, CAPTION, output, run_ffmpeg=False)
    assert receipt["status"] == "REVIEW_MP4_READY_NOT_PUBLISHED"
    assert receipt["approved_for_reel_publication"] is False
    assert receipt["audio_approved_for_publication"] is False
    assert receipt["duration_seconds"] == 18
    assert receipt["effects"]["transition_count"] == 5
    assert (output / "flare_overlay.png").is_file()
    assert len(list(output.glob("ReelFrame*"))) == 6
    assert json.loads((output / "stage.json").read_text())["frame_count"] == 6
    with pytest.raises(reel.ReelBlocked, match="already exists"):
        reel.stage_reel(plan, CAPTION, output, run_ffmpeg=False)


def test_invalid_caption_or_drive_frame_is_blocked():
    with pytest.raises(reel.ReelBlocked):
        reel.verify_reel_caption("TEST ONLY: #AIGeopolitic")
    with pytest.raises(reel.ReelBlocked):
        reel.read_frame("../other.png", "1mvKV0f6LFwv8sln8Ps0YD9Ql5f9lLP9H", "a" * 64)
