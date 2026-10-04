"""Reviewed depiction vocabulary. Unknown concepts never acquire guessed ownership."""
from dataclasses import dataclass

GENERATOR_CONCRETE = "GENERATOR_CONCRETE"
COMPOSITOR_ABSTRACT = "COMPOSITOR_ABSTRACT"
HYBRID = "HYBRID"
OWNERS = {GENERATOR_CONCRETE, COMPOSITOR_ABSTRACT, HYBRID}
MARKS = {"condition_ring", "document_gate", "equal_link"}
PHYSICAL_ARCHITECTURE_CONCEPTS = {"MODEL","RACKS","COOLING","FIBRE","SUBSTATION","GRID","GENERATION","COMPUTE","TRANSMISSION"}


@dataclass(frozen=True)
class Depiction:
    ownership: str
    concrete_visual: str = ""
    compositor_mark: str = "condition_ring"


def concrete(text):
    return Depiction(GENERATOR_CONCRETE, text)


def hybrid(text, mark="condition_ring"):
    return Depiction(HYBRID, text, mark)


ABSTRACT = Depiction(COMPOSITOR_ABSTRACT)
# Exact reviewed concepts, independent of slide number or panelist. Visible
# names, numerical quantities, legal statuses and economic abstractions are
# always composed later; a hybrid names only its concrete evidence material.
VOCABULARY = {
    **dict.fromkeys(("NATIONAL AI RACE", ">$1BN", "5 YEARS", "MODEL", "6,800 MW", "COST ALLOCATION",
        "INCREMENTAL COST", "CROSS-SUBSIDY", "INVESTMENT RISK", "PROPOSED", "REVIEW", "NOT ENACTED",
        "CAPITAL", "TAX", "LOCAL RETENTION", "PRIORITY BUILD", "COST", "VALUE", "RULES", "TIME"), ABSTRACT),
    "PERMIT": Depiction(COMPOSITOR_ABSTRACT, compositor_mark="document_gate"),
    "PERMISSION": Depiction(COMPOSITOR_ABSTRACT, compositor_mark="document_gate"),
    "APPROVAL": Depiction(COMPOSITOR_ABSTRACT, compositor_mark="document_gate"),
    "LOCAL RULES": Depiction(COMPOSITOR_ABSTRACT, compositor_mark="document_gate"),
    "TRUST": Depiction(COMPOSITOR_ABSTRACT, compositor_mark="equal_link"),
    "LOCAL HOST": hybrid("a local settlement neighbouring physical computing infrastructure"),
    "LAND": concrete("physical terrain and the footprint of infrastructure"),
    "POWER": concrete("electricity transmission pylons and a power substation"),
    "ENERGY": concrete("electricity generation and transmission infrastructure"),
    "GRID": concrete("electricity transmission pylons and interconnected power lines"),
    "WATER": concrete("water reservoirs and physical supply pipes"),
    "LABOUR": concrete("workers maintaining physical infrastructure, no panelist likeness"),
    "JOBS": hybrid("workers constructing and maintaining infrastructure"),
    "SKILLS": hybrid("technicians working on physical computing equipment"),
    "EDUCATION": hybrid("a training workshop with physical technical equipment"),
    "RACKS": concrete("rows of computing server racks"),
    "COOLING": concrete("industrial cooling pipes and heat-exchange equipment"),
    "FIBRE": concrete("physical fibre-optic cables and conduit"),
    "SUBSTATION": concrete("an electrical substation with transformers"),
    "GENERATION": concrete("physical electricity-generating machinery"),
    "COMPUTE": concrete("computing equipment and server racks"),
    "REMOTE USERS": hybrid("distant settlements connected by physical communications infrastructure"),
    "NEW LOAD": hybrid("additional physical electricity demand from computing infrastructure"),
    "CONNECTION": concrete("physical electricity cabling linking infrastructure to the grid"),
    "TRANSMISSION": concrete("electricity transmission lines and pylons"),
    "FERC": hybrid("a public administrative building without signage", "document_gate"),
    "PJM": hybrid("electricity-grid infrastructure without branding"),
    "EXISTING CUSTOMERS": hybrid("homes and businesses connected to electricity infrastructure"),
    "RATEPAYER": hybrid("homes and businesses connected to electricity infrastructure"),
    "LOCAL AUTHORITY": hybrid("a local civic building without signage", "document_gate"),
    "CAPE TOWN": concrete("Cape Town coastal urban topography with Table Mountain"),
    "KING AIR INDUSTRIA": hybrid("an industrial development site within a Cape Town urban landscape"),
    "~170 MW PROPOSED": hybrid("an unbuilt proposed data-centre site, never imply completed operation"),
    "CHIPS": concrete("physical semiconductor components"),
}


def reviewed_depiction(label):
    try:
        return VOCABULARY[label]
    except KeyError:
        raise ValueError("SEMANTIC_OWNERSHIP_UNKNOWN") from None


VISUAL_BRIEFS = {
    "layered_system": "{conditions} equal-status supporting conditions distributed across ONE COHERENT TEXT-FREE EDITORIAL ILLUSTRATION of institutional and physical data-centre hosting material. Balanced system; no visual ranking. The analytical framework is constructed later by the compositor, not drawn as a finished layered diagram.",
    "physical_stack": "One coherent text-free editorial illustration of genuinely physical computing architecture and its material support infrastructure. Physical equipment relationships, not a pyramid or infographic page.",
    "allocation_flow": "One coherent text-free editorial illustration of local infrastructure, productive work and physical connections through which investment can support a host community. Economic allocation logic is composed later, not an illustrated scorecard.",
    "regional_pathway": "One coherent text-free editorial illustration of regional geography and physical infrastructure around a proposed urban data-centre development. Geographic continuity and resource connections, not a diagram page or decorative continent silhouette.",
    "system_map": "One coherent text-free editorial illustration of computing infrastructure embedded in its local material and institutional surroundings. Relationships are illustrated through a shared scene, not an infographic.",
    "evidence_dossier": "One coherent text-free editorial illustration of physical institutional and infrastructure evidence material, without document lettering, cards or a dossier page.",
    "dependency_chain": "One coherent text-free editorial illustration of connected material infrastructure and its physical dependencies, without a diagram page or labelled sequence.",
    "institutional_sequence": "One coherent text-free editorial illustration of civic and physical infrastructure evidence material. Legal stages and statuses are compositor-owned, not lettering or a maturity ladder.",
    "feedback_loop": "One coherent text-free editorial illustration of physical infrastructure and monitoring equipment, without screens, dashboards or a labelled cycle.",
    "comparison_field": "One coherent text-free editorial illustration of contrasting physical infrastructure situations within a shared scene, without charts or evidence cards.",
    "decision_tree": "One coherent text-free editorial illustration of civic and physical infrastructure material. Decision logic is compositor-owned, not a tree diagram or flowchart.",
}

DEPICTION_GUARDS = {
    "layered_system": ("Equal conditions, not an official ranked industry standard; no pyramid, hierarchy, staircase, funnel or pentagon.",),
    "regional_pathway": ("Proposed development, not fully built or operating; no invented project capacity figures or signage.",),
    "allocation_flow": ("No invented job, tax or revenue quantities; no dollar signs or stock handshake imagery.",),
}


def visual_brief_for(family, count):
    if family not in VISUAL_BRIEFS or type(count) is not int or not 1 <= count <= 8:
        raise ValueError("VISUAL_ARGUMENT_UNREVIEWED")
    word=("One","Two","Three","Four","Five","Six","Seven","Eight")[count-1]
    return VISUAL_BRIEFS[family].format(conditions=word)
