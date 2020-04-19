from Player import *
from random import choice


class Bot(Player):
    def __init__(self, score=0):
        Player.__init__(self, choice(["Ken", "Barbie", "Mickael", "Joe la classe", "Samsoldine"]), "bot", score)

    def get_shot(self, opponent):
        shot = choice(self.remaining_shots[opponent])
        self.remaining_shots[opponent].remove(shot)
        return shot
