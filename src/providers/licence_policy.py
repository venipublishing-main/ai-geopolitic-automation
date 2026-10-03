"""Small, explicit internal-use policy; public credit delivery is not implemented."""
from dataclasses import asdict
from urllib.parse import urlparse

from .contracts import Modality, UseCase, UseContext
from .model_registry import PermissionState

# Attachment A of CreativeML Open RAIL++-M. These remain obligations, not
# permission inferred from the model family or an empty reference restrictions list.
OPENRAIL_RESTRICTIONS = (
    "illegal_use", "harm_to_minors", "harmful_false_information", "harmful_personal_data",
    "defamation_or_harassment", "automated_legal_decisions", "individual_profiling",
    "vulnerability_exploitation", "protected_class_discrimination", "medical_advice",
    "justice_law_enforcement_immigration_decisions",
)
RESTRICTIONS = OPENRAIL_RESTRICTIONS + ("no_implied_trademark_endorsement",)
SCOPE_EXCLUSIONS = {"automated_legal_decisions", "individual_profiling", "medical_advice",
                    "justice_law_enforcement_immigration_decisions"}


def _source(value):
    return isinstance(value, str) and urlparse(value).scheme == "https" and bool(urlparse(value).netloc)


def model_permission_rejections(model, job):
    reasons = []
    state = model.permission_state if model is not None else None
    if state is PermissionState.PROHIBITED:
        return ("MODEL_USE_PROHIBITED",)
    if (model is None or state is PermissionState.UNKNOWN or
            model.commercial_output_allowed is not True or not model.licence):
        reasons.append("MODEL_COMMERCIAL_PERMISSION_UNPROVEN")
    elif model.attribution_required is None:
        reasons.append("MODEL_ATTRIBUTION_UNKNOWN")
    elif state is None:
        # Preserve the established legacy registry contract and existing tests.
        if model.attribution_required and not job.output.attribution_allowed:
            reasons.append("MODEL_ATTRIBUTION_REQUIRED")
    else:
        if not _source(model.licence_source) or not _source(model.permission_source):
            reasons.append("MODEL_PERMISSION_EVIDENCE_MISSING")
        obligations = model.attribution_required or bool(model.known_restrictions)
        if obligations and state is not PermissionState.ALLOWED_WITH_OBLIGATIONS:
            reasons.append("MODEL_PERMISSION_STATE_INCONSISTENT")
        if state is PermissionState.ALLOWED_WITH_OBLIGATIONS:
            if not job.use.record_obligations:
                reasons.append("MODEL_OBLIGATIONS_NOT_RECORDED")
            if model.attribution_required:
                if not model.creator or not model.attribution_text:
                    reasons.append("MODEL_ATTRIBUTION_METADATA_MISSING")
                if job.use.context is UseContext.PRODUCTION_PUBLISH:
                    reasons.append("PUBLIC_ATTRIBUTION_SURFACE_UNCONFIGURED")
    if model is not None and model.known_restrictions:
        supported_scope = (state is PermissionState.ALLOWED_WITH_OBLIGATIONS and
                           job.use.context is UseContext.INTERNAL_BENCHMARK and
                           job.use.case is UseCase.NON_PERSONAL_INFRASTRUCTURE and
                           job.use.record_obligations and job.modality is Modality.IMAGE and
                           job.purpose == "contextual_art" and not job.reference_assets and not job.image_edit)
        if not supported_scope or any(r not in RESTRICTIONS for r in model.known_restrictions):
            reasons.append("MODEL_RESTRICTIONS_UNHANDLED")
    return tuple(reasons)


def permission_audit(model, job):
    """Retain credit and unresolved content review all the way to a future handoff."""
    if model is None or model.permission_state is None:
        return None
    internal_scope = (job.use.context is UseContext.INTERNAL_BENCHMARK and
                      job.use.case is UseCase.NON_PERSONAL_INFRASTRUCTURE and
                      job.purpose == "contextual_art" and job.modality is Modality.IMAGE and
                      not job.reference_assets and not job.image_edit)
    return {
        "model": model.model_id, "creator": model.creator, "permission_state": model.permission_state.value,
        "licence": model.licence, "commercial_output_allowed": model.commercial_output_allowed,
        "attribution_text": model.attribution_text, "licence_source": model.licence_source,
        "permission_source": model.permission_source, "use": asdict(job.use),
        "obligations_recorded": job.use.record_obligations,
        "known_restrictions": list(model.known_restrictions),
        "restriction_checks": {r: "EXCLUDED_BY_DECLARED_TASK_SCOPE" if internal_scope and r in SCOPE_EXCLUSIONS
                               else "HUMAN_REVIEW_REQUIRED" for r in model.known_restrictions},
        "review_state": "HUMAN_REVIEW_REQUIRED",
        "scope_note": "Non-personal physical data-centre illustration. Declared scope does not prove raster/content compliance; review before any publication.",
        "publication_attribution_required": model.attribution_required,
        "publication_handoff": {"model": model.model_id, "creator": model.creator,
            "required_attribution_text": model.attribution_text,
            "source": model.permission_source, "licence_source": model.licence_source,
            "publication_attribution_required": model.attribution_required,
            "public_attribution_surface_configured": False, "state": "BLOCKED",
            "blockers": ["HUMAN_REVIEW_REQUIRED"] + (["PUBLIC_ATTRIBUTION_SURFACE_UNCONFIGURED"]
                                                      if model.attribution_required else [])},
    }
