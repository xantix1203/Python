from Grille import *


class Player:
    def __init__(self, name, species="human", score=0):
        self.name = name
        self.score = score
        self.grille = Grille(species)
        self.eliminated = False

    def fire(self, player, shot):
        for boat in player.grille.floating_boat:
            hit, sunk = boat.evaluate_shot(shot)
            if sunk:
                player.grille.floating_boat.remove(boat)
                player.grille.sunk_boat.append(boat)
                self.score += 1
            if hit:
                self.score += 1

    @staticmethod
    def get_shot():
        return int(input("ordonnee tir: ")), int(input("abscisse tir"))
