# magmacrunch

The terminal arcade. One command, a menu of every cabinet installed on the
machine, and a way into one.

## Install

**The quickest way in, on any platform, is not to install it at all:**

```
uvx magmacrunch
```

[uv](https://docs.astral.sh/uv/) pulls the arcade and its cabinets into a
throwaway environment and starts them. Nothing lands on your PATH, nothing can
collide with anything, and it behaves the same on macOS, Linux and Windows —
every package in the stack is a pure-Python `py3-none-any` wheel, so there is
nothing to compile on any of them. `pipx run magmacrunch` is the same trick if
you already have pipx.

To keep the command around afterwards:

```
uv tool install magmacrunch
```

`pipx install magmacrunch` does the same job. Either one puts `magmacrunch` —
and each cabinet's own command — on your PATH inside an isolated virtualenv.

| you want | run |
|---|---|
| to just play, right now | `uvx magmacrunch` |
| the command, kept | `uv tool install magmacrunch` |
| the command, and you have pipx | `pipx install magmacrunch` |
| Homebrew to own it (macOS, Linux) | `brew install magmacrunchmedia/tap/magmacrunch` |

That one install brings the arcade and all three cabinets.

### If you reached for pip

`pip install magmacrunch` is not wrong, but on its own it is the one route that
regularly installs successfully and then appears to have done nothing. Three
ways that happens, all of them recoverable:

- **`error: externally-managed-environment`.** Homebrew and most current Python
  builds refuse to install into the system Python. That is pip working
  correctly, not a broken package. Use `uv`, `pipx`, or a virtualenv.
- **It installed, but the command is not on your PATH.** `pip` only reaches
  your PATH from an activated virtualenv or with `--user`. Run against a system
  Python, the arcade is on disk and unreachable.
- **You installed it from inside IPython or a notebook.** It went into whatever
  environment that kernel runs on, which is usually not the one your shell
  reaches.

In all three the arcade is already installed, and this starts it, PATH or no
PATH:

```
python3 -m magmacrunch
```

One more, because it costs people five minutes: `magmacrunch` is a **shell**
command. Typing it at a `>>>` prompt is only ever a `NameError` — leave Python
first.

## Playing

```
magmacrunch          the arcade — every cabinet on the machine
george-boole         2048 with logic gates, on its own
lava-dome            solo hold'em, on its own
moonlight-drift      the endless drifter, on its own
```

A game plays identically whether you start it directly or pick it from the
arcade: the arcade is not a wrapper around them, it is the same host they run
on.

On the arcade floor, `←→` move between cabinets, `↑↓` move a row, `Enter`
plays and `Q` quits. **`Esc` inside a game returns to the arcade**, not to the
shell — which is the whole reason the host exists.

A cabinet says so on its own title screen, and only when the arcade started
it: the same key ends the session when the game was launched as its own
command, so a hint printed unconditionally would be a lie half the time.
Games ask `Host.seated` to tell the two apart, and nothing else about them
changes — see `magmacrunch.engine.arcade`.

Each card carries your best score on that cabinet, read from the same file
the game writes when you set one — so it is there the moment you come back
from the run that set it. A cabinet you have never played says nothing rather
than `BEST 0`, which would be inviting you to beat a score that does not
exist.

```
                                                                     __
    .--------.---.-.-----.--------.---.-.----.----.--.--.-----.----.|  |--.
    |        |  _  |  _  |        |  _  |  __|   _|  |  |     |  __||     |
    |__|__|__|___._|___  |__|__|__|___._|____|__| |_____|__|__|____||__|__|
                   |_____|
                         EVERY CABINET ON THIS MACHINE
                                  INSERT COIN


      ┌──────────────────────────────┐  ┌──────────────────────────────┐
      │ George Boole Has Entered The │  │ Moonlight Drift              │
      │ Chat                         │  │                              │
      │                              │  │ Thread the columns. Hold to  │
      │ 2048 played with logic gates │  │ climb, release to fall.      │
      │ — merge, invert, overflow.   │  │                              │
      │                              │  │                              │
      │ ▶ ENTER_        BEST 131,072 │  │ ▶ ENTER           BEST 8,420 │
      └──────────────────────────────┘  └──────────────────────────────┘
                                   PAGE 1/2


                      ↑↓←→ CHOOSE    ENTER PLAY    Q QUIT
                 © 2026 magmacrunch media  ·  magmacrunch.com
```

It is `magmacrunch.com/arcade` in a shell — the same palette, the same card
grid, the same blinking cursor on the card you are about to start. The one
thing that could not come across is the typography: `arcade.css` sets
`Press Start 2P` on nearly every string, and a terminal program does not
choose its font. Pixel lettering has to be *drawn*, out of block glyphs, which
is what the narrow title variant does — and what the web page's own title art
does too, in Courier Prime rather than Press Start 2P, for the same reason.

The title art stands down as the window grows or shrinks, and always before
the cabinets have to — which is what keeps the floor as low as it is:

| window | banner |
|---|---|
| 121×34 and up | the full site wordmark, MAGMACRUNCH over ARCADE, 119×19 |
| ~73×30 | the same two words in 71 columns instead of 119 |
| **80×24** | **MAGMACRUNCH alone, 71×5** |
| ~62–72 cols | the ARCADE wordmark alone, 60×8 |
| ~50 cols | a block-glyph MAGMACRUNCH, 48×2 |
| 36 cols | spaced capitals |

Art is measured rather than declared, so the 119-column piece can sit at the
top of the list without ever bothering someone on an ordinary terminal — it
is simply never the one that fits. Adding your own is one entry in `VARIANTS`
in [`banner.py`](magmacrunch/banner.py) and nothing else.

Choosing a cabinet starts it on the terminal the arcade is already holding.
Leaving the game brings you back here. Every game is also its own command
(`george-boole`, `lava-dome`, `moonlight-drift`) and plays identically either way — the arcade is
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
[`magmacrunch.engine.arcade`](https://github.com/magmacrunchmedia/magmacrunch);
the three
cabinets in the table below are worked examples of it.

## Cabinets

| | |
|---|---|
| `magmacrunch-george-boole` | 2048 played with logic gates |
| `magmacrunch-thld` | Solo hold'em against a climbing threshold |
| `magmacrunch-moonlight-drift` | Thread the columns; hold to climb |

Installing `magmacrunch` installs all three.

## Requires

Python 3.10+, and a terminal at least 36×17. Individual cabinets ask for more
(around 59×22); below that their card greys out, says the size it wants, and
cannot be started. The arcade's own floor is deliberately lower than any
game's, so getting to the floor is never the thing that fails.

Two cards sit side by side from 70 columns and stack into one below that. More
cabinets than fit are paged, not scrolled.

Truecolor helps but is not required.

## Licence

Two licences, split at the same seam the code is. The launcher is PolyForm
Noncommercial 1.0.0 — [LICENSE](LICENSE) — because the games it seats are. The
TUI engine, everything under `magmacrunch/engine/`, is Apache-2.0 —
[LICENSE-APACHE](LICENSE-APACHE) — because it depends on none of them, and
because texastoast still ships the same extracted code under it.

Every engine file carries an SPDX header saying which. [NOTICE](NOTICE) sets
out both in full.
