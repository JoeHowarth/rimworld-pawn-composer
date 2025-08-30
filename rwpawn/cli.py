from __future__ import annotations

import argparse
from pathlib import Path

from .compose import compose_preview


def _parse_xy(val: str) -> tuple[int, int]:
    try:
        x_str, y_str = val.split(",", 1)
        return int(x_str.strip()), int(y_str.strip())
    except Exception:
        raise SystemExit(f"Invalid offset '{val}'. Use 'x,y' (e.g., 0,-6)")


def _parse_range(spec: str) -> list[int]:
    """Parse a range like 'start:stop:step' into a list of ints inclusive of stop if aligned."""
    try:
        start_s, stop_s, step_s = spec.split(":", 2)
        start, stop, step = int(start_s), int(stop_s), int(step_s)
    except Exception:
        raise SystemExit(f"Invalid range '{spec}'. Use 'start:stop:step' (e.g., -8:2:2)")
    if step == 0:
        raise SystemExit("Range step cannot be 0")
    vals: list[int] = []
    if start <= stop and step > 0:
        v = start
        while v <= stop:
            vals.append(v)
            v += step
    elif start >= stop and step < 0:
        v = start
        while v >= stop:
            vals.append(v)
            v += step
    else:
        # Allow single value case like '0:0:1'
        if start == stop:
            vals = [start]
        else:
            raise SystemExit(f"Range direction mismatch: '{spec}'")
    return vals


def _parse_color(val: str) -> tuple[int, int, int]:
    s = val.strip()
    if s.startswith("#"):
        s = s[1:]
    if "," in s:
        parts = [p.strip() for p in s.split(",")]
        if len(parts) != 3:
            raise SystemExit(f"Invalid color '{val}'. Use '#RRGGBB' or 'R,G,B'")
        try:
            r, g, b = (int(parts[0]), int(parts[1]), int(parts[2]))
        except Exception:
            raise SystemExit(f"Invalid color '{val}'. Components must be integers 0-255")
        for c in (r, g, b):
            if c < 0 or c > 255:
                raise SystemExit(f"Invalid color '{val}'. Components must be 0-255")
        return (r, g, b)
    if len(s) == 6:
        try:
            r = int(s[0:2], 16)
            g = int(s[2:4], 16)
            b = int(s[4:6], 16)
            return (r, g, b)
        except Exception:
            raise SystemExit(f"Invalid color hex '{val}'")
    raise SystemExit(f"Invalid color '{val}'. Use '#RRGGBB' or 'R,G,B'")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Compose RimWorld humanlike pawn outfit preview (N,S,E)")
    p.add_argument("--assets-root", required=True, help="Path to Humanlike assets folder (…/Things/Pawn/Humanlike)")
    p.add_argument("--body-type", default="Male", choices=["Male", "Female", "Thin", "Fat", "Hulk"], help="Body type variant")
    p.add_argument("--hair", default=None, help="Hair name, e.g. Afro, Bob")
    p.add_argument("--beard", default=None, help="Beard name without 'Beard' prefix, e.g. Stubble, Full")
    p.add_argument("--head", default=None, help="Head name, e.g. Female_Average_Normal or None_Average_Skull")
    p.add_argument("--eyes", default=None, help="Eyes attachment folder, e.g. GrayEyes")
    p.add_argument("--eyes-gender", default=None, choices=["Male", "Female"], help="Gender variant for eyes asset (defaults from body-type)")
    p.add_argument("--apparel", action="append", default=[], help="Apparel directory names under Apparel/ (repeatable)")
    p.add_argument("--dirs", default="north,south,east", help="Comma-separated directions to render (subset of north,south,east)")
    # Offsets (pixels) for alignment; can be per-direction
    p.add_argument("--body-offset", default=None, help="Global body offset 'x,y' applied to all dirs")
    p.add_argument("--head-offset", default=None, help="Global head offset 'x,y' applied to all dirs")
    p.add_argument("--canvas-offset", default=None, help="Global canvas offset 'x,y' (pads frame and shifts all layers)")
    for d in ("north", "south", "east"):
        p.add_argument(f"--body-offset-{d}", dest=f"body_offset_{d}", default=None, help=f"Body offset for {d} ('x,y')")
        p.add_argument(f"--head-offset-{d}", dest=f"head_offset_{d}", default=None, help=f"Head offset for {d} ('x,y')")
        p.add_argument(f"--canvas-offset-{d}", dest=f"canvas_offset_{d}", default=None, help=f"Canvas offset for {d} ('x,y')")
    # Relative offsets (added on top of head offset)
    p.add_argument("--hair-offset", default=None, help="Global hair offset relative to head ('x,y')")
    p.add_argument("--eyes-offset", default=None, help="Global eyes offset relative to head ('x,y')")
    p.add_argument("--headgear-offset", default=None, help="Global headgear offset relative to head ('x,y')")
    for d in ("north", "south", "east"):
        p.add_argument(f"--hair-offset-{d}", dest=f"hair_offset_{d}", default=None, help=f"Hair offset relative to head for {d} ('x,y')")
        p.add_argument(f"--eyes-offset-{d}", dest=f"eyes_offset_{d}", default=None, help=f"Eyes offset relative to head for {d} ('x,y')")
        p.add_argument(f"--headgear-offset-{d}", dest=f"headgear_offset_{d}", default=None, help=f"Headgear offset relative to head for {d} ('x,y')")
    # Grid exploration for head offsets: "x0:x1:step,y0:y1:step"
    p.add_argument("--grid-head", default=None, help="Render a grid sweeping head offsets: 'x0:x1:step,y0:y1:step' (e.g., -2:2:1,-10:2:2)")
    # Grid exploration for hair offsets relative to head
    p.add_argument("--grid-hair", default=None, help="Render a grid sweeping hair offsets relative to head: 'x0:x1:step,y0:y1:step'")
    # Grid exploration for headgear offsets relative to head
    p.add_argument("--grid-headgear", default=None, help="Render a grid sweeping headgear offsets relative to head: 'x0:x1:step,y0:y1:step'")
    # Colors per category
    p.add_argument("--color-hair", default=None, help="Hair color (#RRGGBB or R,G,B)")
    p.add_argument("--color-beard", default=None, help="Beard color (#RRGGBB or R,G,B)")
    p.add_argument("--color-headgear", default=None, help="Headgear color (#RRGGBB or R,G,B)")
    # Skin tone (applies to both head and body)
    p.add_argument("--color-skin", default=None, help="Skin tone for head and body (#RRGGBB or R,G,B)")
    p.add_argument("--color-body", default=None, help="Alias for --color-skin (deprecated)")
    p.add_argument("--color-pants", default=None, help="Pants color (#RRGGBB or R,G,B)")
    p.add_argument("--color-shirt", default=None, help="Shirt color (#RRGGBB or R,G,B)")
    p.add_argument("--color-outer", default=None, help="Outerwear color (#RRGGBB or R,G,B)")
    p.add_argument("--color-belt", default=None, help="Belt/pack color (#RRGGBB or R,G,B)")
    p.add_argument("--color-apparel", default=None, help="Fallback apparel color (#RRGGBB or R,G,B)")
    p.add_argument("--out", required=True, help="Output PNG path")
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    assets_root = Path(args.assets_root)
    dirs = [d.strip() for d in str(args.dirs).split(",") if d.strip()]
    # default head from body-type if not provided
    default_head = args.head
    if default_head is None and args.body_type in ("Male", "Female"):
        default_head = f"{args.body_type}_Average_Normal"

    eyes_gender = args.eyes_gender or (args.body_type if args.body_type in ("Male", "Female") else None)

    dirs = [d.strip() for d in str(args.dirs).split(",") if d.strip()]
    # default head from body-type if not provided
    default_head = args.head
    if default_head is None and args.body_type in ("Male", "Female"):
        default_head = f"{args.body_type}_Average_Normal"

    eyes_gender = args.eyes_gender or (args.body_type if args.body_type in ("Male", "Female") else None)

    # Build offset maps
    body_offsets = {}
    head_offsets = {}
    canvas_offsets = {}
    if args.body_offset:
        off = _parse_xy(args.body_offset)
        for d in dirs:
            body_offsets[d] = off
    if args.head_offset:
        off = _parse_xy(args.head_offset)
        for d in dirs:
            head_offsets[d] = off
    if args.canvas_offset:
        off = _parse_xy(args.canvas_offset)
        for d in dirs:
            canvas_offsets[d] = off
    for d in ("north", "south", "east"):
        v = getattr(args, f"body_offset_{d}")
        if v:
            body_offsets[d] = _parse_xy(v)
        v = getattr(args, f"head_offset_{d}")
        if v:
            head_offsets[d] = _parse_xy(v)
        v = getattr(args, f"canvas_offset_{d}")
        if v:
            canvas_offsets[d] = _parse_xy(v)

    # Build default colors and apply overrides
    colors: dict[str, tuple[int, int, int]] = {
        "hair": (59, 42, 31),
        "beard": (59, 42, 31),
        "headgear": (194, 168, 120),
        "body": (239, 208, 175),
        "head": (239, 208, 175),
        "pants": (58, 74, 90),
        "shirt": (159, 211, 242),
        "outer": (47, 62, 92),
        "belt": (85, 107, 120),
    }
    if args.color_hair:
        colors["hair"] = _parse_color(args.color_hair)
    if args.color_beard:
        colors["beard"] = _parse_color(args.color_beard)
    if args.color_headgear:
        colors["headgear"] = _parse_color(args.color_headgear)
    # Single skin tone control: prefer --color-skin, fall back to --color-body/--color-head
    skin_val = args.color_skin or args.color_body or getattr(args, "color_head", None)
    if skin_val:
        skin_rgb = _parse_color(skin_val)
        colors["body"] = skin_rgb
        colors["head"] = skin_rgb
    if args.color_pants:
        colors["pants"] = _parse_color(args.color_pants)
    if args.color_shirt:
        colors["shirt"] = _parse_color(args.color_shirt)
    if args.color_outer:
        colors["outer"] = _parse_color(args.color_outer)
    if args.color_belt:
        colors["belt"] = _parse_color(args.color_belt)
    if args.color_apparel:
        colors["apparel"] = _parse_color(args.color_apparel)

    if args.grid_head:
        # Force single direction (use the first provided)
        if not dirs:
            dirs = ["south"]
        direction = dirs[0]
        try:
            xspec, yspec = args.grid_head.split(",", 1)
        except Exception:
            raise SystemExit("--grid-head expects 'x0:x1:step,y0:y1:step'")
        xs = _parse_range(xspec)
        ys = _parse_range(yspec)

        from PIL import Image, ImageDraw, ImageFont

        tiles: list[Image.Image] = []
        base_head_off = head_offsets.get(direction, (0, 0)) if head_offsets else (0, 0)
        for y in ys:
            for x in xs:
                # Apply offset delta on top of base
                local_head_offsets = dict(head_offsets) if head_offsets else {}
                local_head_offsets[direction] = (base_head_off[0] + x, base_head_off[1] + y)
                im = compose_preview(
                    assets_root=assets_root,
                    body_type=args.body_type,
                    hair=args.hair,
                    beard=args.beard,
                    head=default_head,
                    eyes=args.eyes,
                    eyes_gender=eyes_gender,
                    apparels=args.apparel,
                    directions=[direction],
                    body_offsets=body_offsets or None,
                    head_offsets=local_head_offsets,
                    canvas_offsets=canvas_offsets or None,
                    colors=colors,
                )
                # Overlay label
                draw = ImageDraw.Draw(im)
                label = f"({local_head_offsets[direction][0]},{local_head_offsets[direction][1]})"
                try:
                    font = ImageFont.load_default()
                except Exception:
                    font = None
                # draw semi-transparent box for readability
                bbox_w, bbox_h = draw.textbbox((0, 0), label, font=font)[2:]
                pad = 2
                draw.rectangle([0, 0, bbox_w + 2 * pad, bbox_h + 2 * pad], fill=(0, 0, 0, 128))
                draw.text((pad, pad), label, fill=(255, 255, 255, 255), font=font, stroke_width=1, stroke_fill=(0, 0, 0, 255))
                tiles.append(im)

        # Build grid image (cols=len(xs), rows=len(ys))
        cols, rows = len(xs), len(ys)
        grid = Image.new("RGBA", (128 * cols, 128 * rows), (0, 0, 0, 0))
        idx = 0
        for r in range(rows):
            for c in range(cols):
                grid.alpha_composite(tiles[idx], (c * 128, r * 128))
                idx += 1
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        grid.save(out_path)
        print(f"Wrote grid {out_path} ({grid.size[0]}x{grid.size[1]}), cols={cols}, rows={rows}")
    elif args.grid_hair:
        if not args.hair:
            raise SystemExit("--grid-hair requires --hair to be specified")
        if not dirs:
            dirs = ["south"]
        direction = dirs[0]
        try:
            xspec, yspec = args.grid_hair.split(",", 1)
        except Exception:
            raise SystemExit("--grid-hair expects 'x0:x1:step,y0:y1:step'")
        xs = _parse_range(xspec)
        ys = _parse_range(yspec)

        from PIL import Image, ImageDraw, ImageFont

        tiles = []
        # Establish base offsets from any provided args
        base_head_off = head_offsets.get(direction, (0, 0)) if head_offsets else (0, 0)
        base_hair_rel = (0, 0)
        if args.hair_offset:
            base_hair_rel = _parse_xy(args.hair_offset)
        v = getattr(args, f"hair_offset_{direction}")
        if v:
            base_hair_rel = _parse_xy(v)

        for y in ys:
            for x in xs:
                # Apply relative hair delta on top of base relative
                local_head_offsets = dict(head_offsets) if head_offsets else {}
                local_hair_offsets_rel = {}
                local_hair_offsets_rel[direction] = (base_hair_rel[0] + x, base_hair_rel[1] + y)
                im = compose_preview(
                    assets_root=assets_root,
                    body_type=args.body_type,
                    hair=args.hair,
                    beard=args.beard,
                    head=default_head,
                    eyes=args.eyes,
                    eyes_gender=eyes_gender,
                    apparels=args.apparel,
                    directions=[direction],
                    body_offsets=body_offsets or None,
                    head_offsets=local_head_offsets or None,
                    hair_offsets_rel=local_hair_offsets_rel,
                    canvas_offsets=canvas_offsets or None,
                    colors=colors,
                )
                # Label with relative hair offset (x,y)
                draw = ImageDraw.Draw(im)
                label = f"({local_hair_offsets_rel[direction][0]},{local_hair_offsets_rel[direction][1]})"
                try:
                    font = ImageFont.load_default()
                except Exception:
                    font = None
                bbox_w, bbox_h = draw.textbbox((0, 0), label, font=font)[2:]
                pad = 2
                draw.rectangle([0, 0, bbox_w + 2 * pad, bbox_h + 2 * pad], fill=(0, 0, 0, 128))
                draw.text((pad, pad), label, fill=(255, 255, 255, 255), font=font, stroke_width=1, stroke_fill=(0, 0, 0, 255))
                tiles.append(im)

        cols, rows = len(xs), len(ys)
        grid = Image.new("RGBA", (128 * cols, 128 * rows), (0, 0, 0, 0))
        idx = 0
        for r in range(rows):
            for c in range(cols):
                grid.alpha_composite(tiles[idx], (c * 128, r * 128))
                idx += 1
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        grid.save(out_path)
        print(f"Wrote grid {out_path} ({grid.size[0]}x{grid.size[1]}), cols={cols}, rows={rows}")
    elif args.grid_headgear:
        if not any(a for a in args.apparel):
            raise SystemExit("--grid-headgear requires at least one headgear item passed via --apparel (e.g., CowboyHat)")
        if not dirs:
            dirs = ["south"]
        direction = dirs[0]
        try:
            xspec, yspec = args.grid_headgear.split(",", 1)
        except Exception:
            raise SystemExit("--grid-headgear expects 'x0:x1:step,y0:y1:step'")
        xs = _parse_range(xspec)
        ys = _parse_range(yspec)

        from PIL import Image, ImageDraw, ImageFont

        tiles = []
        base_head_off = head_offsets.get(direction, (0, 0)) if head_offsets else (0, 0)
        # Determine current base headgear relative offset if provided
        base_headgear_rel = (0, 0)
        if args.headgear_offset:
            base_headgear_rel = _parse_xy(args.headgear_offset)
        v = getattr(args, f"headgear_offset_{direction}")
        if v:
            base_headgear_rel = _parse_xy(v)

        for y in ys:
            for x in xs:
                local_head_offsets = dict(head_offsets) if head_offsets else {}
                local_headgear_offsets_rel = {}
                local_headgear_offsets_rel[direction] = (base_headgear_rel[0] + x, base_headgear_rel[1] + y)
                im = compose_preview(
                    assets_root=assets_root,
                    body_type=args.body_type,
                    hair=args.hair,
                    beard=args.beard,
                    head=default_head,
                    eyes=args.eyes,
                    eyes_gender=eyes_gender,
                    apparels=args.apparel,
                    directions=[direction],
                    body_offsets=body_offsets or None,
                    head_offsets=local_head_offsets or None,
                    headgear_offsets_rel=local_headgear_offsets_rel,
                    canvas_offsets=canvas_offsets or None,
                    colors=colors,
                )
                draw = ImageDraw.Draw(im)
                label = f"({local_headgear_offsets_rel[direction][0]},{local_headgear_offsets_rel[direction][1]})"
                try:
                    font = ImageFont.load_default()
                except Exception:
                    font = None
                bbox_w, bbox_h = draw.textbbox((0, 0), label, font=font)[2:]
                pad = 2
                draw.rectangle([0, 0, bbox_w + 2 * pad, bbox_h + 2 * pad], fill=(0, 0, 0, 128))
                draw.text((pad, pad), label, fill=(255, 255, 255, 255), font=font, stroke_width=1, stroke_fill=(0, 0, 0, 255))
                tiles.append(im)

        cols, rows = len(xs), len(ys)
        grid = Image.new("RGBA", (128 * cols, 128 * rows), (0, 0, 0, 0))
        idx = 0
        for r in range(rows):
            for c in range(cols):
                grid.alpha_composite(tiles[idx], (c * 128, r * 128))
                idx += 1
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        grid.save(out_path)
        print(f"Wrote grid {out_path} ({grid.size[0]}x{grid.size[1]}), cols={cols}, rows={rows}")
    else:
        # Relative layer offsets
        hair_offsets_rel = {}
        eyes_offsets_rel = {}
        headgear_offsets_rel = {}
        if args.hair_offset:
            off = _parse_xy(args.hair_offset)
            for d in dirs:
                hair_offsets_rel[d] = off
        if args.eyes_offset:
            off = _parse_xy(args.eyes_offset)
            for d in dirs:
                eyes_offsets_rel[d] = off
        if args.headgear_offset:
            off = _parse_xy(args.headgear_offset)
            for d in dirs:
                headgear_offsets_rel[d] = off
        for d in ("north", "south", "east"):
            v = getattr(args, f"hair_offset_{d}")
            if v:
                hair_offsets_rel[d] = _parse_xy(v)
            v = getattr(args, f"eyes_offset_{d}")
            if v:
                eyes_offsets_rel[d] = _parse_xy(v)
            v = getattr(args, f"headgear_offset_{d}")
            if v:
                headgear_offsets_rel[d] = _parse_xy(v)

        img = compose_preview(
            assets_root=assets_root,
            body_type=args.body_type,
            hair=args.hair,
            beard=args.beard,
            head=default_head,
            eyes=args.eyes,
            eyes_gender=eyes_gender,
            apparels=args.apparel,
            directions=dirs,
            body_offsets=body_offsets or None,
            head_offsets=head_offsets or None,
            hair_offsets_rel=hair_offsets_rel or None,
            eyes_offsets_rel=eyes_offsets_rel or None,
            canvas_offsets=canvas_offsets or None,
            colors=colors,
            headgear_offsets_rel=headgear_offsets_rel or None,
        )
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path)
        print(f"Wrote {out_path} ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
