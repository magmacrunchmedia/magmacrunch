# magmacrunch

The terminal arcade. One command, a menu of every cabinet installed on the
machine, and a way into one.

```
pip install magmacrunch
magmacrunch
```

```
          |                            |             |    |
. . .,---.|    ,---.,---.,-.-.,---.    |--- ,---.    |--- |---.,---.
| | ||---'|    |    |   || | ||---'    |    |   |    |    |   ||---'
`-'-'`---'`---'`---'`---'` ' '`---'    `---'`---'    `---'`   '`---'
                   EVERY CABINET ON THIS MACHINE
                            INSERT COIN


┌──────────────────────────────┐  ┌──────────────────────────────┐
│ George Boole Has Entered The │  │ Texas Hold'Em Lava Dome      │
│ Chat                         │  │                              │
│                              │  │ Solo hold'em against a       │
│ 2048 played with logic gates │  │ threshold that climbs every  │
│ — merge, invert, overflow.   │  │ round.                       │
│                              │  │                              │
│ ▶ ENTER_                     │  │ ▶ ENTER                      │
└──────────────────────────────┘  └──────────────────────────────┘

                ↑↓←→ CHOOSE    ENTER PLAY    Q QUIT
```

It is `magmacrunch.com/arcade` in a shell — the same palette, the same card
grid, the same blinking cursor on the card you are about to start. The one
thing that could not come across is the typography: `arcade.css` sets
`Press Start 2P` on nearly every string, and a terminal program does not
choose its font. Pixel lettering has to be *drawn*, out of block glyphs, which
is what the narrow title variant does — and what the web page's own title art
does too, in Courier Prime rather than Press Start 2P, for the same reason.

The title art stands down as the window narrows, before the cabinets have to:
the wide art at 69 columns, a block-glyph wordmark at 48, spaced capitals at
35. That is what keeps the floor as low as it is.

Choosing a cabinet starts it on the terminal the arcade is already holding.
Leaving the game brings you back here. Every game is also its own command
(`george-boole`, `lava-dome`) and plays identically either way — the arcade is
not a wrapper around them, it is the same host they run on.

## What is installed

```
magmacrunch --list
```

Prints every cabinet found, what terminal size it wants, and how it wants
input. If a game you installed is not in the menu, this says why — a game that
fails to load is reported rather than silently skipped.

## How games get here

Games are **not** bundled. Each one lives in its own repo alongside its browser
and Wii versions, publishes its own wheel, and declares an entry point:

```toml
[project.entry-points."magmacrunch.games"]
george-boole = "boole.arcade:GAME"
```

pointing at an object with `info: GameInfo` and `start(host) -> scene`. The
launcher enumerates that group at startup. **Installing a game makes it appear
here; uninstalling makes it vanish; neither needs a release of the arcade.**

Nothing in this package imports a game, so the arcade runs with none installed
and tells you how to get one. The contract lives in
[`texastoast.arcade`](https://pypi.org/project/texastoast/); the two cabinets
above are worked examples of it.

## Cabinets

| | |
|---|---|
| `magmacrunch-george-boole` | 2048 played with logic gates |
| `magmacrunch-thld` | Solo hold'em against a climbing threshold |

Installing `magmacrunch` installs both.

## Requires

Python 3.10+, and a terminal at least 36×16. Individual cabinets ask for more
(around 59×22); below that their card greys out, says the size it wants, and
cannot be started. The arcade's own floor is deliberately lower than any
game's, so getting to the floor is never the thing that fails.

Two cards sit side by side from 70 columns and stack into one below that. More
cabinets than fit are paged, not scrolled.

Truecolor helps but is not required.

## Licence

PolyForm Noncommercial 1.0.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
Noncommercial because the games it seats are. The engine underneath,
[texastoast](https://pypi.org/project/texastoast/), stays Apache-2.0.
