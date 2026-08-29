"""Importing the engine must not drag Textual in with it.

Inherited from texastoast, where Textual was an optional extra and the engine
declared no required dependencies at all. Here it is a hard dependency, so the
question is no longer "does it still work without Textual" — it is **when**
Textual gets imported.

That still matters, and for two reasons. ``magmacrunch --list`` and the
`magmacrunch.games` discovery it drives never draw anything, and should not pay
to start a terminal framework in order to print a table. And the cell buffer
and renderer are deliberately separable from the Textual host — the split a
hand-written ANSI backend would reuse — which is only true for as long as
nothing imports upward. Both are properties of import time, which is what these
measure.

Each check runs in a subprocess: once the test session has imported Textual for
the backend tests, ``sys.modules`` in *this* process can no longer answer the
question.
"""

import subprocess
import sys
import textwrap

import pytest


def _probe(body: str) -> str:
    """Run ``body`` in a clean interpreter and return its stdout."""
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(body)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        pytest.fail(f"probe failed:\n{result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def test_importing_the_engine_starts_no_terminal_framework():
    out = _probe("""
        import sys
        import magmacrunch.engine
        loaded = [m for m in ("textual", "rich") if m in sys.modules]
        print(",".join(loaded))
    """)
    assert out == "", f"import magmacrunch.engine pulled in: {out}"


def test_importing_render_pulls_no_backend():
    out = _probe("""
        import sys
        import magmacrunch.engine.render
        loaded = [m for m in ("textual", "rich") if m in sys.modules]
        print(",".join(loaded))
    """)
    assert out == "", f"import magmacrunch.engine.render pulled in: {out}"


def test_the_cell_buffer_is_reachable_without_the_host():
    # The half of the terminal backend a future ANSI stack reuses. If this ever
    # needs Textual, the split has failed.
    out = _probe("""
        import sys
        from magmacrunch.engine.render.cellbuffer import CellBuffer
        buf = CellBuffer(4, 1)
        buf.write(0, 0, "ok")
        print(buf.to_text(), "textual" in sys.modules, "rich" in sys.modules)
    """)
    assert out == "ok False False"


def test_the_tui_renderer_is_reachable_with_no_terminal_library():
    # TuiRenderer draws into a buffer and flushes to an injected surface, so it
    # is usable — and testable — without Textual present.
    out = _probe("""
        import sys
        from magmacrunch.engine.render.tui import TuiRenderer
        r = TuiRenderer(6, 1)
        r.draw_hud_text(0, 0, "hi")
        r.present()
        print(r.to_text(), "textual" in sys.modules, "curses" in sys.modules)
    """)
    assert out == "hi False False"


def test_the_scheduler_protocol_needs_nothing():
    out = _probe("""
        import sys
        from magmacrunch.engine.core.scheduler import ManualScheduler, Scheduler
        print(isinstance(ManualScheduler(), Scheduler), "textual" in sys.modules)
    """)
    assert out == "True False"


def test_the_game_loop_runs_with_no_host_at_all():
    # The point of naming the Scheduler seam: the loop is driven by whatever
    # satisfies it, so a test can run a real one to completion in no time.
    out = _probe("""
        import sys
        from magmacrunch.engine.core.loop import GameLoop
        from magmacrunch.engine.core.scheduler import ManualScheduler
        sched = ManualScheduler()
        ticks = []
        loop = GameLoop(sched, lambda dt: ticks.append(dt), lambda: None, fps=30)
        loop.start()
        sched.tick(3)
        loop.stop()
        print(len(ticks), "textual" in sys.modules)
    """)
    assert out == "4 False"


# texastoast had one more check here: asking it for `TuiGame` with the extra
# uninstalled had to raise an ImportError naming `texastoast[tui]` rather than a
# bare ModuleNotFoundError. It is not ported because both halves of it are gone
# — there is no extra to leave out, Textual being a hard requirement, and
# `magmacrunch.engine` exposes no lazily-resolved TuiGame attribute to ask for.
# A test whose premise no longer exists is worse than no test.


# ── The licence split, as an artifact rather than a paragraph ───────


def test_every_engine_file_says_it_is_apache():
    """The engine is Apache-2.0 and the launcher is not, and a file that does
    not say so ships under the wrong one.

    Until 0.4.1 the split was prose in README and AGENTS.md with nothing
    behind it: NOTICE said the whole repository was Noncommercial, and no
    Apache text existed anywhere in the tree. Adding the header to every file
    once fixes that day; this is what keeps the next file from missing it.
    """
    import pathlib

    engine = pathlib.Path(__file__).resolve().parent.parent.parent / "magmacrunch" / "engine"
    missing = [
        path.name
        for path in sorted(engine.rglob("*.py"))
        if "SPDX-License-Identifier: Apache-2.0"
        not in path.read_text(encoding="utf-8")[:200]
    ]
    assert not missing, f"engine files with no SPDX header: {missing}"


def test_the_launcher_is_not_tagged_apache():
    """The header belongs to the engine, not to everything.

    A blanket sweep that tagged `magmacrunch/*.py` too would relicense the
    launcher by accident, and the mistake would look exactly like the fix.
    """
    import pathlib

    package = pathlib.Path(__file__).resolve().parent.parent.parent / "magmacrunch"
    mistagged = [
        path.name
        for path in sorted(package.glob("*.py"))
        if "Apache-2.0" in path.read_text(encoding="utf-8")[:200]
    ]
    assert not mistagged, f"launcher files tagged Apache: {mistagged}"


def test_both_licence_files_exist():
    """NOTICE names them; a missing one makes it a promise rather than a fact."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent.parent
    assert (root / "LICENSE").is_file()
    assert (root / "LICENSE-APACHE").is_file()
    assert (root / "magmacrunch" / "engine" / "LICENSE").is_file()
    assert "Apache License" in (root / "LICENSE-APACHE").read_text(encoding="utf-8")
