"""R2.2d deterministic engraving studies; no network, providers or new facts.

Two explicit visual-family recipes enrich the historical test harness only.
Source labels/claims stay in the Manifest. Coordinates are based on the
user-reviewed R2.2c proof; the original source portraits are not touched.
These schematic reliefs are not surveyed geography or quantitative data.
"""
from __future__ import annotations

import io
import math
import random
from hashlib import sha256

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

SIZE = (984, 599)
PAPER = (245, 242, 234)
INK = (35, 39, 39)
BLUE = (51, 107, 163)
GOLD = (139, 110, 44)
FAMILIES = {"layered cartographic evidence", "concentric sovereignty wheel"}


class EnrichmentError(ValueError):
    pass


def _mix(a, b, t):
    return tuple(round(x * (1 - t) + y * t) for x, y in zip(a, b))


def _font(size, bold=False):
    names = (["/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
              "C:/Windows/Fonts/arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else
             ["/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
              "C:/Windows/Fonts/arial.ttf", "DejaVuSans.ttf"])
    for name in names:
        try:
            return ImageFont.truetype(name, round(size))
        except OSError:
            continue
    raise EnrichmentError("Missing readable font for enrichment study.")


class _Plate:
    """Two-times supersampled deterministic print-like line drawing."""
    scale = 2

    def __init__(self, seed):
        self.im = Image.new("RGB", tuple(v * self.scale for v in SIZE), PAPER)
        self.d = ImageDraw.Draw(self.im)
        self.rng = random.Random(seed)
        # Sparse fibre, not a colour wash or a full-page decorative grid.
        for _ in range(14000):
            x = self.rng.randrange(self.im.width)
            y = self.rng.randrange(self.im.height)
            n = self.rng.randrange(-8, 7)
            self.d.point((x, y), fill=tuple(max(0, min(255, c+n)) for c in PAPER))

    def line(self, pts, colour=INK, width=1):
        self.d.line([(round(x*2), round(y*2)) for x, y in pts],
                    fill=colour, width=max(1, round(width*2)))

    def poly(self, pts, fill, outline=INK, width=1):
        self.d.polygon([(round(x*2), round(y*2)) for x, y in pts], fill=fill)
        if outline is not None:
            self.line(pts + [pts[0]], outline, width)

    def ellipse(self, box, fill=None, outline=INK, width=1):
        self.d.ellipse(tuple(round(v*2) for v in box), fill=fill,
                       outline=outline, width=max(1, round(width*2)))

    def text(self, xy, text, size=16, colour=INK, bold=False, anchor="la"):
        self.d.text(tuple(round(v*2) for v in xy), text,
                    font=_font(size*2, bold), fill=colour, anchor=anchor)

    def finish(self):
        return self.im.resize(SIZE, Image.Resampling.LANCZOS)


def _shared_environment(p):
    # Measured architectural baseline and receding floor strokes. They are
    # illustration, not charts/data axes. They remain behind portrait pixels.
    soft = _mix(INK, PAPER, .76)
    faint = _mix(INK, PAPER, .88)
    for i in range(15):
        x = 20 + i*70
        p.line([(x, 598), (490 + (x-490)*.52, 400)], faint, .6)
    for y in (414, 431, 454, 484, 524, 575):
        p.line([(10, y), (975, y)], faint, .6)
    for x in range(14, 980, 20):
        p.line([(x, 587), (x+12, 580)], soft, .6)
    # Light cartographic guilloche around/behind the canonical apertures.
    for offset in range(10):
        pts = [(x, 302 + offset*5 + 11*math.sin(x/130 + offset*.3))
               for x in range(5, 980, 6)]
        p.line(pts, faint, .45)


def _label(p, xy, text, width, colour=INK):
    # Exact essential-label text only; no truncation or ad hoc abbreviations.
    for size in range(17, 11, -1):
        if p.d.textlength(text, font=_font(size*2, True)) <= width*2:
            p.text(xy, text, size, colour, True)
            return
    raise EnrichmentError("Exact source scene label cannot fit.")


def _etched_plaque(p, box, accent):
    x0, y0, x1, y1 = box
    # A drawn physical surface planned BEFORE exact glyph compositing.
    p.poly([(x0+6, y0+8), (x1+6, y0+8), (x1+6, y1+8), (x0+6, y1+8)],
           _mix(accent, PAPER, .8), _mix(INK, PAPER, .5), .7)
    p.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
           PAPER, _mix(INK, PAPER, .45), 1.1)
    p.line([(x0+7, y0+7), (x1-7, y0+7)], _mix(accent, PAPER, .25), .8)
    p.line([(x0+7, y1-7), (x1-7, y1-7)], _mix(accent, PAPER, .5), .65)
    for x in range(round(x0+8), round(x1-4), 9):
        p.line([(x, y1+1), (x+5, y1+7)], _mix(INK, PAPER, .4), .7)
    for x, y in ((x0+8, y0+16), (x1-8, y0+16), (x0+8, y1-16), (x1-8, y1-16)):
        p.ellipse((x-1.8, y-1.8, x+1.8, y+1.8), PAPER, _mix(accent, PAPER, .2), .7)


def _greenland_plate(p, labels):
    _shared_environment(p)
    # Schematic outline inherited from the earlier proof, now articulated
    # with printed relief cuts. Not a surveyed or legally authoritative map.
    raw = [(708,36),(759,43),(799,72),(826,104),(846,126),(835,162),
           (861,193),(852,226),(825,238),(820,278),(788,297),(752,285),
           (736,310),(698,295),(681,266),(663,241),(630,213),(632,175),
           (650,145),(649,110),(670,88),(675,58)]
    shape = []
    for j, (a,b) in enumerate(zip(raw, raw[1:]+raw[:1])):
        shape.append(a)
        # Incised coastline detail adds engraving texture, not new locations.
        if j % 2 == 0:
            mx, my = (a[0]+b[0])/2, (a[1]+b[1])/2
            dx, dy = b[0]-a[0], b[1]-a[1]
            length = max(1, math.hypot(dx,dy))
            shape.extend([(mx+dy/length*4,my-dx/length*4),
                          (mx-dy/length*2,my+dx/length*2)])
    # Fine architectural registration, clipped away from label areas.
    for y in range(62, 328, 30):
        p.line([(680,y),(932,y-8)], _mix(BLUE,PAPER,.85), .55)
    for dy, tone in ((33,_mix(BLUE,PAPER,.2)),(19,_mix(BLUE,PAPER,.65)),(0,PAPER)):
        poly = [(x,y+dy) for x,y in shape]
        p.poly(poly,tone,INK,1.5)
        if dy:
            for j in range(0,len(shape),2):
                x,y=shape[j]
                p.line([(x,y+dy),(x-2,y+dy+5)],_mix(INK,PAPER,.25),.6)
    # Masked cartographic contours and small hachure strokes.
    mask=Image.new('L',p.im.size,0)
    md=ImageDraw.Draw(mask)
    md.polygon([(round(x*2),round(y*2)) for x,y in shape], fill=255)
    ink=Image.new('RGB',p.im.size,PAPER); di=ImageDraw.Draw(ink)
    for y in range(15,334,9):
        pts=[]
        for x in range(625,870,3):
            yy=y+12*math.sin((x-628)/48)+5*math.sin(x/21+y/70)
            pts.append((x*2,round(yy*2)))
        di.line(pts,fill=_mix(INK,PAPER,.23 if y%27==6 else .57),width=1)
    for _ in range(1100):
        x=p.rng.randrange(630,863); y=p.rng.randrange(35,312)
        di.line((x*2,y*2,(x+2)*2,(y-3)*2),fill=_mix(INK,PAPER,.64),width=1)
    # Hand-etched relief ridges, symbolic rather than measured elevations.
    for ridge in range(7):
        xbase=667+ridge*25
        pts=[]
        for y in range(64,282,5):
            x=xbase+9*math.sin(y/29+ridge)+3*math.sin(y/9)
            pts.append((round(x*2),y*2))
            if y % 10 == 4:
                for side in (-1,1):
                    length=8+4*math.sin(y/25+ridge)
                    di.line((round(x*2),y*2,round((x+side*length)*2),(y+7)*2),
                            fill=_mix(INK,PAPER,.55),width=1)
        di.line(pts,fill=_mix(INK,PAPER,.3),width=1)
    p.im.paste(ink,(0,0),mask);p.d=ImageDraw.Draw(p.im)
    p.line(shape+[shape[0]],INK,1.3)
    # Two scale-independent callouts identify the two conceptual layers.
    _label(p,(482,115),labels[0],132,INK)
    _label(p,(482,240),labels[1],132,BLUE)
    p.line([(482,140),(610,140),(645,165)],INK,.9)
    p.line([(482,263),(620,263),(677,284)],BLUE,1.0)
    p.ellipse((640,161,647,168),PAPER,INK,1)
    p.ellipse((673,280,680,287),BLUE,BLUE,1)
    # A raised drafting table gives the hero an analytical setting.
    p.poly([(564,329),(918,329),(954,348),(535,348)],PAPER,INK,1.1)
    p.poly([(535,348),(954,348),(954,359),(535,359)],_mix(INK,PAPER,.83),INK,.8)
    for x in range(539,950,7):
        p.line([(x,351),(x+5,357)],_mix(INK,PAPER,.48),.55)
    p.text((901,35),'SCHEMATIC',11,_mix(INK,PAPER,.45),anchor='ra')
    # Keep the approved phrase aperture (global 606,755..1006,969) clear.
    _etched_plaque(p,(552,365,965,579),BLUE)
    return "schematic_relief_and_access_strata"


def _arc_text(p, text, centre, radius, size, colour):
    font=_font(size*2,True)
    advances=[p.d.textlength(c,font=font)/2 for c in text]
    total=sum(advances)
    angle=-math.pi/2-total/(2*radius)
    for c,w in zip(text,advances):
        angle += w/(2*radius)
        x=centre[0]+radius*math.cos(angle);y=centre[1]+radius*math.sin(angle)
        tile=Image.new('RGBA',(96,96),(0,0,0,0))
        td=ImageDraw.Draw(tile)
        td.text((48,48),c,font=font,fill=(*colour,255),anchor='mm')
        tile=tile.rotate(-math.degrees(angle)-90,resample=Image.Resampling.BICUBIC)
        p.im.paste(tile,(round(x*2-48),round(y*2-48)),tile)
        angle += w/(2*radius)
    p.d=ImageDraw.Draw(p.im)


def _sovereignty_instrument(p,labels):
    _shared_environment(p)
    cx,cy=810,210
    # The same five concentric layers now form an engraved mechanical plate.
    # They do NOT imply numerical measurements or completed political steps.
    p.ellipse((cx-157,cy-146,cx+157,cy+173),_mix(INK,PAPER,.68),INK,1)
    for r in range(155,149,-2):
        p.ellipse((cx-r,cy-r,cx+r,cy+r),None,_mix(INK,PAPER,.45),.8)
    radii=(149,121,94,67,40)
    for j,r in enumerate(radii):
        col=BLUE if j%2==0 else GOLD
        p.ellipse((cx-r,cy-r,cx+r,cy+r),_mix(col,PAPER,.91),INK,1.05)
        p.ellipse((cx-r+3,cy-r+3,cx+r-3,cy+r-3),None,_mix(col,PAPER,.42),.7)
        # Tiny concentric ruled edges: physical printwork, not a new chart.
        for off in (8,10,12):
            p.ellipse((cx-r+off,cy-r+off,cx+r-off,cy+r-off),None,_mix(INK,PAPER,.68),.4)
    for i in range(80):
        a=math.tau*i/80
        r=155; length=8 if i%5==0 else 3
        p.line([(cx+r*math.cos(a),cy+r*math.sin(a)),
                (cx+(r+length)*math.cos(a),cy+(r+length)*math.sin(a))],
               INK if i%5==0 else _mix(INK,PAPER,.45), .65)
    for i in range(12):
        a=math.tau*i/12
        x,y=cx+142*math.cos(a),cy+142*math.sin(a)
        if y > cy-108:  # clear the lettering arcs
            p.ellipse((x-2.7,y-2.7,x+2.7,y+2.7),PAPER,INK,.75)
            p.line([(x-1.2,y+.8),(x+1.2,y-.8)],INK,.55)
    # Etched sector shadow and radial hatch marks give the five rings depth
    # without implying numeric quantities. Only the lower half is shaded,
    # keeping exact-source labels legible on the upper face of each ring.
    for ring,r in enumerate(radii):
        for i in range(55):
            a=math.pi*(.10+i/65)
            outer=r-4
            inner=max(18,r-18)
            p.line([(cx+inner*math.cos(a),cy+inner*math.sin(a)),
                    (cx+outer*math.cos(a+.014),cy+outer*math.sin(a+.014))],
                   _mix(INK,PAPER,.45+ring*.045),.5)
    # Labels are copied exactly, never generated as pseudo-lettering.
    for label,r,size in zip(labels,(137,109,82,55,27),(13,13,12,12,9)):
        _arc_text(p,label,(cx,cy),r,size,INK)
    p.ellipse((cx-13,cy-13,cx+13,cy+13),_mix(GOLD,PAPER,.8),INK,.9)
    p.line([(cx-9,cy),(cx+9,cy)],INK,.65)
    p.line([(cx,cy-9),(cx,cy+9)],INK,.65)
    # Schematic supports anchor the disc and reserve the approved lower plane.
    p.poly([(696,365),(929,365),(947,378),(679,378)],PAPER,INK,1)
    for x in (707,912):
        p.poly([(x,350),(x+11,350),(x+11,369),(x,369)],_mix(INK,PAPER,.8),INK,.7)
    _etched_plaque(p,(650,387,968,581),GOLD)
    return "five_linked_engraved_mechanical_rings"


def render_enriched_hero(slide: dict) -> tuple[bytes, dict]:
    """Closed two-family offline recipe; labels remain exactly source-derived."""
    family=slide.get('preferred_visual_reasoning_family')
    if family not in FAMILIES:
        raise EnrichmentError('No approved enrichment recipe for this visual family.')
    labels=slide.get('essential_labels')
    if (not isinstance(labels,list) or not all(isinstance(x,str) and x.strip() for x in labels)):
        raise EnrichmentError('Exact source labels are required.')
    is_map=family=='layered cartographic evidence'
    if len(labels)!=(4 if is_map else 5):
        raise EnrichmentError('Unexpected source label count; review the scene recipe.')
    p=_Plate(13601 if is_map else 13609)
    recipe=_greenland_plate(p,labels) if is_map else _sovereignty_instrument(p,labels)
    img=p.finish(); out=io.BytesIO();img.save(out,format='PNG')
    data=out.getvalue()
    return data, {
        'recipe':recipe, 'dimensions':list(SIZE), 'original_label_strings':labels,
        'content_source':'supplied_manifest_only', 'new_factual_claims':False,
        'procedural_schematic':True, 'geographic_survey_accuracy_claimed':False,
        'external_image_provider_calls':0, 'hero_sha256':sha256(data).hexdigest(),
        'visual_approval':'REQUIRED',
    }
