from Bot import *


class Game:
    def __init__(self):
        self.multiplayer = self.init_get_multiplayer()
        self.remaining_players = []
        self.eliminated_players = []
        number_of_players = self.init_get_number_of_players()
        self.remaining_players = self.init_get_players(number_of_players)
        for player in self.remaining_players:
            opponents_list = list(self.remaining_players)
            opponents_list.remove(player)
            for opponent in opponents_list:
                player.occupied_spaces[opponent] = []
                if player.species == "bot":
                    player.remaining_shots[opponent] = [(i, j) for i in range(10) for j in range(10)]
        for player in self.remaining_players:
            print(player)
            print(player.grid)

    def round(self):
        for player in self.remaining_players:
            opponents_list = list(self.remaining_players)
            opponents_list.remove(player)
            for opponent in opponents_list:
                print(player)
                print(opponent)
                player.fire(opponent, player.get_shot(opponent))
                if not opponent.grid.floating_boat:
                    self.remaining_players.remove(opponent)
                    self.eliminated_players.append(opponent)
            print("liste bateaux {}".format(player))
            for boat in player.grid.floating_boat:
                print(boat.list, boat.state)

    @staticmethod
    def init_get_multiplayer():
        return True

    @staticmethod
    def init_get_number_of_players():
        return 2

    @staticmethod
    def init_get_players(number_of_players):
        if number_of_players == 1:
            return [Player("Arnaud")] + [Bot()]
        elif number_of_players == 2:
            return [Player("Arnaud")] + [Player("Barry")]
        else:
            players_list = []
            for i in range(number_of_players):
                players_list.append((str(input("Nom du joueur {}: ".format(i + 1)))))
            return players_list
