# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 magmacrunch media
"""What characters this terminal can actually draw.

Colour degrades on its own: Textual honours ``NO_COLOR`` with a monochrome
line filter, and Rich steps truecolor down to 256 or 16 by looking at the
terminal. Neither of them touches *characters*. A game that draws its board
with ``∧`` and ``⊕``, or its columns with ``█``, hands those straight to the
encoder, and on a console that cannot represent them the result is mojibake —
from a title screen, which is decoration, or from the operator glyphs that are
the game itself.

So this is the other half of terminal capability, and the half nothing under
us owns.

Two ways to ask, and choosing between them is the whole design:

**Per glyph**, with :meth:`Glyphs.__call__`, when a character stands alone::

    STAR = g("✦", "*")

**Per group**, with :meth:`Glyphs.resolve`, when several characters are read
against each other and a half-translated set is worse than a plain one. That
is not a hypothetical: cp1252 can encode ``¬`` and cannot encode ``∧``, ``∨``
or ``⊕``, so asking glyph by glyph draws George Boole's board with a real NOT
sign sitting beside ``&``, ``|`` and ``^`` — four operators in two alphabets,
which is harder to read than any one alphabet would have been::

    ops = g.resolve("logic")        # all four, or none of them
    label = ops["∧"]

:data:`GROUPS` is where that judgement lives, and it is the file's actual
content. The rule for adding to it: characters go in the same group when a
player reads them as a set.

**What cannot be detected is the font.** An encoding says the byte can be
written, not that the glyph has a picture, and a terminal set to a font with
no box-drawing characters shows tofu whatever we ask. That is what
``ascii_only`` and :data:`ASCII_ENV` are for — the escape hatch for a person
who can see their own screen, which is a thing no amount of probing replaces.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

#: Set this to any non-empty value to force plain ASCII everywhere, in every
#: cabinet at once. The per-game ``--ascii`` flag says the same thing for one
#: game; this is for a terminal that is always going to need it.
ASCII_ENV = "MAGMACRUNCH_ASCII"


#: Everything the arcade draws that is not ASCII, and what it becomes —
#: grouped by what degrades together.
#:
#: One table for the whole family rather than one per game, because the games
#: share most of it (three of them draw ``↑`` in a hint line) and because a
#: character that two cabinets spell differently in ASCII is a character a
#: player has to learn twice.
GROUPS: dict[str, dict[str, str]] = {
    # Every substitute here is **exactly one cell wide**, which is what lets
    # bigtext measure a title before drawing it and still be right about the
    # plain face. The half blocks become the ASCII character that sits in the
    # same half of the cell, which is the only reason a half-height face reads.
    "blocks": {
        "█": "#",   # FULL BLOCK
        "▓": "%",   # DARK SHADE
        "▒": "+",   # MEDIUM SHADE
        "░": ":",   # LIGHT SHADE
        "▀": '"',   # UPPER HALF BLOCK
        "▄": "_",   # LOWER HALF BLOCK
        "─": "-",   # BOX DRAWINGS LIGHT HORIZONTAL
    },
    # Hint lines. Spelled as the keycap rather than as a picture: "^" for up
    # is a convention a terminal user already reads. Grouped because "↑v" —
    # which is what cp437 would give, having neither but being asked one at a
    # time — reads as a typo rather than as a pair of keys.
    "arrows": {
        "←": "<",
        "→": ">",
        "↑": "^",
        "↓": "v",
        "▲": "^",   # BLACK UP-POINTING TRIANGLE
        "▼": "v",   # BLACK DOWN-POINTING TRIANGLE
    },
    # The ellipsis is load-bearing: it is what marks a hint line as having
    # been cut, so losing it silently loses the only signal that anything was
    # truncated.
    #
    # It is a single dot rather than three because of the rule below, which
    # ``...`` would be the only exception to.
    "punctuation": {
        "…": ".",
        "—": "-",
        "·": ".",
    },
    "stars": {
        "✦": "*",   # BLACK FOUR POINTED STAR, Moonlight Drift's sky
    },
    # The letters Lava Dome's own --ascii already used before this module
    # existed. Two routes to a plain card that disagreed on the letter would
    # be worse than one.
    "suits": {
        "♠": "S",
        "♣": "C",
        "♥": "H",
        "♦": "D",
    },
    # George Boole's operators, which are the game rather than its decoration.
    # The plain forms are the ones a programmer already reads, and the ones
    # the browser build's keyboard help names.
    #
    # **This group is why `resolve` exists.** cp1252 and cp437 both encode ¬
    # and neither encodes the other three.
    "logic": {
        "¬": "!",   # NOT
        "∧": "&",   # AND
        "∨": "|",   # OR
        "⊕": "^",   # XOR
    },
}

#: Every group flattened, for the per-glyph question and for tests that want
#: to sweep the lot.
FALLBACKS: dict[str, str] = {
    fancy: plain
    for group in GROUPS.values()
    for fancy, plain in group.items()
}

# **Every substitute is exactly one cell wide**, and that is a load-bearing
# rule rather than a tidiness one.
#
# Substitution happens inside
# :class:`~magmacrunch.engine.render.tui.TuiRenderer`, *after* the caller has
# measured. The games lay a screen out by counting cells -- a hint line
# trimmed to the window, a title centred in a box, a card sized to its label
# -- and they count the string they are holding, which is the one with the
# fancy glyphs in it. A substitute of a different width would move the text
# off the layout that was computed for it, and it would do so only on the
# terminals nobody developing this is looking at.
#
# Asserted at import, because the cost of getting it wrong is a screen that is
# subtly wrong somewhere else entirely.
assert all(len(plain) == 1 for plain in FALLBACKS.values()), (
    "every fallback must be one cell: "
    f"{[f for f, p in FALLBACKS.items() if len(p) != 1]}"
)

# **Every substitute is exactly one cell wide**, and that is a load-bearing
# rule rather than a tidiness one.
#
# Substitution happens inside
# :class:`~magmacrunch.engine.render.tui.TuiRenderer`, *after* the caller has
# measured. The games lay a screen out by counting cells -- a hint line
# trimmed to the window, a title centred in a box, a card sized to its label
# -- and they count the string they are holding, which is the one with the
# fancy glyphs in it. A substitute of a different width would move the text
# off the layout that was computed for it, and it would do so only on the
# terminals nobody developing this is looking at.
#
# Asserted at import, because the cost of getting it wrong is a screen that is
# subtly wrong somewhere else entirely.
assert all(len(plain) == 1 for plain in FALLBACKS.values()), (
    "every fallback must be one cell: "
    f"{[f for f, p in FALLBACKS.items() if len(p) != 1]}"
)

# **Every substitute is exactly one cell wide**, and that is a load-bearing
# rule rather than a tidiness one.
#
# Substitution happens inside
# :class:`~magmacrunch.engine.render.tui.TuiRenderer`, *after* the caller has
# measured. The games lay a screen out by counting cells -- a hint line
# trimmed to the window, a title centred in a box, a card sized to its label
# -- and they count the string they are holding, which is the one with the
# fancy glyphs in it. A substitute of a different width would move the text
# off the layout that was computed for it, and it would do so only on the
# terminals nobody developing this is looking at.
#
# Asserted at import, because the cost of getting it wrong is a screen that is
# subtly wrong somewhere else entirely.
assert all(len(plain) == 1 for plain in FALLBACKS.values()), (
    "every fallback must be one cell: "
    f"{[f for f, p in FALLBACKS.items() if len(p) != 1]}"
)

# **Every substitute is exactly one cell wide**, and that is a load-bearing
# rule rather than a tidiness one.
#
# Substitution happens inside
# :class:`~magmacrunch.engine.render.tui.TuiRenderer`, *after* the caller has
# measured. The games lay a screen out by counting cells -- a hint line
# trimmed to the window, a title centred in a box, a card sized to its label
# -- and they count the string they are holding, which is the one with the
# fancy glyphs in it. A substitute of a different width would move the text
# off the layout that was computed for it, and it would do so only on the
# terminals nobody developing this is looking at.
#
# Asserted at import, because the cost of getting it wrong is a screen that is
# subtly wrong somewhere else entirely.
assert all(len(plain) == 1 for plain in FALLBACKS.values()), (
    "every fallback must be one cell: "
    f"{[f for f, p in FALLBACKS.items() if len(p) != 1]}"
)


def _stream_encoding(stream: object | None) -> str | None:
    """The encoding a stream will be written with, if it admits to one.

    ``sys.stdout`` is not guaranteed to have ``encoding`` — it is replaced by
    all sorts of things in test harnesses and capture buffers — so this asks
    rather than assumes, and a stream that will not say returns ``None`` for
    the caller to treat as unknown.
    """
    return getattr(stream, "encoding", None) or None


@dataclass(frozen=True)
class Glyphs:
    """A terminal's character repertoire.

    Frozen, and built once at startup: the encoding cannot change under a
    running program, and a game that re-detected per frame would be paying
    for an answer it already had. ``_cache`` is the exception the ``field``
    below exists for — it memoises a pure function of ``encoding``, which is
    why mutating it does not make the object mutable in any sense that counts.
    """

    #: The encoding output will be written in, or ``None`` when unknown.
    #: Unknown is treated as capable: refusing to draw a glyph because a test
    #: harness replaced ``sys.stdout`` would make every suite render ASCII and
    #: hide the real behaviour from the tests written to check it.
    encoding: str | None = None

    #: Force the plain forms regardless of what the encoding can do. The
    #: ``--ascii`` flag, and the answer for a capable encoding in a font that
    #: has no picture for the character.
    ascii_only: bool = False

    _cache: dict[str, bool] = field(default_factory=dict, repr=False,
                                    compare=False)

    # ── Building ────────────────────────────────────────────────────

    @classmethod
    def detect(cls, *, ascii_only: bool | None = None,
               stream: object | None = None,
               environ: dict[str, str] | None = None) -> Glyphs:
        """Read the terminal's capability off the environment.

        ``ascii_only`` is the caller's flag, and it can only ever turn the
        plain forms *on*: ``True`` forces them, ``False`` and ``None`` leave
        the decision to :data:`ASCII_ENV` and then to the encoding. There is
        deliberately no way for a flag to demand the fancy forms on a terminal
        that cannot encode them — that argument ends in mojibake, and the
        person who wants it wants a different terminal.

        ``stream`` and ``environ`` are injected for the tests, which have to
        be able to pose as a cp1252 console on a machine that is not one.
        """
        env = os.environ if environ is None else environ
        forced = bool(ascii_only) or bool(env.get(ASCII_ENV))
        out = sys.stdout if stream is None else stream
        return cls(encoding=_stream_encoding(out), ascii_only=forced)

    # ── Asking ──────────────────────────────────────────────────────

    def can(self, text: str) -> bool:
        """Whether every character of ``text`` survives this encoding.

        Answered by encoding it, which is the only honest test — a table of
        codepoints per codec would be this same question, cached badly and
        wrong for the next codec Python grows. ``LookupError`` is the encoding
        naming something Python has never heard of, which is not the glyph's
        fault and so is not held against it.
        """
        if self.ascii_only:
            return text.isascii()
        if self.encoding is None:
            return True
        cached = self._cache.get(text)
        if cached is not None:
            return cached
        try:
            text.encode(self.encoding)
        except UnicodeEncodeError:
            answer = False
        except LookupError:
            answer = True
        else:
            answer = True
        # Only glyphs are memoised. The callers that pass whole lines pass a
        # different line every frame, and a cache keyed on those is a leak
        # wearing an optimisation's clothes.
        if len(text) <= 2:
            self._cache[text] = answer
        return answer

    def __call__(self, fancy: str, plain: str) -> str:
        """``fancy`` where this terminal can draw it, ``plain`` where it cannot.

        For a character that stands on its own. Where several are read as a
        set, use :meth:`resolve` — see the module docstring for the board this
        distinction was found on.

        The argument order is the good case first, so a call site reads as the
        glyph it normally is rather than as a conditional.
        """
        return fancy if self.can(fancy) else plain

    def resolve(self, *groups: str) -> dict[str, str]:
        """The final character for every glyph in ``groups``, all or none.

        Each named group of :data:`GROUPS` is decided as a unit: if any one of
        its glyphs will not encode, every glyph in it takes its plain form.
        Several groups may be named at once and are decided independently,
        then merged — which is what a hint line drawing both arrows and an
        ellipsis needs.

        The result maps each glyph to what should be drawn for it, so a caller
        can index it directly (``ops["∧"]``) or hand it to :meth:`translate`.
        """
        out: dict[str, str] = {}
        for name in groups:
            table = GROUPS[name]
            keep = not self.ascii_only and all(self.can(c) for c in table)
            out.update({c: c for c in table} if keep else table)
        return out

    def translate(self, text: str, table: dict[str, str]) -> str:
        """``text`` with every key of ``table`` replaced by its value.

        A blind substitution — ``table`` is expected to have come from
        :meth:`resolve` and to already say what should be drawn. Characters
        the table does not mention are left alone, so a glyph nobody thought
        about shows up as mojibake rather than being quietly replaced with
        something wrong.
        """
        if not table:
            return text
        return text.translate(str.maketrans(table))


__all__ = ["ASCII_ENV", "FALLBACKS", "GROUPS", "Glyphs"]
