"""The title art, and picking the biggest one that fits.

``arcade.css`` sets ``Press Start 2P`` on nearly every string on the arcade
page. None of that can come across: a terminal program does not choose its
font. What carries the same look instead is art drawn *out of characters*,
which reads the same in whatever monospace font the terminal is set to - and
the web page already does exactly this for its own title, in Courier Prime
rather than Press Start 2P, for the same reason.

A terminal is small and resizable, so one piece of art is not enough. The
variants below are ordered **best first** and :func:`best_fit` returns the
first the window can actually hold, down to a single line of spaced capitals
that fits anything. Best rather than widest, because two variants can differ
on both axes: :data:`ARCADE` is narrower than :data:`WELCOME` and wants twice
the rows, and on an ordinary 80x24 terminal it is the one worth showing.

That ladder is what keeps the floor low: the banner gives up room before the
cabinets have to, so the smallest window the arcade draws in is set by one
card and not by the art.

**Adding art:** put it in :data:`VARIANTS` at the rung it deserves and nothing
else changes. Art is measured, not declared - a variant too big for the window
is simply never chosen, so a wrong guess costs a rung rather than breaking a
screen. That is why :data:`FULL` can sit at the top at 119 columns without
hurting anyone running a normal terminal.
"""

from __future__ import annotations

#: The arcade page's complete title art, from ``website/arcade/index.html``.
#:
#: 119x19 - it needs about a 121x34 terminal, which is a maximised window on a
#: large monitor and nothing smaller. It is here because it costs nothing to
#: offer and looks like the website when there is room for it.
FULL = r"""                                                                                                              /$$      
                                                                                                             | $$      
  /$$$$$$/$$$$   /$$$$$$   /$$$$$$  /$$$$$$/$$$$   /$$$$$$   /$$$$$$$  /$$$$$$  /$$   /$$ /$$$$$$$   /$$$$$$$| $$$$$$$ 
 | $$_  $$_  $$ |____  $$ /$$__  $$| $$_  $$_  $$ |____  $$ /$$_____/ /$$__  $$| $$  | $$| $$__  $$ /$$_____/| $$__  $$
 | $$ \ $$ \ $$  /$$$$$$$| $$  \ $$| $$ \ $$ \ $$  /$$$$$$$| $$      | $$  \__/| $$  | $$| $$  \ $$| $$      | $$  \ $$
 | $$ | $$ | $$ /$$__  $$| $$  | $$| $$ | $$ | $$ /$$__  $$| $$      | $$      | $$  | $$| $$  | $$| $$      | $$  | $$
 | $$ | $$ | $$|  $$$$$$$|  $$$$$$$| $$ | $$ | $$|  $$$$$$$|  $$$$$$$| $$      |  $$$$$$/| $$  | $$|  $$$$$$$| $$  | $$
 |__/ |__/ |__/ \_______/ \____  $$|__/ |__/ |__/ \_______/ \_______/|__/       \______/ |__/ |__/ \_______/|__/ |__/  
                          /$$  \ $$                                                                                    
                         |  $$$$$$/                                                                                    
                          \______/                                                                                     
                                                /$$                                                                    
                                               | $$                                                                    
  /$$$$$$   /$$$$$$   /$$$$$$$  /$$$$$$   /$$$$$$$  /$$$$$$                                                            
 |____  $$ /$$__  $$ /$$_____/ |____  $$ /$$__  $$ /$$__  $$                                                           
  /$$$$$$$| $$  \__/| $$        /$$$$$$$| $$  | $$| $$$$$$$$                                                           
 /$$__  $$| $$      | $$       /$$__  $$| $$  | $$| $$_____/                                                           
|  $$$$$$$| $$      |  $$$$$$$|  $$$$$$$|  $$$$$$$|  $$$$$$$                                                           
 \_______/|__/       \_______/ \_______/ \_______/ \_______/                                                           """

#: MAGMACRUNCH at 71x5 - **the rung a standard 80x24 terminal gets**, and the
#: only wordmark that fits one. :data:`FULL` says the same word in 119 columns
#: and eleven rows, which no ordinary window has; this says it in five.
CHUNKY = """\
                                                                 __
.--------.---.-.-----.--------.---.-.----.----.--.--.-----.----.|  |--.
|        |  _  |  _  |        |  _  |  __|   _|  |  |     |  __||     |
|__|__|__|___._|___  |__|__|__|___._|____|__| |_____|__|__|____||__|__|
               |_____|"""

#: The ARCADE half of :data:`FULL` on its own, 60x8. Narrower than
#: :data:`CHUNKY`, so it is what a window between about 62 and 72 columns gets
#: - and it is the half of the big art that was always going to survive the
#: trip, since the MAGMACRUNCH word above it cannot.
ARCADE = r"""                                                /$$         
                                               | $$         
  /$$$$$$   /$$$$$$   /$$$$$$$  /$$$$$$   /$$$$$$$  /$$$$$$ 
 |____  $$ /$$__  $$ /$$_____/ |____  $$ /$$__  $$ /$$__  $$
  /$$$$$$$| $$  \__/| $$        /$$$$$$$| $$  | $$| $$$$$$$$
 /$$__  $$| $$      | $$       /$$__  $$| $$  | $$| $$_____/
|  $$$$$$$| $$      |  $$$$$$$|  $$$$$$$|  $$$$$$$|  $$$$$$$
 \_______/|__/       \_______/ \_______/ \_______/ \_______/"""

#: The thin strapline alone, 69x4. Wider than :data:`ARCADE` but a quarter of
#: the height, which is what makes it the right answer for a short window.
WELCOME = r"""           |                            |             |    |         
 . . .,---.|    ,---.,---.,-.-.,---.    |--- ,---.    |--- |---.,---.
 | | ||---'|    |    |   || | ||---'    |    |   |    |    |   ||---'
 `-'-'`---'`---'`---'`---'` ' '`---'    `---'`---'    `---'`   '`---'"""

#: A middle rung for windows too narrow for any of the art above. Block glyphs
#: rather than line drawing because at this size the pixel-lettering look is
#: the point - this is the nearest a terminal gets to Press Start 2P.
WORDMARK = """█▀▄▀█ ▄▀█ █▀▀ █▀▄▀█ ▄▀█ █▀▀ █▀█ █ █ █▄ █ █▀▀ █ █
█ ▀ █ █▀█ █▄█ █ ▀ █ █▀█ █▄▄ █▀▄ █▄█ █ ▀█ █▄▄ █▀█"""

#: The bottom rung, and the reason the floor is as low as it is. Spaced
#: capitals are not art, but they fit a 36-column window and still read as a
#: title rather than a sentence.
PLAIN = "M A G M A C R U N C H   A R C A D E"


def lines(art: str) -> list[str]:
    return art.split("\n")


def size(art: str) -> tuple[int, int]:
    """``(cols, rows)`` the art occupies."""
    rows = lines(art)
    return max((len(line) for line in rows), default=0), len(rows)


def over(top: str, bottom: str) -> str:
    """One block above another, each centred on the wider of the two.

    Composed rather than written out, so that a stacked variant cannot drift
    from the pieces it is made of. Each block is indented as a whole; centring
    the *lines* would ragged a block apart, since art lines are not all the
    same length before padding.
    """
    width = max(size(top)[0], size(bottom)[0])

    def block(art: str) -> list[str]:
        indent = " " * ((width - size(art)[0]) // 2)
        return [(indent + line).ljust(width) for line in lines(art)]

    return "\n".join(block(top) + [" " * width] + block(bottom))


#: MAGMACRUNCH over ARCADE at 71x14: everything :data:`FULL` says, in the
#: width an ordinary terminal has. It needs a tall window rather than a wide
#: one, which is the easier of the two to come by.
STACK = over(CHUNKY, ARCADE)

#: The strapline over the ARCADE wordmark, 69x13.
HERO = over(WELCOME, ARCADE)

#: Best first. :func:`best_fit` walks this in order and takes the first that
#: fits, so the ordering is the editorial judgement and the measuring is not.
#:
#: The order is not by width. :data:`ARCADE` is narrower than :data:`CHUNKY`
#: and twice as tall, and which of them a window can take depends on both.
VARIANTS: tuple[str, ...] = (
    FULL, STACK, HERO, CHUNKY, ARCADE, WELCOME, WORDMARK, PLAIN,
)


def best_fit(cols: int, rows: int) -> list[str]:
    """The best variant fitting ``cols`` x ``rows``, as lines to draw.

    Lines come back padded to the art's own width. Art is a block, and a
    caller centring each line by its own length would ragged the block apart -
    the top line of :data:`WELCOME` is mostly leading space, so it would sit a
    dozen cells right of the line beneath it.

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


__all__ = ["ARCADE", "CHUNKY", "FULL", "HERO", "PLAIN", "STACK", "VARIANTS",
           "WELCOME", "WORDMARK", "best_fit", "lines", "over", "size"]
