"""Entry point: setup menu, window, round loop, end screen."""

import threading

import pygame as pg

from battleship.engine.game import Game
from battleship.network import client, server
from battleship.network.connection import loopback_pair
from battleship.ui import board_view, input_handler, screens, sound


def setup_fleets(players, window):
    for player in players:
        if player.species == "bot":
            player.grid.place_fleet_randomly()
        else:
            input_handler.place_boats_interactively(player.grid, window, player.name)


def get_shot(player, opponent, window):
    if player.species == "bot":
        return player.get_shot(opponent)
    return input_handler.get_shot_via_mouse(player, opponent, window)


def make_on_result(window):
    def on_result(player, opponent, shot, hit, sunk_boat):
        if sunk_boat is not None:
            sound.play_sunk(player.country)
        elif hit:
            sound.play_hit(player.country)
        else:
            sound.play_miss(player.country)
        input_handler.flash_result(window, player, opponent, shot, hit, sunk_boat)

    return on_result


def main():
    pg.init()
    window = board_view.new_menu_window("Bataille navale")
    sound.init()

    mode, payload = screens.run_setup_menu(window)
    window = board_view.new_window("Bataille navale")  # resize for the board itself

    if mode == "host":
        _run_host(window, payload)
    elif mode == "join":
        local_player, connection = payload
        client.run_client(window, connection, local_player.name)
    else:
        _run_local(window, payload)

    pg.quit()


def _run_host(window, payload):
    """Host both the authoritative server (background thread) and this machine's
    own player view, wired to the server through an in-process loopback so the
    host plays through the exact same client code path as every joiner.
    """
    host_player, joined = payload
    server_end, host_end = loopback_pair()
    endpoints = [server.Endpoint(server_end, host_player.name, host_player.country)]
    endpoints += [server.Endpoint(peer["conn"], peer["name"], peer["country"]) for peer in joined]
    threading.Thread(target=server.serve, args=(endpoints,), daemon=True).start()
    client.run_client(window, host_end, host_player.name)


def _run_local(window, players):
    game = Game(players)
    setup_fleets(players, window)

    on_result = make_on_result(window)
    while not game.is_over:
        game.play_round(lambda player, opponent: get_shot(player, opponent, window), on_result=on_result)

    if game.winner is not None:
        sound.play_victory()
    screens.show_end_screen(window, players, game.winner)


if __name__ == "__main__":
    main()
