"""Exactly three historical Ep104 hero jobs, sequential review gates, no retry.

Preflight is offline. Execute-next submits only the next reserved slide, then
waits for terminal technical QA. Agent visual review is a separate explicit step.
No current daily readiness, production publication or runtime references.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
import uuid
from urllib.request import Request, urlopen

from PIL import Image

from .premium_scene_compiler import ROOT, compile_scene
from .premium_sdxl_prompt import compile_sdxl_prompt, prompt_record
from .premium_hero_qa import inspect_hero
from .premium_slide_renderer import render_preview
from .scene_contract import digest
from .providers.contracts import (GenerationJob, JobState, Modality, OutputRequirements, TraceMetadata,
                                 UseCase, UseContext, UseRequirements)
from .providers.cloud.ai_horde import AIHordeProvider, ALBEDO_SETTINGS
from .providers.cloud.common import validate_cloud_job
from .providers.cloud.models import (ALBEDO_MODEL_ID, ALBEDO_CHECKPOINT_SHA256, ALBEDO_PERMISSION_SOURCE,
                                    ALBEDO_VERSION_SOURCE, SDXL_LICENCE_SOURCE)
from .providers.licence_policy import permission_audit
from .phase_c_cloud import HordeLifecycleObserver

PACKAGE = ROOT / "output/phase-d2/Ep104"
MANIFEST = ROOT / "tests/fixtures/premium_scenes/ep104_manifest.json"
MANIFEST_SHA256 = "955c5aad9d28e044f7454032cd811f39bc7eb5fa55798d87e5384b6a6f2e405d"
BASE_LICENCE_SHA256 = "19b6998b569b53ac1fc2158a8a3202c8699a9a4605b47075715d9c96be7fb6d0"
SELECTION = ((14, "nora", "slide-14-nora"), (12, "diane_sterling", "slide-12-diane"), (16, "amari_ndlovu", "slide-16-amari"))
CONTINUABLE = {"RENDERED", "HERO_VISUAL_GUARDRAIL_FAILED", "SCENE_CONTRACT_VISUALLY_INCOMPATIBLE"}
FLAGS = ("text_or_pseudotext_detected", "watermark_or_signature_detected", "logo_detected", "panelist_identity_detected",
         "literal_fluffy_cloud_or_icon_detected", "neon_cyberpunk_detected", "poster_or_contact_sheet_detected")
AUTHORITY = {"CURRENT_READINESS":"NOT_ASSERTED", "SOURCE":"ACCEPTED_EP104_HISTORICAL_SNAPSHOT",
             "production_date_sast":"2026-10-03", "execution_context":"INTERNAL_BENCHMARK", "publication_allowed":False}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(path.name + ".pending")
    with pending.open("w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(pending, path)


def accepted_manifest():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if digest(manifest) != MANIFEST_SHA256 or manifest["episode_id"] != "Ep104" or manifest["production_date_sast"] != "2026-10-03":
        raise ValueError("ACCEPTED_EP104_MANIFEST_MISMATCH")
    return manifest


def preflight(root=PACKAGE):
    manifest = accepted_manifest()
    contracts = [compile_scene(manifest, n) for n, _, _ in SELECTION]
    if any(c.panelist != expected for c, (_, expected, _) in zip(contracts, SELECTION)):
        raise ValueError("D2_SELECTION_AUTHORITY_MISMATCH")
    signatures = {(c.portrait.side, c.portrait.vertical_position, c.hero_region, c.shape_language,
                   c.headline.treatment, c.takeaway_arrangement, tuple(o.zone for o in c.semantic_objects)) for c in contracts}
    if len(signatures) != 3 or len({c.panelist_grammar for c in contracts}) != 3 or len({c.reasoning_family for c in contracts}) != 3:
        raise ValueError("D2_CONTRACTS_NOT_MATERIALLY_DISTINCT")
    report = {**AUTHORITY, "state":"ZERO_GENERATION_PREFLIGHT_PASSED", "manifest_sha256":MANIFEST_SHA256,
              "planned_total":3, "real_submissions":0, "runtime_reference_dependency":False, "slides":[]}
    for contract, (_, _, directory) in zip(contracts, SELECTION):
        prompt = prompt_record(contract)
        job_for(contract).validate()
        for name, value in (("contract.json",contract.to_dict()),("prompt.json",prompt)):
            path = Path(root)/directory/name
            if path.exists() and digest(json.loads(path.read_text(encoding="utf-8"))) != digest(value):
                raise ValueError("IMMUTABLE_D2_PREFLIGHT_EVIDENCE_CHANGED")
        write_json(Path(root)/directory/"contract.json", contract.to_dict())
        write_json(Path(root)/directory/"prompt.json", prompt)
        report["slides"].append({"slide_number":contract.slide_number,"panelist":contract.panelist,
            "panelist_grammar":contract.panelist_grammar,"reasoning_family":contract.reasoning_family,
            "contract_sha256":contract.sha256,"prompt_sha256":prompt["prompt_sha256"],"expected_generation_count":1})
    write_json(Path(root)/"preflight.json", report)
    return contracts, report


def job_for(contract):
    prompt = compile_sdxl_prompt(contract)
    return GenerationJob(f"phase-d2-Ep104-{contract.slide_number}-{digest(prompt)[:16]}", Modality.IMAGE,
        "contextual_art", prompt, OutputRequirements("png",1024,1024), model_preference=ALBEDO_MODEL_ID,
        trace=TraceMetadata("Ep104",contract.slide_number,1,(("contract_sha256",contract.sha256),)),
        use=UseRequirements(UseContext.INTERNAL_BENCHMARK,UseCase.NON_PERSONAL_INFRASTRUCTURE,True))


def validate_permission_evidence(reference, author, version, licence):
    try:
        valid = (reference["name"] == ALBEDO_MODEL_ID and
            any(d["sha256sum"].upper() == ALBEDO_CHECKPOINT_SHA256 for d in reference["config"]["download"]) and
            reference["licensing"]["commercial_use"] == "allowed_with_conditions" and
            "OpenRAIL++-M" in reference["licensing"]["license_ids"] and
            author["id"] == 140737 and author["creator"]["username"] == "albedobond" and
            author["allowNoCredit"] is False and {"Image","Rent"} <= set(author["allowCommercialUse"]) and
            author["allowDerivatives"] is True and author["allowDifferentLicense"] is False and
            version["id"] == 1041855 and version["modelId"] == 140737 and version["baseModel"] == "SDXL 1.0" and
            any(f["hashes"].get("SHA256","").upper() == ALBEDO_CHECKPOINT_SHA256 for f in version["files"]) and
            hashlib.sha256(licence).hexdigest() == BASE_LICENCE_SHA256)
    except (KeyError, TypeError, AttributeError):
        valid = False
    if not valid:
        raise ValueError("CURRENT_ALBEDO_PERMISSION_OR_IDENTITY_UNPROVEN")


def fetch_current_permissions(root=PACKAGE):
    urls = ("https://models.aihorde.net/api/model_references/v2/image_generation/model/AlbedoBase%20XL%203.1",
            ALBEDO_PERMISSION_SOURCE, ALBEDO_VERSION_SOURCE, SDXL_LICENCE_SOURCE.replace("/blob/", "/raw/"))
    raw = []
    for url in urls:
        with urlopen(Request(url,headers={"User-Agent":"ai-geopolitic/phase-d2"}),timeout=30) as response:
            value = response.read(8_000_001)
        if len(value) > 8_000_000:
            raise ValueError("PERMISSION_EVIDENCE_TOO_LARGE")
        raw.append(value)
    validate_permission_evidence(*(json.loads(v) for v in raw[:3]),raw[3])
    report = {"checked_at_utc":datetime.now(timezone.utc).isoformat(), "model":ALBEDO_MODEL_ID,
        "checkpoint_sha256":ALBEDO_CHECKPOINT_SHA256,"creator":"albedobond","state":"REVALIDATED",
        "sources":[{"url":url,"sha256":hashlib.sha256(value).hexdigest()} for url,value in zip(urls,raw)]}
    write_json(Path(root)/"current-permission-evidence.json", report)
    return report


class AttemptLedger:
    """Atomic reservations survive a crash before ACK. No reset/retry API.

    Every attempted submit consumes its slot even if no remote ID is returned.
    A lock protects concurrent reservation, and previous review must be terminal.
    """
    def __init__(self, root):
        self.path = Path(root)/"attempt-ledger.json"
        self.lock = Path(root)/"attempt-ledger.lock"

    def read(self):
        value = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else []
        if (not isinstance(value,list) or len(value)>3 or
                any(not isinstance(r,dict) or r.get("slide_number") != SELECTION[i][0] or
                    r.get("attempt") != 1 or r.get("provider") != "ai_horde" for i,r in enumerate(value))):
            raise ValueError("D2_LEDGER_INVALID")
        return value

    def _change(self, action):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        fd = os.open(self.lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
        try:
            rows = self.read()
            result = action(rows)
            write_json(self.path,rows)
            return result
        finally:
            os.close(fd)
            self.lock.unlink()

    def next_number(self):
        rows = self.read()
        if len(rows)==3:
            raise ValueError("D2_ATTEMPT_CEILING_REACHED")
        if rows and rows[-1]["state"] not in CONTINUABLE:
            raise ValueError("PREVIOUS_SLIDE_REVIEW_OR_ENGINEERING_STOP")
        return SELECTION[len(rows)][0]

    def reserve(self, contract, job):
        def reserve(rows):
            if len(rows)>=3 or (rows and rows[-1]["state"] not in CONTINUABLE):
                raise ValueError("D2_ATTEMPT_OR_SEQUENCE_BLOCKED")
            if contract.slide_number != SELECTION[len(rows)][0] or job != job_for(contract):
                raise ValueError("D2_TARGET_OR_JOB_MISMATCH")
            rows.append({"slide_number":contract.slide_number,"attempt":1,"provider":"ai_horde",
                "job_id":job.job_id,"contract_sha256":contract.sha256,"prompt_sha256":digest(job.prompt),
                "reserved_at_utc":datetime.now(timezone.utc).isoformat(),"state":"SUBMISSION_RESERVED"})
        self._change(reserve)

    def update(self, number, **fields):
        def update(rows):
            if not rows or rows[-1]["slide_number"] != number or set(fields)&{"slide_number","attempt","provider","job_id","contract_sha256","prompt_sha256"}:
                raise ValueError("D2_LEDGER_MUTATION_REJECTED")
            rows[-1].update(fields)
        self._change(update)


def execute_next(*, root=PACKAGE, provider=None, permission_reader=fetch_current_permissions, sleep=time.sleep, timeout=1800):
    contracts, _ = preflight(root)  # all three must compile before ANY submit
    ledger = AttemptLedger(root)
    number = ledger.next_number()
    contract = next(c for c in contracts if c.slide_number==number)
    directory = next(d for n,_,d in SELECTION if n==number)
    package = Path(root)/directory
    permissions = permission_reader(root)
    if permissions.get("state") != "REVALIDATED":
        raise ValueError("CURRENT_PERMISSION_REQUIRED")
    provider = provider or AIHordeProvider(settings=ALBEDO_SETTINGS,
        artifact_root=ROOT/"output/phase-c1/phase-d2-staging")
    if provider.provider_id != "ai_horde" or provider.settings != ALBEDO_SETTINGS:
        raise ValueError("EXACT_ALBEDO_PROVIDER_REQUIRED")
    job = job_for(contract)
    validate_cloud_job(provider,job)
    model = provider.models.get("ai_horde",ALBEDO_MODEL_ID,Modality.IMAGE)
    audit = permission_audit(model,job)
    if not audit or audit["publication_handoff"]["state"] != "BLOCKED":
        raise ValueError("CONDITIONAL_ATTRIBUTION_POLICY_REQUIRED")
    observer = HordeLifecycleObserver(provider.http,package/"lifecycle-progress.json")
    provider.http = observer
    ledger.reserve(contract,job)  # fsync before the only POST
    receipt = {**AUTHORITY,"slide_number":number,"panelist":contract.panelist,"provider":"ai_horde",
        "model":ALBEDO_MODEL_ID,"attempt":1,"job_id":job.job_id,"contract_sha256":contract.sha256,
        "prompt_sha256":digest(job.prompt),"licence_audit":audit,"current_permission_evidence":permissions,
        "sampling_plan":asdict(ALBEDO_SETTINGS),"requested_seed":ALBEDO_SETTINGS.seed,"reference_assets":[],
        "state":"SUBMISSION_RESERVED"}
    metadata = package/"generated-metadata.json"
    write_json(metadata,receipt)
    try:
        try:
            identifier = provider.submit(job)
            uuid.UUID(identifier)
        except Exception:
            receipt["state"] = "AMBIGUOUS_SUBMISSION_STOP"
            ledger.update(number,state=receipt["state"])
            write_json(metadata,receipt)
            raise ValueError("D2_AMBIGUOUS_SUBMISSION_STOP") from None
        receipt.update(provider_job_id=identifier,state="SUBMITTED")
        ledger.update(number,state="SUBMITTED",provider_job_id=identifier)
        write_json(metadata,receipt)
        start = time.monotonic()
        while True:
            try:
                status = provider.status(identifier)
            except Exception:
                receipt["state"] = "AMBIGUOUS_STATUS_STOP"
                raise ValueError("D2_AMBIGUOUS_STATUS_STOP") from None
            if status.state is JobState.SUCCEEDED:
                break
            if status.state in {JobState.FAILED,JobState.CANCELLED}:
                receipt["state"] = "TERMINAL_TECHNICAL_FAILURE_STOP"
                raise ValueError("D2_TERMINAL_TECHNICAL_FAILURE_STOP")
            if time.monotonic()-start>timeout:
                receipt["state"] = "AMBIGUOUS_TIMEOUT_STOP"
                raise ValueError("D2_AMBIGUOUS_TIMEOUT_STOP")
            sleep(10)
        result = provider.result(identifier)
        if result.provider_id != "ai_horde" or result.job_id != identifier or len(result.artifacts)!=1:
            raise ValueError("GENERATION_RESULT_AUTHORITY_MISMATCH")
        shutil.copyfile(result.artifacts[0].identifier,package/"context-art.png")
        receipt.update(state="GENERATED_AWAITING_VISUAL_REVIEW",raster_sha256=sha(package/"context-art.png"),
            provider_lifecycle=observer.summary(),real_submissions=1,provider_result=asdict(result))
        generations = receipt["provider_lifecycle"]["returned_generations"]
        if len(generations)!=1 or generations[0].get("model")!=ALBEDO_MODEL_ID or generations[0].get("seed") is None:
            raise ValueError("PROVIDER_RESULT_IDENTITY_OR_SEED_MISSING")
        receipt["seed"] = generations[0]["seed"]
        technical = inspect_hero(contract,package/"context-art.png",job.prompt,
            source_kind="d2_generated_benchmark",generation_receipt=receipt)
        receipt["technical_qa"] = technical.to_dict()
        if not technical.mechanical_passed:
            raise ValueError("D2_TECHNICAL_QA_STOP")
        ledger.update(number,state=receipt["state"],raster_sha256=receipt["raster_sha256"],seed=receipt["seed"])
        return receipt
    except Exception as exc:
        if receipt["state"] not in {"AMBIGUOUS_SUBMISSION_STOP","AMBIGUOUS_STATUS_STOP","AMBIGUOUS_TIMEOUT_STOP","TERMINAL_TECHNICAL_FAILURE_STOP"}:
            receipt.update(state="ENGINEERING_OR_RESULT_FAILURE_STOP",failure_code=type(exc).__name__)
        ledger.update(number,state=receipt["state"])
        raise
    finally:
        receipt["provider_lifecycle"] = observer.summary()
        write_json(metadata,receipt)
        provider.http = observer.transport


def render_qa(contract, manifest, image_path, report):
    with Image.open(image_path) as image:
        image.verify()
    with Image.open(image_path) as image:
        image.load()
        if image.format!="PNG" or image.size!=(1080,1080) or hashlib.sha256(image.convert("RGB").tobytes()).hexdigest()!=report["pixel_sha256"]:
            raise ValueError("RENDER_RASTER_QA_FAILED")
    expected = [o.label for o in contract.semantic_objects] + [contract.headline.text,contract.subheadline.text,
        contract.phrase.text,*[t["idea"] for t in manifest["slides"][contract.slide_number-1]["takeaway_ideas"]],*[f.text for f in contract.furniture]]
    if ([r["text"] for r in report["text_draw_trace"]]!=expected or report["accent"]!=contract.accent or
            report["canonical_portrait_sha256"]!=sha(ROOT/contract.portrait.path) or
            report["runtime_reference_dependency"] is not False or report["legacy_renderer_fallback"] is not False):
        raise ValueError("RENDER_COPY_OR_AUTHORITY_QA_FAILED")
    return {"state":"MECHANICAL_RENDER_QA_PASSED","format":"PNG","dimensions":[1080,1080],
        "output_sha256":sha(image_path),"copy_verification":"ACTUAL_DRAW_TRACE_NOT_OCR",
        "exact_copy":True,"takeaway_count":3,"canonical_portrait_sha256":report["canonical_portrait_sha256"],
        "accent":contract.accent,"safe_copy":True,"protected_face_collision":False,
        "runtime_reference_dependency":False,"legacy_renderer_fallback":False}


def record_visual_review(number, evidence, *, root=PACKAGE):
    ledger = AttemptLedger(root)
    rows = ledger.read()
    if not rows or rows[-1]["slide_number"]!=number or rows[-1]["state"]!="GENERATED_AWAITING_VISUAL_REVIEW":
        raise ValueError("D2_AWAITING_VISUAL_REVIEW_REQUIRED")
    contracts,_ = preflight(root)
    contract = next(c for c in contracts if c.slide_number==number)
    package=Path(root)/next(d for n,_,d in SELECTION if n==number)
    receipt=json.loads((package/"generated-metadata.json").read_text(encoding="utf-8"))
    if (evidence.get("artifact_sha256")!=sha(package/"context-art.png") or
            evidence.get("contract_sha256")!=contract.sha256 or evidence.get("performed") is not True or
            any(type(evidence.get(k)) is not bool for k in (*FLAGS,"approved_for_composition","annotation_anchors_plausible","composition_safe")) or
            evidence.get("scene_contract_status") not in {"SCENE_CONTRACT_VISUALLY_COMPATIBLE","SCENE_CONTRACT_PARTIALLY_COMPATIBLE","SCENE_CONTRACT_VISUALLY_INCOMPATIBLE"}):
        raise ValueError("VISUAL_REVIEW_EVIDENCE_INVALID")
    review={**AUTHORITY,"slide_number":number,"agent_visual_observations":evidence,
            "human_visual_review":"REQUIRED_AUTHORITATIVE","computer_vision_claim":False}
    try:
        # Rejected heroes still need authority checks before their visual failure
        # can unlock the next job. A receipt/raster mismatch is engineering, not
        # permission to continue merely because a visual flag was also set.
        technical=inspect_hero(contract,package/"context-art.png",compile_sdxl_prompt(contract),
            source_kind="d2_generated_benchmark",generation_receipt=receipt)
        if (not technical.mechanical_passed or receipt.get("provider_job_id")!=rows[-1].get("provider_job_id") or
                receipt.get("job_id")!=rows[-1].get("job_id")):
            raise ValueError("D2_REVIEW_RECEIPT_AUTHORITY_MISMATCH")
        review["technical_qa"]=technical.to_dict()
        if any(evidence[k] for k in FLAGS):
            review["state"]="HERO_VISUAL_GUARDRAIL_FAILED"
        elif (not evidence["approved_for_composition"] or not evidence["annotation_anchors_plausible"] or
              not evidence["composition_safe"] or evidence["scene_contract_status"]=="SCENE_CONTRACT_VISUALLY_INCOMPATIBLE"):
            review["state"]="SCENE_CONTRACT_VISUALLY_INCOMPATIBLE"
        else:
            qa=inspect_hero(contract,package/"context-art.png",compile_sdxl_prompt(contract),
                source_kind="d2_generated_benchmark",content_evidence=evidence,generation_receipt=receipt)
            image,report=render_preview(contract,accepted_manifest(),package/"context-art.png",qa,
                content_evidence=evidence,generation_receipt=receipt)
            image.save(package/"rendered-slide.png","PNG")
            review.update(state="RENDERED",hero_qa=qa.to_dict(),render_metadata=report,
                render_qa=render_qa(contract,accepted_manifest(),package/"rendered-slide.png",report))
        ledger.update(number,state=review["state"])
    except Exception:
        review["state"]="RENDER_ARCHITECTURE_FAILURE_STOP"
        ledger.update(number,state=review["state"])
        raise
    finally:
        write_json(package/"review.json",review)
    return review


def benchmark_report(root=PACKAGE):
    rows=AttemptLedger(root).read()
    report={**AUTHORITY,"real_submitted_generation_count":len(rows),"maximum":3,"slides":[],
            "state":"BENCHMARK_INCOMPLETE_OR_BLOCKED","runtime_reference_dependency":False}
    for n,p,d in SELECTION:
        package=Path(root)/d
        item={"slide_number":n,"panelist":p,"files":{}}
        for name in ("contract.json","prompt.json","context-art.png","generated-metadata.json","rendered-slide.png","reference-final.png","reference-metadata.json","review.json"):
            path=package/name
            if path.exists(): item["files"][name]={"path":str(path.resolve()),"sha256":sha(path)}
        for name,key in (("generated-metadata.json","generation"),("review.json","review")):
            if (package/name).exists(): item[key]=json.loads((package/name).read_text(encoding="utf-8"))
        if (package/"contract.json").exists():
            c=json.loads((package/"contract.json").read_text(encoding="utf-8"))
            item["scene_contract_summary"]={k:c[k] for k in ("panelist_grammar","reasoning_family","hero_region",
                "quiet_zones","portrait","semantic_objects","phrase","takeaway_arrangement","accent")}
        report["slides"].append(item)
    if len(rows)==3 and all(r["state"] in CONTINUABLE for r in rows):
        report["state"]="PHASE D.2 THREE-SLIDE GENERALISATION BENCHMARK READY FOR HUMAN REVIEW"
    elif rows and rows[-1]["state"].endswith("STOP"):
        report["state"]="BENCHMARK_STOPPED_BEFORE_COMPLETION"
        report["stop_reason"]=rows[-1]["state"]
    write_json(Path(root)/"benchmark-report.json",report)
    text="# Phase D.2 — three-slide historical benchmark\n\n"+report["state"]+"\n\nCURRENT_READINESS = NOT_ASSERTED\nSOURCE = ACCEPTED_EP104_HISTORICAL_SNAPSHOT\n\nPublic publication: BLOCKED. Human review is authoritative.\n\n"
    for item in report["slides"]:
        g=item.get("generation",{});r=item.get("review",{})
        c=item.get("scene_contract_summary",{});v=r.get("agent_visual_observations",{});life=g.get("provider_lifecycle",{})
        text+=f"\n## Slide {item['slide_number']} — {item['panelist']}\n\nState: {r.get('state',g.get('state','NOT_SUBMITTED'))}. "
        text+=f"Hero QA: {r.get('state') if r.get('state')!='RENDERED' else 'PASSED'}. Compatibility: {v.get('scene_contract_status','NOT_REVIEWED')}.\n\n"
        text+=f"Grammar / reasoning: {c.get('panelist_grammar')} / {c.get('reasoning_family')}. Accent: {c.get('accent')}.\n\n"
        text+=f"AI Horde / {g.get('model')}; job `{g.get('provider_job_id')}`; returned seed `{g.get('seed')}`. "
        text+=f"Observed queue {life.get('queue_duration_seconds')} s; processing {life.get('generation_duration_seconds')} s. Polling bounds, not worker instrumentation.\n\n"
        for observation in v.get("observations",[]): text+=f"- {observation}\n"
        text+="\n"
        for name,label in (("context-art.png","Generated hero"),("rendered-slide.png","Generalized render"),("reference-final.png","Manual current final — comparison only")):
            file=item["files"].get(name)
            if file: text+=f"### {label}\n\n![{label}]({Path(file['path']).as_posix()})\n\n"
            elif name=="rendered-slide.png": text+="Generalized render withheld / unavailable; rejected hero remains visible above.\n\n"
    text+=f"\nReserved/submitted attempt count: {len(rows)} / 3. No retries or fallback.\n\nRequired credit retained in every receipt: Context illustration generated with AlbedoBase XL 3.1 by albedobond.\n"
    (Path(root)/"benchmark-report.md").write_text(text,encoding="utf-8")
    return report


def verify_evidence(root=PACKAGE):
    """Validate stored receipt bindings; this does not authenticate remote pixels.

    Provider-result model/seed observations must agree with the acknowledged job.
    Human references are hashed only for packaging, never passed to the renderer.
    """
    rows=AttemptLedger(root).read()
    contracts,_=preflight(root)
    ids=[]
    observed_submissions=0
    for row in rows:
        number=row["slide_number"]
        contract=next(c for c in contracts if c.slide_number==number)
        path=Path(root)/next(d for n,_,d in SELECTION if n==number)
        receipt=json.loads((path/"generated-metadata.json").read_text(encoding="utf-8"))
        if (receipt["job_id"]!=row["job_id"] or receipt["contract_sha256"]!=contract.sha256 or
                receipt["prompt_sha256"]!=digest(compile_sdxl_prompt(contract)) or receipt["attempt"]!=1 or
                receipt["publication_allowed"] is not False or receipt["reference_assets"]!=[] or
                receipt["CURRENT_READINESS"]!="NOT_ASSERTED" or receipt["SOURCE"]!=AUTHORITY["SOURCE"]):
            raise ValueError("D2_EVIDENCE_AUTHORITY_MISMATCH")
        if receipt.get("provider_job_id"):
            uuid.UUID(receipt["provider_job_id"])
            if receipt["provider_job_id"]!=row.get("provider_job_id"):
                raise ValueError("D2_REMOTE_JOB_ID_MISMATCH")
            ids.append(receipt["provider_job_id"])
            lifecycle=receipt["provider_lifecycle"]
            submits=[o for o in lifecycle["observations"] if o["method"]=="POST"]
            if (len(submits)!=1 or submits[0]["endpoint"]!="/v2/generate/async" or
                    submits[0].get("id")!=receipt["provider_job_id"] or
                    lifecycle["horde_job_id"]!=receipt["provider_job_id"] or lifecycle["retries"]!=0):
                raise ValueError("D2_OBSERVED_SUBMISSION_COUNT_OR_ACK_MISMATCH")
            observed_submissions+=len(submits)
        if receipt["state"]=="GENERATED_AWAITING_VISUAL_REVIEW":
            generations=receipt["provider_lifecycle"]["returned_generations"]
            if (len(generations)!=1 or generations[0]["model"]!=ALBEDO_MODEL_ID or
                    generations[0]["seed"]!=receipt["seed"] or receipt["raster_sha256"]!=sha(path/"context-art.png")):
                raise ValueError("D2_GENERATION_EVIDENCE_MISMATCH")
            review=json.loads((path/"review.json").read_text(encoding="utf-8")) if (path/"review.json").exists() else None
            if review and review["state"]=="RENDERED":
                render_qa(contract,accepted_manifest(),path/"rendered-slide.png",review["render_metadata"])
                if review["render_qa"]["output_sha256"]!=sha(path/"rendered-slide.png"):
                    raise ValueError("D2_RENDER_HASH_MISMATCH")
    if len(ids)!=len(set(ids)):
        raise ValueError("D2_DUPLICATE_REMOTE_JOB_ID")
    report=benchmark_report(root)
    for item in report["slides"]:
        for name,file in item["files"].items():
            if sha(file["path"])!=file["sha256"]:
                raise ValueError("D2_PACKAGE_HASH_MISMATCH")
    return {"state":"D2_EVIDENCE_BINDINGS_VERIFIED","attempt_count":len(rows),"acknowledged_job_ids":ids,
            "observed_submit_requests":observed_submissions,"hidden_fourth_request":False,
            "request_count_basis":"DURABLE_LEDGER_AND_RECORDED_PROVIDER_HTTP_OBSERVATIONS",
            "publication_allowed":False}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument("--execute-next",action="store_true")
    mode.add_argument("--record-review",type=Path)
    mode.add_argument("--report",action="store_true")
    parser.add_argument("--review-slide",type=int,choices=(14,12,16))
    args=parser.parse_args(argv)
    try:
        if args.execute_next:
            result=execute_next()
        elif args.record_review:
            if args.review_slide is None: parser.error("Review requires --review-slide.")
            result=record_visual_review(args.review_slide,json.loads(args.record_review.read_text(encoding="utf-8")))
        elif args.report:
            result=benchmark_report()
        else:
            _,result=preflight()
        print(json.dumps(result,indent=2,ensure_ascii=True))
        return 0
    except Exception as exc:
        benchmark_report()
        print(json.dumps({**AUTHORITY,"state":"STOPPED","code":type(exc).__name__,
                          "reason":str(exc) if isinstance(exc,ValueError) else "Operation failed; no retry authorized."}))
        return 1


if __name__=="__main__":
    raise SystemExit(main())
