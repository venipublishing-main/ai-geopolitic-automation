"""Offline obligation enforcement and exact-checkpoint evidence; no legal compliance claim."""
from dataclasses import replace
import json
from pathlib import Path

import pytest

from src import phase_c, phase_c_cloud
from src.providers.cloud import common
from src.providers.cloud.ai_horde import AIHordeProvider, ALBEDO_SETTINGS
from src.providers.cloud.models import (ALBEDO_MODEL, ALBEDO_MODEL_ID, ALBEDO_CHECKPOINT_SHA256,
    SDXL_MODEL, HORDE_PROVIDER, cloud_registry)
from src.providers.contracts import (UseRequirements, UseCase, UseContext, Modality, MonetaryCost,
                                    JobState, UnsupportedJob, InvalidGenerationJob)
from src.providers.licence_policy import model_permission_rejections, permission_audit, RESTRICTIONS
from src.providers.model_registry import ModelMetadata, ModelRegistry, PermissionState
from src.providers.router import GenerationRouter, NoFreeGenerationProviderAvailable
from test_generation_router import RecordedProvider, job, registry
from test_phase_c_cloud import Wire, snapshot
from test_phase_c_kai_bridge import kai_ready

INTERNAL = UseRequirements(UseContext.INTERNAL_BENCHMARK, UseCase.NON_PERSONAL_INFRASTRUCTURE, True)


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    monkeypatch.setattr(phase_c_cloud, "OUTPUT", tmp_path / "output/phase-c1")
    def forbidden(*a, **kw):
        raise AssertionError("Licence tests never access network")
    monkeypatch.setattr("urllib.request.OpenerDirector.open", forbidden)


def conditional_job(**changes):
    return job(purpose="contextual_art", use=INTERNAL, **changes)


def model(**changes):
    return replace(ALBEDO_MODEL, model_id="fixture-model", provider="recorded", **changes)


@pytest.mark.parametrize("state,accepted,code", [
    (PermissionState.ALLOWED, True, None),
    (PermissionState.UNKNOWN, False, "MODEL_COMMERCIAL_PERMISSION_UNPROVEN"),
    (PermissionState.PROHIBITED, False, "MODEL_USE_PROHIBITED"),
])
def test_explicit_permission_states(state, accepted, code):
    p = RecordedProvider()
    metadata = model(permission_state=state, attribution_required=False, known_restrictions=())
    router = GenerationRouter((p,), models=ModelRegistry((metadata,)))
    if accepted:
        router.submit(conditional_job())
    else:
        with pytest.raises(NoFreeGenerationProviderAvailable) as e:
            router.submit(conditional_job())
        assert code in e.value.audit[0].reasons and "submit" not in p.calls


def test_obligation_recording_required():
    request = conditional_job()
    request = replace(request, use=replace(INTERNAL, record_obligations=False))
    assert "MODEL_OBLIGATIONS_NOT_RECORDED" in model_permission_rejections(model(), request)


def test_internal_credit_result_and_handoff():
    p = RecordedProvider()
    router = GenerationRouter((p,), models=ModelRegistry((model(),)))
    router.submit(conditional_job())
    p.state = JobState.SUCCEEDED
    data = dict(router.result("job-1").data)
    audit = json.loads(data["licence_audit"])
    handoff = json.loads(data["publication_handoff"])
    assert audit["attribution_text"] == ALBEDO_MODEL.attribution_text
    assert audit["creator"] == "albedobond" and audit["obligations_recorded"] is True
    assert audit["known_restrictions"] == list(RESTRICTIONS)
    assert audit["restriction_checks"]["medical_advice"] == "EXCLUDED_BY_DECLARED_TASK_SCOPE"
    assert audit["restriction_checks"]["illegal_use"] == "HUMAN_REVIEW_REQUIRED"
    assert handoff["publication_attribution_required"] is True and handoff["state"] == "BLOCKED"


def test_production_hidden_metadata_and_legacy_flag_are_not_public_credit():
    request = conditional_job()
    request = replace(request, use=replace(INTERNAL, context=UseContext.PRODUCTION_PUBLISH),
                      output=replace(request.output, attribution_allowed=True))
    codes = model_permission_rejections(model(), request)
    assert "PUBLIC_ATTRIBUTION_SURFACE_UNCONFIGURED" in codes


@pytest.mark.parametrize("change,code", [
    ({"commercial_output_allowed": False}, "MODEL_COMMERCIAL_PERMISSION_UNPROVEN"),
    ({"attribution_text": None}, "MODEL_ATTRIBUTION_METADATA_MISSING"),
    ({"creator": None}, "MODEL_ATTRIBUTION_METADATA_MISSING"),
    ({"permission_source": None}, "MODEL_PERMISSION_EVIDENCE_MISSING"),
    ({"licence_source": "not-evidence"}, "MODEL_PERMISSION_EVIDENCE_MISSING"),
    ({"permission_state": PermissionState.ALLOWED}, "MODEL_PERMISSION_STATE_INCONSISTENT"),
    ({"known_restrictions": ("unreviewed restriction",)}, "MODEL_RESTRICTIONS_UNHANDLED"),
])
def test_missing_conflicting_or_unknown_permissions_fail_closed(change, code):
    assert code in model_permission_rejections(model(**change), conditional_job())


def test_unsupported_use_and_reference_still_block_restrictions():
    for request in (replace(conditional_job(), use=replace(INTERNAL, case=UseCase.UNSPECIFIED)),
                    conditional_job(reference_assets=("person.png",)), job(use=INTERNAL)):
        assert "MODEL_RESTRICTIONS_UNHANDLED" in model_permission_rejections(model(), request)


@pytest.mark.parametrize("cost", [MonetaryCost.PAID, MonetaryCost.UNKNOWN])
def test_zero_cost_gate_unchanged(cost):
    p = RecordedProvider()
    p.caps = replace(p.caps, monetary_cost=cost)
    router = GenerationRouter((p,), models=ModelRegistry((model(),)))
    with pytest.raises(NoFreeGenerationProviderAvailable) as e:
        router.submit(conditional_job())
    assert "ZERO_COST_POLICY_REJECTED" in e.value.audit[0].reasons and "submit" not in p.calls


def test_sdxl_use_restrictions_are_not_blanket_commercial_prohibition():
    assert SDXL_MODEL.commercial_output_allowed is True and SDXL_MODEL.known_restrictions
    assert not model_permission_rejections(SDXL_MODEL, conditional_job())
    assert permission_audit(SDXL_MODEL, conditional_job())["review_state"] == "HUMAN_REVIEW_REQUIRED"


def test_exact_albedo_fixture_identity_and_author_permission():
    root = Path(__file__).parent / "fixtures/cloud"
    reference = json.loads((root / "horde_albedo_v2.json").read_text())
    author = json.loads((root / "albedo_author_permissions.json").read_text())
    version = author["modelVersions"][0]
    assert reference["name"] == ALBEDO_MODEL.model_id == ALBEDO_MODEL_ID
    assert reference["config"]["download"][0]["sha256sum"].upper() == ALBEDO_CHECKPOINT_SHA256
    assert any(f["hashes"].get("SHA256", "").upper() == ALBEDO_CHECKPOINT_SHA256 for f in version["files"])
    assert version["id"] == 1041855 and version["modelId"] == author["id"] == 140737
    assert author["creator"]["username"] == ALBEDO_MODEL.creator == "albedobond"
    assert author["allowNoCredit"] is False and set(author["allowCommercialUse"]) == {"Image", "Rent", "RentCivit"}
    assert reference["licensing"]["commercial_use"] == "allowed_with_conditions"
    assert not model_permission_rejections(ALBEDO_MODEL, conditional_job())
    assert "MODEL_COMMERCIAL_PERMISSION_UNPROVEN" in model_permission_rejections(
        replace(ALBEDO_MODEL, permission_state=PermissionState.UNKNOWN), conditional_job())


def albedo(tmp_path):
    wire = Wire()
    wire.active = [{"name": ALBEDO_MODEL_ID, "count": 3}]
    wire.generation["model"] = ALBEDO_MODEL_ID
    wire.state = snapshot("success")
    return AIHordeProvider(settings=ALBEDO_SETTINGS, transport=wire, models=cloud_registry(),
        api_key="0000000000", artifact_root=tmp_path / "output/phase-c1/albedo"), wire


def test_dry_run_exact_live_copy_and_no_dispatch(kai_ready, tmp_path):
    p, wire = albedo(tmp_path)
    report = phase_c_cloud.benchmark(kai_ready, (p,), priority=(HORDE_PROVIDER,), slide_number=5)
    assert report["state"] == "DRY_RUN_READY" and not report["blockers"]
    assert report["selected_bridge_profile"] == "KAI_NETWORK_MESH"
    assert report["predicted_generation_count"] == 1 and report["generation_attempts_total"] == 0
    assert report["providers"][0]["licence_audit"]["obligations_recorded"] is True
    assert not any(c[0] == "POST" for c in wire.calls)
    positive, negative = report["submitted_prompt"].split("###")
    assert "cloud" not in positive.lower() and "watermark" in negative
    assert kai_ready.manifest["slides"][4]["hero_visual"] in positive


def test_one_dispatch_metadata_negative_conditioning_no_composition_or_retry(kai_ready, tmp_path, monkeypatch):
    p, wire = albedo(tmp_path)
    monkeypatch.setattr(phase_c, "compose", lambda *a: pytest.fail("Must screen art before composition"))
    report = phase_c_cloud.benchmark(kai_ready, (p,), priority=(HORDE_PROVIDER,), slide_number=5, execute=True)
    assert report["state"] == "ARTIFACT_REVIEW_REQUIRED" and not report["blockers"]
    post = [c for c in wire.calls if c[0] == "POST"]
    assert len(post) == 1 and post[0][2]["models"] == [ALBEDO_MODEL_ID]
    params = post[0][2]["params"]
    assert params["steps"] == 30 and params["cfg_scale"] == 7.5 and params["sampler_name"] == "k_euler_a"
    assert params["seed"] == "1234567890" and params["karras"] is True and params["n"] == 1
    assert post[0][2]["prompt"].count("###") == 1
    root = Path(report["benchmark_package"])
    phase_c_cloud.write_benchmark_report(report, root)
    metadata = json.loads((root / "ai_horde/generation-metadata.json").read_text())
    assert metadata["licence_audit"] == report["licence_audit"]
    assert metadata["requested_seed"] == "1234567890"
    assert metadata["publication_handoff"]["publication_attribution_required"] is True
    assert ALBEDO_MODEL.attribution_text in (root / "benchmark-report.md").read_text()
    assert not (root / "ai_horde/slide-composite.png").exists()
    blocked = phase_c_cloud.benchmark(kai_ready, (p,), priority=(HORDE_PROVIDER,), slide_number=5,
                                     execute=True, diagnosis="No second attempt even with diagnosis")
    assert "GENERATION_BUDGET_BLOCKED" in blocked["blockers"]
    assert len([c for c in wire.calls if c[0] == "POST"]) == 1


def test_adapter_blocks_missing_negative_and_production_before_post(tmp_path):
    p, wire = albedo(tmp_path)
    request = phase_c_cloud.cloud_job(p, "positive###negative", "Ep104", 5)
    with pytest.raises(UnsupportedJob, match="PUBLIC_ATTRIBUTION"):
        p.submit(replace(request, use=UseRequirements()))
    with pytest.raises(UnsupportedJob, match="SDXL_NEGATIVE"):
        p.submit(replace(request, prompt="only positive"))
    assert not any(c[0] == "POST" for c in wire.calls)


def test_invalid_context_enum_rejected_before_provider_io():
    p = RecordedProvider()
    with pytest.raises(InvalidGenerationJob):
        GenerationRouter((p,), models=registry(p)).submit(job(use=UseRequirements(context="INTERNAL_BENCHMARK")))
    assert not p.calls
