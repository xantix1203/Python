"""Pygame event loops: ship placement and firing. Talks to models only through
their public methods (Grid.can_place/place, Player.has_fired_at) — no model
class needs to know Pygame exists.
"""

import pygame as pg

from ..config import BOAT_TYPE_NAMES, COLOR_BLACK, COLOR_BLUE, COLOR_GREY, COLOR_RED, FLEET, WINDOW_SIZE
from . import board_view
from .events import pump_and_wait, quit_if_closed
from .widgets import TextBox

DIRECTIONS = {"vertical": (0, 1), "horizontal": (1, 0)}


def place_boats_interactively(grid, window, player_name):
    vertical = True
    for size in sorted(FLEET, reverse=True):
        for _ in range(FLEET[size]):
            status_lines = [
                f"Mise en place : {player_name}",
                f"Placez votre {BOAT_TYPE_NAMES[size]} ({size} cases) — R pour pivoter",
            ]
            boat, vertical = _place_one_boat(grid, window, size, vertical, status_lines)
            _prompt_boat_name(window, grid, boat, size)


def _place_one_boat(grid, window, size, vertical, status_lines):
    _redraw_placement_board(window, grid, status_lines)
    pg.display.flip()
    while True:
        for event in pg.event.get():
            quit_if_closed(event)
            if event.type == pg.KEYDOWN and event.key == pg.K_r:
                vertical = not vertical
            elif event.type == pg.MOUSEMOTION:
                x, y = board_view.cell_from_pos(event.pos)
                direction = DIRECTIONS["vertical" if vertical else "horizontal"]
                preview = None
                if grid.can_place(x, y, size, direction):
                    dx, dy = direction
                    preview = [(x + dx * i, y + dy * i) for i in range(size)]
                _redraw_placement_board(window, grid, status_lines, preview)
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                x, y = board_view.cell_from_pos(event.pos)
                direction = DIRECTIONS["vertical" if vertical else "horizontal"]
                if grid.can_place(x, y, size, direction):
                    boat = grid.place(x, y, size, direction)
                    return boat, vertical
        pg.display.flip()


def _prompt_boat_name(window, grid, boat, size):
    status_lines = [f"Nommez votre {BOAT_TYPE_NAMES[size]} (Entrée pour valider)"]
    box = TextBox((WINDOW_SIZE // 2 - 150, WINDOW_SIZE // 2 - 20, 300, 40), "")
    box.active = True
    font = board_view.get_font()
    while True:
        for event in pg.event.get():
            quit_if_closed(event)
            if event.type == pg.KEYDOWN and event.key in (pg.K_RETURN, pg.K_KP_ENTER):
                typed = box.text.strip()
                if typed:
                    boat.name = typed
                return
            box.handle_event(event)
        _redraw_placement_board(window, grid, status_lines)
        box.draw(window, font)
        pg.display.flip()


def _redraw_placement_board(window, grid, status_lines, preview_cells=None):
    window.fill(COLOR_BLUE)
    board_view.draw_grid_lines(window)
    for boat in grid.floating_boats:
        board_view.draw_boat_full(window, boat, COLOR_BLACK)
    if preview_cells is not None:
        for cell in preview_cells:
            board_view.draw_cross(window, COLOR_GREY, cell)
    board_view.draw_status_bar(window, status_lines)


def get_shot_via_mouse(shooter, opponent, window):
    status_lines = [f"Tour de {shooter.name}", f"Visez la flotte de {opponent.name}"]
    _redraw_firing_board(window, shooter, opponent, status_lines)
    pg.display.flip()
    while True:
        for event in pg.event.get():
            quit_if_closed(event)
            if event.type == pg.MOUSEMOTION:
                cursor = board_view.cell_from_pos(event.pos)
                if not board_view.in_bounds(*cursor):
                    cursor = None
                _redraw_firing_board(window, shooter, opponent, status_lines, cursor)
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                shot = board_view.cell_from_pos(event.pos)
                if board_view.in_bounds(*shot) and not shooter.has_fired_at(opponent, shot):
                    return shot
        pg.display.flip()


def _redraw_firing_board(window, shooter, opponent, status_lines, cursor_cell=None):
    window.fill(COLOR_BLUE)
    board_view.draw_grid_lines(window)
    for cell in shooter.shots_fired[opponent]:
        board_view.draw_cross(window, COLOR_BLACK, cell)
    for boat in opponent.grid.floating_boats:
        board_view.draw_boat_partial(window, boat)
    for boat in opponent.grid.sunk_boats:
        board_view.draw_boat_full(window, boat, COLOR_RED)
    if cursor_cell is not None:
        board_view.draw_cross(window, COLOR_GREY, cursor_cell)
    board_view.draw_status_bar(window, status_lines)


def flash_result(window, shooter, opponent, shot, hit, sunk_boat, duration_ms=900):
    if sunk_boat is not None:
        message = f"{shooter.name} a coulé le {sunk_boat.name} de {opponent.name} !"
    elif hit:
        message = f"{shooter.name} a touché un bateau !"
    else:
        message = f"{shooter.name} a raté."
    _redraw_firing_board(window, shooter, opponent, [message])
    pg.display.flip()
    pump_and_wait(duration_ms)
