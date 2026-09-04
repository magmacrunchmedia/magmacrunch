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

**`texastoast` still ships its own copy of all of this**, because the engine
was extracted rather than moved and deleting it would break a published
Apache-2.0 package that has other consumers. Where the two disagree, the copy
here is the one the arcade and its cabinets use — `magmacrunch.engine.arcade`
is the seam, and `texastoast.arcade` is a fossil of it. Both define
`ENTRY_POINT_GROUP = "magmacrunch.games"`, and that string must stay identical
in both or installed games stop being found.

## Terminal capability: colour is inherited, characters are ours

**Do not write colour degradation.** Textual reads `NO_COLOR` when the `App` is
constructed and appends a `Monochrome` line filter; Rich steps truecolor down
to 256 or 16 by looking at the terminal. Both reach this engine's own `Strip`,
even though `GameSurface` overrides `render_line` and builds Rich `Style`s
straight from hex without touching Textual's CSS — the filters are applied in
`StylesCache.render_widget`, which takes `widget.render_line` and
`widget.get_line_filters()` together. Nothing in this package mentions
`NO_COLOR`, and that is correct.

That inheritance is a fact about Textual's internals, so a version bump could
drop it silently. `tests/engine/test_no_color.py` asserts on *rendered output*
rather than on `app._filters` for exactly that reason — a filter that is
installed and not applied is the bug being guarded against, and checking the
list would pass straight through it. It carries a control test so it cannot
pass by rendering nothing.

**Characters are the half nothing under us owns**, and that is
`magmacrunch.engine.ui.glyphs`. `TuiRenderer` substitutes on the way into the
cell buffer — one place, rather than a question asked at thirty draw calls a
frame across three games — and a renderer built without a `Glyphs` substitutes
nothing, which is what keeps test expectations independent of whatever stream
pytest attached.

Two rules there are load-bearing and both were arrived at by measuring:

- **Glyphs degrade by group, not one at a time.** cp1252 and cp437 both encode
  `¬` and neither encodes `∧`, `∨` or `⊕`. Asked per glyph, George Boole's
  board draws a real NOT sign beside `&`, `|` and `^` — one set of operators
  in two alphabets, which is worse than either alphabet alone.
- **Every substitute is exactly one cell.** Substitution happens *after* the
  games have measured — a hint line trimmed to the window, a title centred in
  a box, `bigtext.width` consulted before drawing. A stand-in of a different
  width moves text off the layout computed for it, and only on the terminals
  nobody developing this is looking at. `…` is therefore `.` and not `...`,
  and `glyphs.py` asserts the rule at import.

A new glyph drawn by any cabinet belongs in `GROUPS`, in the group a player
reads it as part of. One that is not there goes through as mojibake — visibly,
which is the intended failure.

## Tests: `tests/engine/` is the engine's, `tests/test_cabinet.py` is the launcher's

The extraction brought the code across without its tests, leaving 24 modules
shipping untested behind a launcher suite that never touched them. The engine's
tests were ported from `texastoast/tests/` afterwards and live in
`tests/engine/`, one file per module, with imports rewritten.

Four of texastoast's files were **not** ported and should not be: `test_ui.py`,
`test_input.py`, `test_render_protocol.py` and `test_loop.py` drive moved
modules *through* parts that stayed behind — `input/keyboard.py`,
`render/canvas.py`, `core/game.py`. `tests/conftest.py` there is entirely
tkinter fixtures and must never be copied: this package has no tkinter
dependency and should not acquire one to run its tests. (`tests/conftest.py`
*here* is a different file and a legitimate one — a single fixture pointing
score reads at a temporary directory. It imports no GUI toolkit.)

**That is a reason not to copy those files, not a reason for the modules to go
untested**, and the two were conflated here until 0.5.0. What settles the
question now is `pytest --cov`, which CI runs once on ubuntu — see the
`coverage` job. The suite sits around 91%, most of it earned indirectly: the
launcher suite drives a real Textual app, so a module with no test file of its
own is usually still well covered. **Count lines, not files** — going by
files said `core/tui_game.py` was the worst hole in the engine, and going by
lines it was already at 82% while `input/abstract.py` sat at 59%.

`tests/engine/test_input_state.py` is what that second number produced: fresh
tests for the dataclass, written against the module directly rather than
ported through the keyboard backend that stayed behind. It is the shape any
further coverage work here should take.

`test_recording.py` was the fourth unported file, needing the `i2c` package.
It has no subject any more — `input/recording.py` was **deleted in 0.5.0**. It
was 148 statements at 0% coverage with no caller anywhere in this repo, which
coverage is what surfaced. texastoast still ships the module under Apache-2.0
for anyone who wants input recording; a second copy that nothing called and
nothing tested was not a spare, it was a liability.

Individual tests dropped during the port say so where they were, rather than
vanishing — see the notes at the foot of `tests/engine/test_no_hard_deps.py`
and the top of `tests/engine/test_scheduler.py`.

## AI Attribution

**No AI attribution.** Do not append `Co-Authored-By: Claude …`, "Generated with
…", or any similar trailer to commit messages, PR bodies, or release notes. If
your tooling adds such a line by default, remove it before committing.

## Games are never vendored here, and this package imports none of them

Each game lives in its own repo with its `web/`, `wii/` and `tui/` versions
together, and publishes its own wheel built from `tui/`. This repo holds the
launcher and the engine, and no games.

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

**That split is now backed by artifacts, not just by this paragraph.** Until
0.4.1 it was prose only — `NOTICE` said the whole repository was Noncommercial,
there was no Apache text anywhere, and the engine was therefore Noncommercial
under the only file that governed. There are now `LICENSE-APACHE` at the root,
`magmacrunch/engine/LICENSE`, an SPDX header on every engine module, and a
`NOTICE` that carves the exception out explicitly.

**A new file under `magmacrunch/engine/` needs the two-line SPDX header**, or
it ships under the wrong licence. `test_every_engine_file_says_it_is_apache`
in `tests/engine/test_no_hard_deps.py` is what catches you forgetting.
