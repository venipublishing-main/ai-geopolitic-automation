"""D.2 coordinator, real-adapter contract semantics with offline synthetic art."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import socket
import uuid

from PIL import Image,ImageDraw
import pytest

from src import phase_d2_benchmark as d2
from src import premium_compositor,editorial_fusion,fidelity_finish
from src.providers.cloud.ai_horde import ALBEDO_SETTINGS,horde_status
from src.providers.cloud.models import cloud_registry,ALBEDO_MODEL_ID
from src.providers.contracts import (GenerationResult,OutputArtifact,Modality,ProviderCapabilities,MonetaryCost,
    ResourceState,HealthReport,HealthState,WorkerLocation,ActivityState)
from src.premium_sdxl_prompt import compile_sdxl_prompt
from src.premium_hero_qa import inspect_hero
from src.premium_slide_renderer import render_preview


@pytest.fixture(autouse=True)
def no_network_or_legacy(monkeypatch):
    def forbidden(*a,**k): pytest.fail("Offline D.2 test attempted network or a legacy compositor")
    monkeypatch.setattr(socket.socket,"connect",forbidden)
    monkeypatch.setattr(premium_compositor,"compose_premium",forbidden)
    monkeypatch.setattr(editorial_fusion,"compose_fusion",forbidden)
    # C.4 entrypoint differs from C.3; prohibit the actual public composition call.
    monkeypatch.setattr(fidelity_finish,"finish_proof",forbidden)
    from src import render_identity_slide,render_kai_layout_family
    monkeypatch.setattr(render_identity_slide,"render",forbidden)
    monkeypatch.setattr(render_kai_layout_family,"render",forbidden)


class FakeHTTP:
    def __init__(self,provider): self.provider=provider;self.posts=0;self.checks=0
    def json(self,method,path,payload=None,headers=None):
        if method=="POST":
            self.posts+=1;self.checks=0
            if self.provider.mode=="submit_ambiguous": raise RuntimeError("ACK lost")
            return {"id":str(uuid.UUID(int=self.posts))}
        if "/check/" in path:
            if self.provider.mode=="status_ambiguous": raise RuntimeError("status unavailable")
            self.checks+=1
            fault=self.provider.mode=="fault"
            return dict(done=self.checks>=3 or fault,faulted=fault,finished=1 if self.checks>=3 and not fault else 0,
                processing=1 if self.checks==2 and not fault else 0,waiting=1 if self.checks==1 and not fault else 0)
        if "/status/" in path:
            return dict(done=True,faulted=False,finished=1,processing=0,waiting=0,
                generations=[dict(model=ALBEDO_MODEL_ID,seed=str(100+self.posts),state="ok",censored=False,id="generation-id")])
        raise AssertionError(path)


class FakeHorde:
    provider_id="ai_horde"
    settings=ALBEDO_SETTINGS
    def __init__(self,tmp_path,mode="ok"):
        self.mode=mode;self.root=tmp_path;self.http=FakeHTTP(self);self.transport=self.http
        self.models=cloud_registry();self.submitted=[]
    def available(self): return True
    def health(self): return HealthReport(HealthState.HEALTHY)
    def resource_state(self): return ResourceState(online=True,activity=ActivityState.IDLE,available_model_ids=(ALBEDO_MODEL_ID,))
    def capabilities(self): return ProviderCapabilities(modalities=(Modality.IMAGE,),output_formats=("png",),
        image_generation=True,max_width=3072,max_height=3072,model_ids=(ALBEDO_MODEL_ID,),default_model_id=ALBEDO_MODEL_ID,
        deterministic_seed=False,location=WorkerLocation.REMOTE,monetary_cost=MonetaryCost.ZERO_COST)
    def submit(self,job):
        self.submitted.append(job)
        return self.http.json("POST","/v2/generate/async",{"models":[job.model_preference]})["id"]
    def status(self,identifier): return horde_status(self.http.json("GET","/v2/generate/check/"+identifier),identifier)
    def result(self,identifier):
        self.http.json("GET","/v2/generate/status/"+identifier)
        image=Image.new("RGB",(1024,1024),(245,241,231))
        ImageDraw.Draw(image).rectangle((180,100,820,840),fill=(85,85,85))
        path=self.root/(identifier+".png");image.save(path)
        return GenerationResult(identifier,"ai_horde",Modality.IMAGE,(OutputArtifact(str(path),"png",1024,1024),))


def permissions(root): return {"state":"REVALIDATED","test_fixture":True}


def execute(root,provider):
    return d2.execute_next(root=root,provider=provider,permission_reader=permissions,sleep=lambda _:None)


def evidence(root,number,**overrides):
    receipt=json.loads((root/next(d for n,_,d in d2.SELECTION if n==number)/"generated-metadata.json").read_text())
    return {"artifact_sha256":receipt["raster_sha256"],"contract_sha256":receipt["contract_sha256"],"performed":True,
        **{k:False for k in d2.FLAGS},"approved_for_composition":True,"annotation_anchors_plausible":True,
        "composition_safe":True,"scene_contract_status":"SCENE_CONTRACT_PARTIALLY_COMPATIBLE",**overrides}


def test_all_three_preflight_before_no_inference(tmp_path):
    contracts,report=d2.preflight(tmp_path)
    assert [c.slide_number for c in contracts]==[14,12,16]
    assert [c.panelist for c in contracts]==["nora","diane_sterling","amari_ndlovu"]
    assert len({c.panelist_grammar for c in contracts})==3
    assert len({c.reasoning_family for c in contracts})==3
    assert report["real_submissions"]==0 and report["planned_total"]==3
    assert report["CURRENT_READINESS"]=="NOT_ASSERTED"
    for c in contracts:
        assert len(c.slide["panelists"])==1 and c.panelist!="kai_patel"
        assert [o.label for o in c.semantic_objects]==c.slide["essential_labels"]
        job=d2.job_for(c)
        assert not job.reference_assets and job.seed is None and job.use.context.value=="INTERNAL_BENCHMARK"
        assert job.model_preference==ALBEDO_MODEL_ID and job.trace.attempt==1
        prompt=compile_sdxl_prompt(c)
        assert prompt.count("###")==1 and "watermark" in prompt.split("###")[1]
        assert "REMOTE USERS" not in prompt and "Slide05" not in prompt
        for obj in c.semantic_objects: assert obj.label in prompt


def test_scene_error_before_any_provider_job(tmp_path,monkeypatch):
    provider=FakeHorde(tmp_path)
    original=d2.compile_scene
    def fails(manifest,number):
        if number==16: raise ValueError("unsupported contract")
        return original(manifest,number)
    monkeypatch.setattr(d2,"compile_scene",fails)
    with pytest.raises(ValueError): execute(tmp_path,provider)
    assert not provider.submitted and not d2.AttemptLedger(tmp_path).read()


def test_three_sequential_jobs_no_fourth_or_retry(tmp_path):
    provider=FakeHorde(tmp_path)
    for number,_,directory in d2.SELECTION:
        receipt=execute(tmp_path,provider)
        assert receipt["slide_number"]==number and receipt["technical_qa"]["mechanical_passed"]
        assert receipt["licence_audit"]["publication_attribution_required"] is True
        assert receipt["licence_audit"]["publication_handoff"]["state"]=="BLOCKED"
        with pytest.raises(ValueError,match="PREVIOUS|CEILING"): execute(tmp_path,provider)
        review=d2.record_visual_review(number,evidence(tmp_path,number),root=tmp_path)
        assert review["state"]=="RENDERED" and review["render_qa"]["exact_copy"] is True
        assert review["render_qa"]["takeaway_count"]==3
        assert (tmp_path/directory/"rendered-slide.png").exists()
    assert [j.trace.slide_number for j in provider.submitted]==[14,12,16]
    assert provider.transport.posts==3
    with pytest.raises(ValueError,match="CEILING"): execute(tmp_path,provider)
    verified=d2.verify_evidence(tmp_path)
    assert verified["attempt_count"]==3 and verified["publication_allowed"] is False
    report=d2.benchmark_report(tmp_path)
    assert "READY FOR HUMAN REVIEW" in report["state"] and "ACCEPTED" not in report["state"]


@pytest.mark.parametrize("flag",d2.FLAGS)
def test_content_failure_withheld_no_retry_can_continue(tmp_path,flag):
    provider=FakeHorde(tmp_path)
    execute(tmp_path,provider)
    review=d2.record_visual_review(14,evidence(tmp_path,14,**{flag:True,"approved_for_composition":False}),root=tmp_path)
    assert review["state"]=="HERO_VISUAL_GUARDRAIL_FAILED"
    assert not (tmp_path/"slide-14-nora/rendered-slide.png").exists()
    assert (tmp_path/"slide-14-nora/context-art.png").exists()
    assert execute(tmp_path,provider)["slide_number"]==12
    assert provider.transport.posts==2 and all(j.trace.attempt==1 for j in provider.submitted)


@pytest.mark.parametrize("mode",["submit_ambiguous","status_ambiguous","fault"])
def test_provider_uncertainty_or_terminal_failure_stops_everything(tmp_path,mode):
    provider=FakeHorde(tmp_path,mode)
    with pytest.raises(ValueError): execute(tmp_path,provider)
    assert provider.transport.posts==1


def test_extra_recorded_submit_cannot_hide_in_evidence(tmp_path):
    provider=FakeHorde(tmp_path);execute(tmp_path,provider)
    path=tmp_path/"slide-14-nora/generated-metadata.json"
    receipt=json.loads(path.read_text())
    receipt["provider_lifecycle"]["observations"].append(dict(receipt["provider_lifecycle"]["observations"][0]))
    d2.write_json(path,receipt)
    with pytest.raises(ValueError,match="OBSERVED_SUBMISSION"):
        d2.verify_evidence(tmp_path)


def test_ambiguous_status_retains_count_without_claiming_completion(tmp_path):
    provider=FakeHorde(tmp_path,"status_ambiguous")
    with pytest.raises(ValueError,match="AMBIGUOUS_STATUS"):
        execute(tmp_path,provider)
    verified=d2.verify_evidence(tmp_path)
    assert verified["observed_submit_requests"]==1 and verified["attempt_count"]==1
    report=d2.benchmark_report(tmp_path)
    assert report["state"]=="BENCHMARK_STOPPED_BEFORE_COMPLETION"
    assert report["stop_reason"]=="AMBIGUOUS_STATUS_STOP"
    assert "READY FOR HUMAN REVIEW" not in report["state"]
    with pytest.raises(ValueError,match="PREVIOUS"): execute(tmp_path,provider)
    assert provider.transport.posts==1


def test_reservation_survives_restart_without_ack(tmp_path):
    contracts,_=d2.preflight(tmp_path)
    ledger=d2.AttemptLedger(tmp_path)
    ledger.reserve(contracts[0],d2.job_for(contracts[0]))
    with pytest.raises(ValueError,match="PREVIOUS"): d2.AttemptLedger(tmp_path).next_number()
    with pytest.raises(ValueError,match="BLOCKED"): ledger.reserve(contracts[0],d2.job_for(contracts[0]))
    assert len(ledger.read())==1


@pytest.mark.parametrize("kind",["contract","portrait","copy","renderer"])
def test_engineering_failure_blocks_next_generation(tmp_path,monkeypatch,kind):
    provider=FakeHorde(tmp_path)
    execute(tmp_path,provider)
    def bad(*a,**k): raise ValueError(kind+" failure")
    monkeypatch.setattr(d2,"render_preview",bad)
    with pytest.raises(ValueError): d2.record_visual_review(14,evidence(tmp_path,14),root=tmp_path)
    assert d2.AttemptLedger(tmp_path).read()[0]["state"]=="RENDER_ARCHITECTURE_FAILURE_STOP"
    with pytest.raises(ValueError,match="PREVIOUS"): execute(tmp_path,provider)
    assert provider.transport.posts==1


@pytest.mark.parametrize("field,value",[("artifact_sha256","wrong"),("contract_sha256","wrong"),("performed",False),
    ("composition_safe",None),("scene_contract_status","AUTO_CV_VERIFIED")])
def test_review_authority_rejected(tmp_path,field,value):
    provider=FakeHorde(tmp_path);execute(tmp_path,provider)
    with pytest.raises(ValueError,match="EVIDENCE_INVALID"):
        d2.record_visual_review(14,evidence(tmp_path,14,**{field:value}),root=tmp_path)
    assert d2.AttemptLedger(tmp_path).read()[0]["state"]=="GENERATED_AWAITING_VISUAL_REVIEW"


def test_semantic_incompatibility_withheld_and_no_cv_claim(tmp_path):
    provider=FakeHorde(tmp_path);execute(tmp_path,provider)
    review=d2.record_visual_review(14,evidence(tmp_path,14,scene_contract_status="SCENE_CONTRACT_VISUALLY_INCOMPATIBLE",
        approved_for_composition=False,annotation_anchors_plausible=False),root=tmp_path)
    assert review["state"]=="SCENE_CONTRACT_VISUALLY_INCOMPATIBLE"
    assert review["computer_vision_claim"] is False
    assert not (tmp_path/"slide-14-nora/rendered-slide.png").exists()


def test_receipt_cannot_bypass_human_or_visual_gate(tmp_path):
    provider=FakeHorde(tmp_path);receipt=execute(tmp_path,provider)
    contract=d2.preflight(tmp_path)[0][0]
    path=tmp_path/"slide-14-nora/context-art.png"
    bad=deepcopy(receipt);bad["raster_sha256"]="wrong"
    qa=inspect_hero(contract,path,compile_sdxl_prompt(contract),source_kind="d2_generated_benchmark",generation_receipt=bad)
    assert "D2_GENERATION_RECEIPT_INVALID" in qa.blockers
    qa=inspect_hero(contract,path,compile_sdxl_prompt(contract),source_kind="d2_generated_benchmark",generation_receipt=receipt)
    with pytest.raises(ValueError,match="VISUAL_REVIEW_REQUIRED"):
        render_preview(contract,d2.accepted_manifest(),path,qa,generation_receipt=receipt)


def test_evidence_tamper_detected_and_reference_independent(tmp_path):
    provider=FakeHorde(tmp_path);execute(tmp_path,provider)
    d2.record_visual_review(14,evidence(tmp_path,14),root=tmp_path)
    assert d2.verify_evidence(tmp_path)["attempt_count"]==1
    # There are deliberately no reference files anywhere in this runtime test.
    metadata=tmp_path/"slide-14-nora/generated-metadata.json"
    receipt=json.loads(metadata.read_text());receipt["seed"]="tampered"
    d2.write_json(metadata,receipt)
    with pytest.raises(ValueError,match="GENERATION_EVIDENCE_MISMATCH"): d2.verify_evidence(tmp_path)


@pytest.mark.parametrize("mutation",["hash","permission","creator","licence","version"])
def test_current_permission_revalidation_fail_closed(mutation,monkeypatch):
    base=Path(__file__).parent/"fixtures/cloud"
    reference=json.loads((base/"horde_albedo_v2.json").read_text())
    author=json.loads((base/"albedo_author_permissions.json").read_text())
    version=deepcopy(author["modelVersions"][0])
    licence=b"test reviewed licence"
    # These offline fixtures exercise identity/permission conditions independently
    # of network availability; raw licence hash is pinned separately in production.
    import hashlib
    monkeypatch.setattr(d2,"BASE_LICENCE_SHA256",hashlib.sha256(licence).hexdigest())
    d2.validate_permission_evidence(reference,author,version,licence)
    if mutation=="hash": reference["config"]["download"][0]["sha256sum"]="wrong"
    if mutation=="permission": author["allowCommercialUse"]=[]
    if mutation=="creator": author["creator"]["username"]="other"
    if mutation=="licence": reference["licensing"]["commercial_use"]="prohibited"
    if mutation=="version": version["id"]=999
    with pytest.raises(ValueError,match="UNPROVEN"):
        d2.validate_permission_evidence(reference,author,version,licence)


def test_no_model_switch_and_permission_failure_before_post(tmp_path):
    provider=FakeHorde(tmp_path)
    provider.settings=None
    with pytest.raises(ValueError,match="EXACT_ALBEDO"): execute(tmp_path,provider)
    assert not provider.submitted
    provider.settings=ALBEDO_SETTINGS
    with pytest.raises(ValueError,match="CURRENT_PERMISSION"):
        d2.execute_next(root=tmp_path,provider=provider,permission_reader=lambda _: {"state":"UNKNOWN"})
    assert not provider.submitted


def test_preflight_evidence_is_immutable(tmp_path):
    d2.preflight(tmp_path)
    path=tmp_path/"slide-12-diane/prompt.json"
    record=json.loads(path.read_text());record["prompt"]="bespoke replacement"
    d2.write_json(path,record)
    with pytest.raises(ValueError,match="IMMUTABLE"): d2.preflight(tmp_path)


def test_rejected_hero_cannot_hide_receipt_authority_failure(tmp_path):
    provider=FakeHorde(tmp_path);execute(tmp_path,provider)
    path=tmp_path/"slide-14-nora/generated-metadata.json"
    receipt=json.loads(path.read_text());receipt["provider_job_id"]=str(uuid.UUID(int=999))
    d2.write_json(path,receipt)
    with pytest.raises(ValueError,match="AUTHORITY_MISMATCH"):
        d2.record_visual_review(14,evidence(tmp_path,14,text_or_pseudotext_detected=True,approved_for_composition=False),root=tmp_path)
    assert d2.AttemptLedger(tmp_path).read()[0]["state"]=="RENDER_ARCHITECTURE_FAILURE_STOP"
    with pytest.raises(ValueError,match="PREVIOUS"): execute(tmp_path,provider)
    assert provider.transport.posts==1
