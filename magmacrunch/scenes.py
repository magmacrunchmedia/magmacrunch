"""The arcade floor, as a scene.

One screen: the title art, a grid of every cabinet that was found, and a way
into one. It draws through the engine's ``Renderer``/``UISurface`` protocols
and does not know what Textual is.

The layout follows magmacrunch.com's arcade page - banner, tagline, a blinking
INSERT COIN, then the card grid - and gives up its parts in that order as the
window shrinks, so that the cabinets are the last thing to go. See
:mod:`magmacrunch.banner` and :mod:`magmacrunch.cards`.

Modality is the stack, not a flag - the engine's own rule. This sits at the
bottom; seating a cabinet pushes its scenes on top, and the cabinet leaving
pops back down to here. Nothing needs an ``in_game`` boolean, and the floor
cannot be updated while a game is over it because the stack will not call it.

The engine's ``Menu`` widget is deliberately not used. It draws a centred list
of single-line rows, which is the wrong shape for a grid of bordered cards -
so selection state lives here instead, in :attr:`CabinetScene.selected`.
"""

from __future__ import annotations

from magmacrunch import banner, cards, theme

MENU_HELP = "↑↓←→ CHOOSE    ENTER PLAY    Q QUIT"

EMPTY_FLOOR = (
    "NO CABINETS INSTALLED",
    "",
    "pip install magmacrunch-george-boole",
    "pip install magmacrunch-thld",
    "",
    "Any package declaring a magmacrunch.games entry point",
    "appears here - no release of the arcade needed.",
)


def _fit(text: str, width: int) -> str:
    """Trim to ``width``, marking the cut so a clipped line reads as clipped."""
    if width <= 1 or len(text) <= width:
        return text
    return text[:width - 1] + "…"


def _too_small(renderer, cols: int, rows: int) -> bool:
    """Say so rather than drawing a clipped screen.

    Two short lines rather than one long one, because the message is being
    shown precisely when the terminal is narrow: a single line stating both
    sizes runs past 40 columns and gets cut mid-number, which reads as a bug in
    the thing reporting the problem.
    """
    if renderer.width >= cols and renderer.height >= rows:
        return False
    renderer.ui_text(1, 1, "TERMINAL TOO SMALL", fill=theme.ERROR)
    renderer.ui_text(
        1, 2,
        f"need {cols}x{rows}, have {renderer.width}x{renderer.height}",
        fill=theme.MUTED,
    )
    return True


class CabinetScene:
    """The grid of installed games.

    ``render_below`` is deliberately *not* set: a cabinet seated on top covers
    this completely, so drawing underneath it would be wasted work.
    """

    def __init__(self, app):
        self.app = app
        #: Which cabinet the cursor is on. Kept here rather than in a widget
        #: because the grid is drawn here - see the module docstring.
        self.selected = 0
        #: Seconds since the scene started, for the blinking cursor and coin.
        #: A frame clock rather than a wall clock so the blink is the engine's
        #: business and stays put when the loop is stopped in a test.
        self.elapsed = 0.0

    # -- The grid ----------------------------------------------------

    @property
    def highlighted(self):
        if not self.app.games:
            return None
        return self.app.games[self.selected]

    def _enabled(self, game) -> bool:
        """Whether this window is big enough to seat ``game``.

        ``GameInfo.fits`` exists for exactly this. Asked at the moment it is
        needed rather than cached, so a resize is reflected in the same frame
        that draws it.
        """
        r = self.app.renderer
        return game.info.fits(r.width, r.height)

    def _grid_region(self) -> tuple[int, int]:
        """``(width, height)`` left for cards after the chrome takes its share."""
        r = self.app.renderer
        used = self._banner_rows() + theme.HEADER_ROWS + theme.FOOTER_ROWS + 2
        return r.width, max(0, r.height - used)

    def _banner_rows(self) -> int:
        r = self.app.renderer
        return len(banner.best_fit(r.width - 2, self._banner_budget()))

    def _banner_budget(self) -> int:
        """Rows the banner may have.

        It is given whatever is left once one row of cards and the chrome are
        accounted for, so the art stands down before the cabinets do. That is
        what keeps the floor at one card rather than at the widest banner.
        """
        r = self.app.renderer
        spare = r.height - (theme.HEADER_ROWS + theme.CARD_H + theme.FOOTER_ROWS + 2)
        return max(0, spare)

    def _move(self, delta: int) -> None:
        if not self.app.games:
            return
        self.selected = (self.selected + delta) % len(self.app.games)

    def _move_row(self, delta: int) -> None:
        """Up/down moves by a whole row of the grid, not by one card."""
        if not self.app.games:
            return
        width, height = self._grid_region()
        self._move(delta * cards.columns(width))

    def choose(self) -> None:
        game = self.highlighted
        if game is None or not self._enabled(game):
            return
        if not self.app.play(game):
            # Nothing was pushed, so nothing will pop and no on_resume will
            # fire. The error is drawn on the floor instead.
            pass

    # -- Stack hooks -------------------------------------------------

    def on_resume(self) -> None:
        """Take the terminal back from a cabinet that has just left.

        ``TuiHost.seat()`` applies the seated game's declared ``fps`` and
        ``hold_ms``, and nothing puts them back - so a real-time cabinet
        handing control back would leave the floor running at its frame rate
        with its held-key decay, and arrows would skate across the grid on
        auto-repeat instead of stepping.

        Retuning here rather than in the host is deliberate: the host cannot
        know what to revert *to*. Only whatever is underneath does, and that
        is this.
        """
        self.app.host.apply(self.app.info)

    # -- Frame -------------------------------------------------------

    def update(self, dt: float) -> None:
        self.elapsed += dt

    def handle_key(self, key: str) -> bool:
        if key in ("left", "a", "h"):
            self._move(-1)
        elif key in ("right", "d", "l"):
            self._move(1)
        elif key in ("up", "w", "k"):
            self._move_row(-1)
        elif key in ("down", "s", "j"):
            self._move_row(1)
        elif key in ("enter", "space"):
            self.choose()
        elif key == "q":
            self.app.host.quit()
        elif key == "escape":
            # The same call a cabinet makes to leave. This is the bottom of the
            # stack, so it ends the session - see TuiHost.pop_scene.
            self.app.host.pop_scene()
        else:
            return False
        return True

    def render(self) -> None:
        r = self.app.renderer
        r.clear()
        r.draw_rect(0, 0, r.width, r.height, theme.BG)

        if _too_small(r, theme.MIN_COLS, theme.MIN_ROWS):
            r.present()
            return

        cx = r.width // 2
        y = self._render_header(r, cx)

        if self.app.games:
            self._render_grid(r, y)
        else:
            self._render_empty_floor(r, cx, y)

        self._render_footer(r, cx)
        r.present()

    def _render_header(self, r, cx: int) -> int:
        """Banner, tagline and coin. Returns the first row below them."""
        y = 0
        art = banner.best_fit(r.width - 2, self._banner_budget())
        for line in art:
            r.ui_text(cx, y, line, fill=theme.CYAN, anchor="n")
            y += 1

        r.ui_text(cx, y, theme.TAGLINE, fill=theme.PINK, anchor="n")
        y += 1
        if self._blink(theme.COIN_BLINK_SECONDS):
            r.ui_text(cx, y, theme.INSERT_COIN, fill=theme.YELLOW, anchor="n")
        y += 2
        return y

    def _render_grid(self, r, top: int) -> None:
        width, height = self._grid_region()
        slots = cards.layout(len(self.app.games), self.selected, width, height)
        cursor = self._blink(theme.BLINK_SECONDS)

        for slot in slots:
            game = self.app.games[slot.index]
            cards.draw(
                r, cards.Slot(slot.index, slot.x, slot.y + top), game.info,
                accent=theme.accent(slot.index),
                selected=slot.index == self.selected,
                enabled=self._enabled(game),
                cursor=cursor,
            )

        total = cards.pages(len(self.app.games), width, height)
        if total > 1 and slots:
            capacity = cards.columns(width) * cards.rows(height)
            here = self.selected // capacity + 1
            # Directly under the grid rather than at a fixed row near the
            # bottom, where it would land on the error line.
            below = top + max(s.y for s in slots) + theme.CARD_H
            r.ui_text(r.width // 2, below, f"PAGE {here}/{total}",
                      fill=theme.MUTED, anchor="n")

    def _render_footer(self, r, cx: int) -> None:
        if self.app.error:
            r.ui_text(cx, r.height - 4, _fit(self.app.error, r.width - 2),
                      fill=theme.ERROR, anchor="n")
        r.ui_text(cx, r.height - 3, _fit(MENU_HELP, r.width - 2),
                  fill=theme.MUTED, anchor="n")
        self._render_credits(r, cx)

    def _render_credits(self, r, cx: int) -> None:
        """The signature, with the domain in the colour the web page links in.

        Drawn as two runs at computed positions rather than one centred
        string, because ``.credits-row a`` is cyan against muted text and a
        single ``ui_text`` gets one colour. Falls back to the copyright alone
        when the window is too narrow to carry both.
        """
        y = r.height - 2
        full = theme.COPYRIGHT + theme.CREDITS_SEP + theme.DOMAIN
        if len(full) + 2 > r.width:
            r.ui_text(cx, y, _fit(theme.COPYRIGHT, r.width - 2),
                      fill=theme.CARD_BORDER, anchor="n")
            return
        x = cx - len(full) // 2
        r.ui_text(x, y, theme.COPYRIGHT + theme.CREDITS_SEP,
                  fill=theme.CARD_BORDER)
        r.ui_text(x + len(theme.COPYRIGHT) + len(theme.CREDITS_SEP), y,
                  theme.DOMAIN, fill=theme.CYAN)

    def _render_empty_floor(self, r, cx: int, top: int) -> None:
        for i, line in enumerate(EMPTY_FLOOR):
            fill = theme.YELLOW if i == 0 else theme.MUTED
            r.ui_text(cx, top + i + 1, _fit(line, r.width - 2),
                      fill=fill, anchor="n")

    def _blink(self, period: float) -> bool:
        """On for the first half of each period, off for the second.

        ``animation: blink 0.6s step-end infinite`` in ``arcade.css``.
        """
        return (self.elapsed % period) < period / 2
