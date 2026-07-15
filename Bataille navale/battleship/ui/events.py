"""Small shared helpers for pygame event loops."""

import pygame as pg

from . import board_view


def quit_if_closed(event):
    if event.type == pg.QUIT:
        pg.quit()
        raise SystemExit


def pump_and_wait(duration_ms):
    """Keep processing events (so closing the window still works) for a fixed pause."""
    deadline = pg.time.get_ticks() + duration_ms
    while pg.time.get_ticks() < deadline:
        for event in pg.event.get():
            quit_if_closed(event)
        pg.time.wait(16)


def play_impact_animation(window, redraw_fn, cells, duration_ms=900, present=pg.display.flip):
    """Calls `redraw_fn()` each frame with a hit/miss burst overlaid on every
    cell in `cells` (a list of (cell, hit) pairs, all sharing one synchronized
    progress -- a single shot is just a one-element list), presenting the
    result and pumping events (so closing the window still works) for
    `duration_ms`. `present` defaults to a plain flip; pass a different
    callable when `window` isn't the real display surface (e.g. MatchView
    draws to a fixed-size canvas and scale-blits it to the window).
    """
    clock = pg.time.Clock()
    elapsed = 0
    while elapsed < duration_ms:
        for event in pg.event.get():
            quit_if_closed(event)
        redraw_fn()
        progress = elapsed / duration_ms
        for cell, hit in cells:
            board_view.draw_impact_effect(window, cell, progress, hit)
        present()
        elapsed += clock.tick(60)


def play_flyover_animation(window, redraw_fn, cells, hit_cells, duration_ms=5000, fps=25, present=pg.display.flip):
    """The Pygame-native stand-in for Italy's special (the spec describes a
    CSS plane-flyover, which doesn't apply to this Pygame app): a plane sprite
    flies smoothly and continuously across `cells` (an ordered row or column)
    over `duration_ms` (~5s by default), updated at `fps` (25 by default,
    deliberately lower than the usual 60 for a more cinematic feel) rather
    than jumping cell to cell. Each cell's hit/miss burst is still revealed
    staggered as the plane's nose passes it. `hit_cells` is the subset of
    `cells` that are hits.
    """
    horizontal = cells[0][1] == cells[-1][1]  # same y across the run -> flying left-to-right
    n = len(cells)
    stagger_ms = duration_ms / n
    (x0, y0), (x1, y1) = cells[0], cells[-1]
    clock = pg.time.Clock()
    elapsed = 0
    while elapsed < duration_ms:
        for event in pg.event.get():
            quit_if_closed(event)
        redraw_fn()
        progress = elapsed / duration_ms
        position = (x0 + (x1 - x0) * progress, y0 + (y1 - y0) * progress)
        board_view.draw_plane(window, position, horizontal)
        nose_index = min(int(elapsed / stagger_ms), n - 1)
        for i, cell in enumerate(cells):
            if i > nose_index:
                continue
            local_progress = min((elapsed - i * stagger_ms) / 250, 1.0)
            board_view.draw_impact_effect(window, cell, local_progress, cell in hit_cells)
        present()
        elapsed += clock.tick(fps)
