"""Controlled Ep103/12 benchmark. Default read-only worker preflight; no inference."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

from .daily_readiness import DailyBuildReadiness, DailyBuildReadinessResult, current_production_date
from .episode_manifest_v2 import load_canonical_characters, validate_manifest_v2
from .production_inputs import InputSourceError, RcloneDriveInput
from .providers.contracts import (GenerationJob, JobState, Modality, OutputRequirements,
                                 ResourceRequirements, TraceMetadata, capability_rejections, resource_rejections)
from .providers.local.base import LocalWorkerConfig
from .providers.local.comfyui import ComfyUIProvider
from .providers.local.image import ImageProfile, inspect_png, nvidia_resources
from .providers.local.wangp import WanGPProvider
from .providers.model_registry import ModelMetadata, ModelRegistry
from .providers.router import GenerationRouter, ZeroCostPolicy

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/phase-c/ep103-slide12"
LOCKED_ART = (
    "Sophisticated editorial engraving, etched newspaper illustration on warm off-white paper. "
    "Crisp dark ink, controlled dense cross-hatching, strong spatial hierarchy, one coherent scene. "
    "Material infrastructure and workers; leave negative space for deterministic overlay. "
    "TEXT-FREE: no typography, synthetic labels, headline, footer, slide numbers, fake charts or dashboard text. "
    "No panelist portrait or Thabo likeness, logos, decorative flags, collage/grid, cyberpunk neon, "
    "glowing AI imagery or glossy 3D advertising."
)


def compile_slide(readiness: DailyBuildReadinessResult):
    """Only the validated current Ep103 Slide 12; never compiles other slides."""
    today = current_production_date().isoformat()
    if (not isinstance(readiness, DailyBuildReadinessResult) or readiness.build != "READY" or
            readiness.state != "BUILD_READY" or readiness.blockers or readiness.production_date_sast != today):
        raise ValueError("LIVE_BUILD_READY_REQUIRED")
    manifest = readiness.manifest
    if validate_manifest_v2(manifest, load_canonical_characters()):
        raise ValueError("VALIDATED_MANIFEST_REQUIRED")
    if manifest["episode_id"] != "Ep103" or manifest["production_date_sast"] != today or manifest["source_rnd_date_sast"] != today:
        raise ValueError("CURRENT_EP103_REQUIRED")
    slide = manifest["slides"][11]
    if slide["slide_number"] != 12 or slide["panelists"] != ["thabo_mokoena"]:
        raise ValueError("SINGLE_THABO_SLIDE_12_REQUIRED")
    # The existing material_chain consumes five labelled stages. No invented labels.
    if len(slide["essential_labels"]) != 5:
        raise ValueError("COMPOSITION_BRIDGE_REQUIRES_FIVE_EXPLICIT_LABELS")
    render = {"slide_number": 12, "total_slides": 20, "speaker": "thabo_mokoena",
              "content_type": "material_handoff", "layout_family": "material_chain",
              "headline": slide["headline"], "deck": slide["subheadline"], "quote": slide["main_visual_phrase"],
              "facts": [idea["idea"] for idea in slide["takeaway_ideas"]], "takeaway": slide["core_argument"],
              "chain": [{"label": label, "note": ""} for label in slide["essential_labels"]]}
    fields = ("hero_visual", "core_argument", "visual_psychology_traits", "preferred_visual_reasoning_family",
              "anti_cliche_guardrail", "factual_guardrails")
    prompt = " ".join(f"{key}: {json.dumps(slide[key], ensure_ascii=False)}." for key in fields) + " " + LOCKED_ART
    return render, prompt


def generation_job(provider, prompt, attempt=1, seed=None):
    profile = provider.profile
    digest = hashlib.sha256(prompt.encode()).hexdigest()[:16]
    job = GenerationJob(f"phase-c-Ep103-12-{provider.provider_id}-{digest}-{attempt}", Modality.IMAGE,
                        "contextual_art", prompt, OutputRequirements("png", profile.width, profile.height),
                        model_preference=profile.model.model_id, seed=seed,
                        trace=TraceMetadata("Ep103", 12, attempt),
                        resources=ResourceRequirements(True, profile.model.min_vram_mb))
    job.validate()
    return job


def compose(render_spec, artifact, destination):
    """Stage solely in ignored assets; keep the existing renderer authoritative."""
    from .render_thabo_layout_family import render
    staging = ROOT / "assets/_phase_c_runtime"
    if not staging.resolve().is_relative_to((ROOT / "assets").resolve()) or staging.is_symlink():
        raise ValueError("Unsafe compositor staging root.")
    staging.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ep103-12-", dir=staging) as temporary:
        plate = Path(temporary) / "context-art.png"
        shutil.copyfile(artifact, plate)
        spec = {**render_spec, "context_art": {"source": "asset", "path": plate.relative_to(ROOT).as_posix(),
                "box": [96, 104, 940, 875], "opacity": 0.34, "tint": "ink_accent", "layer": "background", "paper_wash": False,
                "exclusions": [[96, 104, 631, 350], [675, 126, 940, 418], [96, 365, 555, 525],
                               [585, 430, 940, 600], [96, 610, 940, 875]]}}
        source = Path(temporary) / "render.json"
        source.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        render(source, destination)
    inspect_png(destination, 1080, 1080)


class AttemptLedger:
    """Durable conservative ceiling; ambiguous submission never authorizes retry."""
    def __init__(self, path):
        self.path = Path(path)

    def read(self):
        if not self.path.exists():
            return []
        rows = json.loads(self.path.read_text(encoding="utf-8"))
        if (not isinstance(rows, list) or len(rows) > 4 or
                any(not isinstance(row, dict) or row.get("provider") not in {"wangp", "comfyui"} or
                    row.get("outcome") not in {"reserved", "technical_failure", "success", "cancelled", "unresolved"} for row in rows)):
            raise ValueError("Invalid benchmark attempt ledger; fail closed.")
        for provider in ("wangp", "comfyui"):
            previous = [r for r in rows if r["provider"] == provider]
            if len(previous) > 2 or [r.get("attempt") for r in previous] != list(range(1, len(previous) + 1)):
                raise ValueError("Invalid benchmark per-provider attempt sequence.")
        return rows

    def save(self, rows):
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        os.replace(temporary, self.path)

    def reserve(self, provider, diagnosis=None):
        rows = self.read()
        previous = [row for row in rows if row["provider"] == provider]
        if provider not in {"wangp", "comfyui"} or len(rows) >= 4 or len(previous) >= 2:
            raise ValueError("GENERATION_CEILING_REACHED")
        if previous and (previous[-1]["outcome"] != "technical_failure" or not diagnosis or not diagnosis.strip()):
            raise ValueError("DIAGNOSED_TECHNICAL_FAILURE_REQUIRED_FOR_RETRY")
        rows.append({"provider": provider, "outcome": "reserved", "diagnosis": diagnosis, "attempt": len(previous) + 1})
        self.save(rows)
        return len(rows) - 1, len(previous) + 1

    def finish(self, index, outcome, **details):
        rows = self.read()
        rows[index].update(outcome=outcome, **details)
        self.save(rows)


def execute_candidate(provider, render, prompt, ledger, *, seed=None, diagnosis=None, timeout=1800):
    index, attempt = ledger.reserve(provider.provider_id, diagnosis)
    job = generation_job(provider, prompt, attempt, seed)
    router = GenerationRouter((provider,), models=ModelRegistry((provider.profile.model,)))
    record = {"provider": provider.provider_id, "attempt": attempt, "seed": seed, "job_id": job.job_id,
              "model_profile": asdict(provider.profile), "lifecycle": [], "human_review": "HUMAN REVIEW REQUIRED",
              "requested_dimensions": [job.output.width, job.output.height]}
    started = time.monotonic()
    try:
        record["resource_before"] = asdict(provider.resource_state())
        router.submit(job)
        record["worker_job_id"] = router.submission(job.job_id).provider_job_id
        observed_used = []
        while True:
            status = router.status(job.job_id)
            record["lifecycle"].append({"state": status.state.value, "elapsed_seconds": time.monotonic() - started})
            try:
                measured = provider.resource_state()
                if measured.total_vram_mb is not None and measured.free_vram_mb is not None:
                    observed_used.append(measured.total_vram_mb - measured.free_vram_mb)
            except (ValueError, OSError):
                pass  # Measurement unavailable; never substitute an estimate.
            if status.state in (JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED):
                break
            if time.monotonic() - started > timeout:
                # Cancellation is requested only when verified; unresolved jobs cannot retry.
                if provider.profile.cancellation_verified:
                    router.cancel(job.job_id)
                raise TimeoutError("Job remains unresolved after deadline.")
            time.sleep(1)
        if status.state is not JobState.SUCCEEDED:
            ledger.finish(index, "technical_failure" if status.state is JobState.FAILED else "cancelled", worker_job_id=record["worker_job_id"])
            record["state"] = status.state.value
            record["duration_seconds"] = time.monotonic() - started
            return record
        artifact = Path(router.result(job.job_id).artifacts[0].identifier)
        record["technical_qa"] = inspect_png(artifact, job.output.width, job.output.height)
    except Exception as exc:
        # Lost acknowledgement, malformed status and timeouts may hide a running job.
        # Only artifact QA after explicit success proves a safe technical retry.
        proven_finished = bool(record["lifecycle"] and record["lifecycle"][-1]["state"] == "SUCCEEDED")
        ledger.finish(index, "technical_failure" if proven_finished else "unresolved", error_type=type(exc).__name__)
        record.update(state="BLOCKED", error_type=type(exc).__name__)
        record["duration_seconds"] = time.monotonic() - started
        return record
    ledger.finish(index, "success", worker_job_id=record["worker_job_id"])
    directory = OUTPUT / provider.provider_id
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "context-art.png"
    shutil.copyfile(artifact, target)
    record.update(state="SUCCEEDED", artifact_path=str(target), duration_seconds=time.monotonic() - started,
                  observed_peak_vram_mb=max(observed_used) if observed_used else None,
                  vram_note="Sampled whole-device usage, not an instrumented process peak.")
    try:
        composite = directory / "slide-composite.png"
        compose(render, target, composite)
        record["composition_output"] = str(composite)
    except Exception as exc:
        record["composition_blocker"] = type(exc).__name__  # Never regenerate art for copy/layout failure.
    (directory / "generation-metadata.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def load_workers(path):
    """External reviewed configuration. No built-in model choices or permissions."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not set(data) <= {"wangp", "comfyui"}:
        raise ValueError("Only the two controlled local workers may be configured.")
    workers = []
    for name, value in data.items():
        if not isinstance(value, dict) or set(value) != {"profile", "worker", "artifact_root"}:
            raise ValueError("Unsupported worker configuration fields.")
        profile_data = dict(value["profile"])
        metadata = dict(profile_data.pop("model"))
        metadata["modality"] = Modality(metadata["modality"])
        metadata["known_restrictions"] = tuple(metadata.get("known_restrictions", ()))
        for key in ("evidence_urls", "required_model_files"):
            profile_data[key] = tuple(profile_data[key])
        profile = ImageProfile(ModelMetadata(**metadata), **profile_data)
        cls = WanGPProvider if name == "wangp" else ComfyUIProvider
        workers.append(cls(LocalWorkerConfig(**value["worker"]), profile=profile, artifact_root=value["artifact_root"]))
    return workers


def machine_preflight():
    gpu = asdict(nvidia_resources())
    try:
        smi = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=5)
        smi_report = {"exit_code": smi.returncode, "output": (smi.stdout + smi.stderr).strip()[:4096]}
    except (OSError, subprocess.SubprocessError):
        smi_report = {"exit_code": None, "output": "NVIDIA inspection unavailable."}
    windows = None
    if os.name == "nt":
        script = "$o=Get-CimInstance Win32_OperatingSystem; @{os=$o.Caption;version=$o.Version;ram_kib=$o.TotalVisibleMemorySize;display=@(Get-CimInstance Win32_VideoController|Select-Object Name,DriverVersion,AdapterRAM);disk=@(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3'|Select-Object DeviceID,Size,FreeSpace)}|ConvertTo-Json -Depth 4"
        try:
            result = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True, timeout=20, check=True)
            windows = json.loads(result.stdout)
            if not isinstance(windows, dict) or not windows.get("os"):
                windows = {"inspection": "UNAVAILABLE"}
        except (OSError, ValueError, subprocess.SubprocessError):
            windows = {"inspection": "UNAVAILABLE"}
    installations = None
    if os.name == "nt":
        script = "@{python=@(py -0p 2>&1);listeners=@(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue|Where-Object LocalPort -in 8188,7866,7860|Select-Object LocalAddress,LocalPort);workers=@(Get-CimInstance Win32_Process|Where-Object Name -match '^(python|comfy|wangp)'|Select-Object Name,ProcessId)}|ConvertTo-Json -Depth 3"
        try:
            result = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True, timeout=20, check=True)
            installations = json.loads(result.stdout)
        except (OSError, ValueError, subprocess.SubprocessError):
            installations = {"inspection": "UNAVAILABLE"}
    return {"windows": windows, "python_and_workers": installations, "nvidia": gpu, "nvidia_smi": smi_report,
            "suitable_gpu_verified": bool(gpu["gpu_identity"] and gpu["total_vram_mb"]),
            "installed_or_downloaded_this_run": []}


def benchmark(readiness, workers, hardware, *, execute=False, retry_provider=None, diagnosis=None):
    report = {"episode_id": "Ep103", "slide_number": 12, "mode": "EXECUTE" if execute else "DRY_RUN",
              "hardware": hardware, "readiness": readiness.to_dict(), "blockers": [], "providers": [], "results": [],
              "human_review": "HUMAN REVIEW REQUIRED", "comparison": "UNPROVEN", "drive_upload": None}
    report["created_at_sast_date"] = current_production_date().isoformat()
    report["worker_versions"] = {w.provider_id: w.profile.worker_revision for w in workers}
    report["model_storage"] = {w.provider_id: [{"path": p, "bytes": Path(p).stat().st_size if Path(p).is_file() else None}
                                               for p in w.profile.required_model_files] for w in workers}
    if not hardware["suitable_gpu_verified"]:
        report["blockers"].append("SUITABLE_GPU_UNVERIFIED")
    compiled = False
    try:
        render, prompt = compile_slide(readiness)
        compiled = True
    except ValueError as exc:
        report["blockers"].append(str(exc))
    eligible = []
    for worker in workers:
        available = worker.available()
        reasons = []
        if available and compiled:
            try:
                job = generation_job(worker, prompt)
                caps, resources = worker.capabilities(), worker.resource_state()
                reasons.extend(capability_rejections(job, caps) + resource_rejections(job, resources, caps))
                if not ZeroCostPolicy().allows(caps.monetary_cost):
                    reasons.append("ZERO_COST_UNPROVEN")
                if worker.profile.model.attribution_required:
                    reasons.append("MODEL_ATTRIBUTION_REQUIRED")
            except (ValueError, OSError):
                reasons.append("WORKER_ELIGIBILITY_UNAVAILABLE")
        report["providers"].append({"provider": worker.provider_id, "available": available, "profile": asdict(worker.profile),
                                     "eligibility_blockers": reasons,
                                     "transport": "official MCP v2" if worker.provider_id == "wangp" else "official HTTP jobs API"})
        if available and not reasons:
            eligible.append(worker)
        else:
            report["blockers"].append(worker.provider_id.upper() + "_RUNTIME_UNAVAILABLE")
        if reasons:
            report["blockers"].append(worker.provider_id.upper() + "_INELIGIBLE")
    if not workers:
        report["blockers"].append("REVIEWED_WORKER_MODEL_PROFILES_MISSING")
    input_hardware_clear = hardware["suitable_gpu_verified"] and compiled
    if execute and input_hardware_clear and eligible:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        lock = OUTPUT / "benchmark.lock"
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            ledger = AttemptLedger(OUTPUT / "attempt-ledger.json")
            seeded = all(w.profile.seed_supported for w in eligible)
            report["comparison"] = "NOT MODEL-CONTROLLED; exact underlying weight identity remains unproven"
            for worker in eligible:
                if retry_provider and worker.provider_id != retry_provider:
                    continue
                try:
                    candidate = execute_candidate(worker, render, prompt, ledger, seed=10312 if seeded else None,
                                                  diagnosis=diagnosis if retry_provider else None)
                except ValueError as exc:
                    candidate = {"provider": worker.provider_id, "state": "BLOCKED", "error_type": type(exc).__name__,
                                 "blocker": "ATTEMPT_LEDGER_OR_PRE_DISPATCH_GATE"}
                report["results"].append(candidate)
        finally:
            os.close(descriptor)
            lock.unlink()
    report["generation_attempts_total"] = len(AttemptLedger(OUTPUT / "attempt-ledger.json").read())
    composed = [r for r in report["results"] if r.get("composition_output")]
    if execute:
        report["state"] = "HUMAN_REVIEW_REQUIRED" if composed else "BLOCKED"
        if not composed:
            report["blockers"].append("REAL_GENERATION_COMPOSITION_UNPROVEN")
    else:
        report["state"] = "BLOCKED" if report["blockers"] else "DRY_RUN_READY"
    return report


def write_report(report):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "benchmark-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    text = f"# Phase C controlled benchmark\n\nState: {report['state']}\n\nReal attempt reservations: {report['generation_attempts_total']}\n\n"
    text += "Blockers: " + ", ".join(report["blockers"]) + "\n\n"
    text += "Live readiness blockers: " + ", ".join(b["code"] for b in report["readiness"]["blockers"]) + "\n\n"
    text += "No automatic visual winner. HUMAN REVIEW REQUIRED.\n\nFull hardware, profiles, lifecycle and artifacts: benchmark-report.json.\n"
    (OUTPUT / "benchmark-report.md").write_text(text, encoding="utf-8")
    paths = [r["composition_output"] for r in report["results"] if r.get("composition_output")]
    if len(paths) == 2:
        from PIL import Image
        sheet = Image.new("RGB", (2160, 1080), "white")
        for index, path in enumerate(paths):
            with Image.open(path) as image:
                sheet.paste(image.convert("RGB"), (1080 * index, 0))
        sheet.save(OUTPUT / "comparison-contact-sheet.png")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Explicitly permit the two controlled real submissions after all gates pass.")
    parser.add_argument("--profiles", type=Path, help="External reviewed localhost model/worker configuration.")
    parser.add_argument("--retry-provider", choices=("wangp", "comfyui"))
    parser.add_argument("--technical-diagnosis")
    args = parser.parse_args(argv)
    if (bool(args.retry_provider) != bool(args.technical_diagnosis)) or (args.retry_provider and not args.execute):
        parser.error("Retry requires --execute, --retry-provider and --technical-diagnosis together.")
    hardware = machine_preflight()
    try:
        readiness = DailyBuildReadiness().check(RcloneDriveInput.from_environment())
    except InputSourceError:
        from .control_documents import Blocker
        readiness = DailyBuildReadinessResult(current_production_date().isoformat(), "BLOCKED", "BUILD_BLOCKED",
                                              (Blocker("INPUT_SOURCE_UNAVAILABLE", "Live Drive ingestion failed.", "source"),))
    config_error = None
    try:
        workers = load_workers(args.profiles) if args.profiles else []
    except (OSError, ValueError, TypeError, KeyError) as exc:
        workers, config_error = [], type(exc).__name__
    report = benchmark(readiness, workers, hardware,
                       execute=args.execute, retry_provider=args.retry_provider, diagnosis=args.technical_diagnosis)
    if config_error:
        report["blockers"].append("REVIEWED_PROFILE_INVALID")
        report["profile_error_type"] = config_error
    write_report(report)
    print(json.dumps({"state": report["state"], "blockers": report["blockers"], "report": str(OUTPUT / "benchmark-report.json")}))
    return 1 if report["state"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
