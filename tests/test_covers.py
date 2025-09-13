import os
from pathlib import Path

from app.covers import CoverGenerator
from app.utils import ensure_aspect_ratio


import csv
from app.main import ItchPageWizard

def test_generate_covers_from_csv(tmp_path: Path):
    # Setup
    csv_content = [
        ['title', 'studio', 'font', 'background_color'],
        ['CSV Cover 1', 'Test Studio', 'Arial', '#ff0000'],
        ['CSV Cover 2', 'Test Studio', 'Impact', '#00ff00'],
    ]
    csv_path = tmp_path / "covers.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(csv_content)

    # Run the batch cover generation
    wizard = ItchPageWizard(gui_mode=False)
    wizard.run_batch_covers(str(csv_path))

    # Assertions
    output_dir = tmp_path / "covers_output"
    assert output_dir.is_dir()

    output_files = list(output_dir.glob("*.png"))
    assert len(output_files) == 2

def test_generate_cover(tmp_path: Path):
    gen = CoverGenerator()
    out = gen.generate_cover(
        title="Test Game",
        studio="Studio",
        version="1.0.0",
        output_dir=str(tmp_path),
        export_png=True,
        export_jpg=False,
        include_metadata=True,
        background_type="Solid Color",
        background_color="#2c3e50",
        font="Arial",
        bold=True,
        shadow=True,
    )
    assert out is not None and os.path.exists(out)
    from PIL import Image

    with Image.open(out) as im:
        assert im.size == (630, 500)
        assert ensure_aspect_ratio(im.size, (315, 250))
