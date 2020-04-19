from Boat import *
from random import randint
import numpy as np


class Grid:
    def __init__(self, species, name):
        self.grid = np.zeros((10, 10))
        self.name = name
        self.floating_boat = []
        self.sunk_boat = []
        if species == "bot":  # initialisation grille du bot
            self.init_bot()
        else:  # initialisation grille joueur
            self.init_player()

    def init_bot(self):
        occupied_places = []
        for i in range(5, 1, -1):
            for j in range(list_boats[i - 2]):
                flag = True
                m = 0
                while flag and m < 10000:
                    x, y, alpha = randint(0, 9), randint(0, 9), randint(0, 1)
                    for k in range(4):
                        if (k + alpha) % 4 == 0:
                            if y + i < 10 and (self.grid[x, y:y + i] == np.zeros(i)).all():
                                flag2 = True
                                for n in range(i):
                                    if (x, y + n) in occupied_places:
                                        flag2 = False
                                if flag2:
                                    flag = False
                                    points_list = []
                                    for n in range(i):
                                        points_list.append((x, y + n))
                                        occupied_places.append((x, y + n))
                                    self.floating_boat.append(Boat(i, points_list))
                                    self.grid[x, y:y + i] = [i] * i
                                    break
                        if k + alpha == 1:
                            if x + i < 10 and (self.grid[x: x + i, y] == np.zeros(i)).all():
                                flag2 = True
                                for n in range(i):
                                    if (x + n, y) in occupied_places:
                                        flag2 = False
                                if flag2:
                                    flag = False
                                    points_list = []
                                    for n in range(i):
                                        points_list.append((x + n, y))
                                        occupied_places.append((x + n, y))
                                    self.floating_boat.append(Boat(i, points_list))
                                    self.grid[x:x + i, y] = [i] * i
                                    break
                        if k + alpha == 2:
                            if y - i >= 0 and (self.grid[x, y - i:y] == np.zeros(i)).all():
                                flag2 = True
                                for n in range(i):
                                    if (x, y - n) in occupied_places:
                                        flag2 = False
                                if flag2:
                                    flag = False
                                    points_list = []
                                    for n in range(i):
                                        points_list.append((x, y - n))  # coordonnées distribuées à l'envers
                                        occupied_places.append((x, y - n))
                                    self.floating_boat.append(Boat(i, points_list))
                                    self.grid[x, y - i:y] = [i] * i
                                    break
                        if (k + alpha) == 3:
                            if x - i >= 0 and (self.grid[x - i:x, y] == np.zeros(i)).all():
                                flag2 = True
                                for n in range(i):
                                    if (x - n, y) in occupied_places:
                                        flag2 = False
                                if flag2:
                                    flag = False
                                    points_list = []
                                    for n in range(i):
                                        points_list.append((x - n, y))
                                        occupied_places.append((x - n, y))
                                    self.floating_boat.append(Boat(i, points_list))
                                    self.grid[x - i:x, y] = [i] * i
                                    break
                    m += 1

    def init_player(self):
        pg.init()

        window = pg.display.set_mode((800, 800))  # initialisation de l'affichage
        pg.display.set_caption("Initialisation de la grille de " + self.name)
        window.fill(blue_color)
        for i in range(1, 10):
            pg.draw.line(window, black_color, (80 * i, 0), (80 * i, 800), 1)  # tracé de la grille
            pg.draw.line(window, black_color, (0, 80 * i), (800, 80 * i), 1)
        pg.display.flip()

        vertical = True
        occupied_spaces = []  # positionnement des bateaux
        for i in range(5, 1, -1):  # taille
            for j in range(list_boats[i - 2]):  # nombre
                launched = True
                x_grid0, y_grid0 = (0, 0)
                while launched:
                    for event in pg.event.get():
                        if event.type == pg.MOUSEMOTION:  # affichage bateau temporaire
                            x_grid0, y_grid0 = self.event_mousemotion(event, window, vertical, i, x_grid0, y_grid0)
                        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:  # affichage bateau définitif
                            launched = self.event_mousebuttondown(event, occupied_spaces, vertical, i)
                        if event.type == pg.KEYDOWN and event.key == pg.K_r:
                            vertical = self.event_keyboard(window, vertical)
                    pg.display.flip()

    def event_mousemotion(self, event, window, vertical, i, x_grid0, y_grid0):
        x_disp, y_disp = event.pos
        x_grid, y_grid = (x_disp // 80), (y_disp // 80)
        if vertical and y_grid <= 9 - i + 1:  # bateau vertical
            for boat in self.floating_boat:
                boat.full_display(window, black_color)
            for k in range(i):
                self.draw_cross(window, blue_color, (x_grid0, y_grid0 + k))
                self.draw_cross(window, grey_color, (x_grid, y_grid + k))
            return x_grid, y_grid
        if not vertical and x_grid <= 9 - i + 1:  # horizontal
            for boat in self.floating_boat:
                boat.full_display(window, black_color)
            for k in range(i):
                self.draw_cross(window, blue_color, (x_grid0 + k, y_grid0))
                self.draw_cross(window, grey_color, (x_grid + k, y_grid))
            return x_grid, y_grid
        return x_grid0, y_grid0

    def event_mousebuttondown(self, event, occupied_spaces, vertical, i):
        x_disp, y_disp = event.pos
        x_grid, y_grid = (x_disp // 80), (y_disp // 80)
        if vertical and y_grid <= 9 - i + 1:  # bateau vertical
            points_list = []
            flag = True
            for k in range(i):  # test de validité de l'emplacement
                if (x_grid, y_grid + k) in occupied_spaces:
                    flag = False
                    break
                points_list.append((x_grid, y_grid + k))
            if flag:
                self.floating_boat.append(Boat(i, points_list))  # creation du bateau
                self.grid[x_grid, y_grid:y_grid + i] = [i] * i
                for k in range(i):  # actualisation des emplacements occupés
                    occupied_spaces.append((x_grid, y_grid + k))
                return False
        if not vertical and x_grid <= 9 - i + 1:  # bateau horizontal
            points_list = []
            flag = True
            for k in range(i):  # test de validité de l'emplacement
                if (x_grid + k, y_grid) in occupied_spaces:
                    flag = False
                    break
                points_list.append((x_grid + k, y_grid))
            if flag:
                self.floating_boat.append(Boat(i, points_list))  # creation du bateau
                self.grid[x_grid:x_grid + i, y_grid] = [i] * i
                for k in range(i):  # actualisation des emplacements occupés
                    occupied_spaces.append((x_grid + k, y_grid))
                return False
        return True

    def event_keyboard(self, window, vertical):
        for x_grid in range(10):
            for y_grid in range(10):
                self.draw_cross(window, blue_color, (x_grid, y_grid))
        return not vertical

    def __str__(self):
        return str(self.grid)

    @staticmethod
    def draw_cross(window, color, coordinates_grid):
        x_grid, y_grid = coordinates_grid
        pg.draw.line(window, color, (
            x_grid * 80 + 10, y_grid * 80 + 10), (
                         (x_grid + 1) * 80 - 10, (y_grid + 1) * 80 - 10), 5)
        pg.draw.line(window, color, (
            (x_grid + 1) * 80 - 10, y_grid * 80 + 10), (
                         x_grid * 80 + 10, (y_grid + 1) * 80 - 10), 5)
