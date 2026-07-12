"""Orchestrates one 2-player match over a Connection.

This deliberately does NOT reuse battleship.engine.game.Game: that engine's
play_round drives every player's turn from a single in-process loop, which
only works because local/bot mode has real, mutable Grid objects for both
sides in memory at once. Across two machines neither side has that — each
can only be authoritative for its own Grid — so the turn loop here has a
different shape: alternate between "send my shot, wait for the result" and
"wait for their shot, resolve it locally, send the result back".
"""

import types

import pygame as pg

from ..config import COLOR_BLACK, COLOR_BLUE, COLOR_GREY, COLOR_RED
from ..models.boat import Boat
from ..ui import board_view, screens, sound
from ..ui.events import pump_and_wait, quit_if_closed
from ..ui.input_handler import place_boats_interactively


class RemoteFleetView:
    """Tracks only what we've learned about the opponent's fleet from their
    'result' messages — we never see their real Grid. Shaped so the two
    outcomes we can render (a hit not yet sunk, a fully sunk boat) are cheap
    to draw with the existing board_view primitives.
    """

    def __init__(self):
        self.pending_hit_cells = []
        self.sunk_boats = []

    def record_result(self, shot, hit, sunk, boat_cells, boat_name=None):
        if sunk:
            boat = Boat(len(boat_cells), boat_cells, name=boat_name)
            for cell in boat.cells:
                cell[1] = True
            self.sunk_boats.append(boat)
            for cell in boat_cells:
                if cell in self.pending_hit_cells:
                    self.pending_hit_cells.remove(cell)
        elif hit:
            self.pending_hit_cells.append(shot)


def play_networked_match(window, local_player, connection, is_host):
    connection.send({"type": "hello", "name": local_player.name})
    hello = _wait_for_message(window, connection, ["Connexion à l'adversaire..."])
    opponent_name = hello["name"]

    place_boats_interactively(local_player.grid, window, local_player.name)
    connection.send({"type": "ready"})
    _wait_for_message(window, connection, ["En attente de l'adversaire..."])

    remote_view = RemoteFleetView()
    my_shots = []
    opponent_score = 0
    is_my_turn = is_host

    while True:
        if is_my_turn:
            shot = _get_shot_via_mouse(window, local_player.name, opponent_name, my_shots, remote_view)
            connection.send({"type": "shot", "x": shot[0], "y": shot[1]})
            result = _wait_for_message(window, connection, [f"Tir envoyé : ({shot[0]}, {shot[1]})..."])
            my_shots.append(shot)
            hit, sunk = result["hit"], result["sunk"]
            if hit:
                local_player.score += 1
                if sunk:
                    local_player.score += 1
            boat_cells = [tuple(cell) for cell in result.get("boat_cells", [])]
            boat_name = result.get("boat_name")
            remote_view.record_result(shot, hit, sunk, boat_cells, boat_name)
            _flash_attack_result(window, local_player.name, opponent_name, my_shots, remote_view, hit, sunk)
            if hit and sunk:
                sound.play_sunk(local_player.country)
            elif hit:
                sound.play_hit(local_player.country)
            else:
                sound.play_miss(local_player.country)
            if result["game_over"]:
                break
        else:
            message = _wait_for_shot(window, connection, local_player)
            shot = (message["x"], message["y"])
            hit, sunk_boat = local_player.receive_shot(shot)
            game_over = not local_player.grid.floating_boats
            reply = {"type": "result", "hit": hit, "sunk": sunk_boat is not None, "game_over": game_over}
            if sunk_boat is not None:
                reply["boat_cells"] = [cell for cell, _ in sunk_boat.cells]
                reply["boat_name"] = sunk_boat.name
            connection.send(reply)
            if hit:
                opponent_score += 1
                if sunk_boat is not None:
                    opponent_score += 1
            _flash_defense_result(window, local_player, opponent_name, hit, sunk_boat)
            if game_over:
                break
        is_my_turn = not is_my_turn

    opponent_stub = types.SimpleNamespace(name=opponent_name, score=opponent_score)
    won = bool(local_player.grid.floating_boats)
    winner = local_player if won else opponent_stub
    if won:
        sound.play_victory()
    screens.show_end_screen(window, [local_player, opponent_stub], winner)


def _wait_for_message(window, connection, status_lines):
    while True:
        for event in pg.event.get():
            quit_if_closed(event)
        message = connection.poll()
        if message is not None:
            return message
        window.fill(COLOR_BLUE)
        board_view.draw_grid_lines(window)
        board_view.draw_status_bar(window, status_lines)
        pg.display.flip()
        pg.time.wait(16)


def _wait_for_shot(window, connection, local_player):
    status_lines = ["Tour de l'adversaire", "En attente de son tir..."]
    while True:
        for event in pg.event.get():
            quit_if_closed(event)
        message = connection.poll()
        if message is not None:
            return message
        _redraw_own_board(window, local_player, status_lines)
        pg.display.flip()
        pg.time.wait(16)


def _get_shot_via_mouse(window, local_name, opponent_name, my_shots, remote_view):
    status_lines = [f"Tour de {local_name}", f"Visez la flotte de {opponent_name}"]
    _redraw_attack_board(window, my_shots, remote_view, status_lines)
    pg.display.flip()
    while True:
        for event in pg.event.get():
            quit_if_closed(event)
            if event.type == pg.MOUSEMOTION:
                cursor = board_view.cell_from_pos(event.pos)
                if not board_view.in_bounds(*cursor):
                    cursor = None
                _redraw_attack_board(window, my_shots, remote_view, status_lines, cursor)
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                shot = board_view.cell_from_pos(event.pos)
                if board_view.in_bounds(*shot) and shot not in my_shots:
                    return shot
        pg.display.flip()


def _redraw_attack_board(window, my_shots, remote_view, status_lines, cursor_cell=None):
    """The board you're firing at: what you've learned about the opponent's
    fleet so far, via RemoteFleetView — never their real Grid.
    """
    window.fill(COLOR_BLUE)
    board_view.draw_grid_lines(window)
    for cell in my_shots:
        board_view.draw_cross(window, COLOR_BLACK, cell)
    for cell in remote_view.pending_hit_cells:
        board_view.draw_cross(window, COLOR_RED, cell)
    for boat in remote_view.sunk_boats:
        board_view.draw_boat_full(window, boat, COLOR_RED)
    if cursor_cell is not None:
        board_view.draw_cross(window, COLOR_GREY, cursor_cell)
    board_view.draw_status_bar(window, status_lines)


def _redraw_own_board(window, local_player, status_lines):
    """Your own board while it's the opponent's turn: your real ships (you
    placed them, you already know where they are) with hits marked in red.
    """
    window.fill(COLOR_BLUE)
    board_view.draw_grid_lines(window)
    for boat in local_player.grid.floating_boats:
        for cell, is_hit in boat.cells:
            board_view.draw_square(window, COLOR_BLACK, cell)
            if is_hit:
                board_view.draw_cross(window, COLOR_RED, cell)
    for boat in local_player.grid.sunk_boats:
        board_view.draw_boat_full(window, boat, COLOR_RED)
    board_view.draw_status_bar(window, status_lines)


def _flash_attack_result(window, shooter_name, opponent_name, my_shots, remote_view, hit, sunk, duration_ms=900):
    if sunk:
        message = f"{shooter_name} a coulé le {remote_view.sunk_boats[-1].name} de {opponent_name} !"
    elif hit:
        message = f"{shooter_name} a touché un bateau !"
    else:
        message = f"{shooter_name} a raté."
    _redraw_attack_board(window, my_shots, remote_view, [message])
    pg.display.flip()
    pump_and_wait(duration_ms)


def _flash_defense_result(window, local_player, opponent_name, hit, sunk_boat, duration_ms=900):
    if sunk_boat is not None:
        message = f"{opponent_name} a coulé votre {sunk_boat.name} !"
    elif hit:
        message = f"{opponent_name} a touché un de vos bateaux !"
    else:
        message = f"{opponent_name} a raté."
    _redraw_own_board(window, local_player, [message])
    pg.display.flip()
    pump_and_wait(duration_ms)
