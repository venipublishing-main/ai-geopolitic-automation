"""One current contextual-art slide through free cloud providers; dry run by default."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path

from .control_documents import Blocker, ControlDocumentError, parse_daily_metadata
from .daily_readiness import DailyBuildReadiness, DailyBuildReadinessResult, current_production_date
from .phase_c import AttemptLedger, compile_context_slide, execute_candidate
from .production_inputs import InputSourceError, RcloneDriveInput
from .providers.contracts import GenerationJob, Modality, OutputRequirements, TraceMetadata, UnsupportedJob
from .providers.cloud.ai_horde import AIHordeProvider
from .providers.cloud.cloudflare_workers_ai import CloudflareWorkersAIProvider
from .providers.cloud.common import validate_cloud_job
from .providers.cloud.models import CF_PROVIDER, HORDE_PROVIDER, EVIDENCE

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/phase-c1"
DEFAULT_PRIORITY = (CF_PROVIDER, HORDE_PROVIDER)


def cloud_job(provider, prompt, episode, slide_number, attempt=1, seed=None):
    digest = hashlib.sha256(prompt.encode()).hexdigest()[:16]
    job = GenerationJob(f"phase-c1-{episode}-{slide_number}-{provider.provider_id}-{digest}-{attempt}",
                        Modality.IMAGE, "contextual_art", prompt, OutputRequirements("png", 1024, 1024),
                        model_preference=provider.capabilities().default_model_id, seed=seed,
                        trace=TraceMetadata(episode, slide_number, attempt))
    job.validate()
    return job


def select_slide(readiness, slide_number=None):
    # Revalidate current readiness before inspecting even one manifest slide.
    if slide_number is not None:
        render, prompt = compile_context_slide(readiness, slide_number)
        if readiness.manifest["slides"][slide_number - 1]["preferred_visual_reasoning_family"] != "material_chain":
            raise ValueError("SUPPORTED_CURRENT_CONTEXT_ART_SLIDE_MISSING")
        return slide_number, render, prompt
    if (not isinstance(readiness, DailyBuildReadinessResult) or readiness.build != "READY" or
            readiness.state != "BUILD_READY" or readiness.blockers or
            readiness.production_date_sast != current_production_date().isoformat() or not readiness.manifest):
        raise ValueError("LIVE_BUILD_READY_REQUIRED")
    # The inherited bridge supports one Thabo material chain. No inferred labels or new layouts.
    for number in range(1, 21):
        try:
            render, prompt = compile_context_slide(readiness, number)
            family = readiness.manifest["slides"][number - 1]["preferred_visual_reasoning_family"]
            if family != "material_chain":
                continue
            return number, render, prompt
        except ValueError:
            continue
    raise ValueError("SUPPORTED_CURRENT_CONTEXT_ART_SLIDE_MISSING")


def terminal_failure_proven(status):
    # Local coordinator failure/timeout is not proof that remote inference stopped.
    return status.failure.code in {
        "HORDE_JOB_FAULTED", "AUTHENTICATION_REJECTED", "ENTITLEMENT_REJECTED",
        "BILLING_OR_PLAN_REQUIRED", "FREE_QUOTA_EXHAUSTED", "RATE_OR_QUOTA_LIMIT",
        "CLOUDFLARE_API_FAILED", "INVALID_IMAGE_BASE64", "IMAGE_DECODE_FAILED",
        "IMAGE_FORMAT_OR_DIMENSIONS_INVALID", "EMPTY_IMAGE_CONTENT",
    }


def benchmark(readiness, providers, *, priority=DEFAULT_PRIORITY, episode_hint=None,
              slide_number=None, execute=False, diagnosis=None):
    ids = tuple(p.provider_id for p in providers)
    if len(set(ids)) != len(ids) or len(set(priority)) != len(priority) or set(priority) != set(ids):
        raise ValueError("PRIORITY_MUST_NAME_EACH_REGISTERED_PROVIDER_ONCE")
    episode = readiness.manifest["episode_id"] if readiness.manifest else episode_hint
    report = {"mode": "EXECUTE" if execute else "DRY_RUN", "readiness": readiness.to_dict(),
              "created_at_sast_date": current_production_date().isoformat(),
              "episode_id": episode, "episode_source": "validated_manifest" if readiness.manifest else "human_metadata_only",
              "selected_slide": None, "requested_slide": slide_number, "expected_dimensions": [1024, 1024],
              "registered_providers": list(ids), "priority": list(priority),
              "providers": [], "blockers": [b.code for b in readiness.blockers], "results": [],
              "predicted_generation_count": 0, "generation_attempts_total": 0,
              "human_review": "HUMAN REVIEW REQUIRED", "drive_upload": None}
    compiled = False
    try:
        number, render, prompt = select_slide(readiness, slide_number)
        report["selected_slide"] = number
        compiled = True
    except ValueError as exc:
        report["blockers"].append("CURRENT_SLIDE_BRIDGE_UNAVAILABLE")
        report["bridge_blocker"] = str(exc)
    ordered = sorted(providers, key=lambda p: priority.index(p.provider_id))
    eligible = []
    for provider in ordered:
        health, caps, resources = provider.health(), provider.capabilities(), provider.resource_state()
        model = provider.models.get(provider.provider_id, caps.default_model_id, Modality.IMAGE)
        reasons = []
        # Eligibility can be observed while readiness blocks; a fixed probe job never goes to submit.
        job = cloud_job(provider, prompt if compiled else "Read-only eligibility probe.", episode, report["selected_slide"])
        try:
            validate_cloud_job(provider, job)
            if provider.provider_id == CF_PROVIDER and len(job.prompt) > 2048:
                reasons.append("CLOUDFLARE_PROMPT_OR_DIMENSIONS_UNSUPPORTED")
        except UnsupportedJob as exc:
            reasons.extend(exc.reasons)
        report["providers"].append({"provider": provider.provider_id, "health": asdict(health),
                                    "monetary_cost": caps.monetary_cost.value, "selected_model": caps.default_model_id,
                                    "licence": asdict(model) if model else None, "licence_evidence": EVIDENCE[provider.provider_id],
                                    "resources": asdict(resources), "observations": provider.observations(),
                                    "eligibility_blockers": reasons, "eligible": not reasons})
        if not reasons:
            eligible.append(provider)
    if not eligible:
        report["blockers"].append("NO_ELIGIBLE_FREE_CLOUD_PROVIDER")
    ledger = AttemptLedger(OUTPUT / "attempt-ledger.json", providers=DEFAULT_PRIORITY, maximum=2, single_provider=True)
    try:
        rows = ledger.read()
        report["generation_attempts_total"] = len(rows)
        budget_ok = not rows or (len(rows) == 1 and rows[0]["outcome"] == "technical_failure" and
                                bool(diagnosis and diagnosis.strip()) and eligible and rows[0]["provider"] == eligible[0].provider_id)
        if not budget_ok:
            report["blockers"].append("GENERATION_BUDGET_BLOCKED")
    except (ValueError, OSError):
        report["blockers"].append("ATTEMPT_LEDGER_INVALID")
    if not report["blockers"]:
        report["selected_provider"] = eligible[0].provider_id
        report["predicted_generation_count"] = 1
    if execute and not report["blockers"]:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        lock = OUTPUT / "benchmark.lock"
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            report["blockers"].append("BENCHMARK_ALREADY_LOCKED")
        else:
            try:
                provider = eligible[0]
                result = execute_candidate(provider, render, prompt, ledger, diagnosis=diagnosis,
                    job_factory=lambda p, text, attempt, seed: cloud_job(p, text, episode, number, attempt, seed),
                    models=provider.models, output_root=OUTPUT / episode / f"slide-{number}",
                    terminal_failure_proven=terminal_failure_proven)
                report["results"].append(result)
                if result["state"] != "SUCCEEDED" or result.get("composition_blocker"):
                    report["blockers"].append(result.get("failure_code") or "GENERATION_OR_COMPOSITION_FAILED")
            except Exception as exc:
                report["blockers"].append("BENCHMARK_" + type(exc).__name__.upper())
            finally:
                os.close(descriptor)
                lock.unlink()
                report["generation_attempts_total"] = len(ledger.read())
    report["state"] = "BLOCKED" if report["blockers"] else ("COMPLETED" if execute else "DRY_RUN_READY")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--priority", default=",".join(DEFAULT_PRIORITY))
    parser.add_argument("--slide", type=int)
    parser.add_argument("--diagnosis", help="Explicit diagnosis for one proven terminal technical failure retry.")
    args = parser.parse_args(argv)
    today, episode = current_production_date(), None
    try:
        documents = RcloneDriveInput.from_environment().read()
        readiness = DailyBuildReadiness().evaluate(documents)  # Actual SAST clock; no date override.
        try:
            episode = parse_daily_metadata(documents.slide_design, slide_design=True).episode_id
        except ControlDocumentError:
            pass  # Human hint never replaces validated readiness.
    except InputSourceError:
        readiness = DailyBuildReadinessResult(today.isoformat(), "BLOCKED", "BUILD_BLOCKED",
                    (Blocker("INPUT_SOURCE_UNAVAILABLE", "Drive inputs unavailable.", "source"),))
    providers = (CloudflareWorkersAIProvider(), AIHordeProvider())
    try:
        report = benchmark(readiness, providers, priority=tuple(args.priority.split(",")),
                           episode_hint=episode, slide_number=args.slide, execute=args.execute, diagnosis=args.diagnosis)
        OUTPUT.mkdir(parents=True, exist_ok=True)
        (OUTPUT / "benchmark-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["state"] in {"DRY_RUN_READY", "COMPLETED"} else 1
    except ValueError:
        print(json.dumps({"state": "BLOCKED", "blockers": ["INVALID_CLOUD_BENCHMARK_CONFIGURATION"]}))
        return 1
    finally:
        providers[0].close()


if __name__ == "__main__":
    raise SystemExit(main())
