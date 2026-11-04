"""R2 immutable exact-byte canon for the approved 4 November 2026 Drive assets.

Values were SHA-256 computed from the original Google Drive raw PNG bytes,
not screenshots, generated substitutes or the historical JPEG portrait set.
The data lives in code, not uploaded into a public repository or test fixture.
Changes require an explicit rehydration and governance review.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from .v3_readiness import V3_PORTRAIT_IDS

# slug -> (approved Drive filename, SHA-256 of its raw PNG bytes).
PORTRAIT_CANON = {
    "nora": ("Nora_CANONICAL_PANELIST.png", "9a82adee1f10515e8e97108579fb2f646debdc697995efbe8e223c348650600c"),
    "diane_sterling": ("Diane_Sterling_CANONICAL_PANELIST.png", "9189e6aea9e54d1a61a4e9e570e6f466866eda342ef0e6025975fd4f97cc9ab0"),
    "johan_vosloo": ("Johan_Vosloo_CANONICAL_PANELIST.png", "744877f02e56db4d07ca9f9845c1bcfa415bac73f18159f25e19073b3438882b"),
    "kai_patel": ("Kai_Patel_CANONICAL_PANELIST.png", "9b62bdcbee18842edb8217ff9643d8743f8b1351978a46b34db3ff7cc83e035f"),
    "thabo_mokoena": ("Thabo_Mokoena_CANONICAL_PANELIST.png", "5ddfa59641c2cfccd1a40bc974da70e03325603296e98fe997d1c8c4d79f1f4e"),
    "amari_ndlovu": ("Amari_Ndlovu_CANONICAL_PANELIST.png", "0eccf1164eb8dbfc7ec1c81a5b2f8c5ffabb19236965f9c85aa139296a0ffee4"),
}
# Only the actual Ep128 images fetched and visually inspected for the R2
# compositor qualification. More refs require independent inspection and pinning.
EP128_VERIFIED_REFERENCES = {
    "1u6Fux5vvIJHRzgnnZ_Yrr-TabpZlvQeY": "86a78988f3b1243b277a2fc737c33a207c3701ea3a9284f06ca918c443513e72",  # Slide 01
    "1paH71uL8n5R9r8e-s4LtWtwa0Txrzo62": "f4baf9191820482e649339cdd73ab5761a453c0b06e5d3c52ac777b6b80ef0ee",  # Slide 09
}


class CanonMismatch(ValueError):
    """Exact source bytes differ from the pinned Drive master."""


def verify_portrait_bytes(slug: str, drive_id: str, data: bytes) -> str:
    """Reject all noncanonical portrait bytes before decoding/compositing."""
    item = PORTRAIT_CANON.get(slug)
    if item is None or V3_PORTRAIT_IDS.get(slug) != drive_id:
        raise CanonMismatch(f"Unapproved panelist identity reference: {slug}.")
    if not isinstance(data, bytes) or sha256(data).hexdigest() != item[1]:
        raise CanonMismatch(f"Canonical bytes do not match approved {slug} portrait.")
    return item[1]


def verify_reference_bytes(drive_id: str, data: bytes) -> str:
    expected = EP128_VERIFIED_REFERENCES.get(drive_id)
    if expected is None:
        raise CanonMismatch("Ep128 style reference has not been hydrated and hash-pinned for R2.")
    if not isinstance(data, bytes) or sha256(data).hexdigest() != expected:
        raise CanonMismatch("Ep128 visual style reference does not match its original approved bytes.")
    return expected
