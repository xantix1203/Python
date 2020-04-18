from Grid import *


class Player:
    def __init__(self, name, species="human", score=0):
        self.name = name
        self.score = score
        self.grid = Grid(species, self.name)
        self.eliminated = False

    def fire(self, player, shot):
        for boat in player.grid.floating_boat:
            hit, sunk = boat.evaluate_shot(shot)
            if sunk:
                player.grid.floating_boat.remove(boat)
                player.grid.sunk_boat.append(boat)
                self.score += 1
            if hit:
                self.score += 1

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
        occupied_spaces = []
        all_boats = opponent.grid.floating_boat + opponent.grid.sunk_boat
        for boat in all_boats:
            boat.partial_display(window)
            for coordinates_grid in boat.list:
                if coordinates_grid[1] == -1:
                    occupied_spaces.append(coordinates_grid[0])

        x_grid0, y_grid0 = (0, 0)  # affichage dynamique
        x_grid, y_grid = 0, 0
        while launched:
            for event in pg.event.get():
                if event.type == pg.MOUSEMOTION:  # affichage bateau temporaire
                    x_grid0, y_grid0 = self.event_mousemotion(event, window, all_boats, x_grid0, y_grid0)
                if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:  # affichage bateau définitif
                    launched, (x_grid, y_grid) = self.event_mousebuttondown(event, occupied_spaces)
            pg.display.flip()
        print("ok")
        return x_grid, y_grid

    def event_mousemotion(self, event, window, all_boats, x_grid0, y_grid0):
        x_disp, y_disp = event.pos
        x_grid, y_grid = (x_disp // 100), (y_disp // 100)
        for boat in all_boats:
            boat.partial_display(window)
        self.grid.draw_cross(window, blue_color, (x_grid0, y_grid0))
        self.grid.draw_cross(window, grey_color, (x_grid, y_grid))
        return x_grid, y_grid

    @staticmethod
    def event_mousebuttondown(event, occupied_spaces):
        x_disp, y_disp = event.pos
        x_grid, y_grid = (x_disp // 100), (y_disp // 100)
        if not ((x_grid, y_grid) in occupied_spaces):
            return False, (x_grid, y_grid)
        return True, (x_grid, y_grid)
