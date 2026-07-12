"""Entry point: name entry, starting objects, then rounds until the window
is closed.
"""

import pygame as pg

from bet_game.config import WINDOW_HEIGHT, WINDOW_WIDTH
from bet_game.engine.game import Game
from bet_game.ui import screens

_MISSING_CONTENT_MESSAGE = (
    "Aucun contenu trouvé dans private/. Ce dossier n'est pas versionné : "
    "copie private/dares.example.py, private/simulations.example.py, "
    "private/duels.example.py et private/objects.example.py vers les mêmes "
    "noms sans « .example », puis relance le jeu."
)


def _load_private_content():
    try:
        import private.dares  # noqa: F401
        import private.duels  # noqa: F401
        import private.objects  # noqa: F401
        import private.simulations  # noqa: F401
    except ModuleNotFoundError as error:
        raise SystemExit(_MISSING_CONTENT_MESSAGE) from error


def main():
    _load_private_content()
    pg.init()
    window = pg.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pg.display.set_caption("Bet Game")
    clock = pg.time.Clock()

    player1, player2 = screens.run_setup_screen(window, clock)
    screens.run_objects_screen(window, clock, player1, player2)
    game = Game(player1, player2)
    screens.run_round_screen(window, clock, game)


if __name__ == "__main__":
    main()
