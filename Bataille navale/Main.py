"""Entry point: setup menu, window, round loop, end screen."""

import pygame as pg

from battleship.engine.game import Game
from battleship.network.match import play_networked_match
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
    window = board_view.new_window("Bataille navale")
    sound.init()

    mode, payload = screens.run_setup_menu(window)

    if mode == "network":
        local_player, connection, is_host = payload
        play_networked_match(window, local_player, connection, is_host)
    else:
        players = payload
        game = Game(players)
        setup_fleets(players, window)

        on_result = make_on_result(window)
        while not game.is_over:
            game.play_round(lambda player, opponent: get_shot(player, opponent, window), on_result=on_result)

        if game.winner is not None:
            sound.play_victory()
        screens.show_end_screen(window, players, game.winner)

    pg.quit()


if __name__ == "__main__":
    main()
