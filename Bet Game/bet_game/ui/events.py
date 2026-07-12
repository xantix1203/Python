"""Small shared helper for pygame event loops."""

import pygame as pg


def quit_if_closed(event):
    """Ends the process on a window-close click or Escape, uninitializing
    pygame first so the window and its SDL resources are released cleanly.

    Escape rather than a letter key (e.g. Q) so it can't misfire while a
    player is typing their name on the setup screen (a name containing "q"
    would otherwise quit the game on every keystroke).
    """
    is_close_click = event.type == pg.QUIT
    is_quit_key = event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE
    if is_close_click or is_quit_key:
        pg.quit()
        raise SystemExit
