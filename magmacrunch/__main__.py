"""``magmacrunch`` - open the arcade.

    magmacrunch            play
    magmacrunch --list     print the installed cabinets and exit

Discovery happens here, before the terminal is taken, and that placement is
load-bearing. :func:`texastoast.arcade.discover` reports a game it could not
load with :func:`warnings.warn`, and a warning written onto a live Textual
screen corrupts it. Enumerating first puts anything it has to say on an
ordinary terminal, where it can be read.

``--list`` is the debugging surface for the same thing: it answers "why is my
game not in the menu" without taking the screen over at all.
"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="magmacrunch",
        description="The magmacrunch terminal arcade.",
    )
    parser.add_argument(
        "--list", action="store_true", dest="list_only",
        help="print the installed cabinets and exit, without opening the arcade",
    )
    args = parser.parse_args()

    # Imported here, not at module scope, so --help works without the engine
    # or its terminal extra installed.
    from texastoast.arcade import discover

    games = discover()

    if args.list_only:
        _print(games)
        return

    from texastoast.core.tui_host import TuiHost

    from magmacrunch.app import ARCADE_INFO, ArcadeApp

    host = TuiHost(title=ARCADE_INFO.title, fps=ARCADE_INFO.fps,
                   hold_ms=ARCADE_INFO.hold_ms)
    host.push_scene(ArcadeApp(host, games).root_scene)
    host.run()


def _print(games: list) -> None:
    """What ``--list`` shows: what was found, and what it wants.

    Titles and blurbs are written by whoever wrote the game, so they can hold
    anything Unicode holds - a suit glyph, a card, an emoji. Redirected to a
    file on a legacy Windows codepage that is a ``UnicodeEncodeError``, and a
    diagnostic that dies on the thing it is diagnosing is worse than useless.
    Degrade the characters instead.
    """
    _degrade_gracefully()

    if not games:
        print("No cabinets installed.")
        print()
        print("  pip install magmacrunch-george-boole")
        print("  pip install magmacrunch-thld")
        print()
        print("Any package declaring a magmacrunch.games entry point appears")
        print("here. Nothing above this line is a hardcoded list.")
        return

    print(f"{len(games)} cabinet{'s' if len(games) != 1 else ''} installed:")
    print()
    for game in games:
        info = game.info
        print(f"  {info.key}")
        print(f"    {info.title}")
        print(f"    {info.blurb}")
        print(f"    wants {info.min_cols}x{info.min_rows}, "
              f"{info.fps} fps, hold {info.hold_ms} ms")
        print()


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
