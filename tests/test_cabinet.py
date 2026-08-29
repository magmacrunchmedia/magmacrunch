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

pytest.importorskip("textual", reason='needs: pip install -e ".[dev]"')

from magmacrunch import banner, cards, theme  # noqa: E402
from magmacrunch.app import ARCADE_INFO, ArcadeApp  # noqa: E402
from magmacrunch.engine.arcade import ArcadeGame, GameInfo  # noqa: E402
from magmacrunch.engine.core.tui_host import TuiHost  # noqa: E402
from magmacrunch.scenes import CabinetScene  # noqa: E402

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
                 fps=20, hold_ms=0, min_cols=40, min_rows=12, accent=""):
        self.info = GameInfo(key=key, title=title, blurb=blurb, fps=fps,
                             hold_ms=hold_ms, min_cols=min_cols,
                             min_rows=min_rows, accent=accent)
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


def colours(app: ArcadeApp) -> set:
    buf = app.host.game.surface.buffer
    return {buf.get(x, y).fg
            for y in range(buf.height) for x in range(buf.width)
            if buf.get(x, y).fg}


async def _piloted(app: ArcadeApp, size=(80, 24)):
    from magmacrunch.engine.core.tui_game import _GameApp

    textual_app = _GameApp(app.host.game, app.host.game.surface)
    app.host.game._app = textual_app
    return textual_app.run_test(size=size)


def run(coro):
    return asyncio.run(coro)


# ── The grid ────────────────────────────────────────────────────────


def test_the_floor_is_the_bottom_of_the_stack():
    app = two_cabinets()
    assert isinstance(app.host.scene, CabinetScene)
    assert app.in_menu


def test_one_card_per_discovered_cabinet():
    app = two_cabinets()

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            text = buffer_text(app)
            assert "Alpha Cabinet" in text
            assert "Beta Cabinet" in text
            # Both blurbs, which a one-line-per-game list had no room for.
            assert "The first one." in text
            assert "The second one." in text
            # Two card borders.
            assert text.count(cards.TL) == 2
            app.host.quit()

    run(go())


def test_the_order_discovery_gave_is_the_order_shown():
    """discover() sorts by title; the floor must not re-sort or reverse it."""
    app = two_cabinets()
    scene = app.host.scene
    assert scene.highlighted.info.key == "alpha"
    scene.handle_key("right")
    assert scene.highlighted.info.key == "beta"


def test_left_and_right_step_one_card():
    app = two_cabinets()
    scene = app.host.scene
    scene.handle_key("right")
    assert scene.selected == 1
    scene.handle_key("left")
    assert scene.selected == 0


def test_the_selection_wraps():
    app = two_cabinets()
    scene = app.host.scene
    scene.handle_key("left")
    assert scene.selected == 1


def test_up_and_down_move_a_whole_row_not_one_card():
    """A grid where down moves one card is a list wearing a grid's clothes."""
    app = arcade(*[FakeGame(key=f"g{i}", title=f"Cabinet {i}") for i in range(4)])

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            scene = app.host.scene
            assert cards.columns(80) == 2
            await pilot.press("down")
            await asyncio.sleep(0.15)
            assert scene.selected == 2
            app.host.quit()

    run(go())


# ── Seating ─────────────────────────────────────────────────────────


def test_choosing_a_cabinet_seats_it_over_the_floor():
    app = two_cabinets()
    app.host.scene.handle_key("enter")
    settle(app)
    assert not app.in_menu
    assert isinstance(app.host.scene, FakeScene)
    assert app.host.scene.label == "alpha"
    # The floor is still underneath, which is what leaving lands on.
    assert len(app.host.stack) == 2
    assert isinstance(app.host.stack.scenes[0], CabinetScene)


def test_the_card_that_was_selected_is_the_one_that_starts():
    app = two_cabinets()
    scene = app.host.scene
    scene.handle_key("right")
    scene.handle_key("enter")
    settle(app)
    assert app.host.scene.label == "beta"


def test_leaving_a_cabinet_returns_to_the_floor():
    app = two_cabinets()
    app.host.scene.handle_key("enter")
    settle(app)

    # What a game does to say it is finished.
    app.host.pop_scene()
    settle(app)
    assert app.in_menu
    assert len(app.host.stack) == 1


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


def test_the_card_the_player_left_from_is_still_selected():
    app = two_cabinets()
    scene = app.host.scene
    scene.handle_key("right")
    scene.handle_key("enter")
    settle(app)
    app.host.pop_scene()
    settle(app)
    assert scene.selected == 1


# ── Retuning ────────────────────────────────────────────────────────


def test_the_floor_takes_its_held_key_decay_back_when_a_cabinet_leaves():
    """The half of the retune that bites.

    ``TuiHost.seat()`` applies a game's ``hold_ms`` and nothing puts it back.
    Left alone, returning from a real-time cabinet would leave the floor
    inferring held keys from auto-repeat, and one arrow press would skate the
    cursor across the grid instead of stepping one card.

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


def test_the_floor_takes_its_frame_rate_back_when_a_cabinet_leaves():
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

    scene.selected = 1
    assert scene._enabled(huge) is False
    scene.handle_key("enter")
    settle(app)
    assert app.in_menu
    assert huge.starts == 0


def test_a_cabinet_that_fits_again_can_be_chosen():
    """Fit is asked at the moment it is needed, so growing the window takes
    effect in the same frame rather than after a rebuild."""
    game = FakeGame(key="alpha", min_cols=500, min_rows=500)
    app = arcade(game)
    scene = app.host.scene
    assert scene._enabled(game) is False

    game.info = GameInfo(key="alpha", title="Alpha", blurb="x",
                         min_cols=1, min_rows=1)
    assert scene._enabled(game) is True
    scene.handle_key("enter")
    settle(app)
    assert game.starts == 1


def test_a_card_that_does_not_fit_says_what_it_wants():
    """A greyed card with no explanation is a bug report waiting to happen."""
    app = arcade(FakeGame(key="huge", title="Huge Cabinet",
                          min_cols=500, min_rows=500))

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            text = buffer_text(app)
            assert "500x500" in text
            assert "TOO BIG" in text
            app.host.quit()

    run(go())


# ── Cabinets that will not run ──────────────────────────────────────


def test_a_cabinet_that_will_not_start_does_not_end_the_session():
    """discover() already refuses to let one broken game take down the floor.
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


def test_the_floor_still_works_after_a_cabinet_fails_to_start():
    app = arcade(BrokenGame(key="broken"), FakeGame(key="fine"))
    scene = app.host.scene
    scene.handle_key("enter")
    settle(app)

    scene.handle_key("right")
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

    scene.handle_key("right")
    scene.handle_key("enter")
    settle(app)
    assert app.error == ""


# ── An empty floor ──────────────────────────────────────────────────


def test_an_empty_arcade_says_so_rather_than_drawing_nothing():
    app = arcade()

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            text = buffer_text(app)
            assert "NO CABINETS INSTALLED" in text
            assert "pip install magmacrunch-george-boole" in text
            assert cards.TL not in text
            app.host.quit()

    run(go())


def test_an_empty_arcade_still_takes_keys():
    app = arcade()
    scene = app.host.scene
    assert scene.handle_key("right") is True   # moves nothing, but is not a crash
    assert scene.highlighted is None
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


# ── Layout ──────────────────────────────────────────────────────────


def test_two_columns_when_there_is_room_and_one_when_there_is_not():
    assert cards.columns(80) == 2
    assert cards.columns(theme.MIN_COLS) == 1


def test_the_grid_never_goes_wider_than_two():
    """.game-grid is repeat(2, 1fr) until 1100px, and a terminal is never the
    wide case."""
    assert cards.columns(500) == theme.MAX_COLS


def test_cards_are_laid_out_left_to_right_then_down():
    slots = cards.layout(4, 0, 80, 40)
    assert [(s.index, s.x > slots[0].x, s.y > slots[0].y) for s in slots] == [
        (0, False, False), (1, True, False), (2, False, True), (3, True, True),
    ]


def test_the_grid_is_centred_in_the_window():
    slots = cards.layout(2, 0, 80, 40)
    left = slots[0].x
    right = slots[1].x + theme.CARD_W
    assert left == 80 - right, "grid is not centred"


def test_cabinets_past_the_first_page_are_not_drawn_over_the_chrome():
    """Six cabinets in a window with room for two: the four that do not fit
    are simply not placed, rather than running off the bottom."""
    slots = cards.layout(6, 0, 80, theme.CARD_H)
    assert len(slots) == 2
    assert cards.pages(6, 80, theme.CARD_H) == 3


def test_the_page_follows_the_selection():
    assert cards.page_start(0, 2) == 0
    assert cards.page_start(1, 2) == 0
    assert cards.page_start(2, 2) == 2
    assert cards.page_start(5, 2) == 4


def test_a_page_indicator_appears_only_when_there_is_more_than_one_page():
    many = [FakeGame(key=f"g{i}", title=f"Cabinet {i}") for i in range(8)]

    async def go(games, expected):
        app = arcade(*games)
        async with await _piloted(app, size=(80, 24)) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            assert ("PAGE" in buffer_text(app)) is expected
            app.host.quit()

    run(go(many, True))
    run(go(many[:2], False))


# ── The floor is lower than any cabinet's ───────────────────────────


def test_the_arcade_asks_for_less_room_than_the_games_it_seats():
    """An arcade that refuses to draw in a window where its games would run is
    worse than useless. Both shipped cabinets want about 58x22."""
    assert theme.MIN_COLS < 58
    assert theme.MIN_ROWS < 22


def test_a_terminal_below_the_floor_is_told_so_rather_than_drawn_in():
    app = two_cabinets()

    async def go():
        async with await _piloted(app, size=(30, 10)) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            text = buffer_text(app)
            assert "TOO SMALL" in text
            assert cards.TL not in text
            app.host.quit()

    run(go())


# ── The banner ──────────────────────────────────────────────────────


def _chose(art: str, cols: int, rows: int) -> bool:
    """Whether best_fit picked ``art``. Compared right-stripped, because what
    comes back is padded to the block's width."""
    got = [line.rstrip() for line in banner.best_fit(cols, rows)]
    return got == [line.rstrip() for line in banner.lines(art)]


def _budget(height: int) -> int:
    """The rows the scene leaves the banner at this window height."""
    return height - (theme.HEADER_ROWS + theme.CARD_H + theme.FOOTER_ROWS + 2)


def test_the_banner_stands_down_before_the_cabinets_do():
    """Best art that fits, in order, down to one line rather than none."""
    assert _chose(banner.FULL, 128, _budget(40))
    assert _chose(banner.STACK, 78, _budget(32))
    assert _chose(banner.CHUNKY, 78, _budget(24))
    assert _chose(banner.ARCADE, 70, _budget(24))
    assert _chose(banner.BLOCK, 58, _budget(22))
    # WORDMARK earns its place in the six columns between BLOCK's 54 and its
    # own 48 - the only band where the two-row face is the last art standing.
    assert _chose(banner.WORDMARK, 50, _budget(22))
    assert _chose(banner.PLAIN, 38, _budget(18))
    assert banner.best_fit(20, 8) == []


def test_the_arcade_and_the_cabinets_are_lettered_in_the_same_face():
    """BLOCK comes from magmacrunch.engine.ui.bigtext, which is where George Boole and
    Lava Dome get their titles too."""
    from magmacrunch.engine.ui import bigtext

    assert banner.BLOCK == bigtext.block("MAGMACRUNCH")


def test_a_standard_terminal_gets_a_wordmark():
    """80x24 is the case that matters, and it should say what the program is
    called rather than settling for spaced capitals."""
    got = banner.best_fit(78, _budget(24))
    assert got, "a standard terminal should get a banner"
    assert banner.size("\n".join(got))[1] >= 4, "not just a single line"


def test_the_banner_never_takes_room_the_cards_need():
    """The invariant the ladder exists for: whatever is chosen, one row of
    cards and the chrome still fit underneath it."""
    for width, height in ((80, 24), (80, 32), (128, 40), (70, 24), (58, 22),
                          (theme.MIN_COLS, theme.MIN_ROWS)):
        art = banner.best_fit(width - 2, _budget(height))
        used = len(art) + theme.HEADER_ROWS + theme.CARD_H + theme.FOOTER_ROWS + 2
        assert used <= height, f"banner crowds out the cards at {width}x{height}"


def test_whatever_is_chosen_actually_fits_the_window():
    """FULL is 119 columns on purpose - wider than a terminal, and harmless
    because art is measured rather than trusted. This is what makes that safe."""
    assert banner.size(banner.FULL)[0] > 80
    for width, height in ((80, 24), (80, 32), (70, 24), (58, 22), (40, 18)):
        art = banner.best_fit(width - 2, _budget(height))
        for line in art:
            assert len(line) <= width - 2


def test_the_banner_comes_back_padded_so_the_block_stays_square():
    """Centring each line by its own length raggeds the block apart - the top
    line of WELCOME is mostly leading space."""
    got = banner.best_fit(80, 8)
    assert len({len(line) for line in got}) == 1


def test_stacked_art_is_composed_from_the_pieces_not_copied():
    """STACK and HERO are built by over(), so they cannot drift from the art
    they are made of."""
    for line in banner.lines(banner.CHUNKY):
        assert line.strip() in banner.STACK
    for line in banner.lines(banner.ARCADE):
        assert line.strip() in banner.STACK
        assert line.strip() in banner.HERO


def test_over_centres_each_block_rather_than_each_line():
    wide = "####\n#"
    narrow = "##"
    stacked = banner.lines(banner.over(wide, narrow))
    assert stacked == ["####", "#   ", "    ", " ## "]


# ── The credits ─────────────────────────────────────────────────────


def test_the_floor_is_signed():
    app = two_cabinets()

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            text = buffer_text(app)
            assert theme.COPYRIGHT in text
            assert theme.DOMAIN in text
            app.host.quit()

    run(go())


def test_the_domain_wears_the_link_colour():
    """.credits-row a { color: #00f0ff } - the domain is the one part of the
    signature the web page treats as a link."""
    app = two_cabinets()

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            buf = app.host.game.surface.buffer
            y = buf.height - 2
            used = {buf.get(x, y).fg for x in range(buf.width)
                    if buf.get(x, y).char.strip()}
            assert used == {theme.CARD_BORDER, theme.CYAN}
            app.host.quit()

    run(go())


def test_a_narrow_window_keeps_the_copyright_and_drops_the_domain():
    """Both on one line needs 41 columns; the floor goes down to 36."""
    app = two_cabinets()

    async def go():
        async with await _piloted(app, size=(theme.MIN_COLS, 20)) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            text = buffer_text(app)
            assert theme.COPYRIGHT in text
            assert theme.DOMAIN not in text
            app.host.quit()

    run(go())


def test_an_empty_floor_is_signed_too():
    """The footer is chrome, not something the cards carry."""
    app = arcade()

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            assert theme.COPYRIGHT in buffer_text(app)
            app.host.quit()

    run(go())


# ── The arcade's own colours ────────────────────────────────────────


def test_the_floor_is_painted_in_the_web_arcades_palette():
    """The banner and the tagline come from the selected cabinet now.

    Not from a constant: the floor takes the colour of whatever you are
    standing in front of. With nothing declared that is still the cycled
    position colour, so the first cabinet's floor is the cyan it always was —
    what changed is where the colour comes from, not what it is here.
    """
    app = two_cabinets()
    floor = theme.floor(theme.accent(0))

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            used = colours(app)
            assert theme.CYAN in used, "banner"
            assert floor.accent == theme.CYAN
            assert floor.tagline in used, "tagline"
            assert theme.CARD_TITLE in used, "card titles"
            assert theme.MUTED in used, "card blurbs"
            app.host.quit()

    run(go())


def test_the_floor_retints_as_the_selection_moves():
    """The arcade's version of what a cabinet does inside itself.

    george-boole dresses every bit mode as a different console; the menu that
    seats it should not be the one screen that stays the same no matter what
    is highlighted.
    """
    app = arcade(
        FakeGame(key="alpha", title="Alpha", blurb="One.", accent="#39ff6e"),
        FakeGame(key="beta", title="Beta", blurb="Two.", accent="#ff2e9c"),
    )
    scene = app.host.scene

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            assert scene._floor().accent == "#39ff6e"
            assert "#39ff6e" in colours(app), "banner in the first accent"

            # Right, not down: two cabinets sit side by side in the grid.
            scene.handle_key("right")
            await asyncio.sleep(0.25)
            assert scene._floor().accent == "#ff2e9c"
            assert "#ff2e9c" in colours(app), "banner in the second accent"
            app.host.quit()

    run(go())


def test_a_cabinet_that_declares_no_colour_keeps_its_position_one():
    """The fallback that lets an older cabinet stay unbroken.

    ``GameInfo.accent`` is new, and a game built against an engine that
    predates it does not set it. That must look deliberate rather than
    broken, which is the same arrangement ``score_key`` has.
    """
    app = two_cabinets()
    scene = app.host.scene
    assert not app.games[0].info.accent
    assert scene._accent(0) == theme.accent(0)
    assert scene._accent(1) == theme.accent(1)


def test_a_declared_colour_wins_over_the_position_one():
    app = arcade(FakeGame(key="alpha", accent="#abcdef"))
    assert app.host.scene._accent(0) == "#abcdef"


def test_an_empty_floor_still_has_a_colour():
    # Nothing to take one from, and a crash here would be a screen that only
    # appears on a machine with no cabinets installed — the least tested one.
    app = arcade()
    assert app.host.scene._floor().accent == theme.CYAN


def test_the_selected_card_wears_its_accent_and_the_others_do_not():
    """.game-card:hover { border-color: var(--card-color) } - the border is
    how the web page says which card the pointer is on."""
    app = two_cabinets()

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            buf = app.host.game.surface.buffer
            corners = [(x, y) for y in range(buf.height) for x in range(buf.width)
                       if buf.get(x, y).char == cards.TL]
            assert len(corners) == 2
            fills = [buf.get(x, y).fg for x, y in corners]
            assert fills[0] == theme.accent(0)
            assert fills[1] == theme.CARD_BORDER

            await pilot.press("right")
            await asyncio.sleep(0.25)
            fills = [buf.get(x, y).fg for x, y in corners]
            assert fills[0] == theme.CARD_BORDER
            assert fills[1] == theme.accent(1)
            app.host.quit()

    run(go())


def test_each_cabinet_gets_its_own_accent():
    assert theme.accent(0) != theme.accent(1)
    assert theme.accent(0) == theme.accent(len(theme.ACCENTS))


def test_the_cursor_blinks_only_on_the_selected_card():
    """.card-arrow is opacity 0 until :hover, and a grid where every card
    blinks says nothing about which one Enter would start."""
    app = two_cabinets()
    scene = app.host.scene
    scene.elapsed = 0.0
    assert scene._blink(theme.BLINK_SECONDS) is True
    scene.elapsed = theme.BLINK_SECONDS * 0.75
    assert scene._blink(theme.BLINK_SECONDS) is False

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            # However the blink lands this frame, at most one card shows it.
            assert buffer_text(app).count(theme.PLAY + "_") <= 1
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
    import os
    import subprocess
    import sys

    script = tmp_path / "listing.py"
    script.write_text(
        "from magmacrunch.engine.arcade import GameInfo\n"
        "from magmacrunch.__main__ import _print\n"
        "class G:\n"
        "    info = GameInfo(key='g', title='Deck \\U0001F0A1',\n"
        "                    blurb='cards \\U0001F0A1 and \\u2014 dashes')\n"
        "_print([G()])\n",
        encoding="utf-8",
    )
    # The child is told to write cp1252, so the parent has to read cp1252.
    # Decoding its bytes as UTF-8 blows up on the em-dash (0x97) — which is a
    # failure of this test, not of the thing it is testing, and one that hides
    # on a Windows box whose own default happens to be cp1252.
    # Inherit the environment rather than replacing it. A child handed only
    # those two names cannot start at all on Windows before 3.11, where seeding
    # hash randomisation goes through an API that wants SystemRoot: the process
    # dies in preinit with "failed to get random numbers" and this test reports
    # it as a listing failure, which is a lie about what broke. PYTHONUTF8 is
    # pinned off because an inherited UTF-8 mode would quietly undo the very
    # codepage the test exists to reproduce.
    out = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True,
        encoding="cp1252", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "cp1252:strict", "PYTHONUTF8": "0"},
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

    # All three cabinets' modules, not two: this guard listed `boole` and
    # `lavadome` and would have stayed green through an import of `drift`.
    code = (
        "import sys, magmacrunch, magmacrunch.app, magmacrunch.banner, "
        "magmacrunch.cabinets, magmacrunch.cards, magmacrunch.scenes, "
        "magmacrunch.theme, magmacrunch.__main__; "
        "leaked = [m for m in ('boole', 'lavadome', 'drift') "
        "if m in sys.modules]; "
        "print(leaked)"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                         text=True, check=True)
    assert out.stdout.strip() == "[]", out.stdout


# ── What the package says about itself ──────────────────────────────


def _pyproject() -> dict:
    """The packaging metadata, read from source.

    ``tomllib`` is 3.11; this package supports 3.10. Skipping there rather
    than taking a ``tomli`` dependency for one test is the cheaper trade — the
    CI matrix runs 3.14 as well, so the check still gates every push.
    """
    import pathlib
    import sys

    if sys.version_info < (3, 11):
        pytest.skip("tomllib is 3.11+")
    import tomllib

    root = pathlib.Path(__file__).resolve().parent.parent
    return tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))


def test_the_version_is_the_one_the_package_declares():
    """``__version__`` and pyproject must agree.

    They did not, for a whole release: the literal sat at 0.3.0 while 0.4.0
    shipped. The release workflow compares the git tag against pyproject and
    never looks at the module, so nothing caught it — and nothing read
    ``__version__`` either, which is why it could rot unnoticed. Both halves
    of that are fixed: this is the check, and ``--version`` is the reader.
    """
    import magmacrunch

    assert magmacrunch.__version__ == _pyproject()["project"]["version"]


def test_version_prints_it(capsys, monkeypatch):
    """``--version`` is what makes the literal load-bearing rather than
    decorative, which is the half of the fix a test alone does not give."""
    import sys

    import magmacrunch
    from magmacrunch.__main__ import main

    monkeypatch.setattr(sys, "argv", ["magmacrunch", "--version"])
    with pytest.raises(SystemExit) as exit_info:
        main()
    assert exit_info.value.code == 0
    assert magmacrunch.__version__ in capsys.readouterr().out


# ── The empty floor names every cabinet ─────────────────────────────


def test_the_floor_and_the_listing_suggest_the_same_cabinets(capsys):
    """Two screens say how to get a cabinet, and they had drifted.

    Each named two of the three, omitting moonlight-drift - on precisely the
    screen that exists because the player has none and needs to be told what
    to install. They now read one tuple; this is what keeps them doing so.
    """
    from magmacrunch.__main__ import _print
    from magmacrunch.cabinets import PACKAGES
    from magmacrunch.scenes import EMPTY_FLOOR

    floor = "\n".join(EMPTY_FLOOR)
    _print([])
    listing = capsys.readouterr().out

    for name in PACKAGES:
        assert f"pip install {name}" in floor
        assert f"pip install {name}" in listing


def test_the_empty_floor_names_every_cabinet_the_arcade_installs():
    """The suggestions and the dependency list cannot disagree.

    ``pip install magmacrunch`` brings a set of cabinets; the empty floor tells
    someone with none how to get them. If those two lists differ, one of them
    is lying, and the floor is the one being read by a person.
    """
    from magmacrunch.cabinets import PACKAGES

    deps = _pyproject()["project"]["dependencies"]
    # Requirement strings carry specifiers - take the name off the front.
    import re

    installed = {
        re.split(r"[<>=!~\[; ]", dep, maxsplit=1)[0]
        for dep in deps
    }
    cabinets_installed = {name for name in installed
                          if name.startswith("magmacrunch-")}
    assert set(PACKAGES) == cabinets_installed


def test_the_empty_floor_still_clears_the_footer_at_the_smallest_size():
    """A fourth cabinet must not quietly draw over the key help.

    The empty floor grows by a line per cabinet, and the smallest terminal the
    floor claims to work in is fixed. Adding moonlight-drift's line took the
    slack at 36x17 down to a single row - so the next one lands on the error
    line, and the failure would be a cosmetic overlap nobody notices until a
    screenshot. This is the tripwire: it fails when EMPTY_FLOOR outgrows the
    room, which is the moment to raise MIN_ROWS or shorten the text.
    """
    from magmacrunch.scenes import EMPTY_FLOOR

    # What `_render_empty_floor` occupies: it starts one row below the header
    # and draws a row per line.
    banner_rows = 1  # the bottom rung; the art stands down to one line
    top = banner_rows + theme.HEADER_ROWS + 2
    last_row = top + len(EMPTY_FLOOR)

    # What the footer takes, counted from the bottom as `_render_footer` does.
    first_footer_row = theme.MIN_ROWS - 4

    assert last_row <= first_footer_row, (
        f"the empty floor reaches row {last_row} and the footer starts at "
        f"{first_footer_row} in a {theme.MIN_COLS}x{theme.MIN_ROWS} terminal"
    )


# ── The high score on the card ──────────────────────────────────────


def score_file(directory, key, *scores):
    """Seed a scoreboard the way a cabinet would have left one."""
    import json

    path = directory / "scores" / f"{key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([{"initials": "ABC", "score": s} for s in sorted(scores, reverse=True)]),
        encoding="utf-8",
    )
    return path


def test_a_card_shows_what_the_cabinet_was_last_beaten_at(isolated_scores):
    score_file(isolated_scores, "alpha", 1200, 900)
    app = arcade(FakeGame(key="alpha", title="Alpha Cabinet"))

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            assert "BEST 1,200" in buffer_text(app)
            app.host.quit()

    run(go())


def test_a_cabinet_nobody_has_played_says_nothing(isolated_scores):
    """Zero is not a low score, it is no score. A card reading BEST 0 invites
    somebody to beat it, which is not a thing that can be done."""
    app = arcade(FakeGame(key="alpha", title="Alpha Cabinet"))

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            assert "BEST" not in buffer_text(app)
            app.host.quit()

    run(go())


def test_the_score_follows_the_scoreboard_key_not_the_menu_key(isolated_scores):
    """A game whose two names differ still finds its board.

    magmacrunch-thld is seated as `thld` and scores as `solitaire-thld`.
    Reading `info.key` would look up an empty board and show nothing, forever,
    with no symptom - an unfound scoreboard and an unplayed game look alike.
    """
    score_file(isolated_scores, "solitaire-thld", 4242)
    game = FakeGame(key="thld", title="Lava Dome")
    game.info = GameInfo(key="thld", title="Lava Dome", blurb="Solo hold'em.",
                         score_key="solitaire-thld")
    app = arcade(game)

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            assert "BEST 4,242" in buffer_text(app)
            app.host.quit()

    run(go())


def test_a_score_set_in_a_cabinet_is_on_the_card_when_you_come_back(isolated_scores):
    """The one moment the number can change is the one moment it is re-read."""
    game = FakeGame(key="alpha", title="Alpha Cabinet")
    app = arcade(game)
    assert app.best_for(game) == 0

    app.host.scene.handle_key("enter")
    settle(app)
    # What the cabinet did while it had the terminal.
    score_file(isolated_scores, "alpha", 7777)

    app.host.pop_scene()
    settle(app)
    assert app.best_for(game) == 7777


def test_the_floor_does_not_read_the_disk_every_frame(isolated_scores, monkeypatch):
    """20 fps times one file open per card is not a way to show a number that
    changes once a visit."""
    from magmacrunch.engine import scores as scores_module

    app = arcade(FakeGame(key="alpha", title="Alpha Cabinet"))

    reads = []
    original = scores_module.ScoreBook.best
    monkeypatch.setattr(scores_module.ScoreBook, "best",
                        lambda self: reads.append(self.game) or original(self))

    scene = app.host.scene
    for _ in range(50):
        scene.update(0.05)
        scene.render()
    assert reads == []


def test_an_unreadable_scoreboard_costs_that_card_its_number_and_nothing_else(
        isolated_scores, monkeypatch):
    """A game is a third party. The floor still has to draw."""
    from magmacrunch.engine import scores as scores_module

    def explode(self):
        raise RuntimeError("scoreboard on fire")

    monkeypatch.setattr(scores_module.ScoreBook, "best", explode)
    app = arcade(FakeGame(key="alpha", title="Alpha Cabinet"))

    async def go():
        async with await _piloted(app) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.25)
            text = buffer_text(app)
            assert "Alpha Cabinet" in text
            assert "BEST" not in text
            app.host.quit()

    run(go())


def test_the_number_never_pushes_enter_off_the_card(isolated_scores):
    """ENTER starts the game and the score is decoration. On a card too narrow
    for both, the number is what goes."""
    assert cards.best_label(0) == ""
    assert cards.best_label(1200) == "BEST 1,200"
    # Seven figures still fit a 32-column card beside the ENTER line.
    assert len(theme.PLAY) + 1 + len(cards.best_label(9_999_999)) <= theme.CARD_INNER
