# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 magmacrunch media
"""The arcade seam — what a game exposes so that something else can launch it.

A game normally owns its terminal: it builds a :class:`~magmacrunch.engine.core.tui_game.TuiGame`,
picks a frame rate, decides how input behaves, and runs until quit. That is the
right shape for one game shipped as one command, and both terminal games are
written that way.

It is the wrong shape for a launcher. A menu that seats several games cannot
have each of them constructing its own terminal — there is one terminal, and
whoever started it owns it. So this module names the two halves:

* a **host** owns the terminal, the renderer and the scene stack;
* a **game** owns its rules and its screens, and is handed a host.

Both protocols are structural, like every other seam in this engine
(:mod:`magmacrunch.engine.render.abstract`, :mod:`magmacrunch.engine.core.scheduler`): a game
satisfies :class:`ArcadeGame` by having the members, not by inheriting anything.

**This module depends on no game, and nothing here reaches downward.** That is
deliberate and it is what keeps the licensing clean: the engine is Apache, the
games are not, and a launcher that depends on games is not either. The engine
can name the contract without ever importing a consumer of it — the same
relationship `render/abstract.py` has with its backends.

Discovery is by entry point. A game package declares::

    [project.entry-points."magmacrunch.games"]
    george-boole = "boole.arcade:GAME"

and a launcher enumerates that group. Installing a game makes it appear;
uninstalling makes it vanish; the launcher never needs releasing to add a title.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

#: The entry point group a launcher enumerates. Named for the arcade rather
#: than the engine because it is the arcade's namespace, not the engine's —
#: this module only defines the shape of what goes in it.
ENTRY_POINT_GROUP = "magmacrunch.games"


@dataclass(frozen=True)
class GameInfo:
    """What a launcher needs to know before seating a game.

    Everything here has to be readable *without* starting the game: a menu
    lists titles and blurbs for games it has not launched, and it has to know
    the frame rate and input behaviour before handing over the terminal.
    """

    #: Stable identifier — the entry point name, a command-line argument, what
    #: a launcher files this game under. Kebab-case.
    #:
    #: It is *usually* the scoreboard key too, which is why :attr:`score_key`
    #: defaults to it. It is not always, so do not read this one for scores —
    #: read :attr:`scoreboard`.
    key: str
    #: What the menu shows.
    title: str
    #: One line under the title. Keep it under about 60 characters; a narrow
    #: terminal is the common case, not the exception.
    blurb: str

    #: Frames per second this game wants. A turn-based game is event-driven and
    #: does not care, but it still costs nothing to say so; a real-time one
    #: does care, and a host seating both has to know.
    fps: int = 20

    #: How long a keypress counts as held, in milliseconds.
    #:
    #: Terminals report presses and never releases, so held state has to be
    #: inferred from auto-repeat. ``0`` means edge semantics — one keystroke,
    #: one action — which is what a turn-based game wants and what makes a
    #: single arrow press move one square instead of sliding across the board.
    #:
    #: **A real-time game does not automatically want this above zero**, and
    #: the number to beat is the repeat *delay*, not the repeat interval. A
    #: keyboard sends one event and then goes silent for around 500 ms before
    #: repeating; anything tuned to the interval expires inside that silence
    #: and reads as a control that ignores you for a third of a second and
    #: then works. Anything tuned past the delay stays set for half a second
    #: after a real release.
    #:
    #: Decay suits a held *direction*, where overshoot is survivable. For a
    #: control whose timing is the game, leave this at 0 and drive it from
    #: discrete presses instead — see :class:`~magmacrunch.engine.core.tui_game.TuiInput`.
    hold_ms: int = 0

    #: Smallest terminal the game draws in. A launcher can warn before seating
    #: rather than handing over a window the game will refuse to draw in.
    min_cols: int = 60
    min_rows: int = 20

    #: Where this game's scores are filed, when that is not :attr:`key`.
    #:
    #: Empty means "the same", which is the common case and why this can be
    #: left alone. Set it when a game's scoreboard is named for something
    #: other than its entry point — usually because the browser build got
    #: there first and a shared board later has to mean a *shared* board, not
    #: two boards with different names. `magmacrunch-thld` is the worked
    #: example: it is seated as ``thld`` and scores as ``solitaire-thld``.
    #:
    #: Read :attr:`scoreboard`, never this.
    score_key: str = ""

    #: The colour this cabinet is known by, as ``#rrggbb``.
    #:
    #: Empty means "you choose", and a launcher is expected to have a fallback
    #: — the same arrangement :attr:`score_key` has, and for the same reason: a
    #: cabinet built against an older engine never sets this, and must not
    #: therefore look broken.
    #:
    #: It is here rather than in a table inside the launcher because a launcher
    #: that knew the colours of specific games would be a launcher that knows
    #: about specific games, which is the one thing this module exists to
    #: prevent. A cabinet brings its own; anything installed later brings its
    #: own too, without a release here.
    accent: str = ""

    def fits(self, cols: int, rows: int) -> bool:
        return cols >= self.min_cols and rows >= self.min_rows

    @property
    def scoreboard(self) -> str:
        """The key to open a :class:`~magmacrunch.engine.scores.ScoreBook` with.

        The one thing a launcher should ever use to find this game's scores.
        Going through here rather than reading :attr:`key` directly is what
        keeps a game whose two names differ from silently showing an empty
        board forever — the failure has no symptom, because an unfound
        scoreboard and an unplayed game look exactly alike.
        """
        return self.score_key or self.key


@runtime_checkable
class Host(Protocol):
    """What a game may ask of whatever is running it.

    Deliberately small. A game gets somewhere to draw, somewhere to read input,
    and a way to say it is finished — everything else is the game's own
    business, and a wider protocol would be a wider thing for a second host to
    have to implement.

    :attr:`seated` is the one addition to that list, and it is here because it
    is the only thing in this list a game cannot work out for itself. Everything
    else it needs, it owns.
    """

    @property
    def renderer(self) -> Any:
        """A :class:`~magmacrunch.engine.render.abstract.Renderer` and ``UISurface``."""
        ...

    @property
    def input(self) -> Any:
        """The :class:`~magmacrunch.engine.input.abstract.InputSource` for this session.

        Poll it for held state. Discrete keys arrive at the top scene's
        ``handle_key`` instead, which is what a turn-based game should use.
        """
        ...

    @property
    def seated(self) -> bool:
        """Whether this game was placed over something else.

        **For labelling, and for nothing else.** :meth:`pop_scene` already does
        the right thing in both situations without being told which one it is
        in, and that should stay true — a game that branches its *behaviour* on
        this has reintroduced the flag the stack exists to avoid.

        What it cannot do without asking is describe the key. Esc at a game's
        top menu means "back to the arcade" when seated and "quit" when the
        game was launched on its own, and a hint that has to be right in both
        places can only say one of them. Left unsaid, as it was until this
        existed, a player has no way to discover the route back at all.
        """
        ...

    def push_scene(self, scene: Any) -> None:
        """Put a scene on top. It receives updates and keys until popped."""
        ...

    def pop_scene(self) -> None:
        """Remove the top scene. A game calls this to hand control back."""
        ...

    def quit(self) -> None:
        """End the session and release the terminal."""
        ...


@runtime_checkable
class ArcadeGame(Protocol):
    """A game a launcher can seat.

    The object an entry point resolves to. Usually a module-level singleton,
    since it holds no state — the state belongs to whatever :meth:`start`
    returns.
    """

    @property
    def info(self) -> GameInfo:
        ...

    def start(self, host: Host) -> Any:
        """Build the game's root scene against ``host``.

        Returns a scene — anything with ``update(dt)`` and ``render()``, per
        :mod:`magmacrunch.engine.scene`. The caller pushes it; this method must not
        push it itself, or a launcher cannot decide what to do with it.

        Called once per play. A game returning to the menu and being chosen
        again gets a fresh call, so this is where a new run is set up.
        """
        ...


def discover(group: str = ENTRY_POINT_GROUP) -> list[ArcadeGame]:
    """Every installed game, sorted by title.

    Entry points that fail to load are skipped rather than taking the whole
    arcade down with them: one broken game on the machine should cost you that
    game, not the menu. The failure is re-raised as a warning so it is not
    silent either.
    """
    import warnings
    from importlib.metadata import entry_points

    found: list[ArcadeGame] = []
    for entry in entry_points(group=group):
        try:
            game = entry.load()
        except Exception as exc:  # noqa: BLE001 - one bad game must not be fatal
            warnings.warn(f"could not load arcade game {entry.name!r}: {exc}",
                          RuntimeWarning, stacklevel=2)
            continue
        if not isinstance(game, ArcadeGame):
            warnings.warn(
                f"entry point {entry.name!r} does not satisfy ArcadeGame "
                f"(needs `info` and `start`); skipping",
                RuntimeWarning, stacklevel=2,
            )
            continue
        found.append(game)

    return sorted(found, key=lambda g: g.info.title)


__all__ = ["ENTRY_POINT_GROUP", "ArcadeGame", "GameInfo", "Host", "discover"]
