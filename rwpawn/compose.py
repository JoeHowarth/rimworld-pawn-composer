from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Dict, Tuple

from PIL import Image, ImageOps

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
    beard_offsets_rel: dict[str, tuple[int, int]] | None = None,
    headgear_offsets_rel: dict[str, tuple[int, int]] | None = None,
    canvas_offsets: dict[str, tuple[int, int]] | None = None,
    colors: dict[str, tuple[int, int, int]] | None = None,
) -> Image.Image:
    dirs = directions or ["north", "south", "east"]
    # Defaults: per-direction head offset, and relative offsets for hair/eyes/headgear w.r.t head
    default_head_offsets: Dict[str, Tuple[int, int]] = {
        "south": (0, -30),
        "north": (0, 0),
        "east": (0, 0),
    }
    # Per your calibration, use south (0,-5) as baseline for head-relative layers
    default_hair_offsets_rel: Dict[str, Tuple[int, int]] = {
        "south": (0, -5),
        "north": (0, 0),
        "east": (0, 0),
    }
    default_eyes_offsets_rel: Dict[str, Tuple[int, int]] = {
        "south": (0, -5),
        "north": (0, 0),
        "east": (0, 0),
    }
    default_beard_offsets_rel: Dict[str, Tuple[int, int]] = {
        "south": (0, -5),
        "north": (0, 0),
        "east": (0, 0),
    }
    # Hat slightly higher on south; bump by +2 from prior -10 to -8
    default_headgear_offsets_rel: Dict[str, Tuple[int, int]] = {
        "south": (0, -8),
        "north": (0, 0),
        "east": (0, 0),
    }

    def get_off(
        d: str,
        provided: Dict[str, Tuple[int, int]] | None,
        defaults: Dict[str, Tuple[int, int]],
    ) -> Tuple[int, int]:
        if provided and d in provided:
            return provided[d]
        if d in defaults:
            return defaults[d]
        return (0, 0)

    def get_color(key: str) -> Tuple[int, int, int] | None:
        # colors dict supplied by caller; keys: hair, beard, headgear, pants, shirt, outer, belt, apparel
        if colors and key in colors:
            return colors[key]
        return None

    def apply_color(img: Image.Image, rgb: Tuple[int, int, int] | None) -> Image.Image:
        if not rgb:
            return img
        src = img.convert("RGBA")
        alpha = src.split()[-1]
        lum = src.convert("L")
        colored = ImageOps.colorize(lum, black=(0, 0, 0), white=rgb)
        colored.putalpha(alpha)
        return colored

    frames: List[Image.Image] = []
    for d in dirs:
        # Collect placements (image, x, y) so we can size canvas before drawing
        placements: List[tuple[Image.Image, int, int]] = []

        def place(img: Image.Image, x: int, y: int) -> None:
            placements.append((img, x, y))

        # Base canvas shift applied before composing (prevents clipping)
        default_canvas_offsets: Dict[str, Tuple[int, int]] = {
            "north": (0, 0),
            "south": (0, 10),
            "east": (0, 0),
        }
        cx, cy = get_off(d, canvas_offsets, default_canvas_offsets)

        body = find_body(assets_root, body_type, d)
        if body:
            if body_offsets and d in body_offsets:
                ox, oy = body_offsets[d]
                place(body, cx + ox, cy + oy)
            else:
                place(body, cx, cy)

        buckets = collect_apparel_images(assets_root, apparels, body_type, d)

        # Body apparel on top of body
        for key in ("pants", "shirt", "outer"):
            for img in buckets[key]:
                cat_key = key  # direct mapping
                place(apply_color(img, get_color(cat_key)), cx, cy)

        for img in buckets["belt"]:
            place(apply_color(img, get_color("belt")), cx, cy)

        # Head above body apparel, below hair/hat
        hd = find_head(assets_root, head, d)
        if hd:
            hx, hy = get_off(d, head_offsets, default_head_offsets)
            place(hd, cx + hx, cy + hy)

        h = find_hair(assets_root, hair, d)
        if h:
            hx, hy = get_off(d, head_offsets, default_head_offsets)
            rx, ry = get_off(d, hair_offsets_rel, default_hair_offsets_rel)
            place(apply_color(h, get_color("hair")), cx + hx + rx, cy + hy + ry)

        # Eyes overlay: center relative to head + per-direction relative delta
        ey = load_eyes(assets_root, eyes, eyes_gender)
        if ey:
            hx, hy = get_off(d, head_offsets, default_head_offsets)
            rx, ry = get_off(d, eyes_offsets_rel, default_eyes_offsets_rel)
            ex_abs = cx + hx + rx
            ey_abs = cy + hy + ry
            x = 64 - ey.size[0] // 2 + ex_abs
            y = 64 - ey.size[1] // 2 + ey_abs
            place(ey, x, y)

        b = find_beard(assets_root, beard, d)
        if b:
            hx, hy = get_off(d, head_offsets, default_head_offsets)
            rx, ry = get_off(d, beard_offsets_rel, default_beard_offsets_rel)
            place(apply_color(b, get_color("beard")), cx + hx + rx, cy + hy + ry)

        for img in buckets["headgear"]:
            hx, hy = get_off(d, head_offsets, default_head_offsets)
            rx, ry = get_off(d, headgear_offsets_rel, default_headgear_offsets_rel)
            place(apply_color(img, get_color("headgear")), cx + hx + rx, cy + hy + ry)

        # Any uncategorized apparel renders above outer but below headgear
        for img in buckets["apparel"]:
            place(apply_color(img, get_color("apparel")), cx, cy)

        # Compose without clipping by sizing to placements' extents
        if placements:
            min_x = min(x for _, x, _ in placements)
            min_y = min(y for _, _, y in placements)
            max_x = max(x + im.width for im, x, y in placements)
            max_y = max(y + im.height for im, x, y in placements)
            out_w = max_x - min_x
            out_h = max_y - min_y
            frame = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 0))
            for im, x, y in placements:
                frame.alpha_composite(im, (x - min_x, y - min_y))
            frames.append(frame)
        else:
            frames.append(Image.new("RGBA", (128, 128), (0, 0, 0, 0)))

    # stitch horizontally with variable frame sizes
    total_w = sum(fr.width for fr in frames)
    max_h = max((fr.height for fr in frames), default=128)
    out = Image.new("RGBA", (total_w, max_h), (0, 0, 0, 0))
    x = 0
    for fr in frames:
        out.alpha_composite(fr, (x, 0))
        x += fr.width
    return out
