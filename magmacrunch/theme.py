"""Palette and layout for the arcade floor, in character cells.

The colours are magmacrunch.com's arcade page, lifted from ``arcade.css`` so
the terminal and the browser are recognisably the same place. What could not
come with them is the typography: ``arcade.css`` sets ``Press Start 2P`` on
almost everything, and **a terminal program does not choose its font** - the
font is whatever the person running it has their emulator set to. The web page
already runs into this itself, which is why its own title art is Courier Prime
rather than Press Start 2P: pixel lettering in a terminal has to be drawn out
of block glyphs, not asked for. See :mod:`magmacrunch.banner`.

Split out so :mod:`magmacrunch.scenes` and :mod:`magmacrunch.app` can share it
without importing each other. Nothing here imports the engine.

Every measurement is **cells**, not pixels.
"""

from __future__ import annotations

from dataclasses import dataclass

TAGLINE = "EVERY CABINET ON THIS MACHINE"
INSERT_COIN = "INSERT COIN"

# ── Palette ─────────────────────────────────────────────────────────
# arcade.css, near enough verbatim. The names are the web page's roles.

#: ``body { background: #0a0612 }``
BG = "#0a0612"
#: ``.game-card { background: #150b29 }``
CARD_BG = "#150b29"
#: ``.game-card { border: 2px solid #3a2d5c }`` - the resting border.
CARD_BORDER = "#3a2d5c"
#: ``.card-title { color: #f0f8ff }``
CARD_TITLE = "#f0f8ff"
#: ``.card-desc`` and ``.breadcrumb`` - the muted body colour.
MUTED = "#8a7fa8"

CYAN = "#00f0ff"      # .arcade-title-ascii, links
PINK = "#ff2e9c"      # .arcade-subtitle, --nav-accent, the default card colour
YELLOW = "#fff733"    # .insert-coin, the scoreboard header
GREEN = "#39ff6e"     # card-games card
AMBER = "#ffe03a"     # puzzles card

ERROR = PINK

#: One accent per cabinet, cycled by position, in the order the four category
#: cards use them on the web page. ``.game-card:hover`` puts this on the
#: border and ``.card-play`` puts it on the ENTER line, which is exactly what
#: a selected card does here.
ACCENTS = (CYAN, GREEN, AMBER, PINK)


def accent(index: int) -> str:
    return ACCENTS[index % len(ACCENTS)]


def accent_for(info, index: int) -> str:
    """The colour a cabinet is drawn in.

    Its own if it declares one — see :attr:`magmacrunch.engine.arcade.GameInfo.accent`
    — and otherwise the cycled position colour, which is what every cabinet got
    before any of them could say. A game built against an older engine has no
    ``accent`` attribute at all, so this asks rather than reads: the launcher
    finds cabinets by entry point and has no say in which engine they were
    built against.
    """
    return getattr(info, "accent", "") or accent(index)


#: How far a cabinet's accent is pulled toward the background for the roles
#: that are not the accent itself. The floor keeps :data:`BG` — repainting the
#: whole room on every arrow keypress strobes — so the retint is carried by the
#: title, the tagline and the help line, which is where the web page carries it
#: too (``.game-card:hover`` recolours the card and its border, not the body).
_TAGLINE_MIX = 0.35
_HELP_MIX = 0.60


def _mix(a: str, b: str, t: float) -> str:
    """``a`` moved ``t`` of the way toward ``b``."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#{:02x}{:02x}{:02x}".format(
        *(round(x + (y - x) * t) for x, y in zip(ca, cb, strict=True))
    )


@dataclass(frozen=True)
class Floor:
    """The arcade floor, in one cabinet's colour.

    Three roles derived from one hex rather than six declared per cabinet: a
    cabinet should have to name one colour to be at home here, not fill in a
    stylesheet. Built by :func:`floor`.
    """

    accent: str
    tagline: str
    help: str


def floor(colour: str) -> Floor:
    return Floor(
        accent=colour,
        tagline=_mix(colour, BG, _TAGLINE_MIX),
        help=_mix(colour, BG, _HELP_MIX),
    )


# ── Cards ───────────────────────────────────────────────────────────

#: A card is 32x9 with a two-cell gutter, and the grid is at most two across
#: - ``.game-grid`` is ``repeat(2, 1fr)`` until 1100px, and a terminal is
#: never the wide case.
CARD_W = 32
CARD_H = 9
GAP_X = 2
GAP_Y = 1
MAX_COLS = 2

#: Border on both sides plus a cell of padding inside it.
CARD_PAD = 1
#: What a card has left for text.
CARD_INNER = CARD_W - 2 * (1 + CARD_PAD)

MARGIN_X = 2
#: Rows above the grid that are not the banner: the tagline and INSERT COIN.
HEADER_ROWS = 2
#: Rows below it: the error line, the key help and the credits.
FOOTER_ROWS = 3

#: The footer signature, in two parts so the domain can carry the link colour
#: the web page gives it (``.credits-row a { color: #00f0ff }``).
COPYRIGHT = "© 2026 magmacrunch media"
DOMAIN = "magmacrunch.com"
CREDITS_SEP = "  ·  "

PLAY = "▶ ENTER"
#: ``.card-arrow { animation: blink 0.6s step-end infinite }`` - the cursor
#: after ENTER on the selected card, on for one half-period and off the next.
BLINK_SECONDS = 0.6
#: ``.insert-coin { animation: blink 1s step-end infinite }``
COIN_BLINK_SECONDS = 1.0

#: Smallest terminal the floor is drawn in: one card, one column, plus the
#: chrome that never goes away. Derived so the floor cannot drift from the
#: layout. The banner is not in it - it stands down to whatever fits, and at
#: the bottom rung it is one line. See :func:`magmacrunch.banner.best_fit`.
MIN_COLS = CARD_W + 2 * MARGIN_X
MIN_ROWS = 1 + HEADER_ROWS + CARD_H + FOOTER_ROWS + 2
