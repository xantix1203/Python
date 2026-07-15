"""One player's side of a networked match: the thin client that the host's
authoritative server (network/server.py) talks to. Handles the pre-game
handshake (roster -> place fleet -> ready), then hands off to the MatchView for
the match itself. The host runs this too, over an in-process loopback, so there
is a single client code path for everyone.
"""

from types import SimpleNamespace

import pygame as pg

from ..config import COLOR_BLACK, COLOR_BLUE, COLOR_RED, MATCH_WINDOW_HEIGHT, WINDOW_SIZE
from ..models.grid import Grid
from ..ui import board_view, screens, sound
from ..ui.events import quit_if_closed
from ..ui.input_handler import place_boats_interactively
from ..ui.match_view import MatchView


def run_client(window, conn, local_name):
    """Play a full networked match from this player's seat. `conn` is already
    connected/loopback-linked to the host and (for a remote joiner) has already
    sent its `join` during the lobby.
    """
    try:
        roster = _wait_for(window, conn, "roster", ["Connexion à la partie..."])
        me, seats = roster["you"], roster["seats"]

        _wait_for(window, conn, "place", [f"{len(seats)} joueurs. Placez votre flotte."])
        grid = Grid()
        place_boats_interactively(grid, window, local_name)
        conn.send({"type": "ready", "boats": _fleet_payload(grid)})

        final_state = MatchView(window, conn, me, seats, grid).run()
    except ConnectionError:
        _show_disconnect(_restore_window())
        return

    _show_result(_restore_window(), me, final_state)


def _restore_window():
    """MatchView leaves the display resizable and possibly scaled down to fit
    the screen; the closing screens assume the original fixed layout, so put
    the window back to that before drawing them.
    """
    return pg.display.set_mode((WINDOW_SIZE, MATCH_WINDOW_HEIGHT))


def _fleet_payload(grid):
    return [{"cells": [list(cell) for cell, _ in boat.cells], "name": boat.name} for boat in grid.floating_boats]


def _wait_for(window, conn, msg_type, status_lines):
    """Poll until a message of the given type arrives, keeping the window
    responsive and showing a status message meanwhile.
    """
    while True:
        for event in pg.event.get():
            quit_if_closed(event)
        message = conn.poll()  # raises ConnectionError if the host drops
        if message is not None and message.get("type") == msg_type:
            return message
        window.fill(COLOR_BLUE)
        board_view.draw_grid_lines(window)
        board_view.draw_status_bar(window, status_lines)
        pg.display.flip()
        pg.time.wait(16)


def _show_result(window, me, final_state):
    if final_state is None:
        return
    players = [
        SimpleNamespace(name=board["owner"], score=board["score"]) for board in final_state["boards"]
    ]
    winner_seat = final_state["winner"]
    winner = players[winner_seat] if winner_seat is not None else None
    if winner_seat == me:
        sound.play_victory()
    screens.show_end_screen(window, players, winner)


def _show_disconnect(window):
    font = board_view.get_font()
    window.fill(COLOR_BLUE)
    message = font.render("Connexion perdue. Partie interrompue.", True, COLOR_RED)
    window.blit(message, message.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2)))
    hint = font.render("Cliquez ou appuyez sur une touche pour quitter.", True, COLOR_BLACK)
    window.blit(hint, hint.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2 + 40)))
    pg.display.flip()
    while True:
        for event in pg.event.get():
            quit_if_closed(event)
            if event.type in (pg.KEYDOWN, pg.MOUSEBUTTONDOWN):
                return
        pg.time.wait(16)