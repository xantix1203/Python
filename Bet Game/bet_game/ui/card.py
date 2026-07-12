"""A card that pops into view (scales up with a slight overshoot) to reveal
round content — a scenario, duel instructions, or a gage.
"""

import pygame as pg

from ..config import COLOR_BLACK, COLOR_WHITE

_POP_DURATION = 0.35


class Card:
    def __init__(self, rect, color, title, body):
        self.rect = pg.Rect(rect)
        self.color = color
        self.title = title
        self.body = body
        self._elapsed = 0.0

    @property
    def done_popping(self):
        return self._elapsed >= _POP_DURATION

    def update(self, dt):
        self._elapsed = min(_POP_DURATION, self._elapsed + dt)

    def draw(self, window, title_font, body_font):
        progress = self._elapsed / _POP_DURATION
        scale = max(0.0, _ease_out_back(progress))
        width = max(1, int(self.rect.width * scale))
        height = max(1, int(self.rect.height * scale))
        card_rect = pg.Rect(0, 0, width, height)
        card_rect.center = self.rect.center

        pg.draw.rect(window, self.color, card_rect, border_radius=18)
        pg.draw.rect(window, COLOR_WHITE, card_rect, width=2, border_radius=18)

        if scale < 0.7:
            return
        _draw_wrapped_text(window, self.title, title_font, card_rect, top_offset=28)
        _draw_wrapped_text(window, self.body, body_font, card_rect, top_offset=80)


def _ease_out_back(t, overshoot=1.7):
    t -= 1
    return 1 + (overshoot + 1) * t**3 + overshoot * t**2


def _draw_wrapped_text(window, text, font, card_rect, top_offset):
    max_width = card_rect.width - 40
    y = card_rect.top + top_offset
    for paragraph in text.split("\n"):
        if not paragraph:
            y += font.get_height() // 2
            continue
        line = ""
        for word in paragraph.split(" "):
            candidate = f"{line} {word}".strip()
            if font.size(candidate)[0] > max_width and line:
                y = _blit_line(window, line, font, card_rect, y)
                line = word
            else:
                line = candidate
        if line:
            y = _blit_line(window, line, font, card_rect, y)


def _blit_line(window, line, font, card_rect, y):
    surface = font.render(line, True, COLOR_BLACK)
    window.blit(surface, surface.get_rect(centerx=card_rect.centerx, top=y))
    return y + surface.get_height() + 4
