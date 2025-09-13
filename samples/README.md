# Sample Project - "Pixel Quest Adventures"

This sample project demonstrates all features of ItchPage Wizard using a fictional pixel art platformer game.

## Files Included

- `screenshot1.png` - Main gameplay screenshot (1920×1080)
- `screenshot2.png` - Character selection screen (1920×1080)
- `screenshot3.png` - Boss battle scene (1920×1080)
- `screenshot4.png` - Inventory system (1920×1080)
- `screenshot5.png` - World map overview (1920×1080)
- `gameplay.mp4` - 15-second gameplay clip (1080p)
- `logo.png` - Studio logo with transparency (512×512)
- `project.json` - Project configuration

## Walkthrough

### Step 1: Generate Cover
1. Load ItchPage Wizard
2. Enter project details:
   - Title: "Pixel Quest Adventures"
   - Studio: "Retro Games Studio"
   - Version: "1.2.3"
3. Select Cover Generator
4. Apply settings:
   - Background: Gradient (blue to purple)
   - Font: Impact, Bold, Drop Shadow
5. Export as PNG

**Expected Result:** `cover-630x500.png` (exactly 630×500 pixels)

### Step 2: Create Screenshot Collage
1. Switch to Screenshot Collage tool
2. Load all 5 screenshot files
3. Select Grid layout, 12px gutter
4. Export collage

**Expected Result:** `screens-inline-920w.png` (exactly 920px wide)

### Step 3: Optimize Gameplay GIF
1. Switch to GIF Optimizer
2. Load `gameplay.mp4`
3. Set target size to 3MB
4. Export optimized GIF

**Expected Result:** `promo.gif` (under 3MB, ~3 seconds duration)

### Step 4: Apply Jam Preset
1. Click "Apply Jam Preset" button
2. Regenerate cover with new high-contrast settings
3. Export updated assets

### Step 5: Package Assets
1. Click "Package All Assets"
2. Creates complete `/itch-assets` folder
3. Generates README with checklists

## Automated Reproduction

```bash
# Run sample project in batch mode
python app/main.py --batch --project samples/project.json

# Expected outputs in samples/output/:
# - cover-630x500_20231201_143022.png
# - screens-inline-920w_20231201_143025.png
# - promo_20231201_143045.gif
# - itch-assets-20231201_143050.zip
```

## Quality Validation

Run unit tests against sample outputs:

```bash
python -m pytest tests/test_sample_validation.py -v

# Tests verify:
# ✓ Cover dimensions exactly 630×500
# ✓ Cover aspect ratio 315:250 (±0.01 tolerance)
# ✓ Collage width exactly 920px
# ✓ GIF file size ≤ 3MB
# ✓ All files successfully generated
```

## Performance Benchmarks

On a modern system (16GB RAM, SSD), expect:

- **Cover Generation**: 0.8 seconds
- **Collage Creation**: 3.2 seconds (5 × 1920×1080 images)
- **GIF Optimization**: 28 seconds (15s 1080p → 3MB GIF)
- **Total Package Time**: ~35 seconds

Memory usage peaks at ~280MB during collage processing.
