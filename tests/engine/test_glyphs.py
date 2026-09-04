"""Terminal character repertoire.

The half of terminal capability nothing under us owns. Colour is handled for
free — Textual installs a monochrome filter for ``NO_COLOR``, Rich steps
truecolor down by itself — and ``test_no_color.py`` is what pins that. Nothing
in the stack downgrades a *character*, which is what this module is for.

These tests pose as terminals the machine running them is not: cp1252 and
cp437 are the two a Windows player actually meets, and a suite that could only
test the encoding it happened to run under would test nothing.

**The codec coverage asserted here was measured, not remembered.** It is
counter-intuitive in exactly the way that matters — see
:func:`test_a_western_codepage_keeps_not_and_loses_the_other_three`, which is
the case the whole grouping design exists for.
"""

import pytest

from magmacrunch.engine.ui.glyphs import ASCII_ENV, FALLBACKS, GROUPS, Glyphs

UTF8 = Glyphs(encoding="utf-8")
CP1252 = Glyphs(encoding="cp1252")
CP437 = Glyphs(encoding="cp437")
ASCII = Glyphs(encoding="ascii")
FORCED = Glyphs(encoding="utf-8", ascii_only=True)


# ── Asking, one glyph at a time ─────────────────────────────────────


def test_a_utf8_terminal_keeps_everything():
    for fancy in FALLBACKS:
        assert UTF8(fancy, "?") == fancy


def test_an_ascii_terminal_keeps_nothing():
    for fancy, plain in FALLBACKS.items():
        assert ASCII(fancy, plain) == plain, fancy


def test_cp437_keeps_the_blocks_and_loses_the_stars():
    """The case a single program-wide ASCII flag gets wrong.

    A flag would draw Moonlight Drift's columns as ``#`` on a console that can
    draw them solid. Asking per glyph gets both halves right.
    """
    assert CP437("█", "#") == "█"    # FULL BLOCK
    assert CP437("─", "-") == "─"    # BOX DRAWINGS LIGHT HORIZONTAL
    assert CP437("✦", "*") == "*"    # BLACK FOUR POINTED STAR
    assert CP437("♠", "S") == "S"    # BLACK SPADE SUIT
    assert CP437("↑", "^") == "^"    # UPWARDS ARROW


def test_ascii_only_overrides_a_capable_encoding():
    """The escape hatch for the thing no probe can see: a font with no picture
    for a character the encoding can perfectly well represent."""
    assert UTF8("█", "#") == "█"
    assert FORCED("█", "#") == "#"


def test_an_unknown_encoding_is_treated_as_capable():
    """A stream that will not say what it is gets the benefit of the doubt.

    The alternative is that every test harness and capture buffer — none of
    which set ``encoding`` — silently renders ASCII, hiding the real behaviour
    from the tests written to check it.
    """
    assert Glyphs(encoding=None)("✦", "*") == "✦"


def test_an_encoding_python_has_never_heard_of_is_not_the_glyphs_fault():
    assert Glyphs(encoding="not-a-codec")("✦", "*") == "✦"


# ── Groups, which is the point ──────────────────────────────────────


def test_a_western_codepage_keeps_not_and_loses_the_other_three():
    """Measured, and the reason :meth:`Glyphs.resolve` exists.

    Both codepages a Windows player is likely to meet encode ``¬`` and neither
    encodes ``∧``, ``∨`` or ``⊕``. Asked one at a time, George Boole's board
    would show a real NOT sign beside ``&``, ``|`` and ``^`` — four operators
    in two alphabets, which is harder to read than either alphabet alone.
    """
    for codec in (CP1252, CP437):
        assert codec.can("¬")
        assert not codec.can("∧")
        assert not codec.can("∨")
        assert not codec.can("⊕")


def test_resolve_takes_the_whole_group_down_with_the_worst_glyph():
    ops = CP1252.resolve("logic")
    assert ops == {"¬": "!", "∧": "&", "∨": "|", "⊕": "^"}, (
        "¬ encodes here, and still has to go, or the set reads in two alphabets"
    )


def test_resolve_keeps_the_whole_group_when_every_glyph_survives():
    assert UTF8.resolve("logic") == {"¬": "¬", "∧": "∧", "∨": "∨", "⊕": "⊕"}


def test_groups_are_decided_independently_of_each_other():
    """cp437 has the blocks and not the arrows, and a caller that needs both
    should get the good answer for the half that works."""
    both = CP437.resolve("blocks", "arrows")
    assert both["█"] == "█"
    assert both["↑"] == "^"


def test_ascii_only_takes_every_group_down():
    assert FORCED.resolve("blocks")["█"] == "#"


def test_resolve_rejects_a_group_nobody_defined():
    """A typo'd group name silently resolving to nothing would ship a game
    drawing raw unicode on a terminal that cannot take it."""
    with pytest.raises(KeyError):
        UTF8.resolve("blokcs")


# ── translate ───────────────────────────────────────────────────────


def test_translate_substitutes_what_the_table_says():
    table = CP437.resolve("arrows", "punctuation")
    assert CP437.translate("↑↓ choose — more", table) == "^v choose - more"


def test_translate_leaves_an_untouched_group_alone():
    """cp437 keeps the blocks, so a line of them comes back as it went in."""
    table = CP437.resolve("blocks")
    assert CP437.translate("███", table) == "███"


def test_translate_without_a_table_is_a_no_op():
    assert CP1252.translate("✦", {}) == "✦"


def test_a_character_the_table_does_not_mention_is_left_alone():
    """``translate`` substitutes what it was told about and does not invent.

    A glyph nobody thought about should come through and be visible as
    mojibake, rather than being quietly replaced with something wrong.
    """
    assert CP1252.translate("☃", CP1252.resolve("stars")) == "☃"


def test_substitution_never_changes_the_length_of_a_line():
    """The rule the whole renderer-level design rests on.

    ``TuiRenderer`` substitutes *after* the games have measured -- a hint line
    trimmed to the window, a title centred in a box. If ``…`` became ``...``
    the line would grow by two cells after the layout was computed for it, on
    exactly the terminals nobody developing this is looking at.
    """
    table = ASCII.resolve(*GROUPS)
    for line in ("more…", "↑↓ choose — more", "█▓░", "¬∧∨⊕", "♠♣♥♦"):
        assert len(ASCII.translate(line, table)) == len(line), line


# ── Detection ───────────────────────────────────────────────────────


class FakeStream:
    def __init__(self, encoding):
        self.encoding = encoding


def test_detect_reads_the_streams_encoding():
    g = Glyphs.detect(stream=FakeStream("cp1252"), environ={})
    assert g.encoding == "cp1252"
    assert not g.ascii_only
    assert g("✦", "*") == "*"


def test_a_stream_with_no_encoding_reads_as_unknown():
    assert Glyphs.detect(stream=object(), environ={}).encoding is None


def test_the_env_var_forces_plain_everywhere():
    g = Glyphs.detect(stream=FakeStream("utf-8"), environ={ASCII_ENV: "1"})
    assert g.ascii_only
    assert g("█", "#") == "#"


def test_an_empty_env_var_is_not_a_request():
    g = Glyphs.detect(stream=FakeStream("utf-8"), environ={ASCII_ENV: ""})
    assert not g.ascii_only


def test_the_flag_can_turn_plain_on_but_never_off():
    """There is deliberately no way to demand the fancy forms on a terminal
    that cannot encode them — that argument ends in mojibake."""
    forced = Glyphs.detect(ascii_only=True, stream=FakeStream("utf-8"),
                           environ={})
    assert forced("█", "#") == "#"

    denied = Glyphs.detect(ascii_only=False, stream=FakeStream("cp1252"),
                           environ={})
    assert denied("█", "#") == "#", "the flag cannot veto the encoding"

    still = Glyphs.detect(ascii_only=False, stream=FakeStream("utf-8"),
                          environ={ASCII_ENV: "1"})
    assert still.ascii_only, "nor the env var"


# ── The table ───────────────────────────────────────────────────────


def test_every_substitute_is_actually_ascii():
    """A fallback that is itself unencodable is worse than no fallback: it
    fails on exactly the terminal it was written to rescue."""
    for fancy, plain in FALLBACKS.items():
        assert plain.isascii(), f"{fancy} -> {plain!r}"


def test_no_glyph_is_its_own_fallback():
    for fancy, plain in FALLBACKS.items():
        assert fancy != plain


def test_no_glyph_appears_in_two_groups():
    """A glyph in two groups would be decided twice and resolved by whichever
    was merged last, which is not a decision anybody made."""
    seen: dict[str, str] = {}
    for name, group in GROUPS.items():
        for char in group:
            assert char not in seen, f"{char} is in both {seen[char]} and {name}"
            seen[char] = name


def test_flattening_the_groups_loses_nothing():
    assert len(FALLBACKS) == sum(len(g) for g in GROUPS.values())


def test_the_block_elements_stay_one_cell_wide():
    """:mod:`~magmacrunch.engine.ui.bigtext` measures a title before drawing
    it, so a two-character stand-in for a block would push every title past
    the box that was measured for it."""
    for char, plain in GROUPS["blocks"].items():
        assert len(plain) == 1, char


@pytest.mark.parametrize("fancy,plain", [
    ("¬", "!"), ("∧", "&"), ("∨", "|"), ("⊕", "^"),
])
def test_the_logic_operators_spell_themselves_the_way_code_does(fancy, plain):
    """George Boole's operators are the game rather than its decoration, so
    the plain forms have to be ones a programmer already reads."""
    assert GROUPS["logic"][fancy] == plain


@pytest.mark.parametrize("fancy,plain", [
    ("♠", "S"), ("♣", "C"), ("♥", "H"), ("♦", "D"),
])
def test_the_suits_agree_with_lava_domes_own_ascii_mode(fancy, plain):
    """That game had a ``--ascii`` before this module existed. Two routes to a
    plain card that disagreed on the letter would be worse than one."""
    assert GROUPS["suits"][fancy] == plain
