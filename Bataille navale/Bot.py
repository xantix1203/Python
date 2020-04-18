from Player import *
from random import choice


class Bot(Player):
    def __init__(self, score=0):
        Player.__init__(self, choice(["Ken", "Barbie", "Mickael", "Joe la classe", "Samsoum"]), "bot", score)

    @staticmethod
    def get_shot(opponent):
        return randint(0, 9), randint(0, 9)
