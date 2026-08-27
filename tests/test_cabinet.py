"""The arcade floor, driven headlessly.

Textual's ``run_test`` pilot gives a real app with a real event loop and a real
size, so key handling, the frame loop and resize are exercised as they are in
play - no mocking of the parts most likely to break.

**The cabinets here are fakes, not the real games.** ``ArcadeGame`` is a
structural protocol, so a fake satisfies it by having the members; and a
launcher suite that only passes when two unrelated packages happen to be
installed is a worse suite. The real games are covered by their own repos.
"""

import asyncio

import pytest

pytest.importorskip("textual", reason='needs: pip install -e ".[dev]" with texastoast[tui]')

from texastoast.arcade import ArcadeGame, GameInfo  # noqa: E402
from texastoast.core.tui_host import TuiHost  # noqa: E402

from magmacrunch import theme  # noqa: E402
from magmacrunch.app import ARCADE_INFO, ArcadeApp  # noqa: E402
from magmacrunch.scenes import CabinetScene, min_rows_for  # noqa: E402

# ── Fakes ───────────────────────────────────────────────────────────


class FakeScene:
    """What a cabinet's ``start`` hands back."""

    def __init__(self, label="fake"):
        self.label = label

    def update(self, dt):
        pass

    def render(self):
        pass


class FakeGame:
    """A cabinet that starts, and remembers how often it was asked to."""

    def __init__(self, key="fake", title="Fake Cabinet", blurb="A fake.",
                 fps=20, hold_ms=0, min_cols=40, min_rows=12):
        self.info = GameInfo(key=key, title=title, blurb=blurb, fps=fps,
                             hold_ms=hold_ms, min_cols=min_cols,
                             min_rows=min_rows)
        self.starts = 0

    def start(self, host):
        self.starts += 1
        return FakeScene(self.info.key)


class BrokenGame(FakeGame):
    """A cabinet that is installed but will not run."""

    def start(self, host):
        raise RuntimeError("no such font")


def test_the_fakes_are_real_arcade_games():
    """If this drifts, every test below is testing the wrong shape."""
    assert isinstance(FakeGame(), ArcadeGame)
    assert isinstance(BrokenGame(), ArcadeGame)


# ── Harness ─────────────────────────────────────────────────────────


def settle(app: ArcadeApp) -> None:
    """Apply the stack's pending push/pop, which the engine defers a frame."""
    app.host.stack.update(0.0)


def arcade(*games) -> ArcadeApp:
    """A visit on a real host, built the way the command does."""
    host = TuiHost(title=ARCADE_INFO.title, fps=ARCADE_INFO.fps,
                   hold_ms=ARCADE_INFO.hold_ms)
    app = ArcadeApp(host, list(games))
    host.push_scene(app.root_scene)
    settle(app)
    return app


def two_cabinets() -> ArcadeApp:
    return arcade(
        FakeGame(key="alpha", title="Alpha Cabinet", blurb="The first one."),
        FakeGame(key="beta", title="Beta Cabinet", blurb="The second one."),
    )


def buffer_text(app: ArcadeApp) -> str:
    return app.host.game.surface.buffer.to_text()


async def _piloted(app: ArcadeApp, size=(80, 24)):
    from texastoast.core.tui_game import _GameApp

    textual_app = _GameApp(app.host.game, app.host.game.surface)
    app.host.game._app = textual_app
    return textual_app.run_test(size=size)


def run(coro):
    return asyncio.run(coro)


# ── The list ────────────────────────────────────────────────────────


def test_the_menu_is_the_bottom_of_the_stack():
    app = two_cabinets()
    assert isinstance(app.host.scene, CabinetScene)
    assert app.in_menu


def test_one_row_per_discovered_cabinet():
    app = two_cabinets()
    assert app.host.scene.menu.selected_index == 0

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            text = buffer_text(app)
            assert theme.BANNER in text
            assert "CHOOSE A CABINET" in text
            assert "Alpha Cabinet" in text
            assert "Beta Cabinet" in text
            app.host.quit()

    run(go())


def test_the_order_discovery_gave_is_the_order_shown():
    """discover() sorts by title; the menu must not re-sort or reverse it."""
    app = two_cabinets()
    scene = app.host.scene
    assert scene._highlighted.info.key == "alpha"
    scene.handle_key("down")
    assert scene._highlighted.info.key == "beta"


def test_the_blurb_of_the_highlighted_cabinet_is_shown():
    """GameInfo.blurb is otherwise unused, and a row of bare titles says
    nothing about what a cabinet is."""
    app = two_cabinets()

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            assert "The first one." in buffer_text(app)
            await pilot.press("down")
            await asyncio.sleep(0.25)
            assert "The second one." in buffer_text(app)
            app.host.quit()

    run(go())


# ── Seating ─────────────────────────────────────────────────────────


def test_choosing_a_cabinet_seats_it_over_the_menu():
    app = two_cabinets()
    app.host.scene.handle_key("enter")
    settle(app)
    assert not app.in_menu
    assert isinstance(app.host.scene, FakeScene)
    assert app.host.scene.label == "alpha"
    # The menu is still underneath, which is what leaving lands on.
    assert len(app.host.stack) == 2
    assert isinstance(app.host.stack.scenes[0], CabinetScene)


def test_the_cabinet_that_was_highlighted_is_the_one_that_starts():
    app = two_cabinets()
    scene = app.host.scene
    scene.handle_key("down")
    scene.handle_key("enter")
    settle(app)
    assert app.host.scene.label == "beta"


def test_leaving_a_cabinet_returns_to_the_menu():
    app = two_cabinets()
    app.host.scene.handle_key("enter")
    settle(app)

    # What a game does to say it is finished.
    app.host.pop_scene()
    settle(app)
    assert app.in_menu
    assert len(app.host.stack) == 1


def test_the_menu_is_usable_again_after_a_cabinet_is_popped():
    """Menu.confirm() hides the menu as it fires, so without on_resume the
    screen underneath comes back empty."""
    app = two_cabinets()
    app.host.scene.handle_key("enter")
    settle(app)
    app.host.pop_scene()
    settle(app)

    assert app.host.scene.menu.active
    app.host.scene.handle_key("enter")
    settle(app)
    assert not app.in_menu


def test_playing_a_cabinet_twice_is_two_runs():
    """start() is called per play, so a replay is a fresh game and not the
    state the last one was left in."""
    alpha = FakeGame(key="alpha", title="Alpha Cabinet")
    app = arcade(alpha)
    for _ in range(2):
        app.host.scene.handle_key("enter")
        settle(app)
        app.host.pop_scene()
        settle(app)
    assert alpha.starts == 2


def test_the_row_the_player_left_from_is_still_highlighted():
    app = two_cabinets()
    scene = app.host.scene
    scene.handle_key("down")
    scene.handle_key("enter")
    settle(app)
    app.host.pop_scene()
    settle(app)
    assert scene.menu.selected_index == 1


# ── Retuning ────────────────────────────────────────────────────────


def test_the_menu_takes_its_held_key_decay_back_when_a_cabinet_leaves():
    """The half of the retune that bites.

    ``TuiHost.seat()`` applies a game's ``hold_ms`` and nothing puts it back.
    Left alone, returning from a real-time cabinet would leave the menu
    inferring held keys from auto-repeat, and one arrow press would slide the
    selection down the list instead of stepping one row.

    Headless because ``apply`` sets the input source whether or not a loop is
    running. The frame-rate half needs a live loop and is piloted below.
    """
    app = arcade(FakeGame(key="fast", fps=30, hold_ms=120))
    app.host.scene.handle_key("enter")
    settle(app)
    assert app.host.game.input.hold_ms == 120

    app.host.pop_scene()
    settle(app)
    assert app.host.game.input.hold_ms == ARCADE_INFO.hold_ms


def test_the_menu_takes_its_frame_rate_back_when_a_cabinet_leaves():
    """The same for fps, which only exists once the loop is running."""
    app = arcade(FakeGame(key="fast", fps=30, hold_ms=120))

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.2)
            assert app.host.game.loop.target_fps == ARCADE_INFO.fps

            await pilot.press("enter")
            await asyncio.sleep(0.2)
            assert app.host.game.loop.target_fps == 30, "seat() did not retune"

            app.host.pop_scene()
            await asyncio.sleep(0.2)
            assert app.host.game.loop.target_fps == ARCADE_INFO.fps
            app.host.quit()

    run(go())


# ── Fit-gating ──────────────────────────────────────────────────────


def test_a_cabinet_too_big_for_the_window_cannot_be_chosen():
    huge = FakeGame(key="huge", title="Huge Cabinet", min_cols=500, min_rows=500)
    app = arcade(FakeGame(key="alpha", title="Alpha Cabinet"), huge)
    scene = app.host.scene

    scene.update(0.0)
    assert scene.menu._items[1]["enabled"] is False

    # Selecting it and confirming must seat nothing, not seat it anyway.
    scene.menu._selected = 1
    scene.handle_key("enter")
    settle(app)
    assert app.in_menu
    assert huge.starts == 0


def test_a_cabinet_that_fits_again_comes_back():
    """Fit is re-asked every frame, so growing the window re-enables the row
    without the menu being rebuilt."""
    game = FakeGame(key="alpha", min_cols=500, min_rows=500)
    app = arcade(game)
    scene = app.host.scene

    scene.update(0.0)
    assert scene.menu._items[0]["enabled"] is False

    object.__setattr__(game, "info", GameInfo(key="alpha", title="Alpha",
                                              blurb="x", min_cols=1, min_rows=1))
    scene.update(0.0)
    assert scene.menu._items[0]["enabled"] is True


def test_a_greyed_row_says_what_it_wants():
    """A disabled row with no explanation is a bug report waiting to happen."""
    app = arcade(FakeGame(key="huge", title="Huge Cabinet",
                          min_cols=500, min_rows=500))

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            text = buffer_text(app)
            assert "500x500" in text
            app.host.quit()

    run(go())


# ── Cabinets that will not run ──────────────────────────────────────


def test_a_cabinet_that_will_not_start_does_not_end_the_session():
    """discover() already refuses to let one broken game take down the menu.
    start() is the later moment the same thing can happen, with the terminal
    live."""
    broken = BrokenGame(key="broken", title="Broken Cabinet")
    app = arcade(broken, FakeGame(key="fine", title="Fine Cabinet"))

    app.host.scene.handle_key("enter")
    settle(app)
    assert app.in_menu
    assert len(app.host.stack) == 1
    assert "Broken Cabinet" in app.error
    assert "no such font" in app.error


def test_the_menu_is_still_armed_after_a_cabinet_fails_to_start():
    """Nothing was pushed, so nothing pops and no on_resume fires. Without a
    re-arm the floor is left blank under the error."""
    app = arcade(BrokenGame(key="broken"), FakeGame(key="fine"))
    scene = app.host.scene
    scene.handle_key("enter")
    settle(app)
    assert scene.menu.active

    scene.handle_key("down")
    scene.handle_key("enter")
    settle(app)
    assert not app.in_menu


def test_the_failure_is_shown_on_the_floor():
    app = arcade(BrokenGame(key="broken", title="Broken Cabinet"))

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await asyncio.sleep(0.25)
            assert "would not start" in buffer_text(app)
            app.host.quit()

    run(go())


def test_a_later_success_clears_the_error():
    app = arcade(BrokenGame(key="broken"), FakeGame(key="fine"))
    scene = app.host.scene
    scene.handle_key("enter")
    settle(app)
    assert app.error

    scene.handle_key("down")
    scene.handle_key("enter")
    settle(app)
    assert app.error == ""


# ── An empty floor ──────────────────────────────────────────────────


def test_an_empty_arcade_says_so_rather_than_drawing_nothing():
    """Menu.show([]) returns early and leaves the menu inactive, so without
    this the screen is blank."""
    app = arcade()

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            text = buffer_text(app)
            assert "No cabinets installed" in text
            assert "pip install magmacrunch-george-boole" in text
            app.host.quit()

    run(go())


def test_an_empty_arcade_still_takes_keys():
    app = arcade()
    scene = app.host.scene
    assert scene.handle_key("down") is True   # moves nothing, but is not a crash
    scene.update(0.0)
    assert app.in_menu


# ── Leaving ─────────────────────────────────────────────────────────


def test_escape_on_the_floor_ends_the_session():
    """The bottom of the stack, so the same call a cabinet makes to go back
    goes out instead - see TuiHost.pop_scene."""
    app = two_cabinets()
    quits = []
    app.host.quit = lambda: quits.append("quit")

    app.host.scene.handle_key("escape")
    settle(app)
    assert quits == ["quit"]
    # And it went out rather than emptying the stack under itself.
    assert len(app.host.stack) == 1


def test_q_quits_from_the_floor():
    app = two_cabinets()
    quits = []
    app.host.quit = lambda: quits.append("quit")

    app.host.scene.handle_key("q")
    assert quits == ["quit"]


def test_an_unknown_key_is_not_swallowed():
    app = two_cabinets()
    assert app.host.scene.handle_key("z") is False


# ── The floor is lower than any cabinet's ───────────────────────────


def test_the_arcade_asks_for_less_room_than_the_games_it_seats():
    """An arcade that refuses to draw in a window where its games would run is
    worse than useless."""
    assert theme.MIN_COLS < 58
    assert min_rows_for(3) < 20


def test_the_floor_grows_with_the_number_of_cabinets():
    assert min_rows_for(4) - min_rows_for(1) == 3 * theme.MENU_ITEM_H


def test_a_terminal_below_the_floor_is_told_so_rather_than_drawn_in():
    app = two_cabinets()

    async def go():
        async with await _piloted(app, size=(30, 10)) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            text = buffer_text(app)
            assert "too small" in text
            assert "CHOOSE A CABINET" not in text
            app.host.quit()

    run(go())


# ── --list ──────────────────────────────────────────────────────────


def test_list_names_every_cabinet_and_what_it_wants(capsys):
    from magmacrunch.__main__ import _print

    _print([FakeGame(key="alpha", title="Alpha Cabinet", blurb="The first one.",
                     min_cols=64, min_rows=21, fps=30, hold_ms=120)])
    out = capsys.readouterr().out
    assert "alpha" in out
    assert "Alpha Cabinet" in out
    assert "The first one." in out
    assert "64x21" in out
    assert "30 fps" in out
    assert "120 ms" in out


def test_list_says_how_to_get_a_cabinet_when_there_are_none(capsys):
    from magmacrunch.__main__ import _print

    _print([])
    out = capsys.readouterr().out
    assert "No cabinets installed" in out
    assert "pip install magmacrunch-george-boole" in out


def test_a_blurb_full_of_glyphs_does_not_kill_the_listing(tmp_path):
    """Titles and blurbs are written by whoever wrote the game. Redirected to
    a file on a legacy Windows codepage, a card glyph is a UnicodeEncodeError
    - and a diagnostic that dies on what it is diagnosing is useless."""
    import subprocess
    import sys

    script = tmp_path / "listing.py"
    script.write_text(
        "from texastoast.arcade import GameInfo\n"
        "from magmacrunch.__main__ import _print\n"
        "class G:\n"
        "    info = GameInfo(key='g', title='Deck \\U0001F0A1',\n"
        "                    blurb='cards \\U0001F0A1 and \\u2014 dashes')\n"
        "_print([G()])\n",
        encoding="utf-8",
    )
    out = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True,
        env={"PYTHONIOENCODING": "cp1252:strict", "PATH": ""},
    )
    assert out.returncode == 0, out.stderr
    assert "Deck" in out.stdout


# ── The no-import-edge rule ─────────────────────────────────────────


def test_the_launcher_imports_no_game():
    """The whole package, not just the seam: games are found by entry point
    and never imported. This is what keeps an arcade with nothing installed a
    working program rather than an ImportError. See AGENTS.md."""
    import subprocess
    import sys

    code = (
        "import sys, magmacrunch, magmacrunch.app, magmacrunch.scenes, "
        "magmacrunch.__main__; "
        "leaked = [m for m in ('boole', 'lavadome') if m in sys.modules]; "
        "print(leaked)"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                         text=True, check=True)
    assert out.stdout.strip() == "[]", out.stdout
