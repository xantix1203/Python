"""Shared constants for the battleship game."""

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
