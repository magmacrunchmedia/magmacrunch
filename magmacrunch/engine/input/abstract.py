# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 magmacrunch media
"""What a controller looks like, whatever is behind it.

One dataclass and one protocol. :class:`InputState` is the snapshot every
backend reports in - eight buttons, and two derived axes so a game does not
each write its own arrows-to-direction arithmetic. :class:`InputSource` is the
backend itself.

Both are deliberately poorer than the terminal is capable of. A terminal
delivers *presses* and never releases, so held state is inferred upstream
(see :class:`~magmacrunch.engine.core.tui_game.TuiInput`) and arrives here already
resolved. Anything that needs the keystrokes themselves should take them from
the scene's ``handle_key`` instead, which is what a turn-based game wants.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class InputState:
    """Unified controller state for all input methods."""
    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False
    a: bool = False
    b: bool = False
    start: bool = False
    select: bool = False

    @property
    def dx(self) -> float:
        result = 0.0
        if self.left:
            result -= 1.0
        if self.right:
            result += 1.0
        return result

    @property
    def dy(self) -> float:
        result = 0.0
        if self.up:
            result -= 1.0
        if self.down:
            result += 1.0
        return result

    def is_any_direction(self) -> bool:
        """Whether any arrow is held.

        Not the same question as ``dx or dy``: left and right together cancel
        to zero on the axis while still very much being input.
        """
        return self.up or self.down or self.left or self.right


@runtime_checkable
class InputSource(Protocol):
    """Protocol for all input backends (keyboard, Magma Hub, etc.).

    Runtime-checkable like every other seam in this engine - ``Host``,
    ``ArcadeGame``, ``Scheduler``, ``Renderer``, ``UISurface`` and ``Scene``
    all are. This one was the exception until 0.5.0, for no reason anybody
    recorded, so a test asking whether a backend satisfied it raised
    ``TypeError`` instead of answering.
    """
    def poll(self) -> InputState: ...
    def is_pressed(self, button: str) -> bool: ...
