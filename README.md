# magmacrunch

The terminal arcade. One command, a menu of every cabinet installed on the
machine, and a way into one.

## Install

Every package in the stack is a pure-Python `py3-none-any` wheel, so there is
nothing to compile on macOS, Linux or Windows. What differs between the three is
not the build, it is which installer you already have — so that is what this
table is keyed on, rather than on the operating system:

| you already have | run | |
|---|---|---|
| `uv` | `uvx magmacrunch` | nothing lands on your PATH |
| `pipx` | `pipx run magmacrunch` | the same trick |
| Python 3.10+, and nothing else | `pip install magmacrunch` | the command, kept |
| Homebrew (macOS, Linux) | `brew install magmacrunchmedia/tap/magmacrunch` | brew owns it |
| none of these | install uv, below — it brings its own Python | |

The first two run the arcade out of a throwaway environment: nothing reaches
your PATH, and nothing can collide with anything. To keep the command around
instead:

```
uv tool install magmacrunch
pipx install magmacrunch
```

Either one puts `magmacrunch` — and each cabinet's own command — on your PATH
inside an isolated virtualenv. Whichever route you take, that one install brings
the arcade and all three cabinets.

### Getting uv

`uvx` is the shortest way in *if you have uv*, and no shorter than `pip` if you
do not — so it is worth saying how to get it rather than assuming it is there:

| | |
|---|---|
| macOS, Linux | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Windows | `winget install --id=astral-sh.uv -e` |

Where winget is unavailable, uv's own installer is `powershell -ExecutionPolicy
ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`. `brew install uv` and
`pipx install uv` work too.

### If you reached for pip

`pip install magmacrunch` is not wrong. Whether it is the *awkward* route
depends on the machine, and the ways it goes quiet are not the same on all of
them.

**On Windows it is usually the shortest route, not the risky one.** The
python.org installer's **Add python.exe to PATH** checkbox puts `Scripts\` on
your PATH, and the console script lands in it — so a plain `pip install
magmacrunch`, with no virtualenv and no `--user`, leaves you with a working
`magmacrunch` command.

What does bite on Windows is that **`python3` is usually not Python.** Windows
ships an app-execution alias of that name pointing at the Microsoft Store, so

```
python3 -m magmacrunch
```

answers `Python was not found; run without arguments to install from the
Microsoft Store` on a machine that has Python and has the arcade installed in
it. Use the launcher instead:

```
py -m magmacrunch
```

`python -m magmacrunch` does the same. If the arcade really is unreachable, the
PATH checkbox was most likely skipped at install time — `py` finds it either
way, and the installer's *Modify* can add it afterwards.

**On macOS and Linux** pip is the route that regularly installs successfully and
then appears to have done nothing. Two ways that happens:

- **`error: externally-managed-environment`.** Homebrew and Debian-family
  Pythons refuse to install into the system Python. That is pip working
  correctly, not a broken package. Use `uv`, `pipx`, or a virtualenv.
- **It installed, but the command is not on your PATH.** `pip` reaches your PATH
  only from an activated virtualenv, or with `--user` and `~/.local/bin` on
  PATH. Run against a system Python, the arcade is on disk and unreachable.

Both of those end at `python3 -m magmacrunch`, which does not care about PATH —
and which, on those two platforms, is a real interpreter rather than a Store
shortcut.

**Either way**, two more that cost people time:

- If you installed from inside IPython or a notebook, it went into whatever
  environment that kernel runs on, which is usually not the one your shell
  reaches.
- `magmacrunch` is a **shell** command. Typing it at a `>>>` prompt is only ever
  a `NameError` — leave Python first.

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

The floor takes the colour of whichever cabinet is highlighted: the title, the
tagline and the key line all shift as you arrow across the grid, the way
`.game-card:hover` recolours a card and its border on the web page. A cabinet
names its own colour through `GameInfo.accent`, and one that names none — a
cabinet built against an older engine, or one that simply does not care — gets
the cycled position colour it always had.

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
