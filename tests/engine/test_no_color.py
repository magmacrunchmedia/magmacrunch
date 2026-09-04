"""NO_COLOR, which this engine gets for free and could lose without noticing.

Nothing in this package mentions ``NO_COLOR``. It is honoured anyway: Textual
reads it at construction and appends a ``Monochrome`` line filter, and Rich
steps truecolor down to 256 or 16 by looking at the terminal. The arcade
inherits both and is right to — reimplementing either would be a second
opinion about the same question.

**Inheriting a behaviour is not the same as having one**, which is what this
file is for. The engine does not render the way a Textual application usually
does: :class:`~magmacrunch.engine.core.tui_game.GameSurface` overrides
``render_line`` and returns a ``Strip`` of Rich ``Style`` objects built
straight from hex, never touching Textual's CSS. Whether the app's filters
reach *that* is a fact about Textual's internals — they are applied in
``StylesCache.render_widget``, which takes ``widget.render_line`` and
``widget.get_line_filters()`` together — and it is a fact that a Textual
upgrade could change silently, in a way no other test here would catch. The
symptom would be a player who set NO_COLOR getting full colour anyway.

So this asserts on rendered output rather than on the filter list. A filter
that is installed and not applied is the bug being guarded against, and
checking ``app._filters`` would pass straight through it.
"""

import asyncio

import pytest

pytest.importorskip("textual", reason='needs textual: pip install -e ".[dev]"')

from textual.geometry import Region  # noqa: E402

from magmacrunch.engine.core.tui_host import TuiHost  # noqa: E402

#: Saturated on purpose. Monochrome maps colour to luminance, so a hue whose
#: channels are already equal would survive the filter and prove nothing.
RED = "#ff0000"


class Scene:
    """Fills the screen with one loud colour and nothing else."""

    def __init__(self, host):
        self.host = host

    def update(self, dt):
        pass

    def render(self):
        r = self.host.renderer
        r.clear()
        r.draw_rect(0, 0, r.width, r.height, RED)
        r.present()

    def handle_key(self, key):
        return False


def _colors(app) -> set[str]:
    """Every foreground and background actually emitted for the surface.

    Taken through ``render_lines``, which is the path the compositor uses and
    the one that applies the filters — ``render_line`` on its own is the
    unfiltered half and would answer the wrong question.
    """
    from magmacrunch.engine.core.tui_game import GameSurface

    surface = app.query_one(GameSurface)
    found: set[str] = set()
    for strip in surface.render_lines(Region(0, 0, surface.size.width,
                                             surface.size.height)):
        for segment in strip:
            style = segment.style
            if style is None:
                continue
            for color in (style.color, style.bgcolor):
                if color is not None and color.triplet is not None:
                    found.add(color.triplet.hex)
    return found


def _run(monkeypatch, no_color: bool) -> set[str]:
    from magmacrunch.engine.core.tui_game import _GameApp

    if no_color:
        monkeypatch.setenv("NO_COLOR", "1")
    else:
        monkeypatch.delenv("NO_COLOR", raising=False)

    host = TuiHost(title="t", fps=30)
    host.push_scene(Scene(host))
    host.stack.update(0.0)

    async def go() -> set[str]:
        app = _GameApp(host.game, host.game.surface)
        host.game._app = app
        # Textual reads NO_COLOR when the App is constructed, so the env has
        # to be set before the line above, not before run_test.
        async with app.run_test(size=(20, 5)):
            await asyncio.sleep(0.3)
            found = _colors(app)
            app.exit()
        return found

    return asyncio.run(go())


def test_colour_reaches_the_cells_by_default(monkeypatch):
    """The control. Without this, a filter that blanked everything would make
    the NO_COLOR test below pass for the wrong reason."""
    assert RED in _run(monkeypatch, no_color=False)


def test_no_color_reaches_a_widget_that_renders_its_own_strips(monkeypatch):
    """The actual guard: Textual's monochrome filter is applied to a Strip the
    engine built itself, not only to content Textual styled."""
    found = _run(monkeypatch, no_color=True)
    assert RED not in found, "NO_COLOR was set and the red got through anyway"
    assert found, "nothing rendered at all, so this proves nothing"
    for hex_color in found:
        r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
        assert r == g == b, f"{hex_color} is not grey, so it was not filtered"
