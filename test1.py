import pygame as pg


pg.init()
blue_color = (90, 150, 255)
black_color = (0, 0, 0)
window = pg.display.set_mode((800, 800), pg.RESIZABLE)
window.fill(blue_color)
for i in range(1, 10):
    pg.draw.line(window, black_color, (80 * i, 0), (80 * i, 800))
    pg.draw.line(window, black_color, (0, 80 * i), (800, 80 * i))

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
            x_grid, y_grid = x // 80, y // 80
            for i in range(5):
                pg.draw.line(window, color, (
                    x_grid * 80 + 10, y_grid * 80 + 10), (
                                 (x_grid + 1) * 80 - 10, (y_grid + 1) * 80 - 10), 5)
                pg.draw.line(window, color, (
                    (x_grid + 1) * 80 - 10, y_grid * 80 + 10), (
                                 x_grid * 80 + 10, (y_grid + 1) * 80 - 10), 5)
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            launched = False
    pg.display.flip()

rect = pg.Rect(0, 0, 1, 1)
print(rect)
