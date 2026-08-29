# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 magmacrunch media
"""Renderer protocols — the seam between the engine and any drawing backend.

This engine draws through Textual today, but the protocols are older than that
backend and outlive it: a hand-written ANSI stack is the next one, and console
hardware the one after. They capture what the engine actually asks of a
backend, so game code written against them ports for free when one arrives.

Both are structural (:class:`typing.Protocol`): a backend implements them by
having the methods, not by inheriting anything.
:class:`~magmacrunch.engine.render.tui.TuiRenderer` satisfies both, and so did
the tkinter canvas backend these were first written against — which is the
evidence that they describe a seam rather than one implementation. **This
module must never import a backend.**
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Renderer(Protocol):
    """World-space drawing, offset by a camera.

    ``present()`` exists for backends that draw to an off-screen buffer and
    flip it once per frame. On tkinter it is a no-op — the Canvas is
    retained-mode — but calling it at the end of every render function costs
    nothing today and is the one habit a buffered backend cannot retrofit
    later without touching every game.
    """

    @property
    def camera(self) -> Any: ...

    @property
    def width(self) -> int: ...

    @property
    def height(self) -> int: ...

    def clear(self) -> None: ...

    def present(self) -> None: ...

    def draw_tilemap(self, tilemap: Any, tile_colors: dict[int, str],
                     skip_tiles: Any = None) -> None: ...

    def draw_rect(self, x: float, y: float, w: float, h: float,
                  color: str, tag: str = "") -> None: ...

    def draw_image(self, x: float, y: float, image: Any,
                   anchor: str = "nw", tag: str = "") -> None: ...

    def draw_text(self, x: float, y: float, text: str, **kwargs: Any) -> None: ...

    def draw_hud_text(self, x: float, y: float, text: str, **kwargs: Any) -> None: ...


@runtime_checkable
class UISurface(Protocol):
    """Screen-space drawing for UI widgets, organized into named groups.

    A *group* is a widget's frame of drawing: ``begin_group(name)`` discards
    whatever the group drew last frame, and ``clear_group(name)`` removes it
    entirely (the widget was dismissed). On tkinter's retained-mode canvas
    both map to deleting a tag; an immediate-mode backend may make
    ``begin_group`` a no-op because ``clear()`` already wiped the frame.

    Within one frame, draw order is z-order — later calls draw on top. That
    is the contract; there is no other layering.
    """

    @property
    def width(self) -> int: ...

    @property
    def height(self) -> int: ...

    def begin_group(self, group: str) -> None: ...

    def clear_group(self, group: str) -> None: ...

    def ui_rect(self, x: float, y: float, w: float, h: float, *,
                fill: str, outline: str = "", outline_width: int = 0,
                group: str = "") -> None: ...

    def ui_text(self, x: float, y: float, text: str, *,
                fill: str, font: Any = None, anchor: str = "nw",
                width: float | None = None, group: str = "") -> None: ...


def as_ui_surface(surface: Any) -> Any:
    """Check a widget's first constructor argument is a :class:`UISurface`.

    Structural, like every seam in this engine: anything with ``ui_rect`` is
    one, whatever it inherits from.

    Until 0.5.0 this also *wrapped* — a bare ``tk.Canvas`` passed to a widget
    was adapted by a shim called ``_CanvasUISurface``, which is what the
    pre-0.4 widget signature took. The shim came across in the extraction and
    could never run here: adapting a canvas requires a canvas, and this
    package has no tkinter and must not acquire one. It was 40 lines of
    unreachable tkinter calls sitting in the file that defines the seam.

    Failing loudly replaces it. Wrapping something that is not a surface only
    ever deferred the error to the first draw, where it surfaced as a missing
    method on an object the caller never built and cannot place.
    """
    if hasattr(surface, "ui_rect"):
        return surface
    raise TypeError(
        f"expected a UISurface (something with `ui_rect`), got "
        f"{type(surface).__name__}"
    )
