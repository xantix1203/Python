from random import *


class Grille:
    def __init__(self, species):
        self.grille = [[0] * 10 for i in range(10)]
        if species == "bot":
            for i in range(2, 6):
                for j in range(6 - i):
                    flag = True
                    while flag:
                        x, y, alpha = randint(0, 9), randint(0, 9), randint(0, 1)
                        for i in range()



