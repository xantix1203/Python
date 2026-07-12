"""Shared constants for the battleship game."""

import json
from pathlib import Path

BOARD_SIZE = 10
CELL_SIZE = 80
WINDOW_SIZE = BOARD_SIZE * CELL_SIZE
STATUS_BAR_HEIGHT = 60
WINDOW_HEIGHT = WINDOW_SIZE + STATUS_BAR_HEIGHT

COLOR_BLUE = (90, 150, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GREY = (80, 80, 80)
COLOR_RED = (178, 34, 34)
COLOR_WHITE = (255, 255, 255)
COLOR_DARK_GREY = (40, 40, 40)

FONT_SIZE = 24

NETWORK_PORT = 51500

# Number of boats of each size in a fleet, keyed by boat size (cells long).
FLEET = {2: 1, 3: 2, 4: 1, 5: 1}

BOAT_TYPE_NAMES = {
    2: "torpilleur",
    3: "sous-marin",
    4: "croiseur",
    5: "porte-avion",
}

COUNTRIES = ["Pakistan", "China", "Japan", "USA", "France", "Canada"]

# Nicknames live outside version control (see private/nicknames.example.json
# for the expected format) since the mapping is personal, not project config.
_PRIVATE_DIR = Path(__file__).resolve().parent.parent / "private"
_NICKNAMES_PATH = _PRIVATE_DIR / "nicknames.json"


def _load_nicknames():
    if not _NICKNAMES_PATH.is_file():
        return {}
    with _NICKNAMES_PATH.open(encoding="utf-8") as f:
        return json.load(f)


# Keys are lowercase for case-insensitive, exact-match lookup.
NICKNAMES = _load_nicknames()


def resolve_nickname(name):
    return NICKNAMES.get(name.strip().lower(), name.strip())
