from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageOps

try:
    from .editorial_primitives import INK, PAPER, SAFE, W, H, LayoutError, ensure
except ImportError:
    from editorial_primitives import INK, PAPER, SAFE, W, H, LayoutError, ensure


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_PROCEDURAL_KINDS = {
    "casefile_system",
    "water_infrastructure",
    "river_monitoring",
    "mineworker_claims",
    "care_pathway",
    "oil_market",
}
ALLOWED_SOURCES = {"procedural", "asset"}


def _stable_seed(*parts) -> int:
    text = "|".join(str(p or "") for p in parts)
    return sum((i + 1) * ord(ch) for i, ch in enumerate(text)) & 0xFFFFFFFF


def validate_context_art_spec(spec: dict | None, *, label: str = "context_art") -> None:
    if spec in (None, {}):
        return
    ensure(isinstance(spec, dict), f"{label} must be an object.")
    source = str(spec.get("source", "procedural")).strip().lower()
    ensure(source in ALLOWED_SOURCES, f"{label}.source must be one of {sorted(ALLOWED_SOURCES)}.")

    box = spec.get("box")
    ensure(isinstance(box, list) and len(box) == 4, f"{label}.box must be [x0, y0, x1, y1].")
    ensure(all(isinstance(v, (int, float)) for v in box), f"{label}.box values must be numbers.")
    x0, y0, x1, y1 = [int(v) for v in box]
    ensure(x0 < x1 and y0 < y1, f"{label}.box has invalid dimensions.")
    ensure(x0 >= SAFE and x1 <= W - SAFE and y0 >= SAFE and y1 <= 890,
           f"{label}.box must stay inside the safe editorial content area.")
    ensure(x1 - x0 >= 180 and y1 - y0 >= 150, f"{label}.box is too small for contextual art.")

    opacity = spec.get("opacity", 0.62)
    ensure(isinstance(opacity, (int, float)) and 0.15 <= float(opacity) <= 1.0,
           f"{label}.opacity must be between 0.15 and 1.0.")

    layer = str(spec.get("layer", "background")).strip().lower()
    ensure(layer in {"background", "foreground"},
           f"{label}.layer must be 'background' or 'foreground'.")

    exclusions = spec.get("exclusions", [])
    ensure(isinstance(exclusions, list), f"{label}.exclusions must be a list when supplied.")
    for ex_index, ex in enumerate(exclusions, start=1):
        ensure(isinstance(ex, list) and len(ex) == 4,
               f"{label}.exclusions[{ex_index}] must be [x0, y0, x1, y1].")
        ensure(all(isinstance(v, (int, float)) for v in ex),
               f"{label}.exclusions[{ex_index}] values must be numbers.")
        ex0, ey0, ex1, ey1 = [int(v) for v in ex]
        ensure(ex0 < ex1 and ey0 < ey1, f"{label}.exclusions[{ex_index}] has invalid dimensions.")

    if source == "procedural":
        kind = str(spec.get("kind", "")).strip().lower()
        ensure(kind in ALLOWED_PROCEDURAL_KINDS,
               f"{label}.kind must be one of {sorted(ALLOWED_PROCEDURAL_KINDS)}.")
    else:
        path = spec.get("path")
        ensure(isinstance(path, str) and path.strip(), f"{label}.path is required for source='asset'.")
        rel = Path(path)
        ensure(not rel.is_absolute(), f"{label}.path must be repository-relative.")
        resolved = (PROJECT_ROOT / rel).resolve()
        assets_root = (PROJECT_ROOT / "assets").resolve()
        ensure(resolved == assets_root or assets_root in resolved.parents,
               f"{label}.path must stay under assets/.")
        ensure(resolved.exists(), f"{label}.asset does not exist: {path}")


def _rgba(colour, alpha: int):
    return tuple(colour) + (max(0, min(255, int(alpha))),)


class Plate:
    """Normalised drawing surface clipped to one editorial box."""

    def __init__(self, box, accent, opacity: float, seed: int):
        self.x0, self.y0, self.x1, self.y1 = [int(v) for v in box]
        self.w = self.x1 - self.x0
        self.h = self.y1 - self.y0
        self.accent = tuple(accent)
        self.opacity = float(opacity)
        self.rng = random.Random(seed)
        self.image = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)
        self.ink = _rgba(INK, 205 * self.opacity)
        self.ink_soft = _rgba(INK, 105 * self.opacity)
        self.accent_line = _rgba(self.accent, 195 * self.opacity)
        self.accent_soft = _rgba(self.accent, 95 * self.opacity)
        self.paper = _rgba(PAPER, 235 * self.opacity)

    def p(self, x: float, y: float):
        return (int(x * self.w), int(y * self.h))

    def box(self, x0, y0, x1, y1):
        a = self.p(x0, y0)
        b = self.p(x1, y1)
        return (a[0], a[1], b[0], b[1])

    def line(self, points: Iterable[tuple[float, float]], *, accent=False, width=2, rough=True, soft=False):
        pts = [self.p(x, y) for x, y in points]
        colour = self.accent_soft if (accent and soft) else self.accent_line if accent else self.ink_soft if soft else self.ink
        self.draw.line(pts, fill=colour, width=max(1, int(width)))
        if rough and len(pts) >= 2:
            dx = self.rng.choice((-1, 0, 1))
            dy = self.rng.choice((-1, 0, 1))
            ghost = [(x + dx, y + dy) for x, y in pts]
            ghost_colour = self.accent_soft if accent else self.ink_soft
            self.draw.line(ghost, fill=ghost_colour, width=max(1, int(width - 1)))

    def ellipse(self, box, *, accent=False, width=2, fill=None):
        b = self.box(*box)
        outline = self.accent_line if accent else self.ink
        fill_colour = fill
        if fill == "paper":
            fill_colour = self.paper
        elif fill == "accent":
            fill_colour = self.accent_soft
        self.draw.ellipse(b, outline=outline, width=width, fill=fill_colour)

    def rect(self, box, *, accent=False, width=2, fill=None, radius=0):
        b = self.box(*box)
        outline = self.accent_line if accent else self.ink
        fill_colour = None
        if fill == "paper":
            fill_colour = self.paper
        elif fill == "accent":
            fill_colour = self.accent_soft
        if radius:
            self.draw.rounded_rectangle(b, radius=radius, outline=outline, width=width, fill=fill_colour)
        else:
            self.draw.rectangle(b, outline=outline, width=width, fill=fill_colour)

    def polygon(self, points, *, accent=False, fill=None, width=2):
        pts = [self.p(x, y) for x, y in points]
        outline = self.accent_line if accent else self.ink
        fill_colour = None
        if fill == "paper":
            fill_colour = self.paper
        elif fill == "accent":
            fill_colour = self.accent_soft
        self.draw.polygon(pts, outline=outline, fill=fill_colour)
        if width > 1:
            self.draw.line(pts + [pts[0]], fill=outline, width=width)

    def hatch_rect(self, box, *, accent=False, spacing=0.035, slope=1):
        x0, y0, x1, y1 = box
        colour = self.accent_soft if accent else self.ink_soft
        step = max(5, int(spacing * self.w))
        local = self.box(x0, y0, x1, y1)
        lx0, ly0, lx1, ly1 = local
        span = max(lx1 - lx0, ly1 - ly0)
        for off in range(-span, span * 2, step):
            if slope >= 0:
                a = (lx0 + off, ly1)
                b = (lx0 + off + span, ly0)
            else:
                a = (lx0 + off, ly0)
                b = (lx0 + off + span, ly1)
            # Simple clipping by drawing to a mask-backed patch.
            mask = Image.new("L", (self.w, self.h), 0)
            md = ImageDraw.Draw(mask)
            md.rectangle(local, fill=255)
            stroke = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
            sd = ImageDraw.Draw(stroke)
            sd.line((a, b), fill=colour, width=1)
            self.image.paste(stroke, (0, 0), Image.composite(mask, Image.new("L", mask.size, 0), mask))

    def hatch_polygon(self, points, *, accent=False, spacing=9, slope=1):
        pts = [self.p(x, y) for x, y in points]
        mask = Image.new("L", (self.w, self.h), 0)
        md = ImageDraw.Draw(mask)
        md.polygon(pts, fill=255)
        hatch = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        hd = ImageDraw.Draw(hatch)
        colour = self.accent_soft if accent else self.ink_soft
        span = self.w + self.h
        for off in range(-self.h, self.w + self.h, max(5, spacing)):
            if slope >= 0:
                hd.line((off, self.h, off + self.h, 0), fill=colour, width=1)
            else:
                hd.line((off, 0, off + self.h, self.h), fill=colour, width=1)
        self.image.paste(hatch, (0, 0), mask)

    def distress(self, count=120):
        for _ in range(count):
            x = self.rng.randrange(max(1, self.w))
            y = self.rng.randrange(max(1, self.h))
            if self.rng.random() < 0.72:
                self.draw.point((x, y), fill=self.ink_soft)


def _arrow_head(plate: Plate, start, end, *, accent=True, width=2):
    plate.line([start, end], accent=accent, width=width)
    x0, y0 = start
    x1, y1 = end
    ang = math.atan2(y1 - y0, x1 - x0)
    length = 0.025
    p1 = (x1 - length * math.cos(ang - 0.55), y1 - length * math.sin(ang - 0.55))
    p2 = (x1 - length * math.cos(ang + 0.55), y1 - length * math.sin(ang + 0.55))
    plate.polygon([end, p1, p2], accent=accent, fill="accent", width=1)


def _casefile_system(p: Plate):
    # Stacked files / folders with stamped marks and handoff arrows.
    for i in range(4):
        y = 0.18 + i * 0.13
        x = 0.18 + i * 0.035
        p.rect((x, y, 0.78 + i * 0.02, y + 0.20), accent=(i % 2 == 0), width=2, fill="paper", radius=5)
        p.rect((x + 0.03, y - 0.025, x + 0.23, y + 0.035), accent=True, width=2, fill="paper", radius=4)
        for r in range(3):
            p.line([(x + 0.27, y + 0.055 + r * 0.035), (0.70, y + 0.055 + r * 0.035)], soft=True, rough=False)
    # Round seals / checks.
    for cx, cy in ((0.27, 0.28), (0.36, 0.43), (0.44, 0.58), (0.52, 0.73)):
        p.ellipse((cx - 0.035, cy - 0.035, cx + 0.035, cy + 0.035), accent=True, width=2)
        p.line([(cx - 0.018, cy), (cx - 0.002, cy + 0.016), (cx + 0.025, cy - 0.022)], accent=True, width=2)
    # Handoff arrows to civic outcomes.
    for y in (0.30, 0.46, 0.62, 0.78):
        _arrow_head(p, (0.78, y), (0.94, y), accent=True, width=2)
    # Four tiny civic pictograms at right edge: water, institution, power, care.
    # water drop
    p.polygon([(0.92, 0.19), (0.89, 0.25), (0.92, 0.29), (0.95, 0.25)], accent=True, width=2)
    # institution
    p.polygon([(0.87, 0.40), (0.92, 0.35), (0.97, 0.40)], accent=False, width=2)
    p.rect((0.88, 0.40, 0.96, 0.47), width=2)
    for x in (0.90, 0.92, 0.94):
        p.line([(x, 0.405), (x, 0.465)], soft=False)
    # power bolt
    p.polygon([(0.93, 0.53), (0.89, 0.61), (0.92, 0.61), (0.90, 0.69), (0.96, 0.59), (0.93, 0.59)], accent=True, width=2)
    # medical cross
    p.rect((0.90, 0.76, 0.94, 0.88), accent=True, width=2)
    p.rect((0.86, 0.80, 0.98, 0.84), accent=True, width=2)
    p.hatch_rect((0.13, 0.12, 0.84, 0.87), spacing=0.045, slope=-1)


def _water_infrastructure(p: Plate):
    # Treatment basins at left.
    for cx in (0.16, 0.28):
        p.ellipse((cx - 0.07, 0.55, cx + 0.07, 0.68), accent=True, width=2, fill="paper")
        p.line([(cx - 0.06, 0.615), (cx + 0.06, 0.615)], accent=True, width=2)
    # Pipe network.
    p.line([(0.30, 0.62), (0.45, 0.62), (0.45, 0.48), (0.60, 0.48)], accent=True, width=5)
    p.line([(0.60, 0.48), (0.73, 0.48), (0.73, 0.68), (0.84, 0.68)], accent=True, width=5)
    # Reservoir tower.
    p.ellipse((0.48, 0.23, 0.68, 0.39), width=3, fill="paper")
    p.line([(0.52, 0.38), (0.50, 0.62)], width=3)
    p.line([(0.64, 0.38), (0.66, 0.62)], width=3)
    p.line([(0.50, 0.53), (0.66, 0.53)], soft=True)
    p.hatch_rect((0.49, 0.26, 0.67, 0.35), accent=True, spacing=0.035, slope=1)
    # House and tap.
    p.polygon([(0.76, 0.55), (0.86, 0.45), (0.96, 0.55)], width=3)
    p.rect((0.78, 0.55, 0.94, 0.80), width=3, fill="paper")
    p.rect((0.84, 0.65, 0.89, 0.80), accent=True, width=2)
    p.line([(0.84, 0.68), (0.78, 0.68), (0.78, 0.73)], accent=True, width=3)
    p.line([(0.78, 0.73), (0.75, 0.73)], accent=True, width=3)
    p.polygon([(0.75, 0.75), (0.735, 0.79), (0.75, 0.815), (0.765, 0.79)], accent=True, width=2)
    # Flow arrows.
    _arrow_head(p, (0.20, 0.76), (0.42, 0.76), accent=True, width=2)
    _arrow_head(p, (0.45, 0.76), (0.68, 0.76), accent=True, width=2)
    _arrow_head(p, (0.70, 0.76), (0.90, 0.76), accent=True, width=2)
    # Waterline / terrain.
    for yy in (0.86, 0.89, 0.92):
        pts = [(x / 20, yy + 0.012 * math.sin(x * 0.8)) for x in range(1, 20)]
        p.line(pts, accent=(yy == 0.86), width=2, soft=(yy != 0.86))


def _river_monitoring(p: Plate):
    # River ribbon.
    upper = []
    lower = []
    for i in range(31):
        x = i / 30
        y = 0.52 + 0.13 * math.sin(x * 7.8) + 0.035 * math.sin(x * 17)
        upper.append((x, y - 0.055))
        lower.append((x, y + 0.055))
    p.line(upper, accent=True, width=3)
    p.line(lower, accent=True, width=3)
    for i in range(0, 31, 4):
        p.line([upper[i], lower[i]], accent=True, width=1, soft=True)
    # Sensor posts along banks + radio arcs.
    sensors = [(0.18, 0.35), (0.43, 0.65), (0.68, 0.33), (0.86, 0.62)]
    for x, y in sensors:
        p.line([(x, y), (x, y + 0.16)], width=3)
        p.rect((x - 0.025, y - 0.03, x + 0.025, y + 0.03), accent=True, width=2, fill="paper")
        for r in (0.045, 0.075):
            b = p.box(x - r, y - r, x + r, y + r)
            p.draw.arc(b, 205, 335, fill=p.accent_soft, width=2)
    # Sample points / telemetry route.
    for x, y in ((0.10, 0.72), (0.27, 0.48), (0.52, 0.67), (0.76, 0.44), (0.94, 0.66)):
        p.ellipse((x - 0.012, y - 0.012, x + 0.012, y + 0.012), accent=True, width=2, fill="accent")
    p.line([(0.10, 0.72), (0.27, 0.48), (0.52, 0.67), (0.76, 0.44), (0.94, 0.66)], accent=True, width=2, soft=True)
    # Wrench-like repair mark.
    p.ellipse((0.73, 0.75, 0.80, 0.82), width=2)
    p.line([(0.775, 0.80), (0.90, 0.90)], width=4)
    p.line([(0.89, 0.89), (0.94, 0.87)], width=2)
    p.hatch_rect((0.03, 0.12, 0.97, 0.93), accent=False, spacing=0.05, slope=1)


def _mineworker_claims(p: Plate):
    # Mine headgear / shaft.
    p.line([(0.10, 0.80), (0.23, 0.19), (0.36, 0.80)], width=4)
    p.line([(0.17, 0.48), (0.30, 0.48)], width=3)
    p.line([(0.14, 0.61), (0.33, 0.61)], width=3)
    p.ellipse((0.18, 0.13, 0.31, 0.26), accent=True, width=3)
    p.line([(0.245, 0.26), (0.245, 0.80)], accent=True, width=2)
    # Miner helmet / face silhouette.
    p.ellipse((0.37, 0.30, 0.54, 0.52), width=3, fill="paper")
    p.arc = None
    p.line([(0.38, 0.36), (0.45, 0.30), (0.53, 0.36)], accent=True, width=5)
    p.line([(0.39, 0.36), (0.53, 0.36)], accent=True, width=4)
    p.ellipse((0.445, 0.325, 0.475, 0.355), accent=True, width=2, fill="accent")
    p.line([(0.40, 0.54), (0.34, 0.74)], width=4)
    p.line([(0.51, 0.54), (0.58, 0.74)], width=4)
    p.line([(0.34, 0.74), (0.58, 0.74)], width=4)
    # Claims stack.
    for i in range(3):
        x = 0.61 + i * 0.025
        y = 0.28 + i * 0.035
        p.rect((x, y, 0.92, y + 0.27), accent=(i == 0), width=2, fill="paper", radius=4)
        p.line([(x + 0.04, y + 0.08), (0.86, y + 0.08)], soft=True, rough=False)
        p.line([(x + 0.04, y + 0.13), (0.84, y + 0.13)], soft=True, rough=False)
        p.line([(x + 0.04, y + 0.18), (0.80, y + 0.18)], soft=True, rough=False)
    # Broken payment path / delayed coin.
    _arrow_head(p, (0.60, 0.70), (0.75, 0.70), accent=True, width=3)
    p.line([(0.76, 0.67), (0.81, 0.73)], accent=True, width=3)
    p.line([(0.76, 0.73), (0.81, 0.67)], accent=True, width=3)
    p.ellipse((0.84, 0.63, 0.94, 0.73), accent=True, width=3)
    p.hatch_rect((0.07, 0.12, 0.96, 0.84), spacing=0.045, slope=-1)


def _care_pathway(p: Plate):
    # Clinic / crisis response.
    p.rect((0.08, 0.46, 0.28, 0.78), width=3, fill="paper")
    p.polygon([(0.07, 0.46), (0.18, 0.34), (0.29, 0.46)], accent=True, width=3)
    p.rect((0.155, 0.50, 0.205, 0.68), accent=True, width=2)
    p.rect((0.115, 0.555, 0.245, 0.615), accent=True, width=2)
    # Curved life-after-crisis pathway.
    route = [(0.24, 0.74), (0.39, 0.62), (0.50, 0.68), (0.64, 0.49), (0.80, 0.56), (0.93, 0.36)]
    p.line(route, accent=True, width=4)
    for x, y in route:
        p.ellipse((x - 0.018, y - 0.018, x + 0.018, y + 0.018), accent=True, width=2, fill="paper")
    # Book / skills.
    p.line([(0.46, 0.34), (0.52, 0.30), (0.58, 0.34), (0.58, 0.47), (0.52, 0.43), (0.46, 0.47), (0.46, 0.34)], width=2)
    p.line([(0.52, 0.30), (0.52, 0.43)], accent=True, width=2)
    # Work / briefcase.
    p.rect((0.67, 0.29, 0.80, 0.41), width=2, fill="paper", radius=4)
    p.rect((0.71, 0.25, 0.76, 0.30), accent=True, width=2)
    # Tree / future.
    p.line([(0.90, 0.59), (0.90, 0.83)], width=4)
    for cx, cy, r in ((0.84, 0.57, 0.07), (0.91, 0.52, 0.08), (0.97, 0.58, 0.06)):
        p.ellipse((cx - r, cy - r, cx + r, cy + r), accent=True, width=2, fill="paper")
    p.hatch_rect((0.05, 0.20, 0.98, 0.86), spacing=0.05, slope=1)


def _oil_market(p: Plate):
    # Pumpjack at left.
    p.line([(0.08, 0.74), (0.24, 0.33)], width=4)
    p.line([(0.13, 0.59), (0.34, 0.59)], width=4)
    p.line([(0.21, 0.37), (0.45, 0.31)], accent=True, width=5)
    p.line([(0.42, 0.31), (0.52, 0.40)], accent=True, width=3)
    p.line([(0.49, 0.39), (0.49, 0.70)], accent=True, width=2)
    p.ellipse((0.46, 0.68, 0.52, 0.75), accent=True, width=2)
    # Oil barrel.
    p.rect((0.52, 0.53, 0.64, 0.77), width=3, fill="paper", radius=5)
    p.ellipse((0.52, 0.50, 0.64, 0.57), accent=True, width=2)
    p.ellipse((0.52, 0.73, 0.64, 0.80), accent=True, width=2)
    p.line([(0.525, 0.62), (0.635, 0.62)], soft=True)
    p.line([(0.525, 0.68), (0.635, 0.68)], soft=True)
    # Tanker / route risk.
    p.polygon([(0.65, 0.65), (0.90, 0.65), (0.96, 0.72), (0.69, 0.72)], width=3, fill="paper")
    p.rect((0.72, 0.53, 0.84, 0.65), accent=True, width=2, fill="paper")
    for x in (0.74, 0.78, 0.82):
        p.rect((x, 0.48, x + 0.025, 0.53), width=1, fill="paper")
    # Price line / warning spike.
    pts = [(0.48, 0.35), (0.57, 0.31), (0.64, 0.39), (0.71, 0.26), (0.79, 0.30), (0.91, 0.12)]
    p.line(pts, accent=True, width=4)
    _arrow_head(p, pts[-2], pts[-1], accent=True, width=4)
    # Inflation ripples.
    for r in (0.07, 0.11, 0.15):
        b = p.box(0.82 - r, 0.34 - r, 0.82 + r, 0.34 + r)
        p.draw.arc(b, 205, 335, fill=p.ink_soft, width=2)
    p.hatch_rect((0.05, 0.10, 0.98, 0.84), spacing=0.05, slope=-1)


DRAWERS = {
    "casefile_system": _casefile_system,
    "water_infrastructure": _water_infrastructure,
    "river_monitoring": _river_monitoring,
    "mineworker_claims": _mineworker_claims,
    "care_pathway": _care_pathway,
    "oil_market": _oil_market,
}


def _asset_plate(spec: dict, accent, opacity: float) -> Image.Image:
    path = (PROJECT_ROOT / spec["path"]).resolve()
    source = Image.open(path).convert("RGB")
    box = [int(v) for v in spec["box"]]
    w, h = box[2] - box[0], box[3] - box[1]
    # Cover-resize without distortion.
    scale = max(w / source.width, h / source.height)
    rw, rh = max(1, int(source.width * scale)), max(1, int(source.height * scale))
    source = source.resize((rw, rh), Image.Resampling.LANCZOS)
    left, top = (rw - w) // 2, (rh - h) // 2
    source = source.crop((left, top, left + w, top + h))

    tint = str(spec.get("tint", "ink_accent")).lower()
    gray = ImageOps.grayscale(source)
    if tint == "accent":
        coloured = ImageOps.colorize(gray, black=accent, white=PAPER)
    elif tint == "original":
        coloured = source
    else:
        coloured = ImageOps.colorize(gray, black=INK, white=PAPER)

    # Paper-like transparency: darker source marks survive, highlights disappear.
    alpha = ImageOps.invert(gray).point(lambda v: int(v * opacity * 0.72))
    rgba = coloured.convert("RGBA")
    rgba.putalpha(alpha)
    return rgba


def apply_context_art(img: Image.Image, accent, spec: dict | None, *, seed: int = 0, stage: str = "background") -> bool:
    """Composite contextual art behind exact foreground typography/layout.

    `source=procedural` is deterministic and costs nothing. `source=asset` is the
    future hook for local RTX/NVIDIA/generated or manually approved illustration
    files stored under assets/. Both share the same box/opacity contract.
    """
    if spec in (None, {}):
        return False
    validate_context_art_spec(spec)
    stage = str(stage).strip().lower()
    ensure(stage in {"background", "foreground"}, "context art stage must be background or foreground.")
    requested_layer = str(spec.get("layer", "background")).strip().lower()
    if requested_layer != stage:
        return False
    source = str(spec.get("source", "procedural")).strip().lower()
    opacity = float(spec.get("opacity", 0.62))
    x0, y0, x1, y1 = [int(v) for v in spec["box"]]

    if source == "asset":
        plate_img = _asset_plate(spec, accent, opacity)
    else:
        kind = str(spec["kind"]).strip().lower()
        plate = Plate((x0, y0, x1, y1), accent, opacity, _stable_seed(kind, seed, x0, y0, x1, y1))
        DRAWERS[kind](plate)
        plate.distress(count=max(80, int((plate.w * plate.h) / 2400)))
        plate_img = plate.image

    # Protect exact foreground labels/boxes. Exclusions use absolute slide
    # coordinates so the episode manifest can shield typography while allowing
    # the illustration to remain visible in gutters and negative space.
    exclusions = spec.get("exclusions", [])
    if exclusions:
        alpha = plate_img.getchannel("A")
        ad = ImageDraw.Draw(alpha)
        for ex in exclusions:
            ex0, ey0, ex1, ey1 = [int(v) for v in ex]
            lx0, ly0 = max(0, ex0 - x0), max(0, ey0 - y0)
            lx1, ly1 = min(x1 - x0, ex1 - x0), min(y1 - y0, ey1 - y0)
            if lx0 < lx1 and ly0 < ly1:
                ad.rectangle((lx0, ly0, lx1, ly1), fill=0)
        plate_img.putalpha(alpha)

    # Optional wash keeps art coherent with the cream paper and prevents it from
    # competing with exact foreground copy.
    if bool(spec.get("paper_wash", True)):
        wash = Image.new("RGBA", plate_img.size, (*PAPER, 34))
        plate_img = Image.alpha_composite(plate_img, wash)

    img.paste(plate_img, (x0, y0), plate_img)
    return True
