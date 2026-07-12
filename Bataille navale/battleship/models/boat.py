"""Boat state and hit resolution. No rendering here — see battleship.ui.board_view."""

from ..config import BOAT_TYPE_NAMES


class Boat:
    def __init__(self, size, cells, name=None):
        self.size = size
        self.type = BOAT_TYPE_NAMES[size]
        self.name = name if name else self.type
        self.cells = [[cell, False] for cell in cells]  # [(x, y), is_hit]
        self.hits_remaining = size

    @property
    def is_sunk(self):
        return self.hits_remaining == 0

    def register_hit(self, shot):
        """Apply a shot to this boat. Returns (hit, sunk)."""
        for cell in self.cells:
            if cell[0] == shot and not cell[1]:
                cell[1] = True
                self.hits_remaining -= 1
                return True, self.is_sunk
        return False, False
