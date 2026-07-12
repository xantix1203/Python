"""Shared constants for Bet Game."""

WINDOW_WIDTH = 960
WINDOW_HEIGHT = 720
FPS = 60

# Dare difficulty climbs by one level every ROUNDS_PER_LEVEL rounds played,
# capped at MAX_DARE_LEVEL (see engine.game.Game.level).
ROUNDS_PER_LEVEL = 3
MAX_DARE_LEVEL = 4

COLOR_BG = (24, 22, 34)
COLOR_WHITE = (245, 245, 245)
COLOR_BLACK = (10, 10, 10)
COLOR_GREY = (90, 90, 100)

# One background color per minigame category, so a popping card immediately
# reads as "scenario to act out" vs "forfeit" at a glance.
COLOR_CARD_IMPRO = (64, 120, 220)
COLOR_CARD_DUEL = (200, 60, 90)
COLOR_CARD_GAGE = (220, 150, 40)

TITLE_SIZE = 44
LABEL_SIZE = 26
BODY_SIZE = 22
