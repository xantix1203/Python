"""Round-to-round state for a local two-player match. No Pygame knowledge
here — see bet_game.ui for the screens that drive this.
"""

import random

from ..config import MAX_DARE_LEVEL, ROUNDS_PER_LEVEL
from . import objects
from .dare import eligible_dares, render_dare
from .round import draw_round

_OBJECT_REMOVAL = object()  # sentinel: "remove an object" competing against text dares


def level_for_round(round_number):
    """Difficulty level (1-4) for a given round number: climbs by one every
    ROUNDS_PER_LEVEL rounds, capped at MAX_DARE_LEVEL. Shared by minigame
    selection (which minigame can be drawn) and dare selection (which dare
    can be drawn) so both escalate together.
    """
    return min(MAX_DARE_LEVEL, (round_number - 1) // ROUNDS_PER_LEVEL + 1)


class Game:
    def __init__(self, player1, player2):
        self.players = (player1, player2)
        self.rounds = []
        self._level_reached = 0
        # Object-removal dares forced by a level change rather than a lost
        # duel (see next_round) — the caller (bet_game.ui) is responsible
        # for showing these before the round's own card.
        self.pending_object_removals = []

    @property
    def current_round(self):
        return self.rounds[-1] if self.rounds else None

    @property
    def level(self):
        round_number = self.current_round.number if self.current_round else 1
        return level_for_round(round_number)

    def next_round(self):
        round_number = len(self.rounds) + 1
        level = level_for_round(round_number)
        self.pending_object_removals = []
        if level > self._level_reached:
            self._catch_up_object_removals(self._level_reached)
            self._level_reached = level
        round_ = draw_round(round_number, level)
        self.rounds.append(round_)
        return round_

    def _catch_up_object_removals(self, ended_level):
        """Guarantees each player was asked to remove an object at least
        once during the level that just ended, for whoever wasn't already
        asked (via a lost duel) during that level.
        """
        if ended_level < 1:
            return
        for player in self.players:
            if objects.has_removed_this_level(player, ended_level):
                continue
            dare_text = objects.trigger_object_removal(player, ended_level)
            if dare_text is not None:
                self.pending_object_removals.append((player, dare_text))

    def resolve_duel(self, loser):
        partner = self.players[1] if loser is self.players[0] else self.players[0]
        level = self.level
        dare_text = self._draw_dare_or_object_removal(loser, partner, level)
        self.current_round.resolve_duel(loser, dare_text)

    def _draw_dare_or_object_removal(self, loser, partner, level):
        candidates = list(eligible_dares(level, loser.gender))
        object_removal_eligible = not objects.has_removed_this_level(loser, level) and objects.removable_objects(loser)
        if object_removal_eligible:
            candidates.append(_OBJECT_REMOVAL)
        if not candidates:
            return "Improvise un gage !"
        choice = random.choice(candidates)
        if choice is _OBJECT_REMOVAL:
            return objects.trigger_object_removal(loser, level)
        return render_dare(choice, level, loser, partner)
