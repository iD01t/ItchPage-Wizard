"""
presets.py - PresetManager for one-click configurations (e.g., Jam Preset)
The manager operates on the running PySimpleGUI window by updating element values.
"""

from __future__ import annotations

from typing import Dict, Any


class PresetManager:
    def __init__(self) -> None:
        # Preset definitions; extend as needed
        self._presets: Dict[str, Dict[str, Any]] = {
            "jam": {
                "bg_type": "Solid Color",
                "bg_color": "#111111",
                "font": "Impact",
                "bold": True,
                "shadow": True,
                "gif_target_mb": 3,
                "gif_quality": 85,
                "layout": "Grid",
                "gutter": 12,
            }
        }

    def apply_jam_preset(self, window) -> None:
        """
        Applies the 'Jam' preset into the GUI if elements exist.
        This function is defensive: it checks the presence of each key.
        """
        p = self._presets["jam"]

        def _set(key: str, value):
            if key in window.AllKeysDict:
                window[key].update(value)

        _set("-BG_TYPE-", p["bg_type"])
        _set("-BG_COLOR-", p["bg_color"])
        _set("-FONT-", p["font"])
        _set("-BOLD-", p["bold"])
        _set("-SHADOW-", p["shadow"])
        _set("-GIF_SIZE-", p["gif_target_mb"])
        _set("-GIF_QUALITY-", p["gif_quality"])
        _set("-LAYOUT-", p["layout"])
        _set("-GUTTER-", p["gutter"])

    def list_presets(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._presets)
