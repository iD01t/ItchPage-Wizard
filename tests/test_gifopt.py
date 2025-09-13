from pathlib import Path
from PIL import Image, ImageSequence

from app.gifopt import GIFOptimizer


def _mk_gif(path: Path, frames=10, size=(320, 240)):
    imgs = [Image.new("RGB", size, (i * 10 % 255, 100, 150)) for i in range(frames)]
    imgs[0].save(
        path,
        save_all=True,
        append_images=imgs[1:],
        duration=80,
        loop=0,
        optimize=True,
        format="GIF",
    )


def test_optimize_gif(tmp_path: Path):
    src = tmp_path / "src.gif"
    dst = tmp_path / "dst.gif"
    _mk_gif(src)

    opt = GIFOptimizer()
    out = opt.optimize_gif(str(src), str(dst), target_size_mb=1.0, quality=80, max_colors=128)
    assert Path(out).exists()
    assert dst.stat().st_size <= src.stat().st_size
