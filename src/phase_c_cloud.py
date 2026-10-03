"""One current contextual-art slide through free cloud providers; dry run by default."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from dataclasses import asdict
from pathlib import Path

from .control_documents import Blocker, ControlDocumentError, parse_daily_metadata
from .daily_readiness import DailyBuildReadiness, DailyBuildReadinessResult, current_production_date
from .phase_c import (AttemptLedger, compile_context_slide, execute_candidate,
                      THABO_MATERIAL_CHAIN, KAI_NETWORK_MESH)
from .production_inputs import InputSourceError, RcloneDriveInput
from .providers.contracts import (GenerationJob, Modality, OutputRequirements, TraceMetadata, UnsupportedJob,
                                 UseRequirements, UseContext, UseCase)
from .providers.licence_policy import permission_audit
from .providers.cloud.ai_horde import AIHordeProvider, ALBEDO_SETTINGS
from .providers.cloud.cloudflare_workers_ai import CloudflareWorkersAIProvider
from .providers.cloud.common import validate_cloud_job
from .providers.cloud.models import CF_PROVIDER, HORDE_PROVIDER, ALBEDO_MODEL_ID, model_evidence

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/phase-c1"
DEFAULT_PRIORITY = (CF_PROVIDER, HORDE_PROVIDER)
ALBEDO_PACKAGE = "Ep104/slide-5/albedo-sdxl"


def is_albedo(provider):
    return provider.provider_id == HORDE_PROVIDER and getattr(provider, "settings", None) == ALBEDO_SETTINGS


def albedo_prompt(slide):
    positive = (
        "A physical data-centre hosting campus shown as one coherent technical architectural cutaway. "
        "Remote network users connect through fibre entering the site, visible server and computing "
        "infrastructure, electrical transformers and substation, industrial cooling equipment and "
        "cooling pipes, foundations and land/site footprint. Serious black-ink newspaper editorial "
        "engraving on warm off-white paper, precise cross-hatching, restrained composition, useful "
        "negative space. No textual communication is required from this image. "
        + slide["hero_visual"] + " " + " ".join(slide["factual_guardrails"]))
    negative = (
        "text, letters, words, typography, caption, label, sign, signage, logo, brand mark, watermark, "
        "signature, artist signature, copyright mark, cloud icon, fluffy cloud, cartoon cloud, "
        "literal cloud metaphor, speech bubble, UI, dashboard, infographic text, poster, collage, "
        "contact sheet, neon, cyberpunk, portrait, panelist, human figure")
    if "cloud" in positive.lower() or "###" in positive or slide["main_visual_phrase"] in positive:
        raise ValueError("SDXL_POSITIVE_PROMPT_GUARDRAIL_UNMET")
    # Actual hordelib SDXL worker splits this delimiter into separate CLIP conditioning.
    return positive + "###" + negative


def cloud_job(provider, prompt, episode, slide_number, attempt=1, seed=None):
    digest = hashlib.sha256(prompt.encode()).hexdigest()[:16]
    job = GenerationJob(f"phase-c1-{episode}-{slide_number}-{provider.provider_id}-{digest}-{attempt}",
                        Modality.IMAGE, "contextual_art", prompt, OutputRequirements("png", 1024, 1024),
                        model_preference=provider.capabilities().default_model_id, seed=seed,
                        trace=TraceMetadata(episode, slide_number, attempt),
                        use=UseRequirements(UseContext.INTERNAL_BENCHMARK,
                            UseCase.NON_PERSONAL_INFRASTRUCTURE, True) if is_albedo(provider) else UseRequirements())
    job.validate()
    return job


def select_slide(readiness, slide_number=None):
    # Revalidate current readiness before inspecting even one manifest slide.
    if slide_number is not None:
        # Only this explicit compatibility profile may map Kai's descriptive family.
        # compile_context_slide revalidates full readiness and the live manifest.
        manifest = readiness.manifest if isinstance(readiness, DailyBuildReadinessResult) else None
        slides = manifest.get("slides") if isinstance(manifest, dict) else None
        kai_target = (slide_number == 5 and isinstance(slides, list) and len(slides) == 20 and
                      isinstance(slides[4], dict) and slides[4].get("panelists") == ["kai_patel"])
        profile = KAI_NETWORK_MESH if kai_target else THABO_MATERIAL_CHAIN
        render, prompt = compile_context_slide(readiness, slide_number, profile=profile)
        if profile == THABO_MATERIAL_CHAIN and readiness.manifest["slides"][slide_number - 1]["preferred_visual_reasoning_family"] != "material_chain":
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
    try:
        render, prompt = compile_context_slide(readiness, 5, profile=KAI_NETWORK_MESH)
        return 5, render, prompt
    except ValueError:
        raise ValueError("SUPPORTED_CURRENT_CONTEXT_ART_SLIDE_MISSING") from None


class HordeLifecycleObserver:
    """Pass-through benchmark observation: same requests, no provider behaviour change.

    Never retain headers, payloads, image/base64, or arbitrary response fields.
    Timings are polling observations, not instrumented worker execution times.
    """
    def __init__(self, transport, progress_path):
        self.transport, self.progress_path = transport, Path(progress_path)
        self.started, self.snapshots = time.monotonic(), []
        self.write_unavailable = False

    def json(self, method, path, payload=None, *, headers=None):
        result = self.transport.json(method, path, payload, headers=headers)
        if (path == "/v2/generate/async" or "/v2/generate/check/" in path or
                "/v2/generate/status/" in path) and isinstance(result, dict):
            row = {"method": method, "endpoint": path, "elapsed_seconds": time.monotonic() - self.started}
            for key in ("id", "done", "faulted", "finished", "processing", "waiting", "queue_position", "wait_time"):
                value = result.get(key)
                if type(value) in (str, bool, int, float):
                    row[key] = value[:256] if isinstance(value, str) else value
            if isinstance(result.get("generations"), list):
                row["generations"] = [{key: value[:256] if isinstance(value, str) else value
                    for key, value in generation.items() if key in {"seed", "model", "worker_id", "worker_name", "id", "state", "censored"}
                    and type(value) in (str, bool, int, float)} for generation in result["generations"] if isinstance(generation, dict)]
            self.snapshots.append(row)
            try:
                self.progress_path.parent.mkdir(parents=True, exist_ok=True)
                self.progress_path.write_text(json.dumps(self.summary(), indent=2), encoding="utf-8")
            except OSError:
                self.write_unavailable = True  # Observation must not change ACK/status semantics.
        return result

    def summary(self):
        ack = next((r for r in self.snapshots if r["method"] == "POST" and r.get("id")), None)
        running = next((r for r in self.snapshots if r.get("processing", 0) > 0), None)
        completed = next((r for r in self.snapshots if r.get("done") is True), None)
        generations = next((r["generations"] for r in reversed(self.snapshots) if r.get("generations")), [])
        return {"observations": self.snapshots, "horde_job_id": ack.get("id") if ack else None,
                "returned_generations": generations,
                "queue_duration_seconds": running["elapsed_seconds"] - ack["elapsed_seconds"] if running and ack else None,
                "generation_duration_seconds": completed["elapsed_seconds"] - running["elapsed_seconds"] if completed and running else None,
                "timing_basis": "First observed processing and completion; polling bounds, not worker instrumentation.",
                "progress_write_unavailable": self.write_unavailable, "retries": 0}


def terminal_failure_proven(status):
    # Local coordinator failure/timeout is not proof that remote inference stopped.
    return status.failure.code in {
        "HORDE_JOB_FAULTED", "AUTHENTICATION_REJECTED", "ENTITLEMENT_REJECTED",
        "BILLING_OR_PLAN_REQUIRED", "FREE_QUOTA_EXHAUSTED", "RATE_OR_QUOTA_LIMIT",
        "CLOUDFLARE_API_FAILED", "INVALID_IMAGE_BASE64", "IMAGE_DECODE_FAILED",
        "IMAGE_FORMAT_OR_DIMENSIONS_INVALID", "EMPTY_IMAGE_CONTENT",
    }


def benchmark(readiness, providers, *, priority=DEFAULT_PRIORITY, episode_hint=None,
              slide_number=None, execute=False, diagnosis=None, defer_composition=False):
    ids = tuple(p.provider_id for p in providers)
    if len(set(ids)) != len(ids) or len(set(priority)) != len(priority) or set(priority) != set(ids):
        raise ValueError("PRIORITY_MUST_NAME_EACH_REGISTERED_PROVIDER_ONCE")
    albedo = any(is_albedo(p) for p in providers)
    if albedo and (ids != (HORDE_PROVIDER,) or priority != (HORDE_PROVIDER,)):
        raise ValueError("ALBEDO_REQUIRES_EXCLUSIVE_SINGLE_PROVIDER_BENCHMARK")
    workspace = OUTPUT / ALBEDO_PACKAGE if albedo else OUTPUT
    if albedo:
        defer_composition = True  # Internal benchmark always requires visual review first.
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
        report.update(selected_bridge_profile=KAI_NETWORK_MESH if render["speaker"] == "kai_patel" else THABO_MATERIAL_CHAIN,
                      selected_speaker=render["speaker"], selected_layout=render["layout_family"])
        if albedo:
            if (episode != "Ep104" or number != 5 or render["speaker"] != "kai_patel" or
                    readiness.production_date_sast != "2026-10-03"):
                raise ValueError("AUTHORIZED_ALBEDO_BENCHMARK_TARGET_REQUIRED")
            prompt = albedo_prompt(readiness.manifest["slides"][4])
            report.update(execution_context=UseContext.INTERNAL_BENCHMARK.value,
                          benchmark_package=str(workspace), sampling_plan=asdict(ALBEDO_SETTINGS),
                          submitted_prompt=prompt, publication_allowed=False)
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
                                    "licence": asdict(model) if model else None,
                                    "licence_evidence": model_evidence(provider.provider_id, caps.default_model_id),
                                    "licence_audit": permission_audit(model, job),
                                    "resources": asdict(resources), "observations": provider.observations(),
                                    "eligibility_blockers": reasons, "eligible": not reasons})
        if not reasons:
            eligible.append(provider)
    if not eligible:
        report["blockers"].append("NO_ELIGIBLE_FREE_CLOUD_PROVIDER")
    ledger = AttemptLedger(workspace / "attempt-ledger.json", providers=ids if albedo else DEFAULT_PRIORITY,
                           maximum=1 if albedo else 2, single_provider=True)
    try:
        rows = ledger.read()
        report["generation_attempts_total"] = len(rows)
        budget_ok = not rows or (not albedo and len(rows) == 1 and rows[0]["outcome"] == "technical_failure" and
                                bool(diagnosis and diagnosis.strip()) and eligible and rows[0]["provider"] == eligible[0].provider_id)
        if not budget_ok:
            report["blockers"].append("GENERATION_BUDGET_BLOCKED")
    except (ValueError, OSError):
        report["blockers"].append("ATTEMPT_LEDGER_INVALID")
    if not report["blockers"]:
        report["selected_provider"] = eligible[0].provider_id
        report["predicted_generation_count"] = 1
        audit = next(p["licence_audit"] for p in report["providers"] if p["provider"] == eligible[0].provider_id)
        if audit is not None:
            report.update(licence_audit=audit, publication_handoff=audit["publication_handoff"])
    if execute and not report["blockers"]:
        workspace.mkdir(parents=True, exist_ok=True)
        lock = workspace / "benchmark.lock"
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            report["blockers"].append("BENCHMARK_ALREADY_LOCKED")
        else:
            try:
                provider = eligible[0]
                package = workspace if albedo else OUTPUT / episode / f"slide-{number}"
                observer = None
                if provider.provider_id == HORDE_PROVIDER:
                    observer = HordeLifecycleObserver(provider.http, package / provider.provider_id / "lifecycle-progress.json")
                    provider.http = observer
                try:
                    result = execute_candidate(provider, render, prompt, ledger, diagnosis=diagnosis,
                        job_factory=lambda p, text, attempt, seed: cloud_job(p, text, episode, number, attempt, seed),
                        models=provider.models, output_root=package,
                        terminal_failure_proven=terminal_failure_proven, defer_composition=defer_composition)
                finally:
                    if observer is not None:
                        provider.http = observer.transport
                if observer is not None:
                    result["licence_evidence"] = model_evidence(provider.provider_id, provider.capabilities().default_model_id)
                    result["sampling_plan"] = asdict(provider.settings)
                    result["provider_lifecycle"] = observer.summary()
                    result["provider_lifecycle"]["retries"] = result["attempt"] - 1
                    generations = result["provider_lifecycle"]["returned_generations"]
                    result["requested_seed"] = provider.settings.seed if is_albedo(provider) else result["seed"]
                    result["seed"] = generations[0].get("seed") if len(generations) == 1 else None
                    if result.get("technical_qa"):
                        result["returned_dimensions"] = [result["technical_qa"]["width"], result["technical_qa"]["height"]]
                    metadata = package / provider.provider_id / "generation-metadata.json"
                    metadata.parent.mkdir(parents=True, exist_ok=True)
                    metadata.write_text(json.dumps(result, indent=2), encoding="utf-8")
                report["results"].append(result)
                if result.get("licence_audit"):
                    report["licence_audit"] = result["licence_audit"]
                    report["publication_handoff"] = result["publication_handoff"]
                if result["state"] != "SUCCEEDED" or result.get("composition_blocker"):
                    report["blockers"].append(result.get("failure_code") or "GENERATION_OR_COMPOSITION_FAILED")
            except Exception as exc:
                report["blockers"].append("BENCHMARK_" + type(exc).__name__.upper())
            finally:
                os.close(descriptor)
                lock.unlink()
                report["generation_attempts_total"] = len(ledger.read())
    report["state"] = "BLOCKED" if report["blockers"] else (
        "ARTIFACT_REVIEW_REQUIRED" if execute and defer_composition else "COMPLETED" if execute else "DRY_RUN_READY")
    return report


def write_benchmark_report(report, workspace):
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "benchmark-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    audit = report.get("licence_audit") or next((p.get("licence_audit") for p in report["providers"]
                                                if p.get("licence_audit")), None)
    text = f"# Internal contextual-art benchmark\n\nState: {report['state']}\n\n"
    text += f"Episode: {report['episode_id']}; slide: {report['selected_slide']}. No production publication.\n\n"
    if audit:
        text += (f"Model: {audit['model']}; creator: {audit['creator']}; permission: {audit['permission_state']}.\n\n"
                 f"Required credit: {audit['attribution_text']}\n\n"
                 f"Evidence: {audit['permission_source']} and {audit['licence_source']}.\n\n"
                 f"Publication attribution required: {audit['publication_attribution_required']}. "
                 "Public attribution surface unconfigured; future publishing handoff BLOCKED.\n\n"
                 f"Use: {audit['use']}; obligations recorded: {audit['obligations_recorded']}.\n\n"
                 f"Restrictions: {', '.join(audit['known_restrictions'])}.\n\n"
                 "HUMAN_REVIEW_REQUIRED: declared infrastructure scope does not prove content compliance.\n\n")
    text += f"Blockers: {report['blockers']}; attempts: {report['generation_attempts_total']}.\n"
    (workspace / "benchmark-report.md").write_text(text, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--defer-composition", action="store_true", help="Save the one artifact for visual inspection before composition; never dispatch another job.")
    parser.add_argument("--priority", default=",".join(DEFAULT_PRIORITY))
    parser.add_argument("--slide", type=int)
    parser.add_argument("--horde-profile", choices=("flux", "albedo-sdxl"), default="flux")
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
    albedo = args.horde_profile == "albedo-sdxl"
    providers = ((AIHordeProvider(settings=ALBEDO_SETTINGS),) if albedo else
                 (CloudflareWorkersAIProvider(), AIHordeProvider()))
    try:
        priority = (HORDE_PROVIDER,) if albedo and args.priority == ",".join(DEFAULT_PRIORITY) else tuple(args.priority.split(","))
        report = benchmark(readiness, providers, priority=priority,
                           episode_hint=episode, slide_number=args.slide, execute=args.execute, diagnosis=args.diagnosis,
                           defer_composition=args.defer_composition)
        write_benchmark_report(report, OUTPUT / ALBEDO_PACKAGE if albedo else OUTPUT)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["state"] in {"DRY_RUN_READY", "COMPLETED", "ARTIFACT_REVIEW_REQUIRED"} else 1
    except ValueError:
        print(json.dumps({"state": "BLOCKED", "blockers": ["INVALID_CLOUD_BENCHMARK_CONFIGURATION"]}))
        return 1
    finally:
        for provider in providers:
            if hasattr(provider, "close"):
                provider.close()


if __name__ == "__main__":
    raise SystemExit(main())
