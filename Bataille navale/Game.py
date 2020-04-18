from Bot import *


class Game:
    def __init__(self):
        self.remaining_players = []
        self.eliminated_players = []
        numbers_of_players = int(input("Nombre de joueurs: "))
        if numbers_of_players == 1:
            self.remaining_players.append(Player(str(input("Nom du joueur: "))))
            self.remaining_players.append(Bot())
        else:
            for i in range(numbers_of_players):
                self.remaining_players.append(Player(str(input("Nom du joueur {}: ".format(i)))))

    def round(self):
        for player in self.remaining_players:
            opponents_list = list(self.remaining_players)
            opponents_list.remove(player)
            for opponent in opponents_list:
                player.fire(opponent, player.get_shot())
                if not opponent.grille.floating_boat:
                    self.remaining_players.remove(opponent)
                    self.eliminated_players.append(opponent)
