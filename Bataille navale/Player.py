from Grid import *


class Player:
    def __init__(self, name, species="human", score=0):
        self.name = name
        self.score = score
        self.grid = Grid(species, self.name)
        self.eliminated = False
        self.occupied_spaces = {}

    def fire(self, opponent, shot):
        print(shot)
        for boat in opponent.grid.floating_boat:
            hit, sunk = boat.evaluate_shot(shot)
            if sunk:
                opponent.grid.floating_boat.remove(boat)
                opponent.grid.sunk_boat.append(boat)
                self.score += 1
            if hit:
                self.score += 1
        print(self.score)

    def __str__(self):
        return self.name

    def get_shot(self, opponent):
        pg.init()

        window = pg.display.set_mode((1000, 1000), pg.RESIZABLE)  # initialisation de l'affichage
        pg.display.set_caption("Aller " + self.name + " c'est le moment de demonter " + opponent.name + "!")
        window.fill(blue_color)
        for i in range(1, 10):
            pg.draw.line(window, black_color, (100 * i, 0), (100 * i, 1000), 1)  # tracé de la grille
            pg.draw.line(window, black_color, (0, 100 * i), (1000, 100 * i), 1)
        pg.display.flip()
        launched = True
        print(self.occupied_spaces)
        x_grid0, y_grid0 = (0, 0)  # affichage dynamique
        x_grid, y_grid = 0, 0
        while launched:
            for event in pg.event.get():
                if event.type == pg.MOUSEMOTION:  # affichage bateau temporaire
                    x_grid0, y_grid0 = self.event_mousemotion(event, window, opponent, x_grid0, y_grid0)
                if (event.type in [pg.MOUSEBUTTONDOWN, pg.MOUSEBUTTONUP]) and event.button == 1:  # affichage bateau
                    # définitif
                    launched, (x_grid, y_grid) = self.event_mousebuttondown(event, opponent)
            pg.display.flip()
        return x_grid, y_grid

    def event_mousemotion(self, event, window, opponent, x_grid0, y_grid0):
        x_disp, y_disp = event.pos
        x_grid, y_grid = (x_disp // 100), (y_disp // 100)
        self.grid.draw_cross(window, blue_color, (x_grid0, y_grid0))
        for (x_grid1, y_grid1) in self.occupied_spaces[opponent]:
            self.grid.draw_cross(window, black_color, (x_grid1, y_grid1))
        for boat in opponent.grid.floating_boat:
            boat.partial_display(window)
        for boat in opponent.grid.sunk_boat:
            boat.full_display(window, red_color)
        self.grid.draw_cross(window, grey_color, (x_grid, y_grid))
        return x_grid, y_grid

    def event_mousebuttondown(self, event, opponent):
        x_disp, y_disp = event.pos
        x_grid, y_grid = (x_disp // 100), (y_disp // 100)
        if not ((x_grid, y_grid) in self.occupied_spaces[opponent]):
            self.occupied_spaces[opponent].append((x_grid, y_grid))
            return False, (x_grid, y_grid)
        return True, (x_grid, y_grid)
