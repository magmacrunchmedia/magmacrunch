"""Palette and layout for the arcade menu, in character cells.

Split out so :mod:`magmacrunch.scenes` and :mod:`magmacrunch.app` can share it
without importing each other. Nothing here imports the engine.

Every measurement is **cells**, not pixels. The engine's widgets take their
layout metrics as constructor arguments for exactly this reason - the numbers
below are what a terminal wants, where the defaults are what a canvas wants.

The floor is deliberately lower than any cabinet's. An arcade that refuses to
draw in a window where its games would run is worse than useless, so the menu
is kept narrow enough that reaching it is never the constraint.
"""

from __future__ import annotations

BANNER = "M A G M A C R U N C H   A R C A D E"
TAGLINE = "every cabinet on this machine"

#: Menu geometry, in cells. Passed to the engine's Menu widget in place of its
#: pixel defaults (280 wide, 32-cell rows), which would sit entirely offscreen.
#:
#: 44 wide takes the longest title there is ("George Boole Has Entered The
#: Chat", 33) with room to spare. Titles alone go in the rows; a row carrying
#: its blurb too would need about 80 columns, which is a higher floor than the
#: games have - so the blurb goes under the box instead, for the row that is
#: highlighted.
MENU_W = 44
MENU_ITEM_H = 1
MENU_TITLE_H = 2
MENU_PAD = 1
MENU_BORDER = 1

#: Rows the box takes regardless of how many cabinets are in it: the title,
#: the padding above and below the items, and the border on both sides.
BOX_FIXED_ROWS = MENU_TITLE_H + 2 * MENU_PAD + 2 * MENU_BORDER

#: Rows outside the box. The box is centred, so the taller side counts twice:
#: banner, tagline and a blank above; blurb, error and help below, plus a
#: margin.
CHROME_ROWS = 8

#: Smallest terminal the menu is drawn in, with no cabinets in it. One row per
#: cabinet is added on top - see :func:`magmacrunch.scenes.min_rows_for`.
#: Both are derived from the metrics above so the floor cannot drift from
#: where things are actually drawn.
MIN_COLS = MENU_W + 2 * (MENU_BORDER + 2)
MIN_ROWS = CHROME_ROWS + BOX_FIXED_ROWS

BG = "#12101f"
TITLE = "#f59e0b"
DIM = "#4a4a6a"
LABEL = "#6b6b8f"
VALUE = "#e8e8f4"
ERROR = "#ff6b6b"
MENU_BOX = "#1b1730"
MENU_SELECTED = "#f59e0b"
MENU_SELECTION_BG = "#33234d"
#: Cabinets too big for the window. The engine's Menu draws unselectable rows
#: in this colour, which is the whole of the fit-gating presentation.
DISABLED = "#3a3a52"
