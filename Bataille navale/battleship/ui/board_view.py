"""Pygame drawing helpers. Pure functions of (window, data) — no game state lives here."""

import pygame as pg

from ..config import (
    BOARD_SIZE,
    CELL_SIZE,
    COLOR_BLACK,
    COLOR_BLUE,
    COLOR_DARK_GREY,
    COLOR_GREY,
    COLOR_RED,
    COLOR_WHITE,
    FONT_SIZE,
    MENU_WINDOW_SIZE,
    STATUS_BAR_HEIGHT,
    WINDOW_HEIGHT,
    WINDOW_SIZE,
)
from . import sprites

_font = None


def get_font():
    global _font
    if _font is None:
        _font = pg.font.Font(None, FONT_SIZE)
    return _font


def cell_from_pos(pos):
    x_disp, y_disp = pos
    return x_disp // CELL_SIZE, y_disp // CELL_SIZE


def in_bounds(x, y):
    return 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE


def new_window(caption):
    window = pg.display.set_mode((WINDOW_SIZE, WINDOW_HEIGHT))
    pg.display.set_caption(caption)
    window.fill(COLOR_BLUE)
    draw_sea(window)
    draw_grid_lines(window)
    pg.display.flip()
    return window


def new_menu_window(caption):
    """A fixed-size window for the setup menu / lobby / join screens, sized
    independently of CELL_SIZE so their fixed-position buttons always stay on
    screen no matter how the board is configured.
    """
    window = pg.display.set_mode(MENU_WINDOW_SIZE)
    pg.display.set_caption(caption)
    window.fill(COLOR_BLUE)
    pg.display.flip()
    return window


def draw_sea(window):
    """Fills the board's WINDOW_SIZE x WINDOW_SIZE area with the tileable sea
    texture from private/visuals/sea.png, repeated to cover it -- or a flat
    COLOR_BLUE if no art file is present. Independent of CELL_SIZE: the tile
    is drawn at its own resolution, not stretched to fit the grid.
    """
    tile = sprites.get_sea_tile()
    if tile is None:
        window.fill(COLOR_BLUE, (0, 0, WINDOW_SIZE, WINDOW_SIZE))
        return
    tile_w, tile_h = tile.get_size()
    for y in range(0, WINDOW_SIZE, tile_h):
        for x in range(0, WINDOW_SIZE, tile_w):
            window.blit(tile, (x, y))


def draw_status_bar(window, lines):
    bar_rect = pg.Rect(0, WINDOW_SIZE, WINDOW_SIZE, STATUS_BAR_HEIGHT)
    pg.draw.rect(window, COLOR_DARK_GREY, bar_rect)
    font = get_font()
    line_height = font.get_linesize()
    top = WINDOW_SIZE + (STATUS_BAR_HEIGHT - line_height * len(lines)) // 2
    for i, line in enumerate(lines):
        text_surface = font.render(line, True, COLOR_WHITE)
        window.blit(text_surface, (10, top + i * line_height))


def draw_grid_lines(window, color=COLOR_BLACK):
    for i in range(1, BOARD_SIZE):
        pg.draw.line(window, color, (CELL_SIZE * i, 0), (CELL_SIZE * i, WINDOW_SIZE), 1)
        pg.draw.line(window, color, (0, CELL_SIZE * i), (WINDOW_SIZE, CELL_SIZE * i), 1)


def draw_square(window, color, cell):
    x, y = cell
    x0, y0 = x * CELL_SIZE, y * CELL_SIZE
    x1, y1 = x0 + CELL_SIZE, y0 + CELL_SIZE
    for start, end in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
        pg.draw.line(window, color, start, end, 5)


def draw_cross(window, color, cell):
    x, y = cell
    x0, y0 = x * CELL_SIZE + 10, y * CELL_SIZE + 10
    x1, y1 = (x + 1) * CELL_SIZE - 10, (y + 1) * CELL_SIZE - 10
    pg.draw.line(window, color, (x0, y0), (x1, y1), 5)
    pg.draw.line(window, color, (x1, y0), (x0, y1), 5)


def draw_preview_highlight(window, cell, color=(255, 215, 0, 90)):
    """A translucent highlight over `cell`, used to preview the full area a
    multi-cell special (USA's block, Italy's row/column) would affect while
    the player is still choosing where to aim.
    """
    surf = pg.Surface((CELL_SIZE, CELL_SIZE), pg.SRCALPHA)
    surf.fill(color)
    window.blit(surf, (cell[0] * CELL_SIZE, cell[1] * CELL_SIZE))


def draw_energy_icon(window, pos, size=14, color=(255, 220, 60)):
    """A small lightning-bolt badge, top-left anchored at `pos` -- the Energy
    counter's icon. Drawn as a plain vector shape rather than an emoji glyph:
    pygame's default font (ui/match_view.py's captions) can't render emoji at
    all, showing a tofu box instead, so there's no font-based fallback to
    lean on here the way board_view's other icons can.
    """
    x, y = pos
    points = [
        (x + size * 0.65, y),
        (x + size * 0.25, y + size * 0.55),
        (x + size * 0.45, y + size * 0.55),
        (x + size * 0.35, y + size),
        (x + size * 0.75, y + size * 0.45),
        (x + size * 0.55, y + size * 0.45),
    ]
    pg.draw.polygon(window, color, points)


def draw_shield_icon(window, pos, size=14, color=(120, 200, 255)):
    """A small shield badge, top-left anchored at `pos` -- marks a Congo-
    shielded player's own tile. Same emoji-avoidance reasoning as
    draw_energy_icon above.
    """
    x, y = pos
    points = [
        (x, y + size * 0.05),
        (x + size, y + size * 0.05),
        (x + size, y + size * 0.5),
        (x + size * 0.5, y + size),
        (x, y + size * 0.5),
    ]
    pg.draw.polygon(window, color, points)
    pg.draw.polygon(window, COLOR_WHITE, points, 1)


def draw_boat_full(window, boat, color):
    for cell, _ in boat.cells:
        draw_square(window, color, cell)
        draw_cross(window, color, cell)


def draw_boat_partial(window, boat):
    for cell, is_hit in boat.cells:
        if is_hit:
            draw_cross(window, COLOR_RED, cell)


def _boat_topleft(boat):
    xs = [cell[0][0] for cell in boat.cells]
    ys = [cell[0][1] for cell in boat.cells]
    return min(xs) * CELL_SIZE, min(ys) * CELL_SIZE


def draw_boat_preview(window, boat):
    """A translucent version of the boat's real art (or the grey-cross
    fallback) that follows the cursor while the player is choosing where to
    place it -- not yet committed to the grid.
    """
    sprite = sprites.get_boat_sprite(boat)
    if sprite is None:
        for cell, _ in boat.cells:
            draw_cross(window, COLOR_GREY, cell)
        return
    ghost = sprite.copy()
    ghost.fill((255, 255, 255, 170), special_flags=pg.BLEND_RGBA_MULT)
    window.blit(ghost, _boat_topleft(boat))


def draw_boat(window, boat):
    """The boat's real artwork if available -- oriented to match how it was
    placed, and swapped to its 'destroyed' sprite once sunk -- else the
    plain outline+cross fallback. Used for boats whose full extent is meant
    to be visible: your own fleet, and any opponent boat once it's sunk.
    """
    sprite = sprites.get_boat_sprite(boat)
    if sprite is None:
        draw_boat_full(window, boat, COLOR_RED if boat.is_sunk else COLOR_BLACK)
        return
    window.blit(sprite, _boat_topleft(boat))
    if not boat.is_sunk:
        for cell, is_hit in boat.cells:
            if is_hit:
                draw_cross(window, COLOR_RED, cell)


def draw_plane(window, position, horizontal):
    """Italy's plane sprite for the flyover animation, oriented along its
    flight axis and centered on `position` -- an (x, y) in cell units that
    may be fractional (e.g. (2.4, 3.0)), for smooth continuous movement
    rather than jumping cell to cell -- or a simple triangle if no art file
    is present (private/visuals/bombardiro.png).
    """
    x, y = position
    center = (int(x * CELL_SIZE + CELL_SIZE // 2), int(y * CELL_SIZE + CELL_SIZE // 2))
    sprite = sprites.get_plane_sprite()
    if sprite is None:
        _draw_plane_fallback(window, center, horizontal)
        return
    scaled = pg.transform.smoothscale(sprite, (CELL_SIZE * 2, CELL_SIZE))
    # -90 (not +90): pygame's rotate is counter-clockwise, so +90 on a
    # rightward-nosed sprite would point it up, but Italy's column flight
    # always travels top-to-bottom (see _italy_cells) -- nose must point down.
    oriented = scaled if horizontal else pg.transform.rotate(scaled, -90)
    window.blit(oriented, oriented.get_rect(center=center))


def _draw_plane_fallback(window, center, horizontal):
    cx, cy = center
    size = CELL_SIZE // 3
    if horizontal:
        points = [(cx + size, cy), (cx - size, cy - size // 2), (cx - size, cy + size // 2)]
    else:
        points = [(cx, cy + size), (cx - size // 2, cy - size), (cx + size // 2, cy - size)]
    pg.draw.polygon(window, COLOR_BLACK, points)


_HIT_RINGS = [((255, 60, 20), 0.0, 5), ((255, 120, 30), 0.15, 4), ((255, 170, 60), 0.3, 3)]
_MISS_RINGS = [((225, 240, 255), 0.0, 3), ((190, 220, 255), 0.2, 2)]


def draw_impact_effect(window, cell, progress, hit):
    """Overlays a brief animated burst (hit) or ripple (miss) on `cell`.
    `progress` runs 0..1 across the flash pause; call once per rendered frame.
    """
    for color, delay, width in _HIT_RINGS if hit else _MISS_RINGS:
        local_progress = (progress - delay) / (1 - delay)
        if local_progress <= 0:
            continue
        local_progress = min(local_progress, 1.0)
        radius = int(CELL_SIZE * 0.5 * local_progress)
        alpha = int(255 * (1 - local_progress))
        if radius < 1 or alpha <= 0:
            continue
        surf = pg.Surface((CELL_SIZE, CELL_SIZE), pg.SRCALPHA)
        pg.draw.circle(surf, (*color, alpha), (CELL_SIZE // 2, CELL_SIZE // 2), radius, width)
        window.blit(surf, (cell[0] * CELL_SIZE, cell[1] * CELL_SIZE))
    if hit and progress < 0.25:
        flash_progress = progress / 0.25
        radius = int(CELL_SIZE * (0.15 + 0.25 * (1 - flash_progress)))
        alpha = int(255 * (1 - flash_progress))
        surf = pg.Surface((CELL_SIZE, CELL_SIZE), pg.SRCALPHA)
        pg.draw.circle(surf, (255, 235, 180, alpha), (CELL_SIZE // 2, CELL_SIZE // 2), radius)
        window.blit(surf, (cell[0] * CELL_SIZE, cell[1] * CELL_SIZE))
