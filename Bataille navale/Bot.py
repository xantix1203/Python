from Player import *


class Bot(Player):
    def __init__(self, score=0):
        Player.__init__(self, choice(["Ken", "Barbie", "Mickael", "Joe la classe", "Samsoum"]), "bot", score)

    def get_shot():
        return randint(0, 9), randint(0, 9)

    get_shot = staticmethod(get_shot)
