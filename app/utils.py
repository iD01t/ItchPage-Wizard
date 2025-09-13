"""
utils.py - shared utilities for ItchPage Wizard
"""

from __future__ import annotations

import io
import os
import subprocess
from pathlib import Path
from typing import Iterable, Tuple

try:
    import PySimpleGUI as sg  # type: ignore
except Exception:  # pragma: no cover
    sg = None  # GUI-less environments (tests, headless CI)

from PIL import Image


# ----- Paths & FS helpers ----------------------------------------------------


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"


def get_asset_path(*parts: Iterable[str]) -> Path:
    """
    Returns a path inside the /assets directory.
    Usage: get_asset_path('fonts') -> Path('assets/fonts')
    """
    return ASSETS_DIR.joinpath(*parts)


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


# ----- Validation & image helpers -------------------------------------------


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def validate_image(path: str | os.PathLike) -> bool:
    """
    Quick validation that a file exists and Pillow can open it.
    """
    try:
        path = str(path)
        if not os.path.exists(path):
            return False
        if Path(path).suffix.lower() not in IMAGE_EXTS:
            return False
        with Image.open(path) as im:
            im.verify()  # type: ignore
        return True
    except Exception:
        return False


def ensure_aspect_ratio(
    size: Tuple[int, int], ratio_wh: Tuple[int, int], tolerance: float = 0.01
) -> bool:
    """
    Checks width:height ~= ratio_wh within tolerance.
    """
    w, h = size
    rw, rh = ratio_wh
    if w == 0 or h == 0 or rw == 0 or rh == 0:
        return False
    actual = w / h
    target = rw / rh
    return abs(actual - target) <= tolerance * target


def image_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    bio = io.BytesIO()
    img.save(bio, format=fmt)
    return bio.getvalue()


# ----- System checks & UX helpers -------------------------------------------


def check_ffmpeg() -> bool:
    """
    Returns True if ffmpeg is available on PATH.
    """
    try:
        proc = subprocess.run(
            ["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5
        )
        return proc.returncode == 0
    except Exception:
        return False


def show_error(message: str) -> None:  # pragma: no cover (GUI)
    """
    GUI-safe error popup; prints to console if GUI is unavailable.
    """
    if sg is not None:
        try:
            sg.popup_error(message, title="ItchPage Wizard - Error")
            return
        except Exception:
            pass
    # Fallback
    print(f"[ERROR] {message}")
