"""The title art, and picking the biggest one that fits.

``arcade.css`` sets ``Press Start 2P`` on nearly every string on the arcade
page. None of that can come across: a terminal program does not choose its
font. What carries the same look instead is art drawn *out of characters*,
which reads the same in whatever monospace font the terminal is set to - and
the web page already does exactly this for its own title, in Courier Prime
rather than Press Start 2P, for the same reason.

A terminal is small and resizable, so one piece of art is not enough. The
variants below are ordered widest first and :func:`best_fit` returns the
first that the window can hold, down to a single line of spaced capitals that
fits anything. That is what keeps the floor low: the banner gives up room
before the cabinets have to.

**Adding art:** put it at the top of :data:`VARIANTS` and nothing else
changes. Art is measured, not declared - a variant that turns out too wide is
simply never chosen, so a wrong guess costs a rung and not a broken screen.
"""

from __future__ import annotations

#: The arcade page's own title art, from ``website/arcade/index.html``.
#:
#: The `<pre>` there holds two pieces: this one, and a much larger
#: MAGMACRUNCH ARCADE wordmark below it. **The wordmark is 119 columns wide**,
#: which no ordinary terminal has, so only this half comes over.
WELCOME = """\
           |                            |             |    |
 . . .,---.|    ,---.,---.,-.-.,---.    |--- ,---.    |--- |---.,---.
 | | ||---'|    |    |   || | ||---'    |    |   |    |    |   ||---'
 `-'-'`---'`---'`---'`---'` ' '`---'    `---'`---'    `---'`   '`---'"""

#: A middle rung for windows too narrow for the art above. Block glyphs rather
#: than line drawing because at this size the pixel-lettering look is the point
#: - this is the nearest a terminal gets to Press Start 2P.
WORDMARK = """\
█▀▄▀█ ▄▀█ █▀▀ █▀▄▀█ ▄▀█ █▀▀ █▀█ █ █ █▄ █ █▀▀ █ █
█ ▀ █ █▀█ █▄█ █ ▀ █ █▀█ █▄▄ █▀▄ █▄█ █ ▀█ █▄▄ █▀█"""

#: The bottom rung, and the reason the floor is as low as it is. Spaced
#: capitals are not art, but they fit a 36-column window and still read as a
#: title rather than a sentence.
PLAIN = "M A G M A C R U N C H   A R C A D E"

#: Widest first. :func:`best_fit` walks this in order.
VARIANTS: tuple[str, ...] = (WELCOME, WORDMARK, PLAIN)


def lines(art: str) -> list[str]:
    return art.split("\n")


def size(art: str) -> tuple[int, int]:
    """``(cols, rows)`` the art occupies."""
    rows = lines(art)
    return max((len(line) for line in rows), default=0), len(rows)


def best_fit(cols: int, rows: int) -> list[str]:
    """The widest variant fitting ``cols`` x ``rows``, as lines to draw.

    Lines come back padded to the art's own width. Art is a block, and a
    caller centring each line by its own length would ragged the block apart -
    the first line of :data:`WELCOME` is mostly leading space, so it would sit
    a dozen cells right of the line beneath it.

    Returns an empty list when even :data:`PLAIN` will not fit, which the
    caller should treat as "no banner this frame" rather than an error: a
    window that short has better uses for the row, and the cabinets are the
    part worth keeping.
    """
    for art in VARIANTS:
        w, h = size(art)
        if w <= cols and h <= rows:
            return [line.ljust(w) for line in lines(art)]
    return []


__all__ = ["PLAIN", "VARIANTS", "WELCOME", "WORDMARK", "best_fit", "lines", "size"]
