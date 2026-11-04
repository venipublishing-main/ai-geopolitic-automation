"""Read-only active v3 readiness CLI with authenticated rclone Drive proof.

There is deliberately no render, regeneration, storage mutation or publish action.
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from datetime import date

from .control_documents import Blocker, ControlDocumentError, parse_daily_metadata
from .daily_readiness import DailyBuildReadinessResult, current_production_date
from .production_inputs import DailyDocuments, InputSourceError, ProductionInput
from .v3_drive_proof import RcloneV3DriveProof
from .v3_readiness import V3DailyBuildReadiness


def blocked(today: date, code: str, message: str) -> DailyBuildReadinessResult:
    return DailyBuildReadinessResult(today.isoformat(), "BLOCKED", "BUILD_BLOCKED",
                                     (Blocker(code, message, "drive"),), None)


def verify_authenticated(
    source: ProductionInput,
    proof: RcloneV3DriveProof,
    *,
    production_date: date | None = None,
) -> DailyBuildReadinessResult:
    """Read one pair of daily snapshots and verify authenticated remote assets."""
    today = production_date or current_production_date()
    try:
        docs: DailyDocuments = source.read()
    except (InputSourceError, OSError, UnicodeError):
        return blocked(today, "INPUT_SOURCE_UNAVAILABLE",
                       "Cannot read current Drive source documents using configured rclone.")
    try:
        design = parse_daily_metadata(docs.slide_design, slide_design=True)
        archive_name = design.archive_destination
    except ControlDocumentError:
        # The pure validator will report a specific metadata problem. Do not
        # invent or infer an archive location from incomplete source content.
        archive_name = ""

    readiness = V3DailyBuildReadiness(
        archive_folder_exists=lambda folder_id: proof.archive_folder_exists(folder_id, archive_name),
        portrait_asset_exists=proof.portrait_asset_exists,
    )
    return readiness.evaluate(docs, production_date=today)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit metadata-only JSON; no full editorial Manifest.")
    args = parser.parse_args(argv)
    today = current_production_date()

    try:
        proof = RcloneV3DriveProof(
            remote=os.environ.get("AI_GEOPOLITIC_DRIVE_REMOTE", "ai_geopolitic_drive"),
            executable=os.environ.get("AI_GEOPOLITIC_RCLONE", "rclone"),
        )
        # The same pinned-ID authenticated client reads both current native
        # Google Docs and verifies the independent archive / portrait objects.
        result = verify_authenticated(proof, proof, production_date=today)
    except InputSourceError:
        result = blocked(today, "INPUT_SOURCE_UNAVAILABLE",
                         "Drive proof cannot start; check local authorized rclone configuration.")

    # Strictly omit raw R&D, Manifest/editorial prose, OAuth secrets and rclone stderr.
    output = {
        "production_date_sast": result.production_date_sast,
        "build": result.build,
        "state": result.state,
        "episode_id": result.manifest.get("episode_id") if result.ready else None,
        "slide_count": len(result.manifest["slides"]) if result.ready else None,
        "blockers": [asdict(item) for item in result.blockers],
        "verification": "authenticated_read_only_rclone",
        "generation_performed": False,
        "publishing_performed": False,
    }
    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"V3 INPUT BUILD {result.build} | {result.state} | SAST {result.production_date_sast}")
        if result.ready:
            print(f"Verified {output['slide_count']} Manifest slides for {output['episode_id']}.")
        for item in result.blockers:
            print(f"- {item.code}: {item.message}")
    return 0 if result.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
