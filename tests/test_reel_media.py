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
from PIL import Image, ImageChops, ImageDraw

from src import reel_audio, reel_media as reel

CAPTION = (
    "South Africa reports a tenth arrest. Guilt remains unproven.\n\n"
    "#AIGeopolitic #SouthAfrica #Geopolitics #PoliticalAnalysis #NewsBriefing\n\n"
    "Post is Live!"
)


def test_original_audio_is_deterministic_and_stereo(tmp_path):
    # Deprecated five-note generator remains a regression fixture; production
    # stage_reel must never call it or fall back to it.
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


def test_accepted_version_b_is_pinned_exactly_and_copied_without_remixing(tmp_path):
    copy = tmp_path / "VS001.mp3"
    approval = reel.verified_sonora_master(copy)
    assert approval["approval"] == "IAN_APPROVED_2026-11-19_VERSION_B"
    assert approval["production_status"] == "LOCKED_APPROVED_MASTER"
    assert approval["sha256"] == reel.SONORA_MASTER_SHA256
    assert approval["bytes"] == reel.SONORA_MASTER_BYTES == copy.stat().st_size
    assert copy.read_bytes() == reel.SONORA_MASTER_PATH.read_bytes()
    assert approval["substitution_allowed"] is False


def test_approved_audio_missing_or_mutated_blocks_reels(monkeypatch, tmp_path):
    monkeypatch.setattr(reel, "SONORA_MASTER_PATH", tmp_path / "missing.mp3")
    with pytest.raises(reel.ReelBlocked, match="missing"):
        reel.verified_sonora_master()
    fake = tmp_path / "tampered.mp3"
    fake.write_bytes(b"not the accepted Version B master")
    monkeypatch.setattr(reel, "SONORA_MASTER_PATH", fake)
    with pytest.raises(reel.ReelBlocked, match="SHA-256"):
        reel.verified_sonora_master()
    with pytest.raises(reel.ReelBlocked, match="SHA-256"):
        reel.stage_reel(fake_plan(), CAPTION, tmp_path / "reel", run_ffmpeg=False)
    assert not (tmp_path / "reel").exists()


def test_original_flare_is_deterministic_and_transparent(tmp_path):
    a, b = tmp_path / "a" / "flare.png", tmp_path / "b" / "flare.png"
    first, second = reel.make_flare_overlay(a), reel.make_flare_overlay(b)
    assert first == second
    assert first["edits_preset_exact"] is False
    assert first["frame_count"] == 15
    assert first["style"] == "original-centre-expanding-circular-bloom-v3"
    with Image.open(a) as picture:
        assert picture.size == (1080, 1920)
        assert picture.mode == "RGBA"
        assert picture.getpixel((0, 0))[3] == 0
        assert picture.getpixel((540, 959))[3] > 0
    frames = sorted((a.parent / "flare_frames").glob("flare_*.png"))
    assert len(frames) == 15
    with Image.open(frames[0]) as start, Image.open(frames[7]) as middle:
        assert start.getchannel("A").getbbox() is None
        assert middle.getchannel("A").getbbox() is not None
    with Image.open(frames[4]) as early, Image.open(frames[10]) as late:
        early_bounds, late_bounds = early.getchannel("A").getbbox(), late.getchannel("A").getbbox()
        assert early_bounds and late_bounds
        assert (late_bounds[2] - late_bounds[0]) > (early_bounds[2] - early_bounds[0])


def test_reel_render_command_preserves_frames_and_platform_specs(tmp_path):
    frames = [tmp_path / f"ReelFrame{i:02d}of06.png" for i in range(1, 7)]
    cmd = reel.ffmpeg_command(frames, tmp_path / "soundtrack.wav",
                              tmp_path / "flare_frames" / "flare_%02d.png", tmp_path / "Reel.mp4",
                              variant="B_Noticeable")
    command = " ".join(cmd)
    assert cmd[0] == "ffmpeg" and command.count("-loop 1") == 6
    assert "-start_number 0" in command
    assert command.count("xfade=transition=fade") == 5
    assert "offset=2.850" in command and "offset=14.850" in command
    assert command.count("overlay=x=0:y=0") == 5
    assert "fade=t=in:st=0:d=0.900" in command
    assert "fade=t=out:st=17.100:d=0.900" in command
    assert "format=yuva420p,split=5" in command
    assert "trim=duration=0.500" in command
    assert "-b:a 128k" in command
    assert "zoompan" not in command
    assert command.count("perspective=") == 4
    assert command.count("sense=destination:interpolation=cubic:eval=frame") == 4
    assert command.count("0.080000*pow(") == 32
    stronger = " ".join(reel.ffmpeg_command(frames, tmp_path / "soundtrack.wav",
                                             tmp_path / "flare_frames" / "flare_%02d.png",
                                             tmp_path / "stronger.mp4", variant="C_Stronger"))
    assert stronger.count("0.120000*pow(") == 32
    assert "-c:v libx264" in command and "-c:a aac" in command
    assert "-pix_fmt yuv420p" in command
    assert "-t 18.000" in command and "-r 30" in command
    assert all(str(frame) in cmd for frame in frames)
    with pytest.raises(reel.ReelBlocked):
        reel.ffmpeg_command(frames[:5], tmp_path / "soundtrack.wav",
                            tmp_path / "flare_frames" / "flare_%02d.png", tmp_path / "Reel.mp4")
    with pytest.raises(reel.ReelBlocked, match="Unknown Reel"):
        reel.ffmpeg_command(frames, tmp_path / "soundtrack.wav",
                            tmp_path / "flare_frames" / "flare_%02d.png", tmp_path / "Reel.mp4",
                            variant="Unapproved")


def test_ffmpeg_executes_18_second_flare_edit_on_small_synthetic_inputs(tmp_path):
    """An actual codec/filter smoke test without touching an accepted episode."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg and ffprobe are required for the integration check")
    frames = []
    for i in range(1, 7):
        path = tmp_path / f"frame{i}.png"
        picture = Image.new("RGB", (216, 384), (i * 25, 35, 75))
        brush = ImageDraw.Draw(picture)
        brush.rectangle((55, 110, 160, 280), outline=(240, 250, 250), width=6)
        brush.line((18, 60, 192, 320), fill=(255, 220, 40), width=4)
        picture.save(path)
        frames.append(path)
    flare = tmp_path / "flare.png"
    metadata = reel.make_flare_overlay(flare)
    assert metadata["frame_count"] == 15
    output = tmp_path / "review.mp4"
    # A real FFmpeg pass must also accept and transcode the exact pinned MP3.
    run = subprocess.run(reel.ffmpeg_command(frames, reel.SONORA_MASTER_PATH,
                                             tmp_path / metadata["animation_pattern"], output,
                                             variant="B_Noticeable",
                                             render_size=(216, 384)),
                         capture_output=True, text=True, timeout=180)
    assert run.returncode == 0, run.stderr[-2_000:]
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                            str(output)], check=True, capture_output=True, text=True)
    assert abs(float(probe.stdout.strip()) - 18.0) < 0.35
    streams = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
        "stream=codec_name,sample_rate,channels", "-of", "json", str(output),
    ], check=True, capture_output=True, text=True)
    assert json.loads(streams.stdout)["streams"][0] == {
        "codec_name": "aac", "sample_rate": "48000", "channels": 2}

    def frame_at(seconds):
        sample = subprocess.run([
            "ffmpeg", "-v", "error", "-ss", str(seconds), "-i", str(output),
            "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ], check=True, capture_output=True, timeout=30)
        return Image.frombytes("RGB", (216, 384), sample.stdout)

    # Two instants within the same second clip differ because the digital
    # camera zoom really changed, rather than holding the source PNG still.
    assert ImageChops.difference(frame_at(3.55), frame_at(5.45)).getbbox()
    # The centred expanding circular bloom is brighter at the 3-second cut.
    assert sum(frame_at(3.0).getpixel((108, 192))) > sum(frame_at(2.6).getpixel((108, 192)))
    # First visible frame fades up; the final frame fades to black.
    assert sum(frame_at(0.0).getpixel((108, 192))) < sum(frame_at(0.9).getpixel((108, 192)))
    assert sum(frame_at(17.9).getpixel((108, 192))) < sum(frame_at(17.1).getpixel((108, 192)))


def test_subpixel_zoom_keeps_fine_ink_lines_stable(tmp_path):
    """Regress the visible one-pixel shudder from zoompan's integer crop origin."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg is required for subpixel motion QC")
    width, height, count = 216, 384, 99
    frame = tmp_path / "fine-line.png"
    scene = Image.new("RGB", (width, height), "black")
    ImageDraw.Draw(scene).line((58, 0, 58, height), fill="white", width=1)
    scene.save(frame)
    camera = reel.subpixel_zoom_filter(1.12, count - 1)
    result = subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
        "-loop", "1", "-framerate", "30", "-t", "3.3", "-i", str(frame),
        "-vf", f"fps=30,scale={width}:{height},{camera}format=yuv420p",
        "-frames:v", str(count), "-pix_fmt", "gray", "-f", "rawvideo", "-",
    ], capture_output=True, timeout=60)
    assert result.returncode == 0, result.stderr[-2000:]
    frame_bytes = width * height
    assert len(result.stdout) == count * frame_bytes
    centres = []
    for i in range(count):
        # Luma black is ~16. Ignore it when measuring the one-pixel ink edge.
        row_start = i * frame_bytes + height // 2 * width
        row = result.stdout[row_start + 40:row_start + 75]
        weights = [max(0, v - 16) for v in row]
        centres.append(40 + sum((j * v for j, v in enumerate(weights))) / sum(weights))
    assert centres[-1] - centres[0] > 5.0
    assert max(abs(b - a) for a, b in zip(centres, centres[1:])) < 0.4


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
    monkeypatch.setattr(reel, "verified_qc_records", lambda *args: delivered)
    monkeypatch.setattr(reel, "safe_rclone", lambda *args, **kwargs: CAPTION.encode())
    observed, caption = reel.read_reel_archive("Ep145", "2026-11-13")
    assert observed["frame_count"] == 6 and caption == CAPTION
    assert observed["approved_for_reel_publication"] is False
    qc["image_counts"]["reel"] = 5
    with pytest.raises(reel.ReelBlocked):
        reel.read_reel_archive("Ep145", "2026-11-13")


def test_newer_qc_contract_verifies_reel_caption_and_frames(monkeypatch):
    plan = fake_plan()
    qc_sha = reel.sha(CAPTION.encode())
    caption_name = "Ep145_ReelCaption.txt"
    qc = {"counts": {"reel": 6},
          "captions": {"Reel": {"sha256": qc_sha, "text": CAPTION,
                                  "archive": {"filename": caption_name,
                                              "drive_id": "captionfile1234",
                                              "local_sha256": qc_sha,
                                              "readback_sha256": qc_sha,
                                              "bytes_identical": True,
                                              "exact_text_bytes_including_linebreaks": True}}},
          "deliverables": [{"name": caption_name, "id": "captionfile1234",
                            "mime_type": "text/plain"}]}
    files = [{"Name": caption_name, "MimeType": "text/plain", "ID": "captionfile1234"}]
    evidence = {}
    for frame in plan["frames"]:
        files.append({"Name": frame["name"], "MimeType": "image/png", "ID": frame["drive_id"]})
        evidence[frame["name"]] = {
            "drive_id": frame["drive_id"], "source_sha256": frame["sha256"],
            "readback_sha256": frame["sha256"], "readback_verified": True,
            "dimensions": [1080, 1920]}
    monkeypatch.setattr(reel, "read_approved_archive", lambda *args: (
        {"archive_folder_id": plan["archive_folder_id"]}, "carousel", files))
    monkeypatch.setattr(reel, "verified_qc_records", lambda *args: evidence)
    monkeypatch.setattr(reel, "_read_json", lambda *args: qc)
    monkeypatch.setattr(reel, "safe_rclone", lambda *args, **kwargs: CAPTION.encode())
    accepted, _ = reel.read_reel_archive("Ep145", "2026-11-13")
    assert accepted["frame_count"] == 6
    qc["captions"]["Reel"]["archive"]["bytes_identical"] = False
    with pytest.raises(reel.ReelBlocked, match="caption"):
        reel.read_reel_archive("Ep145", "2026-11-13")


def test_stage_never_overwrites_and_has_no_publish_authority(monkeypatch, tmp_path):
    plan = fake_plan()
    output = tmp_path / reel.output_folder("Ep145", "2026-11-13")
    monkeypatch.setattr(reel, "read_frame", lambda *args: b"accepted-png-bytes")
    monkeypatch.setattr(reel, "verify_mp4", lambda *args: {
        "sha256": "b" * 64, "bytes": 100_000, "duration_seconds": 18})
    receipt = reel.stage_reel(plan, CAPTION, output, run_ffmpeg=False)
    assert receipt["status"] == "REVIEW_MP4_READY_NOT_PUBLISHED"
    assert receipt["approved_for_reel_publication"] is False
    assert receipt["audio_approved_for_publication"] is True
    assert receipt["audio"]["sha256"] == reel.SONORA_MASTER_SHA256
    assert receipt["audio"]["approval"] == "IAN_APPROVED_2026-11-19_VERSION_B"
    assert receipt["duration_seconds"] == 18
    assert receipt["effects"]["transition_count"] == 5
    assert set(receipt["videos"]) == {"B_Noticeable", "C_Stronger"}
    assert receipt["effects"]["middle"] == "steady_out_centered_zoom"
    assert receipt["effects"]["camera_implementation"] == "centered_subpixel_cubic_perspective_v3"
    assert receipt["effects"]["variants"] == reel.ZOOM_VARIANTS
    assert receipt["effects"]["preferred_variant"] == "C_Stronger"
    assert (output / "flare_overlay.png").is_file()
    assert reel.sha((output / f"{reel.SONORA_MASTER_ID}.mp3").read_bytes()) == reel.SONORA_MASTER_SHA256
    assert json.loads((output / "audio_provenance.json").read_text()) == receipt["audio"]
    assert len(list(output.glob("ReelFrame*"))) == 6
    assert json.loads((output / "stage.json").read_text())["frame_count"] == 6
    with pytest.raises(reel.ReelBlocked, match="already exists"):
        reel.stage_reel(plan, CAPTION, output, run_ffmpeg=False)


def test_reel_accepts_five_flexible_hashtags():
    parts = CAPTION.split("\n\n")
    parts[1] = "#Uganda #Kampala #EastAfrica #RegionalTrade #TradePolicy"
    caption = "\n\n".join(parts)
    assert reel.verify_reel_caption(caption) == hashlib.sha256(caption.encode("utf-8")).hexdigest()
    with pytest.raises(reel.ReelBlocked):
        reel.verify_reel_caption(caption + " #Extra")
    with pytest.raises(reel.ReelBlocked):
        reel.verify_reel_caption(caption.replace("#Uganda", "#kampala"))


def test_invalid_caption_or_drive_frame_is_blocked():
    with pytest.raises(reel.ReelBlocked):
        reel.verify_reel_caption("TEST ONLY: #AIGeopolitic")
    with pytest.raises(reel.ReelBlocked):
        reel.read_frame("../other.png", "1mvKV0f6LFwv8sln8Ps0YD9Ql5f9lLP9H", "a" * 64)
