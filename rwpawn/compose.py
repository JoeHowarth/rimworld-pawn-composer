from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Dict, Tuple

from PIL import Image

from .assets import (
    DIRECTIONS,
    collect_apparel_images,
    find_head,
    find_beard,
    find_body,
    find_hair,
    load_eyes,
)


def _composite(layers: Iterable[Image.Image], size=(128, 128)) -> Image.Image:
    base = Image.new("RGBA", size, (0, 0, 0, 0))
    for layer in layers:
        base.alpha_composite(layer)
    return base


def compose_preview(
    assets_root: Path,
    body_type: str,
    hair: str | None,
    beard: str | None,
    head: str | None,
    eyes: str | None,
    eyes_gender: str | None,
    apparels: List[str],
    directions: List[str] | None = None,
    body_offsets: dict[str, tuple[int, int]] | None = None,
    head_offsets: dict[str, tuple[int, int]] | None = None,
    hair_offsets_rel: dict[str, tuple[int, int]] | None = None,
    eyes_offsets_rel: dict[str, tuple[int, int]] | None = None,
) -> Image.Image:
    dirs = directions or ["north", "south", "east"]
    # Defaults: per-direction head offset, and relative offsets for hair/eyes w.r.t head
    default_head_offsets: Dict[str, Tuple[int, int]] = {"south": (0, -30), "north": (0, 0), "east": (0, 0)}
    default_hair_offsets_rel: Dict[str, Tuple[int, int]] = {"south": (0, 0), "north": (0, 0), "east": (0, 0)}
    # Convert prior absolute eyes offsets to relative-to-head by subtracting head defaults
    default_eyes_offsets_rel: Dict[str, Tuple[int, int]] = {
        "south": (0, -28 - default_head_offsets.get("south", (0, 0))[1]),
        "north": (0, -25 - default_head_offsets.get("north", (0, 0))[1]),
        "east": (0, -26 - default_head_offsets.get("east", (0, 0))[1]),
    }

    def get_off(d: str, provided: Dict[str, Tuple[int, int]] | None, defaults: Dict[str, Tuple[int, int]]) -> Tuple[int, int]:
        if provided and d in provided:
            return provided[d]
        if d in defaults:
            return defaults[d]
        return (0, 0)
    frames: List[Image.Image] = []
    for d in dirs:
        layers: List[Image.Image] = []

        body = find_body(assets_root, body_type, d)
        if body:
            if body_offsets and d in body_offsets:
                ox, oy = body_offsets[d]
                canvas = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
                canvas.alpha_composite(body, (ox, oy))
                layers.append(canvas)
            else:
                layers.append(body)

        # Head above body, below hair
        hd = find_head(assets_root, head, d)
        if hd:
            hx, hy = get_off(d, head_offsets, default_head_offsets)
            canvas = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
            canvas.alpha_composite(hd, (hx, hy))
            layers.append(canvas)

        buckets = collect_apparel_images(assets_root, apparels, body_type, d)

        # Layering: pants -> shirt -> outer -> belt -> hair -> beard -> headgear
        for key in ("pants", "shirt", "outer"):
            for img in buckets[key]:
                layers.append(img)

        for img in buckets["belt"]:
            layers.append(img)

        h = find_hair(assets_root, hair, d)
        if h:
            hx, hy = get_off(d, head_offsets, default_head_offsets)
            rx, ry = get_off(d, hair_offsets_rel, default_hair_offsets_rel)
            canvas = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
            canvas.alpha_composite(h, (hx + rx, hy + ry))
            layers.append(canvas)

        # Eyes overlay: center relative to head + per-direction relative delta
        ey = load_eyes(assets_root, eyes, eyes_gender)
        if ey:
            hx, hy = get_off(d, head_offsets, default_head_offsets)
            rx, ry = get_off(d, eyes_offsets_rel, default_eyes_offsets_rel)
            ex_abs = hx + rx
            ey_abs = hy + ry
            canvas = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
            x = 64 - ey.size[0] // 2 + ex_abs
            y = 64 - ey.size[1] // 2 + ey_abs
            canvas.alpha_composite(ey, (x, y))
            layers.append(canvas)

        b = find_beard(assets_root, beard, d)
        if b:
            layers.append(b)

        for img in buckets["headgear"]:
            layers.append(img)

        # Any uncategorized apparel renders above outer but below headgear
        for img in buckets["apparel"]:
            layers.append(img)

        frames.append(_composite(layers, (128, 128)))

    # stitch horizontally
    out = Image.new("RGBA", (128 * len(frames), 128), (0, 0, 0, 0))
    for i, fr in enumerate(frames):
        out.alpha_composite(fr, (i * 128, 0))
    return out
