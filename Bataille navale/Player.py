from Grille import Grille

class Player:
    def __init__(self, name, score=0):
        self.name = name
        self.score = score
        self.grille = Grille()
