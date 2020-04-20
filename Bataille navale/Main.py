from GameServeurManager import *


def get_is_local():
    return True


is_local = get_is_local()
if is_local:
    game = Game(True)
    while len(game.remaining_players) > 1:
        game.round()
    else:
        game_server_manager = GameServerManager()
