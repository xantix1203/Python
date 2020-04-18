from Boat import *
from random import randint
import numpy as np


class Grid:
    def __init__(self, species):
        self.grid = np.zeros((10, 10))
        self.floating_boat = []
        self.sunk_boat = []
        if species == "bot":  # initialisation grille du bot
            self.init_bot()
        else:  # initialisation grille joueur
            self.init_player()

    def init_bot(self):
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

    def init_player(self):
        pg.init()

        blue_color = (90, 150, 255)
        black_color = (0, 0, 0)
        grey_color = (100, 100, 100)

        window = pg.display.set_mode((1000, 1000), pg.RESIZABLE)  # initialisation de l'affichage
        window.fill(blue_color)
        for i in range(1, 10):
            pg.draw.line(window, black_color, (100 * i, 0), (100 * i, 1000), 1)
            pg.draw.line(window, black_color, (0, 100 * i), (1000, 100 * i), 1)
        pg.display.flip()
        for i in range(5, 1, -1):  # positionnement des bateaux (taille)
            for j in range(6 - i):  # (nombre)
                launched = True
                vertical = False
                x_grid0, y_grid0 = (0, 0)
                while launched:
                    for event in pg.event.get():
                        if event.type == pg.MOUSEMOTION:  # affichage bateau temporaire
                            x_disp, y_disp = event.pos
                            x_grid, y_grid = (x_disp // 100), (y_disp // 100)
                            if vertical and y_grid <= 9 - i:  # bateau vertical
                                for k in range(i):
                                    self.draw_cross(window, blue_color, (x_grid0, y_grid0 + k))
                                    self.draw_cross(window, grey_color, (x_grid, y_grid + k))
                                x_grid0, y_grid0 = x_grid, y_grid
                            if not vertical and x_grid <= 9 - i:  # horizontal
                                for k in range(i):
                                    self.draw_cross(window, blue_color, (x_grid0 + k, y_grid0))
                                    self.draw_cross(window, grey_color, (x_grid + k, y_grid))
                                x_grid0, y_grid0 = x_grid, y_grid
                        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:  # affichage bateau définitif
                            x_disp, y_disp = event.pos
                            x_grid, y_grid = (x_disp // 100), (y_disp // 100)
                            if vertical and y_grid <= 9 - i:  # bateau vertical
                                points_list = []
                                for k in range(i):
                                    points_list.append((x_grid, y_grid + k))
                                self.floating_boat.append(Boat(i, points_list))
                            launched = False
                    pg.display.flip()

    def __str__(self):
        return str(self.grid)

    @staticmethod
    def draw_cross(window, color, coordinates_grid):
        x_grid, y_grid = coordinates_grid
        pg.draw.line(window, color, (
            x_grid * 100 + 10, y_grid * 100 + 10), (
                         (x_grid + 1) * 100 - 10, (y_grid + 1) * 100 - 10), 5)
        pg.draw.line(window, color, (
            (x_grid + 1) * 100 - 10, y_grid * 100 + 10), (
                         x_grid * 100 + 10, (y_grid + 1) * 100 - 10), 5)
