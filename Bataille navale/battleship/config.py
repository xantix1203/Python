"""Shared constants for the battleship game."""

import json
from pathlib import Path

BOARD_SIZE = 10
CELL_SIZE = 60
WINDOW_SIZE = BOARD_SIZE * CELL_SIZE
STATUS_BAR_HEIGHT = 60
WINDOW_HEIGHT = WINDOW_SIZE + STATUS_BAR_HEIGHT

# Setup menu / lobby / join screens have their own fixed-position buttons that
# have nothing to do with the board -- sized on their own, generously, so
# shrinking CELL_SIZE for the board can never push one of their buttons off
# screen (see screens.py).
MENU_WINDOW_SIZE = (760, 720)

# The N-player network match adds a taller bottom panel (opponent thumbnails +
# scoreboard + event log) below the full-size board, so it uses its own window
# height rather than the 60px status bar of local play.
MATCH_PANEL_HEIGHT = 220
MATCH_WINDOW_HEIGHT = WINDOW_SIZE + MATCH_PANEL_HEIGHT

COLOR_BLUE = (90, 150, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GREY = (80, 80, 80)
COLOR_RED = (178, 34, 34)
COLOR_WHITE = (255, 255, 255)
COLOR_DARK_GREY = (40, 40, 40)

FONT_SIZE = 24

NETWORK_PORT = 51500

# Free-targeting LAN mode. 2..MAX_PLAYERS players share one authoritative host.
# WIN_SCORE / KILL_BONUS were derived from a rough model, not playtesting -- kept
# here so retuning is a one-line change (see SPEC-multiplayer.txt "TUNING NOTE").
MAX_PLAYERS = 5
WIN_SCORE = 15  # first to this many points wins (or last player standing)
SINK_POINTS = 1  # awarded for sinking any ship
KILL_BONUS = 3  # awarded instead of SINK_POINTS when the sink eliminates a player

# Number of boats of each size in a fleet, keyed by boat size (cells long).
FLEET = {2: 1, 3: 2, 4: 1, 5: 1}

# Country-based "specials" (see SPEC-multiplayer.txt / bataille-navale-spec.md).
# Energy is a per-player currency: +1 at the start of your own turn (not on a
# chained bonus shot), +1 more whenever a shot lands a hit on your board.
ENERGY_PASSIVE_GAIN = 1
ENERGY_RETALIATION_GAIN = 1

# Cost to cast each country's special, in Energy. Defined for all countries
# from day one -- see engine/specials.py for why a missing entry is an error
# rather than a silent no-op.
SPECIAL_COSTS = {
    "Pakistan": 6,
    "China": 5,
    "USA": 8,
    "URSS": 5,
    "Italy": 6,
    "Bresil": 7,
    "Congo": 4,
}

# Hard cap on USA's "Accidental Nuclear Test" casts per game. Public (shown
# in the state broadcast as "usa_casts") so the client can grey out the cast
# button and explain why once it's reached -- see engine/specials.py's
# _usa_eligible, the enforcement point.
USA_MAX_CASTS = 2

# How long every other living, unshielded player has to Accept/Refuse
# Pakistan's "Le Cousin à Dubaï" pop-up before the server times it out.
PAKISTAN_VOTE_SECONDS = 10

# How many random un-shot cells of their own board a player takes hits on for
# Refusing Pakistan's offer ("losing an opportunity").
PAKISTAN_REFUSAL_HITS = 3

# One is picked at random each time Pakistan casts, formatted with
# shooter=<caster's name>. Edit/add freely -- see engine/specials.py's
# _pakistan_apply, the only reader.
PAKISTAN_OFFER_TEXTS = [
    "{shooter} envoie une offre à tout le monde... (Le Cousin à Dubaï)",
    "{shooter} propose un investissement extraordinaire à tout le monde !",
    "{shooter} a un cousin à Dubaï avec une opportunité en or pour vous...",
    "{shooter} partage un plan crypto infaillible avec toute la table.",
    "{shooter} vend des parts dans un projet immobilier... à Dubaï, bien sûr.",
]

BOAT_TYPE_NAMES = {
    2: "torpilleur",
    3: "destroyer",
    4: "croiseur",
    5: "porte-avion",
}

COUNTRIES = ["Pakistan", "China", "USA", "URSS", "Italy", "Bresil", "Congo"]

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
