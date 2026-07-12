"""Small reusable pygame UI widgets, shared between the menu (screens.py) and
in-board prompts (input_handler.py's boat naming).
"""

import pygame as pg

from ..config import COLOR_BLACK, COLOR_GREY, COLOR_WHITE

_MAX_TEXT_LENGTH = 16


class TextBox:
    def __init__(self, rect, initial_text):
        self.rect = pg.Rect(rect)
        self.text = initial_text
        self.active = False
        self.locked = False
        self._edited = False

    def handle_event(self, event):
        if self.locked:
            return
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pg.KEYDOWN and self.active:
            if not self._edited:
                # First keystroke clears placeholder/default text (e.g. "Joueur 1")
                # instead of appending to it.
                self.text = ""
                self._edited = True
            if event.key == pg.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.unicode.isprintable() and len(self.text) < _MAX_TEXT_LENGTH:
                self.text += event.unicode

    def draw(self, window, font):
        pg.draw.rect(window, COLOR_WHITE, self.rect)
        pg.draw.rect(window, COLOR_BLACK if self.active else COLOR_GREY, self.rect, 2)
        text_surface = font.render(self.text, True, COLOR_BLACK)
        y = self.rect.y + (self.rect.height - text_surface.get_height()) // 2
        window.blit(text_surface, (self.rect.x + 8, y))


class Button:
    def __init__(self, rect, label):
        self.rect = pg.Rect(rect)
        self.label = label

    def is_clicked(self, event):
        return event.type == pg.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

    def draw(self, window, font, selected=False):
        pg.draw.rect(window, COLOR_BLACK if selected else COLOR_GREY, self.rect)
        text_surface = font.render(self.label, True, COLOR_WHITE)
        window.blit(text_surface, text_surface.get_rect(center=self.rect.center))


class Dropdown:
    """Closed by default, showing options[selected_index]. A click on it
    toggles open/closed; while open, the option list is drawn directly below
    it and a click on one selects it and closes the dropdown.
    """

    def __init__(self, rect, options, selected_index=0):
        self.rect = pg.Rect(rect)
        self.options = options
        self.selected_index = selected_index
        self.open = False

    @property
    def selected(self):
        return self.options[self.selected_index]

    def _option_rects(self):
        return [
            pg.Rect(self.rect.x, self.rect.y + self.rect.height * (i + 1), self.rect.width, self.rect.height)
            for i in range(len(self.options))
        ]

    def handle_event(self, event):
        if event.type != pg.MOUSEBUTTONDOWN or event.button != 1:
            return
        if self.rect.collidepoint(event.pos):
            self.open = not self.open
            return
        if self.open:
            for i, option_rect in enumerate(self._option_rects()):
                if option_rect.collidepoint(event.pos):
                    self.selected_index = i
                    break
            self.open = False

    def draw(self, window, font):
        pg.draw.rect(window, COLOR_WHITE, self.rect)
        pg.draw.rect(window, COLOR_BLACK, self.rect, 2)
        text_surface = font.render(self.selected, True, COLOR_BLACK)
        y = self.rect.y + (self.rect.height - text_surface.get_height()) // 2
        window.blit(text_surface, (self.rect.x + 8, y))
        if self.open:
            for option, option_rect in zip(self.options, self._option_rects()):
                pg.draw.rect(window, COLOR_WHITE, option_rect)
                pg.draw.rect(window, COLOR_GREY, option_rect, 1)
                option_surface = font.render(option, True, COLOR_BLACK)
                oy = option_rect.y + (option_rect.height - option_surface.get_height()) // 2
                window.blit(option_surface, (option_rect.x + 8, oy))
