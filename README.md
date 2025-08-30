RimWorld Pawn Outfit Preview (PNG + PSD)

Quick CLI to compose humanlike pawn previews from the free-for-personal-use RimWorld-like art pack.

Features
- Loads PNGs and PSDs (psd-tools) for apparel.
- Smarter layering order: body → pants → shirt → outer → belt/packs → hair → beard → headgear.
- Outputs three directions (north, south, east) stitched horizontally.

Project Setup (uv)
1) Ensure uv is installed (https://docs.astral.sh/uv/)
2) From the repo root:
   - uv sync
   - uv run rwpawn-preview --help

Example
uv run rwpawn-preview \
  --assets-root free-for-personal-use-rimworld-art/Things/Pawn/Humanlike \
  --body-type Female \
  --hair Bob \
  --apparel Jacket --apparel CowboyHat \
  --out preview_examples/female_bob_jacket_hat.png

Notes
- Some items in the pack are PSD-only (e.g., Hood, Tuque, Pants). PSDs with per-direction files (like Tuque_*_dir.psd) are supported.
- Beards are provided at 256×256; these are downscaled to 128×128 for alignment.
- Heads/eyes are not yet layered; can be added if needed.

