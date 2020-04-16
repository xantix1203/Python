from Player import Player
from random import choice


class Bot(Player):
    def __init__(self, score=0):
        self.type = "bot"
        Player.__init__(choice(["Ken", "Barbie", "Mickael", "Ta mère", "Joe la classe"]), score)
