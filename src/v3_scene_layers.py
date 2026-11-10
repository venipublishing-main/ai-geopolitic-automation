"""R2.2 protected analytical foreground overlay for authored v3.1 scenes.

The optional transparent foreground contains *illustration linework*, not a
person, substitute portrait, or generated text. Its alpha is automatically
clipped around every actual canonical portrait silhouette to preserve the
scaled source portrait pixels exactly. This is an engineering building block,
not an automatic premium visual/style approval.
"""
from __future__ import annotations

import io
from PIL import Image, ImageChops, UnidentifiedImageError


class SceneLayerError(ValueError):
    """A proposed foreground would violate an R2 scene safety constraint."""


def prepare_foreground_layer(png: bytes, expected_size: tuple[int, int]) -> Image.Image:
    if not isinstance(png, bytes) or not (0 < len(png) <= 12 * 1024 * 1024):
        raise SceneLayerError("Missing or oversized authored foreground PNG.")
    try:
        with Image.open(io.BytesIO(png)) as im:
            if im.format != "PNG" or im.mode not in ("RGBA", "LA", "P"):
                raise SceneLayerError("Foreground artwork requires actual transparent PNG source.")
            if im.size != expected_size:
                raise SceneLayerError("Foreground must exactly match the hero aperture; never stretch.")
            im = im.convert("RGBA")
            extrema = im.getchannel("A").getextrema()
            if extrema[0] != 0 or extrema[1] == 0:
                raise SceneLayerError("Foreground needs useful painted marks and genuine transparent regions.")
            return im
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise SceneLayerError("Foreground PNG cannot be decoded.") from exc


def protect_canonical_pixels(
    foreground: Image.Image, portrait_occupancy: Image.Image
) -> tuple[Image.Image, int]:
    """Remove EVERY foreground alpha pixel over a visible portrait pixel.

    Occupancy is from the actual resampled approved RGBA portrait, not a box
    mask. Hard threshold removes overlays even over semi-transparent edges.
    """
    if foreground.mode != "RGBA" or portrait_occupancy.mode != "L":
        raise SceneLayerError("Foreground/portrait protection modes must be RGBA/L.")
    if foreground.size != portrait_occupancy.size:
        raise SceneLayerError("Foreground and portrait occupancy sizes differ.")
    protect = portrait_occupancy.point(lambda value: 255 if value else 0)
    alpha = foreground.getchannel("A")
    clipped = ImageChops.subtract(alpha, protect)
    protected_count = sum(1 for value in protect.getdata() if value)
    result = foreground.copy()
    result.putalpha(clipped)
    return result, protected_count
