from app.utils import ensure_aspect_ratio


def test_cover_aspect_ratio_constant():
    # 630x500 should match 315:250 within tolerance
    assert ensure_aspect_ratio((630, 500), (315, 250), tolerance=0.01) is True


def test_aspect_ratio_tolerance():
    # Slight deviation still accepted within tolerance
    assert ensure_aspect_ratio((630, 501), (315, 250), tolerance=0.02) is True
    # Large deviation rejected
    assert ensure_aspect_ratio((700, 500), (315, 250), tolerance=0.01) is False
