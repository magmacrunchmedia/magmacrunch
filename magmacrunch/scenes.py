"""The arcade floor, as a scene.

One screen: a list of every cabinet that was found, and a way into one. It
draws through the engine's ``Renderer``/``UISurface`` protocols and does not
know what Textual is.

Modality is the stack, not a flag - the engine's own rule. This sits at the
bottom; seating a cabinet pushes its scenes on top, and the cabinet leaving
pops back down to here. Nothing needs an ``in_game`` boolean, and the menu
cannot be updated while a game is over it because the stack will not call it.
"""

from __future__ import annotations

from dataclasses import replace

from texastoast.ui import DEFAULT_THEME, Menu

from magmacrunch import theme

MENU_HELP = "up/down choose    Enter play    Q quit"

EMPTY_FLOOR = (
    "No cabinets installed.",
    "",
    "pip install magmacrunch-george-boole",
    "pip install magmacrunch-thld",
    "",
    "Any package declaring a magmacrunch.games entry point",
    "appears here - no release of the arcade needed.",
)


def min_rows_for(count: int) -> int:
    """Rows the menu needs with ``count`` cabinets in it."""
    return theme.MIN_ROWS + count * theme.MENU_ITEM_H


def _too_small(renderer, cols: int, rows: int) -> bool:
    """Say so rather than drawing a clipped screen.

    Two short lines rather than one long one, because the message is being
    shown precisely when the terminal is narrow: a single line stating both
    sizes runs past 40 columns and gets cut mid-number, which reads as a bug in
    the thing reporting the problem.
    """
    if renderer.width >= cols and renderer.height >= rows:
        return False
    renderer.ui_text(1, 1, "terminal too small", fill=theme.ERROR)
    renderer.ui_text(
        1, 2,
        f"need {cols}x{rows}, have {renderer.width}x{renderer.height}",
        fill=theme.DIM,
    )
    return True


def _fit(text: str, width: int) -> str:
    """Trim to ``width``, marking the cut so a clipped line reads as clipped."""
    if width <= 1 or len(text) <= width:
        return text
    return text[:width - 1] + "…"


class CabinetScene:
    """The menu of installed games.

    ``render_below`` is deliberately *not* set: a cabinet seated on top covers
    this completely, so drawing underneath it would be wasted work.
    """

    def __init__(self, app):
        self.app = app
        self.menu = Menu(
            app.renderer,
            theme=_menu_theme(),
            # Cells, not pixels. The engine's defaults (280 wide, 32-cell rows)
            # would put the whole widget offscreen here.
            menu_width=theme.MENU_W,
            item_height=theme.MENU_ITEM_H,
            title_height=theme.MENU_TITLE_H,
            item_padding=theme.MENU_PAD,
            border_pad=theme.MENU_BORDER,
            selected_color=theme.MENU_SELECTED,
            normal_color=theme.VALUE,
            disabled_color=theme.DISABLED,
        )
        self._show()

    # -- The list ----------------------------------------------------

    def _show(self) -> None:
        """Arm the menu, keeping whatever row was highlighted.

        Called on construction and every time the menu comes back up, because
        ``Menu.confirm()`` hides the menu as it fires the callback - without
        this the screen underneath returns empty.
        """
        if not self.app.games:
            return
        self.menu.show(
            [_fit(game.info.title, theme.MENU_W - 4) for game in self.app.games],
            on_select=self._chose,
            title="CHOOSE A CABINET",
            selected=self.menu.selected_index,
        )

    def _chose(self, index: int, label: str) -> None:  # noqa: ARG002
        if not self.app.play(self.app.games[index]):
            # Nothing was pushed, so nothing will pop and no on_resume will
            # fire. Re-arm here or the floor is left blank under the error.
            self._show()

    @property
    def _highlighted(self):
        if not self.app.games:
            return None
        return self.app.games[self.menu.selected_index]

    # -- Stack hooks -------------------------------------------------

    def on_resume(self) -> None:
        """Take the terminal back from a cabinet that has just left.

        ``TuiHost.seat()`` applies the seated game's declared ``fps`` and
        ``hold_ms``, and nothing puts them back - so a real-time cabinet
        handing control back would leave the menu running at its frame rate
        with its held-key decay, and arrows would slide down the list on
        auto-repeat instead of stepping.

        Retuning here rather than in the host is deliberate: the host cannot
        know what to revert *to*. Only whatever is underneath does, and that
        is this.
        """
        self.app.host.apply(self.app.info)
        self._show()

    # -- Frame -------------------------------------------------------

    def update(self, dt: float) -> None:
        """Grey out the cabinets this window is too small for.

        ``GameInfo.fits`` exists for exactly this, and the engine's Menu
        already refuses to confirm a disabled row and snaps the selection off
        one - so fit-gating needs no logic of its own beyond asking.

        Per frame rather than on a resize event because Menu re-reads the
        surface size live when it renders; asking at the same cadence is what
        keeps the two from disagreeing for a frame after a resize.
        """
        r = self.app.renderer
        for i, game in enumerate(self.app.games):
            self.menu.set_enabled(i, game.info.fits(r.width, r.height))

    def handle_key(self, key: str) -> bool:
        if key in ("up", "w", "k"):
            self.menu.move_up()
        elif key in ("down", "s", "j"):
            self.menu.move_down()
        elif key in ("enter", "space"):
            self.menu.confirm()
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

        if _too_small(r, theme.MIN_COLS, min_rows_for(len(self.app.games))):
            r.present()
            return

        cx = r.width // 2
        r.ui_text(cx, 1, theme.BANNER, fill=theme.TITLE, anchor="n")
        r.ui_text(cx, 2, theme.TAGLINE, fill=theme.DIM, anchor="n")

        if self.app.games:
            self.menu.render()
            self._render_footer(r, cx)
        else:
            self._render_empty_floor(r, cx)

        r.present()

    def _render_footer(self, r, cx: int) -> None:
        """The highlighted cabinet's blurb, then the error, then the keys."""
        game = self._highlighted
        if game is not None:
            info = game.info
            if info.fits(r.width, r.height):
                line, colour = info.blurb, theme.LABEL
            else:
                # A greyed row with no explanation is a bug report waiting to
                # happen. Say what it wants instead.
                line = (f"needs a {info.min_cols}x{info.min_rows} terminal - "
                        f"this one is {r.width}x{r.height}")
                colour = theme.DIM
            r.ui_text(cx, r.height - 4, _fit(line, r.width - 2),
                      fill=colour, anchor="n")

        if self.app.error:
            r.ui_text(cx, r.height - 3, _fit(self.app.error, r.width - 2),
                      fill=theme.ERROR, anchor="n")
        r.ui_text(cx, r.height - 2, MENU_HELP, fill=theme.DIM, anchor="n")

    def _render_empty_floor(self, r, cx: int) -> None:
        top = max(4, r.height // 2 - len(EMPTY_FLOOR) // 2)
        for i, line in enumerate(EMPTY_FLOOR):
            fill = theme.VALUE if i == 0 else theme.DIM
            r.ui_text(cx, top + i, _fit(line, r.width - 2),
                      fill=fill, anchor="n")
        r.ui_text(cx, r.height - 2, "Q quit", fill=theme.DIM, anchor="n")


def _menu_theme():
    """The engine's Theme, recoloured to the arcade's palette.

    ``dataclasses.replace`` because :class:`~texastoast.ui.theme.Theme` is
    frozen - building variants that way is what its docstring asks for.
    """
    return replace(
        DEFAULT_THEME,
        primary=theme.MENU_SELECTED,
        text=theme.VALUE,
        dim_text=theme.DIM,
        disabled=theme.DISABLED,
        box_fill=theme.MENU_BOX,
        box_outline=theme.LABEL,
        outline_width=1,
        selection_fill=theme.MENU_SELECTION_BG,
    )
