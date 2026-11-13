"""Original, deterministic AI Geopolitic instrumental bed (no external music).

This is a review-only prototype, not an approved Veni Sonora sonic master.
The five-note motif and synthetic waveforms are authored for this project;
no samples, libraries, platform tracks, text-to-speech or vocals are used.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 48_000
MOTIF_HZ = (146.83, 174.61, 220.00, 261.63, 196.00)  # D3–F3–A3–C4–G3
GENERATOR = "ai-geopolitic-original-five-note-ambient-v0.1"


def _envelope(t: float, start: float, length: float) -> float:
    elapsed = t - start
    if elapsed < 0 or elapsed >= length:
        return 0.0
    attack = min(1.0, elapsed / 0.25)
    release = min(1.0, (length - elapsed) / 0.6)
    return min(attack, release) ** 1.3


def write_original_bed(path: Path, *, duration: float = 30.0,
                       sample_rate: int = SAMPLE_RATE) -> dict:
    if not 0.25 <= duration <= 90 or not 8_000 <= sample_rate <= 48_000:
        raise ValueError("Original soundtrack duration or rate is out of bounds.")
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = round(duration * sample_rate)
    peak = 0.0
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        chunk = bytearray()
        for i in range(samples):
            t = i / sample_rate
            fade = min(1.0, t / 0.9, (duration - t) / 1.4)
            # The low sustained drone is designed to remain beneath speech
            # if a separately approved narration track is added later.
            drone = (0.050 * math.sin(2 * math.pi * 73.42 * t)
                     + 0.027 * math.sin(2 * math.pi * 110.0 * t))
            notes = 0.0
            for j, frequency in enumerate(MOTIF_HZ):
                for cycle in range(3):
                    start = cycle * 10.0 + 0.55 + j * 1.65
                    envelope = _envelope(t, start, 2.1)
                    if envelope:
                        phase = 2 * math.pi * frequency * (t - start)
                        notes += envelope * (
                            0.070 * math.sin(phase)
                            + 0.016 * math.sin(2 * phase)
                            + 0.008 * math.sin(3 * phase)
                        )
            left = fade * (drone + notes)
            right = fade * (drone * 0.97 + notes * 0.92)
            peak = max(peak, abs(left), abs(right))
            chunk.extend(struct.pack("<hh", round(left * 32767), round(right * 32767)))
            if len(chunk) >= 64 * 1024:
                wav.writeframesraw(chunk)
                chunk.clear()
        if chunk:
            wav.writeframesraw(chunk)
    return {
        "schema": "ai-geopolitic.original-audio-provenance.v1",
        "generator": GENERATOR,
        "five_note_motif_hz": list(MOTIF_HZ),
        "sample_rate": sample_rate,
        "duration_seconds": duration,
        "channels": 2,
        "peak_linear": round(peak, 6),
        "external_samples": False,
        "vocals": False,
        "production_status": "PILOT_REQUIRES_IAN_AUDIO_APPROVAL",
        "wav_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def write_provenance(path: Path, record: dict) -> None:
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
