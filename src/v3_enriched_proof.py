"""Read-only R2.2d enrichment of historical Ep136 proofs, not daily production.

Original R2.2c portrait geometry, crops, font furniture and output dimensions
remain. Only the authored schematic artwork and source takeaway coverage are
extended. No network, external generation, GitHub upload or Drive write here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from PIL import __version__ as pillow_version

from .v3_historical_proof import _manifest_from_archive
from .v3_compositor import PortraitPlacement, R2SlidePlan, compose_r2_slide
from .v3_adaptive_layout import LetteringSurface
from .v3_canon_assets import PORTRAIT_CANON
from .v3_render_qc import audit_exported_png
from .v3_scene_enrichment import render_enriched_hero
from .v3_takeaway_rail import add_source_takeaways

# Exactly the user-reviewed R2.2c portrait positions/crops, not new layouts.
LOCKED_PORTRAITS = {
    1: (('nora',(63,421,504,983)),),
    9: (('nora',(52,435,373,985)),('amari_ndlovu',(378,435,691,985))),
}


def render_enriched_proofs(design_text: str, asset_dir: Path, output_dir: Path) -> list[dict]:
    manifest=_manifest_from_archive(design_text)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError('Use an empty proof directory; never overwrite previous assets.')
    output_dir.mkdir(parents=True,exist_ok=True)
    results=[]
    for number in (1,9):
        slide=manifest['slides'][number-1]
        placements=tuple(PortraitPlacement(slug,box,fit='cover')
                         for slug,box in LOCKED_PORTRAITS[number])
        single=number==1
        ref_id=('1u6Fux5vvIJHRzgnnZ_Yrr-TabpZlvQeY' if single else
                '1paH71uL8n5R9r8e-s4LtWtwa0Txrzo62')
        surface=(LetteringSurface((606,755,1006,969),'engraved',0,True) if single else
                 LetteringSurface((704,790,1009,972),'stamped',0,True))
        plan=R2SlidePlan(
            number,f'EP136-ENRICHMENT-READONLY-{number:02d}',
            slide['preferred_visual_reasoning_family'], placements, ref_id,
            background_human_free_reviewed=True,
            arrangement='portrait-left' if single else 'paired-synthesis',
            material_surface=surface,
        )
        hero,enrichment=render_enriched_hero(slide)
        portraits={slug:(asset_dir/PORTRAIT_CANON[slug][0]).read_bytes()
                   for slug in slide['panelists']}
        reference=(asset_dir/('Ep128_Slide01of10.png' if single else
                             'Ep128_Slide09of10.png')).read_bytes()
        composite=compose_r2_slide(manifest,plan,hero_png=hero,
                                  portrait_pngs=portraits,ep128_reference_png=reference)
        composite=add_source_takeaways(composite,slide)
        audit=audit_exported_png(composite.png_bytes,kind='carousel',
                                item_number=number,compositor_qc=composite.qc)
        if audit['render_integrity_gate']!='HUMAN_REVIEW_REQUIRED':
            raise ValueError('Enriched study must not automatically receive visual approval.')
        coverage=composite.qc['takeaway_coverage']
        if coverage['source_count']!=3:
            raise ValueError('Three exact source ideas are mandatory for this enrichment.')
        name=f'NONPUBLISHABLE_Ep136_Enriched{number:02d}_4x5.png'
        (output_dir/name).write_bytes(composite.png_bytes)
        receipt={'compositor':composite.qc,'enrichment':enrichment,'render':audit,
                 'runtime_pillow':pillow_version,'positioning_preserved':True,
                 'historical_source_date':'2026-11-04','engineering_only':True}
        (output_dir/name.replace('.png','.qc.json')).write_text(
            json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
        results.append({'slide':number,'file':name,'receipt':receipt})
    return results


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--design-text',type=Path,required=True)
    parser.add_argument('--asset-dir',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    a=parser.parse_args(argv)
    results=render_enriched_proofs(a.design_text.read_text(encoding='utf-8-sig'),
                                   a.asset_dir,a.output_dir)
    print(json.dumps({'proofs':[{'slide':p['slide'],'file':p['file'],
                               'status':p['receipt']['render']['render_integrity_gate']}
                              for p in results],
                      'external_image_provider_calls':0,'publishing_performed':False},indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
