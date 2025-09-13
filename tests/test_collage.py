from pathlib import Path
from PIL import Image

from app.collage import ScreenshotCollage


def _mk_img(p: Path, size=(1920, 1080), color=(100, 140, 200)):
    Image.new("RGB", size, color).save(p, "PNG")


def test_create_collage_grid(tmp_path: Path):
    imgs = []
    for i in range(5):
        f = tmp_path / f"s{i}.png"
        _mk_img(f, size=(1920, 1080))
        imgs.append(str(f))

    out = tmp_path / "collage.png"
    collager = ScreenshotCollage()
    result = collager.create_collage(
        image_paths=imgs,
        output_path=str(out),
        layout="Grid",
        gutter=12,
        max_width=920,
        add_captions=False,
    )
    assert Path(result).exists()

    with Image.open(result) as im:
        assert im.width == 920
        assert im.height > 0


from app.main import ItchPageWizard

def test_create_collage_from_folder(tmp_path: Path):
    # Setup
    input_dir = tmp_path / "collage_input"
    input_dir.mkdir()
    for i in range(3):
        f = input_dir / f"s{i}.png"
        _mk_img(f, size=(800, 600))

    # Run the batch collage creation
    wizard = ItchPageWizard(gui_mode=False)
    wizard.run_batch_collage(str(input_dir), "Grid", 16)

    # Assertions
    output_dir = input_dir / "collage_output"
    assert output_dir.is_dir()

    output_files = list(output_dir.glob("*.png"))
    assert len(output_files) == 1

    output_collage = output_files[0]
    assert output_collage.exists()

    with Image.open(output_collage) as im:
        assert im.width == 920
