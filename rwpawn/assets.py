from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from PIL import Image

try:
    from psd_tools import PSDImage  # type: ignore
except Exception:  # pragma: no cover - optional during bootstrap
    PSDImage = None  # type: ignore


DIRECTIONS = ["north", "south", "east"]


# Basic apparel categorization for better layering
HEADGEAR = {
    "AdvancedHelmet",
    "BowlerHat",
    "ClothMask",
    "CowboyHat",
    "Hood",
    "PowerArmorHelmet",
    "PsychicFoilHelmet",
    "ReconArmorHelmet",
    "SimpleHelmet",
    "TribalHeaddress",
    "Tuque",
    "Veil",
    "WarMask",
}

OUTER = {
    "Cape",
    "Duster",
    "FlakJacket",
    "Jacket",
    "Parka",
    "PlateArmor",
    "PowerArmor",
    "ReconArmor",
    "Robe",
}

SHIRTS = {"ShirtBasic", "ShirtButton"}
PANTS = {"Pants", "FlakPants"}
BELTS_PACKS = {"ShieldBelt", "FirefoamPack", "SmokepopPack"}


def load_png(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def load_psd(path: Path) -> Optional[Image.Image]:
    if PSDImage is None:
        return None
    psd = PSDImage.open(path)
    img = psd.composite()
    return img.convert("RGBA")


def normalize_image(img: Image.Image, target: Tuple[int, int] = (128, 128)) -> Image.Image:
    tw, th = target
    w, h = img.size
    if (w, h) == (tw, th):
        return img
    # Many beards are 256x256; downscale by exactly half for alignment
    if (w, h) == (256, 256):
        return img.resize((128, 128), Image.LANCZOS)
    # Otherwise paste centered without scaling to preserve authored offsets
    canvas = Image.new("RGBA", target, (0, 0, 0, 0))
    ox = (tw - w) // 2
    oy = (th - h) // 2
    canvas.alpha_composite(img, (ox, oy))
    return canvas


def find_body(assets_root: Path, body_type: str, direction: str) -> Optional[Image.Image]:
    p = assets_root / "Bodies" / f"Naked_{body_type}_{direction}.png"
    if p.exists():
        return normalize_image(load_png(p))
    return None


def find_head(assets_root: Path, head_name: Optional[str], direction: str) -> Optional[Image.Image]:
    """Head files are usually under Heads/<Gender>/<HeadName>_<dir>.png or at top-level for special cases.
    Example: Heads/Female/Female_Average_Normal_south.png
             Heads/None_Average_Skull_south.psd
    """
    if not head_name:
        return None
    # If head_name already contains a gender prefix, try subdirs first
    parts = head_name.split("_", 1)
    gender_prefix = parts[0] if parts else ""
    subdir = None
    if gender_prefix in {"Male", "Female"}:
        subdir = gender_prefix

    candidates: list[Path] = []
    if subdir:
        candidates.extend([
            assets_root / "Heads" / subdir / f"{head_name}_{direction}.png",
            assets_root / "Heads" / subdir / f"{head_name}_{direction}.psd",
        ])
    # Fallbacks at top-level
    candidates.extend([
        assets_root / "Heads" / f"{head_name}_{direction}.png",
        assets_root / "Heads" / f"{head_name}_{direction}.psd",
    ])
    for p in candidates:
        if p.exists():
            if p.suffix.lower() == ".png":
                return normalize_image(load_png(p))
            elif p.suffix.lower() == ".psd":
                img = load_psd(p)
                if img is not None:
                    return normalize_image(img)
    return None


def load_eyes(assets_root: Path, eyes_name: Optional[str], gender: Optional[str]) -> Optional[Image.Image]:
    """Eyes are 42x42 PNGs at HeadAttachments/<Eyes>/<Gender>/<Eyes>_<Gender>.png"""
    if not eyes_name:
        return None
    if gender is None:
        gender = "Male"
    p = assets_root / "HeadAttachments" / eyes_name / gender / f"{eyes_name}_{gender}.png"
    if p.exists():
        return load_png(p)
    return None


def find_hair(assets_root: Path, hair: Optional[str], direction: str) -> Optional[Image.Image]:
    if not hair:
        return None
    p = assets_root / "Hairs" / f"{hair}_{direction}.png"
    if p.exists():
        return normalize_image(load_png(p))
    return None


def find_beard(assets_root: Path, beard: Optional[str], direction: str) -> Optional[Image.Image]:
    if not beard:
        return None
    if direction == "north":
        return None
    p = assets_root / "Beards" / f"Beard{beard}_{direction}.png"
    if p.exists():
        return normalize_image(load_png(p))
    return None


def _find_apparel_variant_paths(apparel_dir: Path, base_name: str, body_type: str, direction: str) -> Iterable[Path]:
    # Try PNGs then PSDs, most specific to least
    png_candidates = [
        apparel_dir / f"{base_name}_{body_type}_{direction}.png",
        apparel_dir / f"{base_name}_{direction}.png",
        apparel_dir / f"{base_name}.png",
    ]
    for p in png_candidates:
        if p.exists():
            yield p
    psd_candidates = [
        apparel_dir / f"{base_name}_{body_type}_{direction}.psd",
        apparel_dir / f"{base_name}_{direction}.psd",
        apparel_dir / f"{base_name}.psd",
    ]
    for p in psd_candidates:
        if p.exists():
            yield p


def load_apparel(assets_root: Path, name: str, body_type: str, direction: str) -> Optional[Image.Image]:
    apparel_dir = assets_root / "Apparel" / name
    if not apparel_dir.exists():
        # case-insensitive fallback
        parent = assets_root / "Apparel"
        for d in parent.iterdir():
            if d.is_dir() and d.name.lower() == name.lower():
                apparel_dir = d
                break
        else:
            return None
    base_name = apparel_dir.name
    for path in _find_apparel_variant_paths(apparel_dir, base_name, body_type, direction):
        if path.suffix.lower() == ".png":
            return normalize_image(load_png(path))
        elif path.suffix.lower() == ".psd":
            img = load_psd(path)
            if img is not None:
                return normalize_image(img)
    return None


def categorize(name: str) -> str:
    if name in PANTS:
        return "pants"
    if name in SHIRTS:
        return "shirt"
    if name in OUTER:
        return "outer"
    if name in BELTS_PACKS:
        return "belt"
    if name in HEADGEAR:
        return "headgear"
    return "apparel"


def collect_apparel_images(
    assets_root: Path,
    apparels: Iterable[str],
    body_type: str,
    direction: str,
) -> dict[str, List[Image.Image]]:
    out: dict[str, List[Image.Image]] = {
        "pants": [],
        "shirt": [],
        "outer": [],
        "belt": [],
        "headgear": [],
        "apparel": [],
    }
    for name in apparels:
        img = load_apparel(assets_root, name, body_type, direction)
        if img is None:
            continue
        out[categorize(name)].append(img)
    return out
