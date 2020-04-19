import pygame as pg

global blue_color
global black_color
global grey_color
global red_color
global list_boats

blue_color = (90, 150, 255)
black_color = (0, 0, 0)
grey_color = (80, 80, 80)
red_color = (178, 34, 34)
list_boats = [1, 2, 1, 1]


class Boat:
    def __init__(self, size, points):
        # self.sunk = False
        self.type = ["torpilleur", "sous-marin", "croiseur", "porte-avion"][size - 2]
        self.state = size
        self.size = size
        self.list = [[points[i], 0] for i in range(size)]

    def evaluate_shot(self, shot):
        for i in range(self.size):
            if self.list[i][0] == shot:
                self.state -= 1
                self.list[i][1] = -1
                print("touché")
                return True, self.state == 0  # hit, sunk
            print("1 coup dans l'eau")
        return False, False

    def full_display(self, window, color):
        for coordinates_grid in self.list:
            self.draw_square(window, color, coordinates_grid[0])
            self.draw_cross(window, color, coordinates_grid[0])

    def partial_display(self, window):
        for coordinates_grid in self.list:
            if coordinates_grid[1] == -1:
                self.draw_cross(window, red_color, coordinates_grid[0])

    @staticmethod
    def draw_cross(window, color, coordinates_grid):
        x_grid, y_grid = coordinates_grid
        pg.draw.line(window, color, (
            x_grid * 80 + 10, y_grid * 80 + 10), (
                         (x_grid + 1) * 80 - 10, (y_grid + 1) * 80 - 10), 5)
        pg.draw.line(window, color, (
            (x_grid + 1) * 80 - 10, y_grid * 80 + 10), (
                         x_grid * 80 + 10, (y_grid + 1) * 80 - 10), 5)

    @staticmethod
    def draw_square(window, color, coordinates_grid):
        x_grid, y_grid = coordinates_grid
        pg.draw.line(window, color, (
            x_grid * 80, y_grid * 80), (
                         (x_grid + 1) * 80, y_grid * 80), 5)
        pg.draw.line(window, color, (
            (x_grid + 1) * 80, y_grid * 80), (
                         (x_grid + 1) * 80, (y_grid + 1) * 80), 5)
        pg.draw.line(window, color, (
            (x_grid + 1) * 80, (y_grid + 1) * 80), (
                         x_grid * 80, (y_grid + 1) * 80), 5)
        pg.draw.line(window, color, (
            x_grid * 80, (y_grid + 1) * 80), (
                         x_grid * 80, y_grid * 80), 5)
