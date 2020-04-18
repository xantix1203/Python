import pygame as pg

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
        print(event)
        if event.type == pg.QUIT:
            launched = False
        if event.type == pg.MOUSEMOTION:
            color = black_color
            x, y = event.pos
            x_grid, y_grid = x // 100, y // 100
            for i in range(5):
                pg.draw.line(window, color, (
                    x_grid * 100 + 10, y_grid * 100 + 10), (
                                 (x_grid + 1) * 100 - 10, (y_grid + 1) * 100 - 10), 5)
                pg.draw.line(window, color, (
                    (x_grid + 1) * 100 - 10, y_grid * 100 + 10), (
                                 x_grid * 100 + 10, (y_grid + 1) * 100 - 10), 5)
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            launched = False
    pg.display.flip()
