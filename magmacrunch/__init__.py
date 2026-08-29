"""The magmacrunch terminal arcade.

A menu of every installed cabinet, and the wiring that seats one on the
terminal it is already holding.

Games are found by enumerating the ``magmacrunch.games`` entry point group -
see :mod:`magmacrunch.engine.arcade` for the contract. **Nothing in this package
imports a game.** Installing one makes it appear here; uninstalling makes it
vanish; neither needs a release of the arcade.

Imports are kept out of this module so that ``import magmacrunch`` costs
nothing: the launcher's own screens pull in the engine's terminal backend, and
``magmacrunch --help`` should not pay for it.
"""

from __future__ import annotations

__version__ = "0.4.1"

__all__ = ["__version__"]
