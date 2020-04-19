from Game import *

game = Game()
while len(game.remaining_players) > 1:
    game.round()
