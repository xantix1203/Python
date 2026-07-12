"""Pygame drawing helpers. Pure functions of (window, data) — no game state lives here."""

import pygame as pg

from ..config import (
    BOARD_SIZE,
    CELL_SIZE,
    COLOR_BLACK,
    COLOR_BLUE,
    COLOR_DARK_GREY,
    COLOR_RED,
    COLOR_WHITE,
    FONT_SIZE,
    STATUS_BAR_HEIGHT,
    WINDOW_HEIGHT,
    WINDOW_SIZE,
)

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
    draw_grid_lines(window)
    pg.display.flip()
    return window


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
    for i in range(1, 10):
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


def draw_boat_full(window, boat, color):
    for cell, _ in boat.cells:
        draw_square(window, color, cell)
        draw_cross(window, color, cell)


def draw_boat_partial(window, boat):
    for cell, is_hit in boat.cells:
        if is_hit:
            draw_cross(window, COLOR_RED, cell)
