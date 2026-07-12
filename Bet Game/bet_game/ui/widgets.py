"""Small reusable pygame UI widgets, shared between screens."""

import pygame as pg

from ..config import COLOR_BLACK, COLOR_GREY, COLOR_WHITE
from ..models.gender import Gender

_MAX_TEXT_LENGTH = 20


class TextBox:
    def __init__(self, rect, initial_text):
        self.rect = pg.Rect(rect)
        self.text = initial_text
        self.active = False
        self._edited = False

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pg.KEYDOWN and self.active:
            if not self._edited:
                # First keystroke clears the placeholder ("Joueur 1") instead
                # of appending to it.
                self.text = ""
                self._edited = True
            if event.key == pg.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.unicode.isprintable() and len(self.text) < _MAX_TEXT_LENGTH:
                self.text += event.unicode

    def draw(self, window, font):
        pg.draw.rect(window, COLOR_WHITE, self.rect, border_radius=6)
        pg.draw.rect(window, COLOR_BLACK if self.active else COLOR_GREY, self.rect, 2, border_radius=6)
        text_surface = font.render(self.text, True, COLOR_BLACK)
        y = self.rect.y + (self.rect.height - text_surface.get_height()) // 2
        window.blit(text_surface, (self.rect.x + 10, y))


class Button:
    def __init__(self, rect, label):
        self.rect = pg.Rect(rect)
        self.label = label

    def is_clicked(self, event):
        return event.type == pg.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

    def draw(self, window, font):
        pg.draw.rect(window, COLOR_GREY, self.rect, border_radius=8)
        text_surface = font.render(self.label, True, COLOR_WHITE)
        window.blit(text_surface, text_surface.get_rect(center=self.rect.center))


class Checkbox:
    def __init__(self, rect, label, checked=False):
        self.rect = pg.Rect(rect)
        self.label = label
        self.checked = checked

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.checked = not self.checked

    def draw(self, window, font):
        pg.draw.rect(window, COLOR_WHITE, self.rect, 2, border_radius=4)
        if self.checked:
            pg.draw.rect(window, COLOR_WHITE, self.rect.inflate(-10, -10), border_radius=2)
        text_surface = font.render(self.label, True, COLOR_WHITE)
        y = self.rect.y + (self.rect.height - text_surface.get_height()) // 2
        window.blit(text_surface, (self.rect.right + 12, y))


class GenderToggle:
    """A click-to-flip button, since a match only ever has one male and one
    female player — dares are drawn from the m-1..4 / f-1..4 pool matching
    whichever gender is showing.
    """

    _LABELS = {Gender.MALE: "Homme", Gender.FEMALE: "Femme"}

    def __init__(self, rect, gender):
        self.rect = pg.Rect(rect)
        self.gender = gender

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.gender = Gender.FEMALE if self.gender == Gender.MALE else Gender.MALE

    def draw(self, window, font):
        pg.draw.rect(window, COLOR_GREY, self.rect, border_radius=8)
        text_surface = font.render(self._LABELS[self.gender], True, COLOR_WHITE)
        window.blit(text_surface, text_surface.get_rect(center=self.rect.center))
