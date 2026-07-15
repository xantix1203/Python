import random

from ..config import BOARD_SIZE
from .grid import Grid
from .player import Player

BOT_NAMES = ["Ken", "Barbie", "Carlsen", "Joe la classe", "Samsoldine"]

_NEIGHBOR_OFFSETS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


class Bot(Player):
    """A bot that hunts randomly until it lands a hit, then targets the
    neighboring cells of that hit until the boat is sunk (classic
    "hunt/target" Battleship AI) before going back to random hunting.
    """

    species = "bot"

    def __init__(self, score=0):
        super().__init__(random.choice(BOT_NAMES), score)
        self._remaining_shots = {}
        self._hunt_stacks = {}

    def register_opponent(self, opponent):
        super().register_opponent(opponent)
        self._remaining_shots[opponent] = [(x, y) for x in range(BOARD_SIZE) for y in range(BOARD_SIZE)]
        self._hunt_stacks[opponent] = []

    def record_shot_result(self, opponent, shot, hit, sunk_boat):
        if sunk_boat is not None:
            self._hunt_stacks[opponent].clear()
        elif hit:
            x, y = shot
            for dx, dy in _NEIGHBOR_OFFSETS:
                neighbor = (x + dx, y + dy)
                if Grid.in_bounds(*neighbor) and neighbor in self._remaining_shots[opponent]:
                    self._hunt_stacks[opponent].append(neighbor)

    def get_shot(self, opponent):
        remaining = self._remaining_shots[opponent]
        hunt_stack = self._hunt_stacks[opponent]
        while hunt_stack:
            candidate = hunt_stack.pop()
            if candidate in remaining:
                remaining.remove(candidate)
                return candidate
        shot = random.choice(remaining)
        remaining.remove(shot)
        return shot
