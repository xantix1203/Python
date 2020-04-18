from Boat import *
from random import *
import numpy as np


class Grid:
    def __init__(self, species):
        self.grid = np.zeros((10, 10))
        self.floating_boat = []
        self.sunk_boat = []
        if species == "bot":
            for i in range(5, 1, -1):
                for j in range(6 - i):
                    flag = True
                    m = 0
                    while flag and m < 1000:
                        x, y, alpha = randint(0, 9), randint(0, 9), randint(0, 1)
                        for k in range(4):
                            if (k + alpha) % 4 == 0:
                                if y + i < 10 and (self.grid[x, y:y + i] == np.zeros(i)).all():
                                    flag = False
                                    points_list = []
                                    for n in range(i):
                                        points_list.append((x, y + n))
                                    self.floating_boat.append(Boat(i, points_list))
                                    self.grid[x, y:y + i] = [i] * i
                                    break
                            if k + alpha == 1:
                                if x + i < 10 and (self.grid[x: x + i, y] == np.zeros(i)).all():
                                    flag = False
                                    points_list = []
                                    for n in range(i):
                                        points_list.append((x + n, y))
                                    self.floating_boat.append(Boat(i, points_list))
                                    self.grid[x:x + i, y] = [i] * i
                                    break
                            if k + alpha == 2:
                                if y - i >= 0 and (self.grid[x, y - i:y] == np.zeros(i)).all():
                                    flag = False
                                    points_list = []
                                    for n in range(i):
                                        points_list.append((x, y - n))  # coordonnées distribuées à l'envers
                                    self.floating_boat.append(Boat(i, points_list))
                                    self.grid[x, y - i:y] = [i] * i
                                    break
                            if (k + alpha) == 3:
                                if x - i >= 0 and (self.grid[x - i:x, y] == np.zeros(i)).all():
                                    flag = False
                                    points_list = []
                                    for n in range(i):
                                        points_list.append((x - n, y))
                                    self.floating_boat.append(Boat(i, points_list))
                                    self.grid[x - i:x, y] = [i] * i
                        m += 1
        else:
            pg.init()

            blue_color = (90, 150, 255)
            black_color = (0, 0, 0)

            window = pg.display.set_mode((1000, 1000), pg.RESIZABLE)
            window.fill(blue_color)
            for i in range(1, 10):
                pg.draw.line(window, black_color, (100 * i, 0), (100 * i, 1000))
                pg.draw.line(window, black_color, (0, 100 * i), (1000, 100 * i))

            pg.display.flip()
            launched = True
            while launched:
                for event in pg.event.get():
                    if event.type == pg.QUIT:
                        launched = False

    def __str__(self):
        return str(self.grid)
