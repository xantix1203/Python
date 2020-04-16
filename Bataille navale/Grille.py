from random import *


class Grille:
    def __init__(self, species):
        self.grille = [[0] * 10 for i in range(10)]
        if species == "bot":
            for i in range(5, 1, -1):
                for j in range(6 - i):
                    flag = True
                    while flag:
                        x, y, alpha = randint(0, 9), randint(0, 9), randint(0, 1)
                        for k in range(4):
                            if k == 0:
                                if y + i < 10 and self.grille[x][y:y + i] == [0] * i:
                                    flag = False
                                    self.grille[x][y:y + i] = [1] * i
                                    break
                            if k == 1:
                                if x + i < 10 and self.grille[x: x + i][y] == [0] * i:  # TODO tableau numpy ?
                                    flag = False
                                    self.grille[x + i][y] = [1] * i
                                    break
                            if k == 2:
                                if y - i >= 0 and self.grille[x][y - i:y] == [0] * i:
                                    flag = False
                                    self.grille[x][y - i:y] = [1] * i
                                    break
                            if k == 3:
                                if x - i >= 0 and self.grille[x - i:x][y] == [0] * i:
                                    flag = False
                                    self.grille[x - i:x][y] = [1] * i

    def __str__(self):
        return str(self.grille)
