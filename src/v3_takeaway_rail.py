"""Exact-source takeaway typography for reviewed free space in historical proofs.

Opt-in only: no universal three-box template. Uses the existing whitespace
above the hero; fails rather than moving any portrait or approved furniture.
"""
from __future__ import annotations

from hashlib import sha256
from PIL import ImageDraw


class TakeawayFitError(ValueError):
    pass


def draw_takeaway_rail(canvas, ideas, font_loader, accent, *, headline_bottom):
    if (not isinstance(ideas, list) or len(ideas) != 3 or
            any(not isinstance(x, dict) or not isinstance(x.get('idea'), str)
                or not x['idea'].strip() for x in ideas)):
        raise TakeawayFitError('Exactly three source takeaway ideas are required.')
    if headline_bottom > 315:
        raise TakeawayFitError('Takeaway rail would overlap the headline; review the layout.')
    draw=ImageDraw.Draw(canvas)
    receipts=[]
    for i,item in enumerate(ideas):
        copy=item['idea']; x=54+i*326; width=290
        chosen=None
        for size in (19,18,17):
            font=font_loader(size,'sans'); lines=[];current=''
            for word in copy.split():
                if draw.textlength(word,font=font)>width:
                    lines=['','',copy];break
                trial=(current+' '+word).strip()
                if current and draw.textlength(trial,font=font)>width:
                    lines.append(current); current=word
                else:
                    current=trial
            if current: lines.append(current)
            if len(lines)<=2:
                chosen=(font,lines,size);break
        if chosen is None:
            raise TakeawayFitError('Source takeaway does not fit; no truncation allowed.')
        font,lines,size=chosen
        # Open rule-and-type composition, not three enclosed infographic cards.
        draw.line((x,330,x,370),fill=accent,width=2)
        for j,line in enumerate(lines):
            draw.text((x+9,326+j*23),line,font=font,fill=(47,49,47))
        receipts.append({'idea_sha256':sha256(copy.encode('utf-8')).hexdigest(),
                         'source_text':copy,'box':[x,326,x+310,375],
                         'font_size':size,'line_count':len(lines)})
    return {'treatment':'open_source_evidence_rail','ideas':receipts,
            'source_count':3,'copy_rewritten':False}


def add_source_takeaways(composite, slide):
    """Add exact source ideas ONLY in the proven empty header rail.

    The original composer has already checked canonical opaque pixels. This
    wrapper independently verifies that every pixel outside the allowed rail
    is unchanged, so the identity proof remains valid for the new output.
    It binds a fresh QC receipt to the newly encoded PNG, never reuses its hash.
    """
    import io
    from copy import deepcopy
    from PIL import Image, ImageChops
    from .v3_compositor import R2Composite, _font, _fitted

    if sha256(composite.png_bytes).hexdigest()!=composite.qc.get('output_png_sha256'):
        raise TakeawayFitError('Base compositing receipt is not bound to the supplied PNG.')
    with Image.open(io.BytesIO(composite.png_bytes)) as source:
        if source.format!='PNG' or source.size!=(1080,1350) or source.mode!='RGB':
            raise TakeawayFitError('Require the validated original 4:5 RGB proof.')
        before=source.copy()
    after=before.copy(); d=ImageDraw.Draw(after)
    hf,ls,spacing=_fitted(d,slide['headline'],976,204,3,78,42,'headline')
    bottom=167+(len(ls)-1)*spacing+d.textbbox((0,0),ls[-1],font=hf)[3]
    accent_hex=slide['accent_colours'][slide['panelists'][0]]
    accent=tuple(int(accent_hex[i:i+2],16) for i in (1,3,5))
    receipt=draw_takeaway_rail(after,slide['takeaway_ideas'],_font,accent,
                              headline_bottom=bottom)
    difference=ImageChops.difference(before,after)
    # Ignore ONLY the deliberate rail and reject any change elsewhere,
    # including portraits, existing type, illustration and publication marks.
    difference.paste((0,0,0),(50,324,1030,378))
    if difference.getbbox() is not None:
        raise TakeawayFitError('Enrichment altered pixels outside its reserved rail.')
    buf=io.BytesIO();after.save(buf,format='PNG',optimize=False,compress_level=9)
    data=buf.getvalue();qc=deepcopy(composite.qc)
    qc.update(takeaway_coverage=receipt,
              pre_takeaway_output_sha256=sha256(composite.png_bytes).hexdigest(),
              outside_takeaway_rail_pixels_unchanged=True,
              output_png_sha256=sha256(data).hexdigest(),
              render_integrity_status='RENDER_QC_PENDING',publication_authorised=False)
    return R2Composite(data,qc)
