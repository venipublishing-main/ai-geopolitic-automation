"""Offline tests: generic fixture assets only, no private portraits or network."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import io
import json

import pytest
from PIL import Image, ImageDraw

from src import v3_canon_assets
from src.episode_manifest_v2 import COPY_FIELDS, LIST_FIELDS
from src.v3_compositor import _font
from src.v3_scene_enrichment import render_enriched_hero, EnrichmentError, SIZE
from src.v3_takeaway_rail import draw_takeaway_rail, TakeawayFitError
from src.v3_enriched_proof import LOCKED_PORTRAITS, render_enriched_proofs
from src.v3_readiness import V3_ACCENTS, V3_MANIFEST_BEGIN, V3_MANIFEST_END


def slide(family='layered cartographic evidence'):
    return {'preferred_visual_reasoning_family':family,
            'essential_labels':(['SOVEREIGNTY','SECURITY ACCESS','TEST VOTE','PENDING']
                if family=='layered cartographic evidence' else
                ['LEGAL','ACCESS','SCREENING','VALUE','FUTURE CHOICE'])}


@pytest.mark.parametrize('family', ['layered cartographic evidence','concentric sovereignty wheel'])
def test_recipe_repeats_exactly_and_preserves_source(family):
    spec=slide(family); initial=deepcopy(spec)
    a,ra=render_enriched_hero(spec); b,rb=render_enriched_hero(spec)
    assert a==b and ra==rb and spec==initial
    with Image.open(io.BytesIO(a)) as im:
        assert im.size==SIZE and im.format=='PNG'
    assert ra['original_label_strings']==spec['essential_labels']
    assert ra['new_factual_claims'] is False
    assert ra['geographic_survey_accuracy_claimed'] is False
    assert ra['external_image_provider_calls']==0


@pytest.mark.parametrize('change', [
    {'preferred_visual_reasoning_family':'unreviewed_dashboard'},
    {'essential_labels':[]}, {'essential_labels':'not a list'},
    {'essential_labels':['A','B']}, {'essential_labels':['A','B',2,'C']},
])
def test_wrong_source_structure_fails_closed(change):
    value=slide();value.update(change)
    with pytest.raises(EnrichmentError): render_enriched_hero(value)


def test_three_takeaways_exact_no_added_cards():
    im=Image.new('RGBA',(1080,1350),(245,242,234,255))
    ideas=[{'idea':v} for v in ['First exact source idea','Second precise idea','Third unchanged idea']]
    before=deepcopy(ideas)
    receipt=draw_takeaway_rail(im,ideas,_font,(51,107,163),headline_bottom=309)
    assert receipt['source_count']==3 and receipt['copy_rewritten'] is False
    assert [v['source_text'] for v in receipt['ideas']]==[x['idea'] for x in before]
    assert ideas==before
    assert im.getpixel((55,380))==(245,242,234,255)
    assert receipt['ideas'][0]['idea_sha256']==sha256(before[0]['idea'].encode()).hexdigest()


@pytest.mark.parametrize('ideas,bottom', [([],300),([{'idea':'x'}]*3,320),
    ([{'idea':'x'*500}]*3,300)])
def test_takeaway_fit_errors_cannot_be_silently_shortened(ideas,bottom):
    im=Image.new('RGBA',(1080,1350),'white')
    with pytest.raises(TakeawayFitError):
        draw_takeaway_rail(im,ideas,_font,(51,107,163),headline_bottom=bottom)


def test_positioning_remains_the_user_reviewed_baseline():
    assert LOCKED_PORTRAITS=={
        1:(('nora',(63,421,504,983)),),
        9:(('nora',(52,435,373,985)),('amari_ndlovu',(378,435,691,985))),
    }


def _fixture_manifest():
    slides=[]
    for number in range(1,11):
        x={key:'Source fixture wording' for key in COPY_FIELDS}
        x.update({key:['Exact source value'] for key in LIST_FIELDS})
        x.update(slide('concentric sovereignty wheel' if number==9 else
                       'layered cartographic evidence'))
        cast=['nora','amari_ndlovu'] if number==9 else ['nora']
        x.update(slide_number=number,panelists=cast,
                 headline='SOURCE FIXTURE',subheadline='Exact historical source only.',
                 main_visual_phrase='CHOICES AND RULES',
                 takeaway_ideas=[{'idea':x} for x in ['Source one','Source two','Source three']],
                 accent_colours={s:V3_ACCENTS[s] for s in cast},
                 pairing_mode='SYNTHESIS_COMPLEMENTARY' if number==9 else None,
                 central_relationship='synthesize' if number==9 else None,
                 shared_ground='Shared source' if number==9 else None,
                 why_dual='Distinct perspectives' if number==9 else None,
                 panelist_contributions={s:'Source lens' for s in cast} if number==9 else {})
        slides.append(x)
    return {'schema_version':2,'episode_id':'Ep136','episode_title':'SYNTHETIC TEST ONLY',
            'production_date_sast':'2026-11-04','source_rnd_date_sast':'2026-11-04',
            'archive_destination':'Ep136-4November2026','archive_folder_id':'test_archive_id',
            'slides':slides}


def test_local_runner_emits_two_nonpublishable_proofs_and_source_receipts(tmp_path,monkeypatch):
    assets=tmp_path/'assets';assets.mkdir()
    # Patch ONLY test-local expected hashes for clearly fake, synthetic assets.
    for n,slug in enumerate(('nora','amari_ndlovu')):
        im=Image.new('RGBA',(500,500),(0,0,0,0))
        ImageDraw.Draw(im).ellipse((30,20,470,490),fill=(70+n*60,40,120,255))
        buf=io.BytesIO();im.save(buf,format='PNG');data=buf.getvalue()
        filename=v3_canon_assets.PORTRAIT_CANON[slug][0]
        (assets/filename).write_bytes(data)
        monkeypatch.setitem(v3_canon_assets.PORTRAIT_CANON,slug,
                            (filename,sha256(data).hexdigest()))
    for n,ref_id in ((1,'1u6Fux5vvIJHRzgnnZ_Yrr-TabpZlvQeY'),
                     (9,'1paH71uL8n5R9r8e-s4LtWtwa0Txrzo62')):
        im=Image.new('RGB',(500,500),(240,239,230));buf=io.BytesIO();im.save(buf,'PNG')
        (assets/f'Ep128_Slide{n:02d}of10.png').write_bytes(buf.getvalue())
        monkeypatch.setitem(v3_canon_assets.EP128_VERIFIED_REFERENCES,ref_id,
                            sha256(buf.getvalue()).hexdigest())
    original={p.name:sha256(p.read_bytes()).hexdigest() for p in assets.iterdir()}
    text=V3_MANIFEST_BEGIN+'\n'+json.dumps(_fixture_manifest())+'\n'+V3_MANIFEST_END
    output=tmp_path/'proofs'
    result=render_enriched_proofs(text,assets,output)
    assert [p['slide'] for p in result]==[1,9]
    for p in result:
        q=p['receipt']['compositor']
        assert q['size']==[1080,1350]
        assert all(q['opaque_source_pixels_verified'].values())
        assert q['takeaway_coverage']['source_count']==3
        assert p['receipt']['render']['render_integrity_gate']=='HUMAN_REVIEW_REQUIRED'
        assert p['receipt']['render']['publication_authorised'] is False
    assert {p.name:sha256(p.read_bytes()).hexdigest() for p in assets.iterdir()}==original
    with pytest.raises(ValueError,match='empty proof'):
        render_enriched_proofs(text,assets,output)
