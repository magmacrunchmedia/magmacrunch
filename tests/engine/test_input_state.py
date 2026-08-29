"""``InputState`` — the shape every backend reports in.

texastoast's `test_input.py` was not ported: it drives this through
`input/keyboard.py`, which stayed behind. That is a reason not to copy that
file, not a reason to leave the dataclass untested, and coverage saying 59%
is what made the difference visible. These test the module directly and
import no backend at all.
"""

import pytest

from magmacrunch.engine.input.abstract import InputSource, InputState


def test_nothing_is_pressed_by_default():
    """A game constructing one and reading it before any input must get a
    controller at rest, not one drifting in some direction."""
    state = InputState()
    assert state.dx == 0.0
    assert state.dy == 0.0
    assert not state.is_any_direction()


@pytest.mark.parametrize("field, dx, dy", [
    ("left", -1.0, 0.0),
    ("right", 1.0, 0.0),
    ("up", 0.0, -1.0),
    ("down", 0.0, 1.0),
])
def test_each_direction_moves_its_own_axis_only(field, dx, dy):
    state = InputState(**{field: True})
    assert (state.dx, state.dy) == (dx, dy)


def test_opposite_directions_cancel():
    """Both arrows held is a real state a terminal reports, and a controller
    that resolved it to one side would pick a winner nobody chose."""
    assert InputState(left=True, right=True).dx == 0.0
    assert InputState(up=True, down=True).dy == 0.0


def test_cancelling_directions_are_still_directions():
    """`dx == 0` and "no input" are different things. A game that idles when
    the stick reads zero would idle with both arrows held down."""
    assert InputState(left=True, right=True).is_any_direction()


def test_diagonals_carry_both_axes():
    state = InputState(up=True, right=True)
    assert (state.dx, state.dy) == (1.0, -1.0)
    assert state.is_any_direction()


def test_buttons_are_not_directions():
    """a/b/start/select must not register as movement."""
    state = InputState(a=True, b=True, start=True, select=True)
    assert (state.dx, state.dy) == (0.0, 0.0)
    assert not state.is_any_direction()


def test_a_backend_satisfies_the_protocol_structurally():
    """Like every seam in this engine, by having the members."""

    class Fake:
        def poll(self):
            return InputState()

        def is_pressed(self, button):
            return False

    assert isinstance(Fake(), InputSource)
