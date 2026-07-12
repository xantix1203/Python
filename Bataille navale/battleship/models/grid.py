"""Board state and boat-placement rules. No rendering here — see battleship.ui.board_view."""

import random

import numpy as np

from ..config import BOARD_SIZE, FLEET
from .boat import Boat

# (dx, dy) for right, down, left, up.
DIRECTIONS = [(1, 0), (0, 1), (-1, 0), (0, -1)]


class Grid:
    def __init__(self):
        self.cells = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=int)
        self.floating_boats = []
        self.sunk_boats = []
        self._occupied = set()

    @staticmethod
    def in_bounds(x, y):
        return 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE

    def can_place(self, x, y, size, direction):
        dx, dy = direction
        cells = [(x + dx * i, y + dy * i) for i in range(size)]
        return all(self.in_bounds(cx, cy) and (cx, cy) not in self._occupied for cx, cy in cells)

    def place(self, x, y, size, direction):
        dx, dy = direction
        cells = [(x + dx * i, y + dy * i) for i in range(size)]
        boat = Boat(size, cells)
        for cx, cy in cells:
            self.cells[cx, cy] = size
            self._occupied.add((cx, cy))
        self.floating_boats.append(boat)
        return boat

    def place_fleet_randomly(self, max_attempts_per_boat=10000):
        for size in sorted(FLEET, reverse=True):
            for _ in range(FLEET[size]):
                for _ in range(max_attempts_per_boat):
                    x, y = random.randint(0, BOARD_SIZE - 1), random.randint(0, BOARD_SIZE - 1)
                    direction = random.choice(DIRECTIONS)
                    if self.can_place(x, y, size, direction):
                        self.place(x, y, size, direction)
                        break
                else:
                    raise RuntimeError(
                        f"Could not place a boat of size {size} after {max_attempts_per_boat} attempts"
                    )

    def register_shot(self, shot):
        """Apply a shot to this grid's fleet. Returns (hit, sunk_boat_or_None)."""
        for boat in self.floating_boats:
            hit, sunk = boat.register_hit(shot)
            if hit:
                if sunk:
                    self.floating_boats.remove(boat)
                    self.sunk_boats.append(boat)
                    return True, boat
                return True, None
        return False, None

    def __str__(self):
        return str(self.cells)
