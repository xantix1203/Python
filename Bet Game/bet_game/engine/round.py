"""A single round: which minigame was drawn, and (for DUEL minigames) how it
was resolved. Dare selection itself lives in engine.game.Game.resolve_duel,
since it needs the game's current difficulty level.
"""

import random

from .minigame import MinigameCategory, all_minigames


class Round:
    def __init__(self, number, minigame, text=""):
        self.number = number
        self.minigame = minigame
        self.text = text  # the layout drawn for this round (scenario or instructions)
        self.loser = None
        self.gage = None

    @property
    def is_resolved(self):
        return self.minigame.category == MinigameCategory.IMPRO or self.gage is not None

    def resolve_duel(self, loser, dare_text):
        self.loser = loser
        self.gage = dare_text


def draw_round(number, level):
    games = [minigame for minigame in all_minigames() if level in minigame.levels]
    if not games:
        raise RuntimeError(f"Aucun minijeu enregistré pour le niveau {level}.")
    minigame = random.choice(games)
    text = random.choice(minigame.layouts) if minigame.layouts else ""
    return Round(number, minigame, text)
