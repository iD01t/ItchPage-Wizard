from pathlib import Path
from PIL import Image
from app.packager import ZipPackager, PackageInputs
import zipfile


def _mk_png(path: Path, size=(100, 100), color=(200, 80, 80)):
    Image.new("RGB", size, color).save(path, "PNG")


def _mk_gif(path: Path):
    Image.new("RGB", (64, 64), (0, 0, 0)).save(path, "GIF")


def test_package_all(tmp_path: Path):
    # make fake assets
    cover = tmp_path / "cover.png"
    screens = tmp_path / "screens.png"
    promo = tmp_path / "promo.gif"
    _mk_png(cover, (630, 500))
    _mk_png(screens, (920, 300))
    _mk_gif(promo)

    packager = ZipPackager(app_version="1.0.0")
    zip_path = packager.package_all(
        PackageInputs(
            title="Game",
            studio="Studio",
            version="1.0.0",
            cover_path=str(cover),
            screens_path=str(screens),
            gif_path=str(promo),
            dest_dir=str(tmp_path),
        )
    )
    assert zip_path.exists()

    # Inspect ZIP
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        assert "itch-assets/README.md" in names
        assert "itch-assets/manifest.json" in names
        assert "itch-assets/cover-630x500.png" in names
        assert "itch-assets/screens-inline-920w.png" in names
        assert "itch-assets/promo.gif" in names
