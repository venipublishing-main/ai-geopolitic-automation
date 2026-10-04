"""Zero-inference semantic repair and exact acknowledged-job GET reconciliation."""
from copy import deepcopy
from dataclasses import replace
import base64
import io
import json
import socket

from PIL import Image, ImageDraw
import pytest

from src import phase_d2_benchmark as d2
from src import horde_reconciliation as recovery
from src.premium_scene_compiler import compile_scene, FAMILIES, _normalise
from src.premium_sdxl_prompt import compile_sdxl_prompt
from src.semantic_ownership import reviewed_depiction
from src.providers.cloud.http import CloudError


@pytest.fixture(autouse=True)
def no_generation_or_network(monkeypatch):
    def forbidden(*a,**k): pytest.fail("D2R attempted generation or an unmocked network request")
    monkeypatch.setattr(socket.socket,"connect",forbidden)
    monkeypatch.setattr(d2.AIHordeProvider,"submit",forbidden)
    monkeypatch.setattr(d2.AttemptLedger,"reserve",forbidden)
    monkeypatch.setattr(recovery.CloudHTTP,"json",forbidden)


def test_analytical_equal_conditions_and_physical_stack_are_distinct():
    manifest=d2.accepted_manifest()
    nora=compile_scene(manifest,14)
    physical=compile_scene(manifest,3)
    assert FAMILIES[_normalise("synthesis stack")]=="layered_system"
    assert nora.reasoning_family=="layered_system" and nora.panelist_grammar=="system_axis"
    assert physical.reasoning_family=="physical_stack"
    assert [o.label for o in physical.semantic_objects]==["MODEL","RACKS","COOLING","FIBRE","SUBSTATION","GRID","GENERATION"]
    assert nora.route_grammar=="parallel"
    assert len(nora.semantic_objects)==5 and {o.visual_role for o in nora.semantic_objects}=={"equal_condition"}
    assert {o.importance for o in nora.semantic_objects}=={1.0}
    assert not any(o.related_to for o in nora.semantic_objects)
    assert len({o.zone.centre[0] for o in nora.semantic_objects})>1
    assert nora.accent_behaviour=="equal condition nodes"


def test_reviewed_ownership_separates_physical_material_and_abstract_logic():
    contract=compile_scene(d2.accepted_manifest(),14)
    assert {o.label:o.ownership for o in contract.semantic_objects}=={
        "PERMIT":"COMPOSITOR_ABSTRACT","POWER":"GENERATOR_CONCRETE","WATER":"GENERATOR_CONCRETE",
        "LABOUR":"GENERATOR_CONCRETE","TRUST":"COMPOSITOR_ABSTRACT"}
    assert all(o.annotation.text==o.label for o in contract.semantic_objects)
    assert {o.text_ownership for o in contract.semantic_objects}=={"COMPOSITOR"}
    assert all(not o.concrete_visual for o in contract.semantic_objects if o.ownership=="COMPOSITOR_ABSTRACT")
    assert reviewed_depiction("JOBS").ownership=="HYBRID"


def test_physical_alias_cannot_relabel_social_conditions_as_architecture():
    manifest=d2.accepted_manifest()
    manifest["slides"][13]["preferred_visual_reasoning_family"]="architecture stack"
    with pytest.raises(ValueError,match="PHYSICAL_STACK_SEMANTICS_REQUIRED"):
        compile_scene(manifest,14)


def test_unknown_or_tampered_ownership_fails_closed():
    manifest=d2.accepted_manifest()
    manifest["slides"][13]["essential_labels"]=["UNREVIEWED CONCEPT"]
    with pytest.raises(ValueError,match="SEMANTIC_OWNERSHIP_UNKNOWN"):
        compile_scene(manifest,14)
    contract=compile_scene(d2.accepted_manifest(),14)
    with pytest.raises(ValueError,match="OWNERSHIP_INVALID"):
        replace(contract.semantic_objects[0],ownership="GUESS_GENERATOR")
    with pytest.raises(ValueError,match="OWNERSHIP_INVALID"):
        replace(contract.semantic_objects[0],text_ownership="GENERATOR")
    changed=replace(contract.semantic_objects[1],concrete_visual="print an editorial headline")
    with pytest.raises(ValueError,match="OWNERSHIP_AUTHORITY_MISMATCH"):
        compile_sdxl_prompt(replace(contract,semantic_objects=(contract.semantic_objects[0],changed,*contract.semantic_objects[2:])))


def test_nora_prompt_has_no_editorial_copy_or_abstract_label_requests():
    contract=compile_scene(d2.accepted_manifest(),14)
    positive,negative=compile_sdxl_prompt(contract).split("###")
    for text in (contract.headline.text,contract.subheadline.text,contract.phrase.text,
                 *[t.text for t in contract.takeaways],*[f.text for f in contract.furniture]):
        assert text.casefold() not in positive.casefold()
    for text in ("NO SINGLE LAYER CAN CARRY THE BUILD","PERMIT","TRUST","evidence question","failure mode",
                 "depict the","text to print","portrait 20%"):
        assert text not in positive
    assert "ONE COHERENT TEXT-FREE EDITORIAL ILLUSTRATION" in positive
    assert "Five equal-status supporting conditions" in positive and "no visual ranking" in positive
    for text in ("pyramid","triangle hierarchy","tiered pyramid","maturity ladder","staircase hierarchy","funnel","consulting diagram","pentagon"):
        assert text in negative
    assert "physical_stack" not in positive


def test_copy_and_raw_diagram_brief_cannot_leak_via_manifest_conditioning():
    manifest=d2.accepted_manifest()
    original=compile_sdxl_prompt(compile_scene(manifest,14))
    slide=manifest["slides"][13]
    slide.update(headline="EDITORIAL HEADLINE",subheadline="EDITORIAL DECK",main_visual_phrase="EDITORIAL PHRASE",
        notices_first="VISIBLE ATTENTION COPY",density_type_size_note="COPY DENSITY NOTE",
        composition_notes="TYPOGRAPHY PLACEMENT COPY",hero_visual="A labelled stack with evidence cards and visible labels.",
        core_argument="EDITORIAL CORE COPY",anti_cliche_guardrail="RAW COPY GUARDRAIL")
    for index,item in enumerate(slide["takeaway_ideas"]): item["idea"]=f"TAKEAWAY COPY {index}"
    assert compile_sdxl_prompt(compile_scene(manifest,14))==original


def test_repair_preflight_is_zero_jobs_and_separate_from_old_package(tmp_path,monkeypatch):
    monkeypatch.setattr(d2.GenerationJob,"__init__",lambda *a,**k:pytest.fail("Repair created a generation job"))
    report=d2.repair_preflight(tmp_path)
    assert [s["slide_number"] for s in report["slides"]]==[14,12,16]
    assert [s["reasoning_family"] for s in report["slides"]]==["layered_system","allocation_flow","regional_pathway"]
    assert report["post_calls"]==report["generation_calls"]==report["provider_submissions"]==0
    with pytest.raises(ValueError,match="CANNOT_WRITE_ORIGINAL"):
        d2.repair_preflight(d2.PACKAGE)


@pytest.fixture
def original(tmp_path,monkeypatch):
    root=tmp_path/"original"
    receipt={"provider_job_id":recovery.DIANE_JOB_ID,"provider":"ai_horde","model":recovery.ALBEDO_MODEL_ID,
        "state":"AMBIGUOUS_STATUS_STOP","attempt":1,"job_id":"accepted-old-local-job", "contract_sha256":"old-contract",
        "prompt_sha256":"old-prompt","licence_audit":{"publication_attribution_required":True}}
    row={**receipt,"slide_number":12}
    for name,value in (("attempt-ledger.json",[row]),("slide-12-diane/generated-metadata.json",receipt),
                       ("slide-12-diane/prompt.json",{"prompt":"immutable original editorial prompt"})):
        path=root/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value),encoding="utf-8")
    hashes={name:recovery.sha(root/name) for name in recovery.ORIGINAL_HASHES}
    monkeypatch.setattr(recovery,"ORIGINAL_HASHES",hashes)
    return root,hashes


def status(**fields):
    return dict(done=False,faulted=False,finished=0,processing=0,waiting=1,**fields)


class ReadTransport:
    def __init__(self,mode="queued"): self.mode=mode;self.calls=[]
    def json(self,method,path,payload=None,headers=None):
        assert method=="GET" and path.endswith(recovery.DIANE_JOB_ID) and payload is None
        self.calls.append((method,path))
        if self.mode in {"404","503"}: raise CloudError("HTTP_REJECTED",status=int(self.mode))
        if self.mode=="faulted": return dict(done=True,faulted=True,finished=0,processing=0,waiting=0)
        if self.mode=="malformed": return {"done":True}
        if self.mode=="empty_terminal": return dict(done=True,faulted=False,finished=0,processing=0,waiting=0)
        if self.mode=="queued": return status()
        done=dict(done=True,faulted=False,finished=1,processing=0,waiting=0)
        if "/status/" in path:
            image=Image.new("RGB",(1024,1024),"white")
            ImageDraw.Draw(image).rectangle((200,200,800,800),fill="black")
            raw=io.BytesIO();image.save(raw,"PNG")
            done["generations"]=[dict(model="wrong" if self.mode=="wrong_model" else recovery.ALBEDO_MODEL_ID,
                state="ok",censored=False,seed="1234567890",img=base64.b64encode(raw.getvalue()).decode())]
        return done


@pytest.mark.parametrize("mode,expected",[("queued","REMOTE_STATE_UNRESOLVED"),("404","REMOTE_STATE_UNRESOLVED"),
    ("503","REMOTE_STATE_UNRESOLVED"),("malformed","REMOTE_STATE_UNRESOLVED"),("empty_terminal","REMOTE_STATE_UNRESOLVED"),
    ("wrong_model","REMOTE_STATE_UNRESOLVED"),("faulted","REMOTE_JOB_TERMINAL_FAILURE"),("success","REMOTE_JOB_SUCCEEDED")])
def test_repeated_exact_job_reads_never_submit_or_mutate_old_evidence(original,tmp_path,mode,expected):
    old,hashes=original
    transport=ReadTransport(mode)
    reports=[recovery.reconcile_job(12,original=old,root=tmp_path/"repair",transport=transport) for _ in range(2)]
    assert all(r["state"]==expected for r in reports)
    assert reports[0]["evidence_path"]!=reports[1]["evidence_path"]
    assert all(r["provider_job_id"]==recovery.DIANE_JOB_ID and r["post_calls"]==r["new_attempts"]==r["generation_calls"]==0 for r in reports)
    assert all(method=="GET" and path.endswith(recovery.DIANE_JOB_ID) for method,path in transport.calls)
    assert all(recovery.sha(old/name)==digest for name,digest in hashes.items())
    if mode=="success":
        assert reports[0]["seed"]=="1234567890"
        assert reports[0]["raster_sha256"]==recovery.sha(reports[0]["artifact_path"])
        assert reports[0]["composition"]=="WITHHELD_SEPARATE_REVIEW_REQUIRED"


@pytest.mark.parametrize("method,path,payload",[("POST","/v2/generate/async",{}),("DELETE","/v2/generate/status/"+recovery.DIANE_JOB_ID,None),
    ("GET","/v2/generate/status/foreign-job",None),("GET","/v2/generate/check/"+recovery.DIANE_JOB_ID,{"seed":99})])
def test_transport_rejects_generation_cancel_foreign_id_and_payload_before_network(method,path,payload):
    transport=ReadTransport()
    with pytest.raises(ValueError,match="GET_EXACT_JOB_ONLY"):
        recovery.AcknowledgedJobReads(transport,recovery.DIANE_JOB_ID).json(method,path,payload)
    assert transport.calls==[]


def test_changed_receipt_or_original_output_root_prevents_all_reads(original,tmp_path):
    old,_=original;transport=ReadTransport()
    with pytest.raises(ValueError,match="CANNOT_WRITE_ORIGINAL"):
        recovery.reconcile_job(12,original=old,root=old,transport=transport)
    receipt=old/"slide-12-diane/generated-metadata.json"
    receipt.write_text(receipt.read_text()+" ")
    with pytest.raises(ValueError,match="EVIDENCE_CHANGED"):
        recovery.reconcile_job(12,original=old,root=tmp_path/"repair",transport=transport)
    assert not transport.calls


def test_cli_blocks_new_benchmark_without_touching_archived_reports(monkeypatch,capsys):
    monkeypatch.setattr(d2,"benchmark_report",lambda *a,**k:pytest.fail("CLI rewrote archived report"))
    assert d2.main(["--execute-next"])==1
    assert "NEW_D2_BENCHMARK_NOT_AUTHORIZED" in capsys.readouterr().out


@pytest.mark.parametrize("state,exit_code",[("REMOTE_STATE_UNRESOLVED",1),("REMOTE_JOB_SUCCEEDED",0),("REMOTE_JOB_TERMINAL_FAILURE",0)])
def test_cli_reconciliation_state_and_exit_code(monkeypatch,capsys,state,exit_code):
    monkeypatch.setattr(recovery,"reconcile_job",lambda n:{"state":state,"post_calls":0})
    assert d2.main(["--reconcile-job","12"])==exit_code
    assert json.loads(capsys.readouterr().out)["state"]==state
