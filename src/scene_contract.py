"""Immutable D.1 plans. Boxes are page-relative unless explicitly hero-relative.

Semantic zones are instructions, never detected image objects. JSON provenance
preserves every Manifest field without mutable dictionaries inside the contract.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Zone:
    x0: float
    y0: float
    x1: float
    y1: float

    def __post_init__(self):
        if not all(math.isfinite(v) for v in (self.x0, self.y0, self.x1, self.y1)) or not (
                0 <= self.x0 < self.x1 <= 1 and 0 <= self.y0 < self.y1 <= 1):
            raise ValueError("INVALID_NORMALISED_ZONE")

    @property
    def centre(self):
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)

    def pixels(self, parent=(0, 0, 1080, 1080)):
        x, y, right, bottom = parent
        return (round(x + self.x0 * (right - x)), round(y + self.y0 * (bottom - y)),
                round(x + self.x1 * (right - x)), round(y + self.y1 * (bottom - y)))


@dataclass(frozen=True)
class TextPlan:
    text: str
    zone: Zone
    treatment: str
    font_kind: str
    font_size: int
    lines: tuple[str, ...]
    line_step: int


@dataclass(frozen=True)
class SemanticObject:
    object_id: str
    label: str
    zone: Zone  # hero-relative
    visual_role: str
    annotation_side: str
    importance: float
    related_to: tuple[str, ...]
    annotation: TextPlan  # its zone is also hero-relative
    leader: tuple[tuple[float, float], ...]  # hero-relative, terminal in object zone
    ownership: str
    concrete_visual: str
    compositor_mark: str
    text_ownership: str = "COMPOSITOR"

    def __post_init__(self):
        from .semantic_ownership import OWNERS, MARKS, COMPOSITOR_ABSTRACT
        if (not all(isinstance(v,str) for v in (self.ownership,self.concrete_visual,self.compositor_mark,self.text_ownership)) or
                self.ownership not in OWNERS or self.compositor_mark not in MARKS or self.text_ownership != "COMPOSITOR" or
                (self.ownership == COMPOSITOR_ABSTRACT and self.concrete_visual) or
                (self.ownership != COMPOSITOR_ABSTRACT and not self.concrete_visual.strip())):
            raise ValueError("SEMANTIC_OWNERSHIP_INVALID")


@dataclass(frozen=True)
class PortraitPlan:
    side: str
    scale: float
    vertical_position: str
    zone: Zone
    protected_face: Zone  # conservative protected upper portrait, no face recognition
    transition: Zone
    overlap_allowance: float
    path: str
    crop: tuple[int, ...]
    asset_sha256: str


@dataclass(frozen=True)
class SceneContract:
    schema_version: int
    episode_id: str
    production_date_sast: str
    slide_number: int
    panelist: str
    panelist_name: str
    accent: str
    panelist_grammar: str
    reasoning_family: str
    route_grammar: str
    micro_detail: str
    shape_language: str
    accent_behaviour: str
    hero_region: Zone
    art_region: Zone  # hero-relative square, aspect-preserving raster placement
    quiet_zones: tuple[Zone, ...]  # hero-relative annotation lanes
    semantic_objects: tuple[SemanticObject, ...]
    portrait: PortraitPlan
    headline: TextPlan
    subheadline: TextPlan
    phrase: TextPlan
    takeaway_arrangement: str
    takeaways: tuple[TextPlan, ...]
    furniture: tuple[TextPlan, ...]
    manifest_sha256: str
    configuration_sha256: str
    slide_json: str
    grammar_json: str
    visual_brief: str
    depiction_guardrails: tuple[str, ...]

    def to_dict(self):
        return asdict(self)

    @property
    def sha256(self):
        return digest(self.to_dict())

    @property
    def slide(self):
        return json.loads(self.slide_json)

    @classmethod
    def from_dict(cls, data):
        """Strict structural decoding; renderer additionally recompiles authority.

        A decoded contract is not itself readiness or publication permission.
        """
        def text(p):
            return TextPlan(**{**p, "zone": Zone(**p["zone"]), "lines": tuple(p["lines"])})

        objects = tuple(SemanticObject(**{**o, "zone": Zone(**o["zone"]),
            "related_to": tuple(o["related_to"]), "annotation": text(o["annotation"]),
            "leader": tuple(tuple(point) for point in o["leader"])}) for o in data["semantic_objects"])
        p = data["portrait"]
        portrait = PortraitPlan(**{**p, "zone": Zone(**p["zone"]),
            "protected_face": Zone(**p["protected_face"]), "transition": Zone(**p["transition"]),
            "crop": tuple(p["crop"])})
        result = cls(**{**data, "hero_region": Zone(**data["hero_region"]), "art_region": Zone(**data["art_region"]),
            "quiet_zones": tuple(Zone(**z) for z in data["quiet_zones"]),
            "semantic_objects": objects, "portrait": portrait,
            "headline": text(data["headline"]), "subheadline": text(data["subheadline"]),
            "phrase": text(data["phrase"]), "takeaways": tuple(text(t) for t in data["takeaways"]),
            "furniture": tuple(text(t) for t in data["furniture"]),
            "depiction_guardrails": tuple(data["depiction_guardrails"])})
        if result.schema_version != 2 or len(result.takeaways) != 3:
            raise ValueError("SCENE_CONTRACT_SCHEMA_INVALID")
        return result
