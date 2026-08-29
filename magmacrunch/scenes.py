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

from magmacrunch import banner, cabinets, cards, theme

MENU_HELP = "↑↓←→ CHOOSE    ENTER PLAY    Q QUIT"

#: What an arcade with nothing in it says. The install lines come from
#: :data:`magmacrunch.cabinets.PACKAGES` rather than being written out here,
#: because ``--list`` prints the same suggestions and the two had drifted -
#: see that module.
EMPTY_FLOOR = (
    "NO CABINETS INSTALLED",
    "",
    *(f"pip install {name}" for name in cabinets.PACKAGES),
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
        # The return value is deliberately dropped. A cabinet that will not
        # start pushes nothing, so nothing pops and no `on_resume` fires -
        # there is no state here to unwind, and `ArcadeApp.play` has already
        # put the reason in `app.error` for the footer to draw. This used to
        # be an `if` with a comment for a body, which reads as an unfinished
        # branch rather than a considered one.
        self.app.play(game)

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

        Scores are re-read for a related reason. A cabinet writes its
        scoreboard while it is running, and this is the frame after it stopped
        - so it is both the first moment the new number exists and the last
        moment before it would be drawn stale. A player who has just set a
        high score sees it on the card they came back to.
        """
        self.app.host.apply(self.app.info)
        self.app.refresh_scores()

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
        floor = self._floor()
        y = self._render_header(r, cx, floor)

        if self.app.games:
            self._render_grid(r, y)
        else:
            self._render_empty_floor(r, cx, y)

        self._render_footer(r, cx, floor)
        r.present()

    def _accent(self, index: int) -> str:
        """The colour of the cabinet in slot ``index``."""
        return theme.accent_for(self.app.games[index].info, index)

    def _floor(self) -> theme.Floor:
        """The floor, in the selected cabinet's colour.

        The room takes the colour of whatever you are standing in front of,
        which is the arcade's version of what each game does inside itself —
        george-boole dresses every bit mode as a different console, and the
        menu that seats it should not be the one screen that stays the same
        no matter what is highlighted.

        An empty floor has nothing to take a colour from and keeps cyan.
        """
        if not self.app.games:
            return theme.floor(theme.CYAN)
        return theme.floor(self._accent(self.selected))

    def _render_header(self, r, cx: int, floor: theme.Floor) -> int:
        """Banner, tagline and coin. Returns the first row below them."""
        y = 0
        art = banner.best_fit(r.width - 2, self._banner_budget())
        for line in art:
            r.ui_text(cx, y, line, fill=floor.accent, anchor="n")
            y += 1

        r.ui_text(cx, y, theme.TAGLINE, fill=floor.tagline, anchor="n")
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
                accent=self._accent(slot.index),
                selected=slot.index == self.selected,
                enabled=self._enabled(game),
                cursor=cursor,
                best=self.app.best_for(game),
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

    def _render_footer(self, r, cx: int, floor: theme.Floor) -> None:
        if self.app.error:
            r.ui_text(cx, r.height - 4, _fit(self.app.error, r.width - 2),
                      fill=theme.ERROR, anchor="n")
        r.ui_text(cx, r.height - 3, _fit(MENU_HELP, r.width - 2),
                  fill=floor.help, anchor="n")
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
