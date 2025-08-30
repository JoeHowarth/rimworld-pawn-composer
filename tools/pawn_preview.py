#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from PIL import Image
except Exception as e:
    raise SystemExit("Pillow (PIL) is required to run this tool. Please install it: pip install Pillow")


Direction = str


def load_png(path: Path) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    return img


def ensure_size(img: Image.Image, target_size: Tuple[int, int] = (128, 128)) -> Image.Image:
    """
    Resize proportionally to fit exactly into target_size, then paste centered
    onto a transparent canvas of target_size.
    """
    tw, th = target_size
    w, h = img.size
    if (w, h) == (tw, th):
        return img
    # scale to fit within target while preserving aspect ratio
    scale = min(tw / w, th / h)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
    ox = (tw - new_w) // 2
    oy = (th - new_h) // 2
    canvas.alpha_composite(resized, (ox, oy))
    return canvas


def composite_layers(layers: List[Optional[Image.Image]], size=(128, 128)) -> Image.Image:
    base = Image.new("RGBA", size, (0, 0, 0, 0))
    for layer in layers:
        if layer is None:
            continue
        base.alpha_composite(layer)
    return base


def find_body(assets_root: Path, body_type: str, direction: Direction) -> Optional[Image.Image]:
    # e.g., Bodies/Naked_Male_north.png
    path = assets_root / "Bodies" / f"Naked_{body_type}_{direction}.png"
    if path.exists():
        return ensure_size(load_png(path))
    return None


def find_hair(assets_root: Path, hair: Optional[str], direction: Direction) -> Optional[Image.Image]:
    if not hair:
        return None
    # e.g., Hairs/Afro_north.png
    p = assets_root / "Hairs" / f"{hair}_{direction}.png"
    if p.exists():
        return ensure_size(load_png(p))
    return None


def find_beard(assets_root: Path, beard: Optional[str], direction: Direction) -> Optional[Image.Image]:
    if not beard:
        return None
    # Beards often lack a north variant. Use only east/south if available.
    # Files look like: BeardStubble_east.png or BeardStubble_south.png
    if direction == "north":
        return None
    p = assets_root / "Beards" / f"Beard{beard}_{direction}.png"
    if p.exists():
        return ensure_size(load_png(p))
    return None


def find_apparel_variant(apparel_dir: Path, base_name: str, body_type: str, direction: Direction) -> Optional[Path]:
    # Prefer body type variant, then generic direction variant, then single sprite fallback
    candidates = [
        apparel_dir / f"{base_name}_{body_type}_{direction}.png",
        apparel_dir / f"{base_name}_{direction}.png",
        apparel_dir / f"{base_name}.png",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def find_apparel_images(assets_root: Path, apparels: List[str], body_type: str, direction: Direction) -> List[Image.Image]:
    images: List[Image.Image] = []
    for name in apparels:
        apparel_dir = assets_root / "Apparel" / name
        if not apparel_dir.exists():
            # Try to find a matching subdir by case-insensitive search
            parent = assets_root / "Apparel"
            matches = [d for d in parent.iterdir() if d.is_dir() and d.name.lower() == name.lower()]
            if matches:
                apparel_dir = matches[0]
            else:
                continue
        # Base name is typically the same as the directory
        base_name = apparel_dir.name
        p = find_apparel_variant(apparel_dir, base_name, body_type, direction)
        if p is None:
            # no variant for this direction
            continue
        img = ensure_size(load_png(p))
        images.append(img)
    return images


def build_preview(
    assets_root: Path,
    body_type: str,
    hair: Optional[str],
    beard: Optional[str],
    apparels: List[str],
    order: List[str],
    directions: List[Direction],
) -> Image.Image:
    # Render each direction into its own 128x128, then stitch horizontally
    frames: List[Image.Image] = []
    for direction in directions:
        layers: List[Optional[Image.Image]] = []
        # Gather layers based on render order
        for layer_name in order:
            if layer_name == "body":
                layers.append(find_body(assets_root, body_type, direction))
            elif layer_name == "pants":
                # Most pants in this pack are PSD-only; skip unless PNG exists following the convention
                pant_imgs = find_apparel_images(assets_root, ["Pants"], body_type, direction)
                layers.extend(pant_imgs)
            elif layer_name == "shirt":
                # Try common shirt types if the user didn't pass them explicitly
                pass  # Shirts are handled via apparels list
            elif layer_name == "apparel":
                layers.extend(find_apparel_images(assets_root, apparels, body_type, direction))
            elif layer_name == "hair":
                layers.append(find_hair(assets_root, hair, direction))
            elif layer_name == "beard":
                layers.append(find_beard(assets_root, beard, direction))
            elif layer_name == "headgear":
                # Headgear is included via apparels; keep explicit hook for future layer-separated handling
                pass
        frame = composite_layers(layers, (128, 128))
        frames.append(frame)

    # Stitch frames horizontally (north, south, east in that order)
    width = 128 * len(frames)
    out = Image.new("RGBA", (width, 128), (0, 0, 0, 0))
    for i, fr in enumerate(frames):
        out.alpha_composite(fr, (i * 128, 0))
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compose RimWorld humanlike pawn apparel preview (N,S,E)")
    p.add_argument("--assets-root", required=True, help="Path to Humanlike assets folder (…/Things/Pawn/Humanlike)")
    p.add_argument("--body-type", default="Male", choices=["Male", "Female", "Thin", "Fat", "Hulk"], help="Body type variant")
    p.add_argument("--hair", default=None, help="Hair name, e.g. Afro, Bob")
    p.add_argument("--beard", default=None, help="Beard name without 'Beard' prefix, e.g. Stubble, Full")
    p.add_argument("--apparel", action="append", default=[], help="Apparel directory names under Apparel/, repeatable. e.g. --apparel CowboyHat --apparel Jacket")
    p.add_argument("--out", required=True, help="Output PNG path")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    assets_root = Path(args.assets_root)
    if not assets_root.exists():
        raise SystemExit(f"Assets root not found: {assets_root}")

    # Layer order: body -> apparel (shirts/vests/jackets/hats) -> hair -> beard
    # Hats will overlay hair because they are in apparel and then hair comes after; we want hats on top, so order apparel before hair.
    order = [
        "body",
        "apparel",  # includes hats/vests/jackets if provided
        "hair",
        "beard",
    ]

    directions = ["north", "south", "east"]
    img = build_preview(
        assets_root=assets_root,
        body_type=args.body_type,
        hair=args.hair,
        beard=args.beard,
        apparels=args.apparel,
        order=order,
        directions=directions,
    )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    print(f"Wrote {out_path} ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()

