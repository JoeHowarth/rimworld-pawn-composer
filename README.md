RimWorld Pawn Outfit Preview (PNG + PSD)

CLI tool to compose RimWorld-like human pawn previews from the free-for-personal-use art pack.

Highlights
- PNG + PSD support (via Pillow and psd-tools)
- Layering tuned for humanlike pawns
- Per-layer offsets with sensible defaults and sweep grids for calibration
- Variable-size frames to prevent clipping (e.g., tall hats)

Install (uv)
1) Install uv: https://docs.astral.sh/uv/
2) From repo root:
   - uv sync
   - uv run rwpawn-preview --help

Assets Layout Assumptions
- Root points to Humanlike: `.../free-for-personal-use-rimworld-art/Things/Pawn/Humanlike`
- Bodies: `Bodies/Naked_<BodyType>_<dir>.png` (128×128)
- Hairs: `Hairs/<Hair>_<dir>.png` (128×128)
- Beards: `Beards/Beard<Beard>_<dir>.png` (often 256×256; auto-scaled)
- Heads: `Heads/<Gender>/<Head>_<dir>.(png|psd)` or top-level special heads
- Eyes: `HeadAttachments/<Eyes>/<Gender>/<Eyes>_<Gender>.png` (42×42)
- Apparel: `Apparel/<Item>/<Item>[_<BodyType>]_ <dir>.(png|psd)`

Layer Order
- body → body apparel (pants, shirts, outer, belts/packs) → head → hair → headgear → uncategorized apparel

Default Offsets
- Head (absolute): south (0,-30); north/east (0,0)
- Hair, eyes, beard, headgear (relative to head): south (0,-5) except headgear south (0,-8)
- Canvas (pre-composite): south (0,10) to avoid hat clipping; north/east (0,0)

Usage Examples

1) South-only example (one-arg-per-line)
uv run rwpawn-preview \
  --assets-root "./free-for-personal-use-rimworld-art/Things/Pawn/Humanlike" \
  --body-type Female \
  --head Female_Average_Normal \
  --hair Bowlcut \
  --eyes GrayEyes \
  --apparel ShirtButton \
  --apparel Jacket \
  --apparel CowboyHat \
  --dirs south \
  --out preview_examples/south_bowlcut_defaults.png

2) N/S/E strip
uv run rwpawn-preview \
  --assets-root "./free-for-personal-use-rimworld-art/Things/Pawn/Humanlike" \
  --body-type Male \
  --hair Afro \
  --apparel Jacket \
  --out preview_examples/male_strip.png

3) Head offset grid (use equals with negatives)
uv run rwpawn-preview \
  --assets-root "./free-for-personal-use-rimworld-art/Things/Pawn/Humanlike" \
  --body-type Female \
  --head Female_Average_Normal \
  --dirs south \
  --grid-head=-2:2:1,-10:2:2 \
  --out preview_examples/grid_head_south.png

4) Hair offset grid (relative to head)
uv run rwpawn-preview \
  --assets-root "./free-for-personal-use-rimworld-art/Things/Pawn/Humanlike" \
  --body-type Female \
  --head Female_Average_Normal \
  --hair Fancybun \
  --dirs south \
  --grid-hair=-4:4:1,-12:6:2 \
  --out preview_examples/grid_hair_fancybun_south.png

5) Headgear offset grid (relative to head)
uv run rwpawn-preview \
  --assets-root "./free-for-personal-use-rimworld-art/Things/Pawn/Humanlike" \
  --body-type Female \
  --head Female_Average_Normal \
  --hair Bowlcut \
  --apparel CowboyHat \
  --dirs south \
  --grid-headgear=-2:2:1,-12:0:2 \
  --out preview_examples/grid_headgear_hat_south.png

6) Canvas offset (pads frame before composing)
uv run rwpawn-preview \
  --assets-root "./free-for-personal-use-rimworld-art/Things/Pawn/Humanlike" \
  --body-type Female \
  --head Female_Average_Normal \
  --hair Bowlcut \
  --apparel CowboyHat \
  --dirs south \
  --canvas-offset-south 0,10 \
  --out preview_examples/south_canvas_shift.png

Tips / Troubleshooting
- Don’t split the assets path across lines; keep `--assets-root` on a single line inside quotes.
- When passing negative ranges to grid flags, use the equals form: `--grid-head=-2:2:1,-10:2:2`.
- The assets folder is not tracked in Git; point `--assets-root` at your local copy.

