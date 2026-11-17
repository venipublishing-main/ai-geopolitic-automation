"""Read-only canonical Drive -> review-only, six-frame Instagram Reel previews.

No Meta POST, no archive mutation, no publication signal and no Reel approval.
Two Edits-inspired variants animate *rendered video* without changing the six
verified source PNGs. These are not proprietary Edits effects or audio assets.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, UnidentifiedImageError

from src.reel_audio import write_original_bed, write_provenance
from src.threads_media import (
    DRIVE_ID_RE, SHA_RE, ThreadsBlocked, _read_json, has_five_distinct_hashtags,
    read_approved_archive, verified_qc_records,
    safe_rclone, validate_episode,
)

FRAME_COUNT = 6
WIDTH, HEIGHT = 1080, 1920
FPS = 30
DURATION = 18.0
FRAME_SECONDS = 3.0
TRANSITION = 0.30
FLARE_SECONDS = 0.50
OPENING_FADE = 0.90
CLOSING_FADE = 0.90
# At 112%, an even centered crop removes about 5.4% per side; the source
# 7-10% safe margin still requires actual mobile visual QC.
# Names are embedded in artifact filenames and the immutable review receipt.
ZOOM_VARIANTS = {"B_Noticeable": 1.08, "C_Stronger": 1.12}
MAX_PNG = 40 * 1024 * 1024
MAX_REEL = 200 * 1024 * 1024
REEL_SCHEMA = "ai-geopolitic.reel.archive-plan.v1"
STAGE_SCHEMA = "ai-geopolitic.reel.review-stage.v1"


class ReelBlocked(ThreadsBlocked):
    """No fallback to nearby episodes, unverified images, or auto-publishing."""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def output_folder(episode: str, day: str) -> Path:
    validate_episode(episode, day)
    return Path("publisher_media") / f"reel-{episode.lower()}-{day.replace('-', '')}"


def verify_reel_caption(caption: str) -> str:
    if (not isinstance(caption, str)
            or not 30 <= len(caption.encode("utf-8")) <= 2200
            or not has_five_distinct_hashtags(caption)
            or caption.startswith("TEST ONLY")):
        raise ReelBlocked("Canonical Reel caption is missing, unsafe or too long.")
    return sha(caption.encode("utf-8"))


def read_reel_archive(episode: str, day_text: str) -> tuple[dict, str]:
    """Require existing editorial PASS and an independent six-frame QC record."""
    episode, day, _ = validate_episode(episode, day_text)
    carousel_plan, _, files = read_approved_archive(episode, day_text)
    folder = carousel_plan["archive_folder_id"]
    found = {entry["Name"]: entry for entry in files}
    qc = _read_json(f"{episode}_QC_Completion.json", folder, 2_000_000)
    counts = qc.get("image_counts", qc.get("counts"))
    if not isinstance(counts, dict) or counts.get("reel") != FRAME_COUNT:
        raise ReelBlocked("Six Reel frames are not separately certified in production QC.")
    # The shared Threads evidence normalizer verifies original and newer QC
    # schemas, including per-frame exact source/readback SHA and Drive IDs.
    delivered = verified_qc_records(qc, episode, day, folder)
    cap_name = f"{episode}_ReelCaption.txt"
    meta = found.get(cap_name, {})
    if "delivered" in qc:
        rec = delivered.get(cap_name, {})
        expected_caption_sha = rec.get("sha256")
    else:
        captions = qc.get("captions")
        if not isinstance(captions, dict):
            raise ReelBlocked("New-format Reel caption QC is missing.")
        reel_caption = captions.get("Reel", {})
        archive = reel_caption.get("archive", {}) if isinstance(reel_caption, dict) else {}
        indexed = {item.get("name"): item for item in qc.get("deliverables", [])
                   if isinstance(item, dict)}
        rec = {"drive_id": archive.get("drive_id"),
               "readback_verified": archive.get("bytes_identical") is True}
        expected_caption_sha = archive.get("local_sha256")
        if (archive.get("filename") != cap_name
                or not SHA_RE.fullmatch(str(expected_caption_sha or ""))
                or archive.get("readback_sha256") != expected_caption_sha
                or archive.get("exact_text_bytes_including_linebreaks") is not True
                or reel_caption.get("sha256") != expected_caption_sha
                or indexed.get(cap_name, {}).get("id") != archive.get("drive_id")
                or indexed.get(cap_name, {}).get("mime_type") != "text/plain"):
            raise ReelBlocked("Reel caption has no verified production QC readback.")
    if (meta.get("MimeType") != "text/plain"
            or not DRIVE_ID_RE.fullmatch(str(meta.get("ID", "")))
            or rec.get("drive_id") != meta["ID"]
            or rec.get("readback_verified") is not True):
        raise ReelBlocked("Canonical Reel caption is not verified in Drive QC.")
    remote = os.environ.get("AI_GEO_RCLONE_REMOTE", "ai_geopolitic_drive")
    raw_caption = safe_rclone("cat", f"{remote}:{cap_name}", folder, limit=16_000)
    try:
        caption = raw_caption.decode("utf-8-sig")
    except UnicodeError:
        raise ReelBlocked("Reel caption is not valid UTF-8.") from None
    digest = verify_reel_caption(caption)
    if expected_caption_sha != digest:
        raise ReelBlocked("Reel caption SHA disagrees with verified Drive readback.")
    if "delivered" not in qc and reel_caption.get("text") != caption:
        raise ReelBlocked("Reel caption differs from its canonical QC text.")
    frames = []
    for i in range(1, FRAME_COUNT + 1):
        name = f"ReelFrame{i:02d}of06.png"
        meta, rec = found.get(name, {}), delivered.get(name, {})
        if (meta.get("MimeType") != "image/png"
                or not DRIVE_ID_RE.fullmatch(str(meta.get("ID", "")))
                or rec.get("drive_id") != meta["ID"]
                or not SHA_RE.fullmatch(str(rec.get("source_sha256", "")))
                or rec.get("source_sha256") != rec.get("readback_sha256")
                or rec.get("readback_verified") is not True
                or rec.get("dimensions") != [WIDTH, HEIGHT]):
            raise ReelBlocked(f"Reel frame {i:02d} lacks exact accepted source QC.")
        frames.append({"name": name, "drive_id": meta["ID"],
                       "sha256": rec["source_sha256"], "width": WIDTH, "height": HEIGHT})
    plan = {
        "schema": REEL_SCHEMA, "episode": episode,
        "date_sast": day.isoformat(), "archive_folder_id": folder,
        "reel_caption_sha256": digest, "reel_caption_utf8_bytes": len(raw_caption),
        "frames": frames, "frame_count": FRAME_COUNT,
        "carousel_handoff_passed": True,
        "approved_for_reel_publication": False,
        "audio_status": "ORIGINAL_MOTIF_PILOT_PENDING_IAN_APPROVAL",
    }
    return plan, caption


def read_frame(name: str, folder: str, expected_sha: str) -> bytes:
    """Read only one exact, numbered archive PNG; never fetch arbitrary paths."""
    if not re.fullmatch(r"ReelFrame0[1-6]of06\.png", name) or not DRIVE_ID_RE.fullmatch(folder):
        raise ReelBlocked("Disallowed Drive Reel frame path.")
    remote = os.environ.get("AI_GEO_RCLONE_REMOTE", "ai_geopolitic_drive")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", remote):
        raise ReelBlocked("Disallowed Drive remote.")
    try:
        result = subprocess.run([
            "rclone", "cat", f"{remote}:{name}", "--drive-root-folder-id", folder,
            "--count", str(MAX_PNG + 1),
        ], capture_output=True, check=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        raise ReelBlocked("Authenticated read-only Reel frame download failed.") from None
    raw = result.stdout
    if not raw or len(raw) > MAX_PNG or sha(raw) != expected_sha:
        raise ReelBlocked("Reel frame bytes differ from the accepted archive.")
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.format != "PNG" or image.size != (WIDTH, HEIGHT):
                raise ReelBlocked("Reel frame dimensions or format differ from QC.")
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ReelBlocked("Reel frame failed image integrity check.") from None
    return raw


def make_flare_overlay(path: Path) -> dict:
    """Author an expanding circular light bloom, never a travelling line.

    Exactly 15 transparent RGBA frames are generated at half-resolution and
    played at 30fps across each 0.5s transition. The immutable, accepted Reel
    frames are not edited. The effect is original, not an Edits preset copy.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    sequence = path.parent / "flare_frames"
    sequence.mkdir(parents=True, exist_ok=False)
    w, h = WIDTH // 2, HEIGHT // 2
    cx, cy = w // 2, h // 2
    count = round(FLARE_SECONDS * FPS)
    digests = []
    for i in range(count):
        progress = i / (count - 1)
        envelope = max(0.0, math.sin(math.pi * progress)) ** 0.65
        # Radius is defined in full-resolution pixels so the ring becomes
        # visibly larger than the frame's width before it disappears.
        radius = (15 + 1180 * progress ** 1.6) / 2
        box = (round(cx-radius), round(cy-radius),
               round(cx+radius), round(cy+radius))
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))

        halo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(halo)
        outer = radius * 1.20
        d.ellipse((round(cx-outer), round(cy-outer),
                   round(cx+outer), round(cy+outer)),
                  fill=(255, 232, 179, round(62 * envelope)))
        canvas = Image.alpha_composite(canvas, halo.filter(ImageFilter.GaussianBlur(28)))

        ring = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(ring)
        d.ellipse(box, outline=(255, 206, 135, round(190 * envelope)),
                  width=max(3, round(radius * 0.09)))
        canvas = Image.alpha_composite(canvas, ring.filter(ImageFilter.GaussianBlur(11)))
        d = ImageDraw.Draw(canvas)
        d.ellipse(box, outline=(255, 247, 227, round(145 * envelope)),
                  width=max(2, round(radius * 0.018)))

        centre = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(centre)
        core_radius = max(12, radius * 0.23)
        d.ellipse((round(cx-core_radius), round(cy-core_radius),
                   round(cx+core_radius), round(cy+core_radius)),
                  fill=(255, 251, 238, round(95 * envelope)))
        canvas = Image.alpha_composite(canvas, centre.filter(ImageFilter.GaussianBlur(16)))

        filename = sequence / f"flare_{i:02d}.png"
        canvas.save(filename, format="PNG", optimize=False)
        digests.append(sha(filename.read_bytes()))
        if i == count // 2:
            canvas.resize((WIDTH, HEIGHT), Image.Resampling.BICUBIC).save(
                path, format="PNG", optimize=False)

    return {"style": "original-centre-expanding-circular-bloom-v3",
            "edits_preset_exact": False, "width": WIDTH, "height": HEIGHT,
            "frame_count": count, "frame_rate": FPS,
            "animation_pattern": "flare_frames/flare_%02d.png",
            "animation_sha256": sha("".join(digests).encode("ascii")),
            "sha256": sha(path.read_bytes())}


def ffmpeg_command(frames: list[Path], wav: Path, flare: Path, output: Path,
                   *, variant: str = "B_Noticeable", ffmpeg_bin: str = "ffmpeg",
                   render_size: tuple[int, int] = (WIDTH, HEIGHT)) -> list[str]:
    if len(frames) != FRAME_COUNT or len(set(frames)) != FRAME_COUNT:
        raise ReelBlocked("Exactly six distinct approved frames are mandatory.")
    if FRAME_SECONDS * FRAME_COUNT != DURATION:
        raise ReelBlocked("The locked six-by-three-second edit must total 18 seconds.")
    if variant not in ZOOM_VARIANTS:
        raise ReelBlocked("Unknown Reel review zoom variant.")
    if (not isinstance(render_size, tuple) or len(render_size) != 2
            or any(not isinstance(v, int) or v < 64 or v > 4096 for v in render_size)):
        raise ReelBlocked("Invalid Reel preview render dimensions.")
    args = [ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-nostdin", "-y"]
    for index, frame in enumerate(frames):
        # Each boundary transition straddles its exact 3-second cut point.
        # Middle clips contribute half an overlap at both ends.
        clip_duration = FRAME_SECONDS + (TRANSITION / 2 if index in (0, 5) else TRANSITION)
        args += ["-loop", "1", "-framerate", str(FPS),
                 "-t", f"{clip_duration:.3f}", "-i", str(frame)]
    args += ["-framerate", str(FPS), "-start_number", "0", "-i", str(flare)]
    args += ["-i", str(wav)]
    filters = []
    for i in range(FRAME_COUNT):
        # FFmpeg zoompan renders a new crop on each frame. The middle images
        # smoothly reduce from 108% or 112% to 100%; first/last remain still.
        start = ZOOM_VARIANTS[variant] if 1 <= i <= 4 else 1.0
        duration = FRAME_SECONDS + (TRANSITION / 2 if i in (0, 5) else TRANSITION)
        last_frame = max(1, round(duration * FPS) - 1)
        zoom = (f"1+{start - 1:.6f}*pow(max(0,1-on/{last_frame}),2)"
                if start > 1 else "1")
        filters.append(f"[{i}:v]fps={FPS},format=yuv420p,"
                       f"zoompan=z='{zoom}':x='(iw-iw/zoom)/2':"
                       f"y='(ih-ih/zoom)/2':d=1:"
                       f"s={render_size[0]}x{render_size[1]}:fps={FPS},"
                       f"setsar=1,format=yuv420p[v{i}]")
    prior = "v0"
    for i in range(1, FRAME_COUNT):
        target = f"x{i}"
        offset = i * FRAME_SECONDS - TRANSITION / 2
        filters.append(f"[{prior}][v{i}]xfade=transition=fade:"
                       f"duration={TRANSITION:.3f}:offset={offset:.3f}[{target}]")
        prior = target
    filters.append(f"[{prior}]fade=t=in:st=0:d={OPENING_FADE:.3f},"
                   f"fade=t=out:st={DURATION-CLOSING_FADE:.3f}:"
                   f"d={CLOSING_FADE:.3f}[base]")
    filters.append(f"[6:v]fps={FPS},scale={render_size[0]}:{render_size[1]},"
                   "format=yuva420p,split=5" +
                   "".join(f"[fl{i}]" for i in range(1, FRAME_COUNT)))
    prior = "base"
    for i in range(1, FRAME_COUNT):
        offset = i * FRAME_SECONDS - FLARE_SECONDS / 2
        filters.append(f"[fl{i}]trim=duration={FLARE_SECONDS:.3f},"
                       f"setpts=PTS-STARTPTS,"
                       f"setpts=PTS+{offset:.3f}/TB[flare{i}]")
        target = f"overlay{i}"
        # The animation itself expands radially; the overlay remains centered.
        filters.append(f"[{prior}][flare{i}]overlay=x=0:y=0:"
                       f"eval=frame:eof_action=pass:repeatlast=0:shortest=0[{target}]")
        prior = target
    filters.append(f"[{prior}]format=yuv420p[outv]")
    args += ["-filter_complex", ";".join(filters), "-map", "[outv]", "-map", "7:a:0",
             "-t", f"{DURATION:.3f}", "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "21", "-profile:v", "high", "-pix_fmt", "yuv420p",
             "-r", str(FPS), "-c:a", "aac", "-b:a", "128k",
             "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(output)]
    return args


def verify_mp4(mp4: Path, *, ffprobe_bin: str = "ffprobe") -> dict:
    if not mp4.is_file() or not 100_000 <= mp4.stat().st_size <= MAX_REEL:
        raise ReelBlocked("MP4 is missing, too small or exceeds the Reel staging cap.")
    try:
        result = subprocess.run([
            ffprobe_bin, "-v", "error", "-print_format", "json",
            "-show_entries", "stream=codec_type,codec_name,width,height,avg_frame_rate,pix_fmt:format=duration",
            str(mp4)], capture_output=True, check=True, timeout=60)
        info = json.loads(result.stdout)
        streams = info["streams"]
        video = [s for s in streams if s.get("codec_type") == "video"]
        audio = [s for s in streams if s.get("codec_type") == "audio"]
        seconds = float(info["format"]["duration"])
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, KeyError):
        raise ReelBlocked("Rendered video could not be independently probed.") from None
    if (len(video) != 1 or len(audio) != 1
            or video[0].get("codec_name") != "h264"
            or video[0].get("width") != WIDTH or video[0].get("height") != HEIGHT
            or video[0].get("pix_fmt") != "yuv420p"
            or video[0].get("avg_frame_rate") != "30/1"
            or audio[0].get("codec_name") != "aac"
            or abs(seconds - DURATION) > 0.1):
        raise ReelBlocked("MP4 codec, audio, dimensions, FPS or duration failed QC.")
    return {"width": WIDTH, "height": HEIGHT, "fps": FPS,
            "duration_seconds": seconds, "video_codec": "h264",
            "audio_codec": "aac", "bytes": mp4.stat().st_size,
            "sha256": sha(mp4.read_bytes())}


def stage_reel(plan: dict, caption: str, output: Path, *, run_ffmpeg=True) -> dict:
    if output.exists():
        raise ReelBlocked("Reel stage already exists; no silent overwrites.")
    if plan.get("schema") != REEL_SCHEMA or plan.get("approved_for_reel_publication") is not False:
        raise ReelBlocked("Reel plan must be a verified, non-publication plan.")
    if verify_reel_caption(caption) != plan.get("reel_caption_sha256"):
        raise ReelBlocked("Reel caption changed between QC and staging.")
    if not isinstance(plan.get("frames"), list) or len(plan["frames"]) != FRAME_COUNT:
        raise ReelBlocked("Reel plan must contain exactly six frames.")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix="reel-review-", dir=output.parent))
    try:
        frames = []
        for i, record in enumerate(plan["frames"], 1):
            name = f"ReelFrame{i:02d}of06.png"
            if record.get("name") != name or not SHA_RE.fullmatch(str(record.get("sha256", ""))):
                raise ReelBlocked("Six exact source frames are required in order.")
            raw = read_frame(name, plan["archive_folder_id"], record["sha256"])
            target = temp / name
            target.write_bytes(raw)  # exact accepted PNG bytes; no regeneration
            frames.append(target)
        flare = make_flare_overlay(temp / "flare_overlay.png")
        audio = write_original_bed(temp / "soundtrack.wav", duration=DURATION)
        write_provenance(temp / "audio_provenance.json", audio)
        videos = {}
        for variant in ZOOM_VARIANTS:
            video_file = temp / f"Reel_{variant}.mp4"
            if run_ffmpeg:
                try:
                    subprocess.run(ffmpeg_command(frames, temp / "soundtrack.wav",
                                                  temp / flare["animation_pattern"],
                                                  video_file, variant=variant),
                                   check=True, capture_output=True, timeout=1200)
                except (OSError, subprocess.SubprocessError):
                    raise ReelBlocked(f"Deterministic FFmpeg {variant} Reel render failed.") from None
            videos[variant] = verify_mp4(video_file)
        (temp / "caption.txt").write_bytes(caption.encode("utf-8"))
        receipt = {
            "schema": STAGE_SCHEMA,
            "episode": plan["episode"], "date_sast": plan["date_sast"],
            "archive_folder_id": plan["archive_folder_id"],
            "source_frames": plan["frames"], "frame_count": FRAME_COUNT,
            "reel_caption_sha256": plan["reel_caption_sha256"],
            "duration_seconds": DURATION, "frame_seconds": FRAME_SECONDS,
            "effects": {"opening": {"name": "fade_in", "seconds": OPENING_FADE},
                        "middle": "steady_out_centered_zoom",
                        "variants": ZOOM_VARIANTS,
                        "closing": {"name": "fade_out", "seconds": CLOSING_FADE},
                        "transitions": "centre_expanding_circular_bloom",
                        "transition_seconds": TRANSITION,
                        "flare_seconds": FLARE_SECONDS,
                        "transition_count": FRAME_COUNT - 1, "flare": flare,
                        "edits_preset_exact": False},
            "audio": audio, "videos": videos,
            "audio_approved_for_publication": False,
            "approved_for_reel_publication": False,
            "status": "REVIEW_MP4_READY_NOT_PUBLISHED",
        }
        (temp / "stage.json").write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n")
        temp.rename(output)
        return receipt
    finally:
        if temp.exists():
            shutil.rmtree(temp)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "stage"))
    parser.add_argument("--episode", required=True)
    parser.add_argument("--date-sast", required=True)
    args = parser.parse_args(argv)
    try:
        plan, caption = read_reel_archive(args.episode, args.date_sast)
        if args.mode == "plan":
            result = {"status": "REEL_PREFLIGHT_PASSED_NO_PUBLICATION",
                      "episode": args.episode, "frames": FRAME_COUNT,
                      "caption_utf8_bytes": plan["reel_caption_utf8_bytes"],
                      "ready_for_review_render": True}
        else:
            target = output_folder(args.episode, args.date_sast)
            receipt = stage_reel(plan, caption, target)
            result = {"status": receipt["status"], "episode": args.episode,
                      "videos": {name: {"path": str(target / f"Reel_{name}.mp4"),
                                        "sha256": detail["sha256"]}
                                 for name, detail in receipt["videos"].items()}}
        print(json.dumps(result))
        return 0
    except (ReelBlocked, ThreadsBlocked, OSError, ValueError) as exc:
        print(json.dumps({"status": "REEL_BLOCKED_NO_PUBLICATION", "reason": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
