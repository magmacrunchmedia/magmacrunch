# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 magmacrunch media
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Config:
    title: str = "magmacrunch"
    width: int = 640
    height: int = 480
    fps: int = 30
    tile_size: int = 16
    bg_color: str = "#1a1a2e"
    grid_color: str = "#16213e"
    debug: bool = False


DEFAULT_CONFIG = Config()
