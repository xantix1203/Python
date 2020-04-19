from Bot import *


class Game:
    def __init__(self):
        self.remaining_players = []
        self.eliminated_players = []
        numbers_of_players = 1  # int(input("Nombre de joueurs: ")) #TODO remettre en ordre
        if numbers_of_players == 1:
            self.remaining_players.append(Player("Arnaud"))  # str(input("Nom du joueur: "))))
            self.remaining_players.append(Bot())
        else:
            for i in range(numbers_of_players):
                self.remaining_players.append(Player(str(input("Nom du joueur {}: ".format(i + 1)))))
        for player in self.remaining_players:
            opponents_list = list(self.remaining_players)
            opponents_list.remove(player)
            for opponent in opponents_list:
                player.occupied_spaces[opponent] = []

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
