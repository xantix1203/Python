"""Loads real boat artwork from the user's private, gitignored asset folder
(private/visuals/), scaling and rotating each sprite to match the boat's
actual size and placed orientation, and swapping to a '_destroyed' sprite
once the boat is sunk.

Art is optional: if a file is missing -- e.g. a fresh checkout without the
private assets -- get_boat_sprite() returns None and callers fall back to
the plain primitive shapes in board_view.py instead of crashing.
"""

from pathlib import Path

import pygame as pg

from ..config import CELL_SIZE

_VISUALS_DIR = Path(__file__).resolve().parent.parent.parent / "private" / "visuals"

# Boat type name -> (afloat filename, destroyed filename). Both are drawn
# bow-right; the game rotates them to match however the boat was placed.
_SPRITE_FILES = {
    "torpilleur": ("torpilleur.png", "torpilleur_destroyed.png"),
    "destroyer": ("destroyer.png", "destroyer_destroyed.png"),
    "croiseur": ("croiseur.png", "croiseur_destroyed.png"),
    "porte-avion": ("porte-avion.png", "porte-avion_destroyed.png"),
}

# (dx, dy) -> degrees to rotate a bow-right sprite so its bow faces that way.
_ROTATION_BY_DIRECTION = {(1, 0): 0, (0, -1): 90, (-1, 0): 180, (0, 1): -90}

_raw_cache = {}  # type name -> {"afloat": Surface|None, "destroyed": Surface|None}
_prepared_cache = {}  # (type name, direction, is_sunk) -> Surface|None

_SEA_TILE_FILE = "sea.png"
_sea_tile = None
_sea_tile_loaded = False


def get_sea_tile():
    """The tileable sea texture from private/visuals/sea.png, or None if the
    art file isn't present -- callers fall back to a flat color fill, same as
    a missing boat sprite.
    """
    global _sea_tile, _sea_tile_loaded
    if not _sea_tile_loaded:
        _sea_tile = _load_image(_SEA_TILE_FILE)
        _sea_tile_loaded = True
    return _sea_tile


_PLANE_FILE = "bombardiro.png"
_plane_sprite = None
_plane_sprite_loaded = False


def get_plane_sprite():
    """The optional plane art for Italy's special, drawn bow-right, from
    private/visuals/bombardiro.png -- or None if the art file isn't present
    (board_view falls back to a plain triangle, same optional-art pattern as
    everything else in this module).
    """
    global _plane_sprite, _plane_sprite_loaded
    if not _plane_sprite_loaded:
        _plane_sprite = _load_image(_PLANE_FILE)
        _plane_sprite_loaded = True
    return _plane_sprite


def get_boat_sprite(boat):
    """Oriented, scaled sprite for `boat` in its current state, or None if
    no art file is available for it.
    """
    direction = _direction(boat)
    key = (boat.type, direction, boat.is_sunk)
    if key not in _prepared_cache:
        _prepared_cache[key] = _prepare(boat, direction)
    return _prepared_cache[key]


def _direction(boat):
    (x0, y0), _ = boat.cells[0]
    (x1, y1), _ = boat.cells[1]
    return (x1 - x0, y1 - y0)


def _prepare(boat, direction):
    raw = _load_raw(boat.type)
    image = raw["destroyed"] if boat.is_sunk and raw["destroyed"] is not None else raw["afloat"]
    if image is None:
        return None
    scaled = pg.transform.smoothscale(image, (boat.size * CELL_SIZE, CELL_SIZE))
    angle = _ROTATION_BY_DIRECTION.get(direction, 0)
    return pg.transform.rotate(scaled, angle)


def _load_raw(type_name):
    if type_name not in _raw_cache:
        afloat_name, destroyed_name = _SPRITE_FILES.get(type_name, (None, None))
        _raw_cache[type_name] = {
            "afloat": _load_image(afloat_name),
            "destroyed": _load_image(destroyed_name),
        }
    return _raw_cache[type_name]


def _load_image(filename):
    if filename is None:
        return None
    path = _VISUALS_DIR / filename
    if not path.is_file():
        return None
    return pg.image.load(str(path)).convert_alpha()
