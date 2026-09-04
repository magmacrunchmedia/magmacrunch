"""``magmacrunch`` - open the arcade.

    magmacrunch            play
    magmacrunch --list     print the installed cabinets and exit

Discovery happens here, before the terminal is taken, and that placement is
load-bearing. :func:`magmacrunch.engine.arcade.discover` reports a game it could not
load with :func:`warnings.warn`, and a warning written onto a live Textual
screen corrupts it. Enumerating first puts anything it has to say on an
ordinary terminal, where it can be read.

``--list`` is the debugging surface for the same thing: it answers "why is my
game not in the menu" without taking the screen over at all.
"""

from __future__ import annotations

import argparse

from magmacrunch import __version__


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="magmacrunch",
        description="The magmacrunch terminal arcade.",
    )
    parser.add_argument(
        "--list", action="store_true", dest="list_only",
        help="print the installed cabinets and exit, without opening the arcade",
    )
    # Reads the literal in `magmacrunch/__init__.py` rather than asking
    # importlib.metadata, so it answers the same in a source checkout as in an
    # installed wheel. That literal drifted a whole release behind pyproject
    # once, unnoticed because nothing read it; this is what now reads it, and
    # `test_the_version_is_the_one_the_package_declares` is what checks it.
    parser.add_argument(
        "--version", action="version", version=f"magmacrunch {__version__}",
    )
    parser.add_argument(
        "--ascii", action="store_true", dest="ascii_only",
        help="draw with plain ASCII instead of block, arrow and suit "
             "glyphs. Detected automatically from the terminal's "
             "encoding; this forces it, for a font that lacks the "
             "pictures. MAGMACRUNCH_ASCII=1 says the same for every "
             "cabinet at once.",
    )
    args = parser.parse_args()

    # Imported here, not at module scope, so --help works without the engine
    # or its terminal extra installed.
    from magmacrunch.engine.arcade import discover

    games = discover()

    if args.list_only:
        _print(games)
        return

    from magmacrunch.app import ARCADE_INFO, ArcadeApp
    from magmacrunch.engine.core.tui_host import TuiHost
    from magmacrunch.engine.ui.glyphs import Glyphs

    # Set on the host, so every cabinet `seat()` puts on this terminal
    # inherits it. A game seated by the arcade never runs its own run(),
    # so this is the only place the question is asked for it.
    host = TuiHost(title=ARCADE_INFO.title, fps=ARCADE_INFO.fps,
                   hold_ms=ARCADE_INFO.hold_ms,
                   glyphs=Glyphs.detect(ascii_only=args.ascii_only))
    host.push_scene(ArcadeApp(host, games).root_scene)
    host.run()


def _print(games: list) -> None:
    """What ``--list`` shows: what was found, and what it wants.

    Titles and blurbs are written by whoever wrote the game, so they can hold
    anything Unicode holds - a suit glyph, a card, an emoji. Redirected to a
    file on a legacy Windows codepage that is a ``UnicodeEncodeError``, and a
    diagnostic that dies on the thing it is diagnosing is worse than useless.
    Degrade the characters instead.

    Two mechanisms, and they are not redundant. The glyph table knows what the
    arcade's own characters *mean* and turns an em dash into ``-``; stdout's
    ``errors="replace"`` is the backstop for everything else, and turns an
    emoji nobody anticipated into ``?``. Without the first, a blurb on cp1252
    read ``logic gates ? merge``, which is the diagnostic damaging the thing it
    is reporting on. Without the second, a game author could still crash this
    by picking a character the table has never heard of.
    """
    from magmacrunch.engine.ui.glyphs import GROUPS, Glyphs

    _degrade_gracefully()
    glyphs = Glyphs.detect()
    table = glyphs.resolve(*GROUPS)

    def say(text: str = "") -> None:
        print(glyphs.translate(text, table))

    if not games:
        from magmacrunch.cabinets import PACKAGES

        say("No cabinets installed.")
        say()
        for name in PACKAGES:
            say(f"  pip install {name}")
        say()
        say("Any package declaring a magmacrunch.games entry point appears")
        say("here. Nothing above this line is a hardcoded list.")
        return

    say(f"{len(games)} cabinet{'s' if len(games) != 1 else ''} installed:")
    say()
    for game in games:
        info = game.info
        say(f"  {info.key}")
        say(f"    {info.title}")
        say(f"    {info.blurb}")
        say(f"    wants {info.min_cols}x{info.min_rows}, "
            f"{info.fps} fps, hold {info.hold_ms} ms")
        say()


def _degrade_gracefully() -> None:
    """Let stdout substitute characters it cannot encode rather than raising."""
    import sys

    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is None:
        return
    try:
        reconfigure(errors="replace")
    except (ValueError, OSError):
        # Already detached, or not a stream that can be reconfigured. Printing
        # is still worth attempting; this was only ever insurance.
        pass


if __name__ == "__main__":
    main()
