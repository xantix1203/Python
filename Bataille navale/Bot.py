from Player import *


class Bot(Player):
    def __init__(self, score=0):
        Player.__init__(self, choice(["Ken", "Barbie", "Mickael", "Ta mère", "Joe la classe", "Samsoum"]), "bot", score)
