# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 magmacrunch media
"""What a game was configured with, in the units the renderer measures in.

Four fields, and each one is read: :class:`~magmacrunch.engine.core.tui_game.TuiGame`
takes ``title`` and ``fps`` from :data:`DEFAULT_CONFIG` as its own argument
defaults, and keeps ``width``/``height`` up to date as the terminal is resized.

**The sizes are character cells.** They were pixels until 0.5.0, along with
``tile_size``, ``bg_color`` and ``grid_color`` — the shape of the GUI engine
this was extracted from, carried across whole. Nothing here had read any of
them since the terminal backend became the only backend: a `640x480` default
was never reached, because the one caller passes ``DEFAULT_COLS``/
``DEFAULT_ROWS``, and a renderer that refuses pixel units had nothing to do
with a tile size in them.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Config:
    """Mutable, unlike :class:`~magmacrunch.engine.arcade.GameInfo`.

    A resize writes back to :attr:`width` and :attr:`height`, so this tracks
    what the terminal *is* rather than what it was asked to be.
    """

    title: str = "magmacrunch"
    #: Character cells, not pixels. 80x24 is the terminal that always exists.
    width: int = 80
    height: int = 24
    fps: int = 30


DEFAULT_CONFIG = Config()
