# magmacrunch — agent brief

The terminal arcade: the `magmacrunch` command, a menu of every installed
cabinet, and the wiring that seats one on the terminal it is already holding.

## The engine is self-contained

The TUI engine lives in `magmacrunch.engine` — extracted from texastoast's
terminal backend. It provides the character-cell renderer, scene stack, game
loop, input handling, and UI widgets. No tkinter, no GUI.

External dependencies are `textual` and `rich` (used only by
`core/tui_game.py` for the terminal runtime).

The contract for games lives in `magmacrunch.engine.arcade` — `GameInfo`,
`Host`, `ArcadeGame`, `discover`. texastoast remains available as an
alternative engine (tkinter/GUI) but is not a dependency of this package.

## AI Attribution

**No AI attribution.** Do not append `Co-Authored-By: Claude …`, "Generated with
…", or any similar trailer to commit messages, PR bodies, or release notes. If
your tooling adds such a line by default, remove it before committing.

## Games are never vendored here, and this package imports none of them

Each game lives in its own repo with its `web/`, `wii/` and `tui/` versions
together, and publishes its own wheel built from `tui/`. This repo holds the
launcher and nothing else.

The relationship runs in two directions that must not be confused:

- **Distribution:** `pyproject.toml` lists the games as dependencies, so
  `pip install magmacrunch` installs an arcade with cabinets in it.
- **Runtime:** games are found by enumerating the `magmacrunch.games` entry
  point group. `magmacrunch` never imports `boole`, `lavadome`, or any other
  game module.

There is therefore no import edge in either direction, which is what makes an
arcade with its games uninstalled a working program that says the floor is
empty rather than an `ImportError`. `tests/test_cabinet.py` guards this.

It is also what lets a game published later appear in the menu without a
`magmacrunch` release — install it and it is there, uninstall it and it is gone.

## Adding a cabinet

Nothing changes here except the dependency list. A game declares:

```toml
[project.entry-points."magmacrunch.games"]
george-boole = "boole.arcade:GAME"
```

pointing at an object with `info: GameInfo` and `start(host) -> scene`. See
`magmacrunch.engine.arcade` for the contract and `george-boole/tui/boole/arcade.py` for
a worked example. `magmacrunch --list` says what was found and why anything was
skipped.

## Licence

PolyForm Noncommercial 1.0.0, because it depends on Noncommercial games. The
engine underneath stays Apache-2.0; a permissive dependency under a restrictive
package is fine, the reverse would not be.
