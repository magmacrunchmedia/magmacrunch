"""TuiRenderer conformance — the terminal counterpart to test_render_protocol.py.

Most of this runs with nothing installed: TuiRenderer draws into a CellBuffer
and imports no terminal library, which is exactly the property that lets a
future ANSI backend reuse it. The handful of tests that need Textual are
skipped when the ``tui`` extra is absent.
"""

import pytest

from magmacrunch.engine.render.abstract import Renderer, UISurface, as_ui_surface
from magmacrunch.engine.render.cellbuffer import CellBuffer
from magmacrunch.engine.render.tui import FULL_BLOCK, TuiRenderer
from magmacrunch.engine.ui.glyphs import Glyphs


def _has_textual() -> bool:
    try:
        import textual  # noqa: F401
    except ImportError:
        return False
    return True


requires_textual = pytest.mark.skipif(
    not _has_textual(), reason='needs textual: pip install -e ".[dev]"'
)


@pytest.fixture
def renderer():
    return TuiRenderer(20, 6)


# ── Protocol conformance ────────────────────────────────────────────


def test_tui_renderer_satisfies_both_protocols(renderer):
    assert isinstance(renderer, Renderer)
    assert isinstance(renderer, UISurface)


def test_as_ui_surface_passes_a_tui_renderer_through(renderer):
    assert as_ui_surface(renderer) is renderer


def test_renderer_exposes_its_dimensions_in_cells(renderer):
    assert renderer.width == 20
    assert renderer.height == 6
    assert renderer.camera.width == 20


def test_importing_the_backend_pulls_no_terminal_library():
    import sys

    import magmacrunch.engine.render.tui  # noqa: F401

    # The whole point of the surface-injection design.
    assert "textual" not in sys.modules or _has_textual()
    assert "curses" not in sys.modules


# ── present() ───────────────────────────────────────────────────────


def test_present_flushes_to_the_surface():
    # present() is NOT a no-op here, the way it is for a backend that draws
    # straight to the screen — the buffer is off-screen and nothing is visible
    # until it is pushed.
    flushed = []

    class Surface:
        def flush(self, buffer):
            flushed.append(buffer.to_text())

    renderer = TuiRenderer(6, 1, surface=Surface())
    renderer.draw_hud_text(0, 0, "hi")
    renderer.present()
    assert flushed == ["hi"]


def test_present_without_a_surface_is_safe():
    TuiRenderer(4, 1).present()


def test_clear_blanks_the_frame(renderer):
    renderer.draw_hud_text(0, 0, "text")
    renderer.clear()
    assert renderer.to_text().strip() == ""


# ── Drawing ─────────────────────────────────────────────────────────


def test_draw_rect_fills_with_background(renderer):
    renderer.draw_rect(2, 1, 3, 2, "#ff0000")
    assert renderer.buffer.get(2, 1).bg == "#ff0000"
    assert renderer.buffer.get(4, 2).bg == "#ff0000"
    assert renderer.buffer.get(5, 1).bg is None


def test_draw_text_is_offset_by_the_camera(renderer):
    renderer.camera.set_position(3, 1)
    renderer.draw_text(5, 2, "ab")
    assert renderer.buffer.get(2, 1).char == "a"


def test_draw_hud_text_ignores_the_camera(renderer):
    renderer.camera.set_position(3, 1)
    renderer.draw_hud_text(5, 2, "ab")
    assert renderer.buffer.get(5, 2).char == "a"


def test_draw_text_accepts_and_ignores_tk_only_kwargs(renderer):
    # Games ported from the canvas backend pass these; erroring would force a
    # backend check at every call site.
    renderer.draw_hud_text(0, 0, "x", font=("Courier", 10), fill="#abcdef")
    assert renderer.buffer.get(0, 0).fg == "#abcdef"


@pytest.mark.parametrize(
    "anchor,expected_x",
    [("nw", 10), ("n", 8), ("ne", 6), ("w", 10), ("center", 8), ("e", 6)],
)
def test_text_anchors_position_on_the_grid(anchor, expected_x):
    renderer = TuiRenderer(20, 3)
    renderer.draw_hud_text(10, 1, "abcd", anchor=anchor)
    assert renderer.buffer.get(expected_x, 1).char == "a"


def test_draw_image_is_a_no_op(renderer):
    renderer.draw_image(0, 0, object())
    assert renderer.to_text().strip() == ""


def test_draw_image_warns_only_once(renderer, caplog):
    import logging

    with caplog.at_level(logging.DEBUG, logger="magmacrunch.engine.render.tui"):
        renderer.draw_image(0, 0, object())
        renderer.draw_image(0, 0, object())
    assert len([r for r in caplog.records if "draw_image" in r.message]) == 1


# ── Tilemaps ────────────────────────────────────────────────────────


class FakeTileMap:
    tile_size = 16

    def __init__(self, grid):
        self._grid = grid
        self.rows = len(grid)
        self.cols = len(grid[0])

    def get(self, col, row):
        return self._grid[row][col]


def test_draw_tilemap_paints_one_cell_per_tile():
    # One cell per tile regardless of tile_size: 16 pixels means nothing here,
    # and scaling by it would push a small map entirely off-screen.
    renderer = TuiRenderer(4, 2)
    tilemap = FakeTileMap([[1, 1, 0, 1], [0, 1, 1, 0]])
    renderer.draw_tilemap(tilemap, {1: "#00ff00"})
    assert renderer.to_text() == f"{FULL_BLOCK*2} {FULL_BLOCK}\n {FULL_BLOCK*2}"


def test_draw_tilemap_honours_custom_glyphs():
    renderer = TuiRenderer(3, 1)
    renderer.tile_glyphs = {1: "#", 2: "~"}
    tilemap = FakeTileMap([[1, 2, 1]])
    renderer.draw_tilemap(tilemap, {1: "#fff", 2: "#00f"})
    assert renderer.to_text() == "#~#"


def test_draw_tilemap_skips_requested_ids():
    renderer = TuiRenderer(3, 1)
    tilemap = FakeTileMap([[1, 1, 1]])
    renderer.draw_tilemap(tilemap, {1: "#fff"}, skip_tiles=[1])
    assert renderer.to_text() == ""


def test_draw_tilemap_ignores_ids_with_no_color():
    renderer = TuiRenderer(3, 1)
    renderer.tile_glyphs = {1: "#"}
    tilemap = FakeTileMap([[1, 9, 1]])
    renderer.draw_tilemap(tilemap, {1: "#fff"})
    assert renderer.to_text() == "# #"


# ── UISurface ───────────────────────────────────────────────────────


def test_ui_rect_fills_and_outlines(renderer):
    renderer.ui_rect(0, 0, 4, 3, fill="#111111", outline="#ffffff", outline_width=1)
    assert renderer.buffer.get(1, 1).bg == "#111111"
    assert renderer.buffer.get(0, 0).bg == "#ffffff"


def test_ui_rect_without_outline_width_still_fills(renderer):
    renderer.ui_rect(0, 0, 3, 2, fill="#222222")
    assert renderer.buffer.get(2, 1).bg == "#222222"


def test_clear_group_erases_only_that_widget(renderer):
    renderer.ui_text(0, 0, "alpha", fill="#fff", group="one")
    renderer.ui_text(0, 1, "beta", fill="#fff", group="two")
    renderer.clear_group("one")
    assert renderer.to_text().rstrip("\n") == "\nbeta"


def test_begin_group_restarts_a_widgets_drawing(renderer):
    renderer.begin_group("hud")
    renderer.ui_text(0, 0, "old", fill="#fff", group="hud")
    renderer.begin_group("hud")
    renderer.ui_text(0, 0, "new", fill="#fff", group="hud")
    assert renderer.to_text().split("\n")[0] == "new"


def test_a_widget_accumulates_across_several_draw_calls(renderer):
    # begin_group once, then several draws — none of which may wipe the others.
    renderer.begin_group("w")
    renderer.ui_rect(0, 0, 5, 1, fill="#000", group="w")
    renderer.ui_text(0, 0, "hey", fill="#fff", group="w")
    assert renderer.to_text().split("\n")[0] == "hey"
    renderer.clear_group("w")
    assert renderer.to_text().strip() == ""


def test_ui_text_wraps_to_the_given_width(renderer):
    renderer.ui_text(0, 0, "aaa bbb ccc", fill="#fff", width=7)
    assert renderer.to_text().startswith("aaa bbb\nccc")


def test_ui_text_ignores_the_font_argument(renderer):
    renderer.ui_text(0, 0, "x", fill="#fff", font=("Courier", 24))
    assert renderer.buffer.get(0, 0).char == "x"


# ── Resize ──────────────────────────────────────────────────────────


def test_resize_updates_the_renderer_and_camera(renderer):
    renderer.resize(40, 10)
    assert (renderer.width, renderer.height) == (40, 10)
    assert (renderer.camera.width, renderer.camera.height) == (40, 10)


def test_an_injected_buffer_is_used_as_is():
    buffer = CellBuffer(5, 1)
    renderer = TuiRenderer(5, 1, buffer=buffer)
    renderer.draw_hud_text(0, 0, "ok")
    assert buffer.to_text() == "ok"


# ── Textual host ────────────────────────────────────────────────────


@requires_textual
def test_textual_scheduler_satisfies_the_scheduler_protocol():
    from magmacrunch.engine.core.scheduler import Scheduler
    from magmacrunch.engine.core.tui_game import TextualScheduler

    assert isinstance(TextualScheduler(None), Scheduler)


@requires_textual
def test_after_cancel_tolerates_a_dead_timer():
    from magmacrunch.engine.core.tui_game import TextualScheduler

    class Boom:
        def stop(self):
            raise RuntimeError("already gone")

    TextualScheduler(None).after_cancel(Boom())
    TextualScheduler(None).after_cancel(None)


@requires_textual
def test_scheduler_converts_milliseconds_to_seconds():
    from magmacrunch.engine.core.tui_game import TextualScheduler

    seen = []

    class FakeApp:
        def set_timer(self, delay, callback):
            seen.append(delay)
            return "timer"

    TextualScheduler(FakeApp()).after(250, lambda: None)
    assert seen == [0.25]


@requires_textual
def test_game_surface_renders_a_line_of_the_buffer():
    from magmacrunch.engine.core.tui_game import GameSurface

    buffer = CellBuffer(5, 2)
    buffer.write(0, 0, "hi", fg="#ff0000")
    surface = GameSurface(buffer)

    strip = surface.render_line(0)
    assert "".join(seg.text for seg in strip._segments) == "hi   "


@requires_textual
def test_game_surface_coalesces_runs_of_identical_style():
    from magmacrunch.engine.core.tui_game import GameSurface

    buffer = CellBuffer(6, 1)
    buffer.write(0, 0, "aaa", fg="#ff0000")
    buffer.write(3, 0, "bbb", fg="#00ff00")
    surface = GameSurface(buffer)

    strip = surface.render_line(0)
    # Two runs, not six single-character segments.
    assert len(strip._segments) == 2


@requires_textual
def test_tui_game_accepts_tk_style_key_spellings():
    # `<KeyPress-a>` is tkinter's spelling, and nothing here is tkinter. It is
    # still honoured because a game written against the old GUI host binds its
    # keys with those strings, and normalising them costs one function.
    from magmacrunch.engine.core.tui_game import TuiGame

    assert TuiGame._normalize_key("<Left>") == "left"
    assert TuiGame._normalize_key("<KeyPress-a>") == "a"
    assert TuiGame._normalize_key("space") == "space"


@requires_textual
def test_tui_game_exposes_a_renderer_over_its_surface():
    from magmacrunch.engine.core.tui_game import TuiGame

    game = TuiGame(width=10, height=3)
    assert isinstance(game.renderer, Renderer)
    assert isinstance(game.renderer, UISurface)
    game.renderer.draw_hud_text(0, 0, "hey")
    game.renderer.present()
    assert game.surface.buffer.to_text().startswith("hey")


# ── The shared widgets over a terminal surface ──────────────────────
#
# The payoff of TuiRenderer satisfying UISurface: ui/ widgets written for the
# canvas work here unchanged, given layout metrics in cells rather than pixels.


def test_the_menu_widget_renders_over_a_tui_surface():
    from magmacrunch.engine.ui.menu import Menu

    renderer = TuiRenderer(40, 14)
    menu = Menu(renderer, menu_width=30, item_height=1,
                title_height=2, item_padding=1, border_pad=1)
    menu.show(["crumb", "nibble", "byte"], title="MODE")
    renderer.clear()
    menu.render()

    text = renderer.to_text()
    assert "MODE" in text
    assert "> crumb" in text          # the selection marker
    assert "nibble" in text
    assert "byte" in text


def test_menu_selection_moves_and_confirms_over_a_tui_surface():
    from magmacrunch.engine.ui.menu import Menu

    renderer = TuiRenderer(40, 14)
    chosen = []
    menu = Menu(renderer, menu_width=30, item_height=1,
                title_height=2, item_padding=1, border_pad=1)
    menu.show(["a", "b", "c"], on_select=lambda i, label: chosen.append(label))

    menu.move_down()
    renderer.clear()
    menu.render()
    assert "> b" in renderer.to_text()

    menu.confirm()
    assert chosen == ["b"]
    assert not menu.active


def test_a_menu_sized_in_pixels_would_not_fit_a_terminal():
    # Why the metrics had to become configurable: the pixel defaults put the
    # whole widget off-screen on any real terminal.
    from magmacrunch.engine.ui.menu import Menu

    renderer = TuiRenderer(80, 24)
    menu = Menu(renderer)                      # 280 wide, 32-cell rows
    menu.show(["one", "two"], title="NOPE")
    renderer.clear()
    menu.render()
    assert "one" not in renderer.to_text()


def test_the_menu_follows_a_surface_that_resizes():
    # A canvas never changes size, so caching the surface dimensions was
    # harmless there. A terminal resizes constantly, and a menu laid out for
    # whatever the size happened to be at construction is off-centre forever.
    from magmacrunch.engine.ui.menu import Menu

    renderer = TuiRenderer(80, 24)
    menu = Menu(renderer, menu_width=20, item_height=1,
                title_height=1, item_padding=0, border_pad=0)
    menu.show(["aaa"])

    def marker_column() -> int:
        renderer.clear()
        menu.render()
        line = next(ln for ln in renderer.to_text().split("\n") if ">" in ln)
        return line.index(">")

    wide = marker_column()
    renderer.resize(40, 24)
    narrow = marker_column()

    assert narrow < wide, "the menu should re-centre on the smaller surface"
    assert narrow == wide - 20


def test_an_explicit_size_still_wins_over_the_surface():
    from magmacrunch.engine.ui.menu import Menu

    renderer = TuiRenderer(80, 24)
    menu = Menu(renderer, width=40, height=24, menu_width=20, item_height=1,
                title_height=1, item_padding=0, border_pad=0)
    menu.show(["aaa"])
    renderer.clear()
    menu.render()
    before = next(ln for ln in renderer.to_text().split("\n") if ">" in ln).index(">")

    renderer.resize(60, 24)
    renderer.clear()
    menu.render()
    after = next(ln for ln in renderer.to_text().split("\n") if ">" in ln).index(">")
    assert before == after


# ── Glyph substitution ────────────────────────────────────────────
#
# The one place a character the terminal cannot encode is replaced. It happens
# here rather than in the games because there are three of them, each drawing
# thirty times a frame, and a question asked at every draw site is a question
# that will be forgotten at one of them.


def test_a_renderer_with_no_glyphs_draws_exactly_what_it_was_given():
    """The default, and what every test in this suite depends on. A renderer
    that consulted the ambient encoding would make expected output depend on
    whatever stream pytest attached."""
    r = TuiRenderer(20, 3)
    r.ui_text(0, 0, "█↑∧", fill="#fff")
    assert r.buffer.to_text().startswith("█↑∧")


def test_a_terminal_without_the_glyphs_gets_the_plain_forms():
    r = TuiRenderer(20, 3, glyphs=Glyphs(encoding="ascii"))
    r.ui_text(0, 0, "█↑∧", fill="#fff")
    assert r.buffer.to_text().startswith("#^&")


def test_substitution_does_not_move_the_text():
    """The property the one-cell rule buys, checked where it matters: the
    caller centred this before the renderer had an opinion."""
    plain = TuiRenderer(21, 3, glyphs=Glyphs(encoding="ascii"))
    rich = TuiRenderer(21, 3)
    for r in (plain, rich):
        r.ui_text(10, 1, "←…→", fill="#fff", anchor="n")
    a, b = plain.buffer.to_text().split("\n"), rich.buffer.to_text().split("\n")
    assert [len(row) for row in a] == [len(row) for row in b]
    assert a[1].index("<") == b[1].index("←")


def test_the_camera_path_is_substituted_too():
    """``draw_text`` and ``ui_text`` are separate entry points, and a game that
    drew through the world-space one would otherwise be missed."""
    r = TuiRenderer(20, 3, glyphs=Glyphs(encoding="ascii"))
    r.draw_text(0, 0, "██", fill="#fff")
    assert r.buffer.to_text().startswith("##")


def test_use_glyphs_can_be_changed_after_construction():
    r = TuiRenderer(20, 3)
    r.use_glyphs(Glyphs(encoding="ascii"))
    r.ui_text(0, 0, "█", fill="#fff")
    assert r.buffer.to_text().startswith("#")
    r.use_glyphs(None)
    r.clear()
    r.ui_text(0, 0, "█", fill="#fff")
    assert r.buffer.to_text().startswith("█")


def test_a_capable_terminal_costs_nothing_to_have_asked():
    """A UTF-8 terminal stores no table at all, rather than an identity one, so
    the common case is an ``is None`` and not a translate over every string."""
    assert TuiRenderer(4, 1, glyphs=Glyphs(encoding="utf-8"))._plain is None
    assert TuiRenderer(4, 1, glyphs=Glyphs(encoding="ascii"))._plain is not None


def test_a_group_the_terminal_half_supports_still_goes_down_together():
    """The motivating case, end to end through the renderer.

    cp1252 encodes the NOT sign and none of the other three operators. Asked
    one glyph at a time, George Boole's gate list would come back as a real
    ``¬`` beside ``&``, ``|`` and ``^`` -- one set of operators in two
    alphabets, which is harder to read than either alphabet alone.
    """
    r = TuiRenderer(20, 3, glyphs=Glyphs(encoding="cp1252"))
    r.ui_text(0, 0, "¬∧∨⊕", fill="#fff")
    assert r.buffer.to_text().startswith("!&|^")


def test_a_group_the_terminal_fully_supports_is_left_alone():
    """The other half of the same rule. cp1252 has all three punctuation
    glyphs, so it keeps all three -- the group only degrades when it has to."""
    r = TuiRenderer(20, 3, glyphs=Glyphs(encoding="cp1252"))
    r.ui_text(0, 0, "·…—", fill="#fff")
    assert r.buffer.to_text().startswith("·…—")


def test_cp437_takes_the_middle_dot_down_with_the_ellipsis():
    """And the same split again on the codepage where it falls inside
    punctuation rather than inside logic. cp437 has ``·`` and not ``…``."""
    r = TuiRenderer(20, 3, glyphs=Glyphs(encoding="cp437"))
    r.ui_text(0, 0, "·…", fill="#fff")
    assert r.buffer.to_text().startswith("..")
