from Grille import *


class Player:
    def __init__(self, name, grille, score=0):
        self.name = name
        self.score = score
        self.grille = Grille(species="human")
