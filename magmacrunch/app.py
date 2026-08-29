"""Wiring - what outlives one visit to a cabinet, and how the screen reaches it.

Everything that draws lives in :mod:`magmacrunch.scenes`. This holds the host,
the cabinets that were found, and the one decision the launcher actually makes:
seating a game.

**The terminal is not owned here.** It belongs to a
:class:`~magmacrunch.engine.core.tui_host.TuiHost`, which this is handed - the same
arrangement the games use, for the same reason. The launcher is not a special
case of the host; it is another thing seated on one, which is why the menu can
sit underneath a game and come back when the game leaves.
"""

from __future__ import annotations

from typing import Any

from magmacrunch import theme
from magmacrunch.engine.arcade import ArcadeGame, GameInfo
from magmacrunch.scenes import CabinetScene

#: The launcher, described with the same dataclass it reads from cabinets.
#:
#: This is not decoration. ``TuiHost.seat()`` applies a seated game's ``fps``
#: and ``hold_ms`` to the terminal and nothing puts them back, so the menu has
#: to retune on the way out of a game - and having its own ``GameInfo`` makes
#: that ``host.apply(ARCADE_INFO)`` rather than a pair of remembered numbers.
ARCADE_INFO = GameInfo(
    key="arcade",
    title="magmacrunch arcade",
    blurb="Every cabinet installed on this machine.",
    # The menu changes only when a key is pressed, and edge input is what keeps
    # one arrow press from running the selection down the whole list.
    fps=20,
    hold_ms=0,
    min_cols=theme.MIN_COLS,
    min_rows=theme.MIN_ROWS,
)


class ArcadeApp:
    """A visit to the arcade, drawing on somebody else's terminal."""

    #: What this asks of a terminal, in the same shape a cabinet declares it.
    #: The menu reads it back through here when it retunes on the way out of a
    #: game, which is why the scene needs no import from this module.
    info = ARCADE_INFO

    def __init__(self, host: Any, games: list[ArcadeGame] | None = None):
        self.host = host
        #: Sorted by title, the way :func:`magmacrunch.engine.arcade.discover` returns
        #: them. Discovery happens before the terminal is taken - see
        #: ``__main__`` - so this is handed in rather than looked up.
        self.games: list[ArcadeGame] = list(games or [])
        #: What went wrong last time somebody chose a cabinet, if anything.
        self.error: str = ""

        #: Best score per cabinet, by :attr:`GameInfo.scoreboard`.
        #:
        #: Cached rather than read while drawing. ``ScoreBook.best()`` opens
        #: and parses a file, the floor redraws at 20 fps, and a card that
        #: asked every frame would be twenty file reads a second per cabinet
        #: to show a number that changes at most once a visit.
        self.bests: dict[str, int] = {}
        self.refresh_scores()

        #: The menu. The caller pushes it, so that this class does not decide
        #: what the bottom of somebody else's scene stack is.
        self.root_scene = CabinetScene(self)

    # -- What the scene reaches for ----------------------------------

    @property
    def renderer(self):
        return self.host.renderer

    def refresh_scores(self) -> None:
        """Re-read every cabinet's best score from disk.

        Called once when the arcade opens and again each time a cabinet hands
        the terminal back, which is the only moment a score can have changed —
        the games write them, and a game only runs between those two points.

        A cabinet with no scoreboard is absent from the mapping rather than
        present as ``0``. An unplayed game and a game somebody scored nothing
        on are different things, and only one of them should be advertised on
        the floor.
        """
        from magmacrunch.engine.scores import ScoreBook

        self.bests = {}
        for game in self.games:
            key = game.info.scoreboard
            # A game is a third party. A malformed `info`, or a scoreboard on
            # an unreadable disk, must cost that card its number and nothing
            # else - the floor still has to draw. `ScoreBook.load` already
            # swallows OSError and bad JSON; this catches the rest.
            try:
                best = ScoreBook(key).best()
            except Exception:  # noqa: BLE001 - one bad board is not fatal
                continue
            if best > 0:
                self.bests[key] = best

    def best_for(self, game: ArcadeGame) -> int:
        """``game``'s best score, or ``0`` if it has never been played here."""
        return self.bests.get(game.info.scoreboard, 0)

    # -- The one decision --------------------------------------------

    def play(self, game: ArcadeGame) -> bool:
        """Seat a cabinet. Returns whether it started.

        ``TuiHost.seat()`` calls ``game.start(host)``, and that is where a
        cabinet's real imports finally happen - its rules, its screens, its
        widgets. It is therefore the first moment a bad install can raise, and
        it raises with the terminal live and a menu underneath.

        :func:`magmacrunch.engine.arcade.discover` already refuses to let one broken
        game take down the whole menu. This keeps that promise past the point
        where discovery stops looking: the arcade stays up and says which
        cabinet is out of order.
        """
        self.error = ""
        try:
            self.host.seat(game)
        except Exception as exc:  # noqa: BLE001 - one bad cabinet is not fatal
            self.error = f"{game.info.title} would not start: {exc}"
            return False
        return True

    # -- Introspection, for tests ------------------------------------

    @property
    def scene(self):
        return self.host.scene

    @property
    def in_menu(self) -> bool:
        return self.host.scene is self.root_scene
