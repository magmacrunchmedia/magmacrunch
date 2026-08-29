"""The cabinet cards, and where they go.

``.game-grid`` on magmacrunch.com is a two-column grid of bordered cards, each
carrying a title, a description, a ``▶ ENTER`` line in that card's own accent
colour, and a border that lights up in the same colour under the cursor. This
is that, in cells.

Layout is separated from drawing because layout is the part with arithmetic in
it: how many columns a window takes, how many rows of cards fit under the
banner, and which page of cards the selected one is on. All of it is pure and
none of it needs a terminal, so it is tested directly.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass

from magmacrunch import theme

# Box drawing for the card border. Light rather than heavy: the border is
# chrome, and the accent colour is what makes the selected card loud.
TL, TR, BL, BR, H, V = "┌", "┐", "└", "┘", "─", "│"


@dataclass(frozen=True)
class Slot:
    """Where one card goes, and which cabinet is in it."""

    index: int
    x: int
    y: int


def columns(width: int) -> int:
    """How many cards fit across ``width``.

    Two at most - ``.game-grid`` is ``repeat(2, 1fr)`` until 1100px and a
    terminal is never the wide case.
    """
    usable = width - 2 * theme.MARGIN_X
    if usable >= theme.MAX_COLS * theme.CARD_W + theme.GAP_X:
        return theme.MAX_COLS
    return 1


def rows(height: int) -> int:
    """How many rows of cards fit in ``height`` cells."""
    if height < theme.CARD_H:
        return 0
    return 1 + (height - theme.CARD_H) // (theme.CARD_H + theme.GAP_Y)


def page_start(selected: int, capacity: int) -> int:
    """Index of the first card on the page holding ``selected``.

    Paged rather than scrolled by one: a grid that slides a row at a time
    makes the cards move under the cursor on almost every keypress, where a
    page turns rarely and lands somewhere predictable.
    """
    if capacity <= 0:
        return 0
    return (selected // capacity) * capacity


def layout(count: int, selected: int, width: int, height: int) -> list[Slot]:
    """Slots for the cards visible in a ``width`` x ``height`` region.

    The region is what is left after the banner and the chrome have taken
    theirs. Cards that do not fit on the selected card's page are simply not
    in the result - see :func:`page_start`.
    """
    cols = columns(width)
    row_count = rows(height)
    capacity = cols * row_count
    if capacity <= 0 or count <= 0:
        return []

    first = page_start(selected, capacity)
    shown = min(capacity, count - first)

    used_rows = -(-shown // cols)   # ceil
    grid_w = cols * theme.CARD_W + (cols - 1) * theme.GAP_X
    grid_h = used_rows * theme.CARD_H + (used_rows - 1) * theme.GAP_Y
    origin_x = max(theme.MARGIN_X, (width - grid_w) // 2)
    # Centred vertically as well as horizontally: a part-full last page left
    # hard against the banner leaves a block of dead rows under it, which
    # reads as a screen that failed to finish drawing.
    origin_y = max(0, (height - grid_h) // 2)

    slots = []
    for offset in range(shown):
        row, col = divmod(offset, cols)
        slots.append(Slot(
            index=first + offset,
            x=origin_x + col * (theme.CARD_W + theme.GAP_X),
            y=origin_y + row * (theme.CARD_H + theme.GAP_Y),
        ))
    return slots


def pages(count: int, width: int, height: int) -> int:
    """How many pages ``count`` cabinets take. One when they all fit."""
    capacity = columns(width) * rows(height)
    if capacity <= 0:
        return 0
    return (count + capacity - 1) // capacity


def _wrap(text: str, width: int, limit: int) -> list[str]:
    """``text`` over at most ``limit`` lines, the last one elided if it runs on."""
    if width <= 0 or limit <= 0:
        return []
    out = textwrap.wrap(text, width) or [""]
    if len(out) <= limit:
        return out
    kept = out[:limit]
    kept[-1] = kept[-1][:max(0, width - 1)].rstrip() + "…"
    return kept


def best_label(score: int) -> str:
    """``BEST 12,345``, or empty for a game nobody has played here.

    Grouped with commas because a scoreboard is read at a glance and six
    unbroken digits are not. Zero is not a low score, it is no score - see
    :meth:`magmacrunch.app.ArcadeApp.refresh_scores`.
    """
    return f"BEST {score:,}" if score > 0 else ""


def draw(renderer, slot: Slot, info, *, accent: str, selected: bool,
         enabled: bool, cursor: bool, best: int = 0) -> None:
    """One card.

    ``cursor`` is the blinking underscore after ENTER, which the web page
    shows only under the pointer (``.card-arrow`` is ``opacity: 0`` until
    ``:hover``). Here that is the selected card, blinking on the frame clock.

    ``best`` is this game's high score, drawn at the right of the ENTER line.
    It shares that row rather than taking one of its own because the card is
    nine rows and a two-line title with a three-line blurb already fills it -
    a sixth row of text would push the ENTER line onto the border. Defaulted
    so that every existing caller keeps working and a game with no scoreboard
    costs nothing.
    """
    x, y, w, h = slot.x, slot.y, theme.CARD_W, theme.CARD_H
    border = accent if selected else theme.CARD_BORDER
    if not enabled:
        border = theme.CARD_BORDER

    renderer.draw_rect(x, y, w, h, theme.CARD_BG)
    renderer.ui_text(x, y, TL + H * (w - 2) + TR, fill=border)
    renderer.ui_text(x, y + h - 1, BL + H * (w - 2) + BR, fill=border)
    for row in range(1, h - 1):
        renderer.ui_text(x, y + row, V, fill=border)
        renderer.ui_text(x + w - 1, y + row, V, fill=border)

    left = x + 1 + theme.CARD_PAD
    inner = theme.CARD_INNER
    title_fill = theme.CARD_TITLE if enabled else theme.MUTED

    line = y + 1
    for text in _wrap(info.title, inner, 2):
        renderer.ui_text(left, line, text, fill=title_fill)
        line += 1

    line += 1
    if enabled:
        for text in _wrap(info.blurb, inner, 3):
            renderer.ui_text(left, line, text, fill=theme.MUTED)
            line += 1
    else:
        # A greyed card with no explanation is a bug report waiting to happen.
        for text in _wrap(f"needs {info.min_cols}x{info.min_rows}", inner, 2):
            renderer.ui_text(left, line, text, fill=theme.MUTED)
            line += 1

    play_y = y + h - 2
    if enabled:
        # The cursor belongs to the selected card alone - ``.card-arrow`` is
        # ``opacity: 0`` until ``:hover``, and a grid where every card blinks
        # says nothing about which one Enter would start.
        play = theme.PLAY + ("_" if cursor and selected else "")
        renderer.ui_text(left, play_y, play,
                         fill=accent if selected else theme.MUTED)
        _draw_best(renderer, left, play_y, inner, len(play), best)
    else:
        renderer.ui_text(left, play_y, "TOO BIG", fill=theme.CARD_BORDER)


def _draw_best(renderer, left: int, row: int, inner: int, used: int,
               best: int) -> None:
    """The high score, right-aligned on the ENTER row.

    Dropped rather than crowded when the two would touch: ENTER is how you
    start the game and the score is decoration, so on a card too narrow for
    both the number is what goes. In practice a 32-column card has room for
    seven figures, and this only bites if ``CARD_W`` ever shrinks.

    Yellow because that is the scoreboard colour on magmacrunch.com, and it is
    the same on the selected card as on the others - the accent says which
    card Enter would start, and a number that changed colour with the cursor
    would be saying it too.
    """
    label = best_label(best)
    if not label:
        return
    # One space of daylight between ENTER and the number, minimum.
    if used + 1 + len(label) > inner:
        return
    renderer.ui_text(left + inner - len(label), row, label, fill=theme.YELLOW)


__all__ = ["Slot", "best_label", "columns", "draw", "layout", "page_start",
           "pages", "rows"]
