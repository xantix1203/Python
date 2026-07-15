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
        return self.add_boat(cells, name=None)

    def add_boat(self, cells, name=None):
        """Register a boat occupying explicit `cells` (any orientation). Used to
        rebuild an authoritative grid on the host from a client's placement,
        where we get concrete cells rather than an anchor+direction.
        """
        boat = Boat(len(cells), cells, name=name)
        for cx, cy in cells:
            self.cells[cx, cy] = boat.size
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

    def remove_boat(self, boat):
        """Detach `boat` from this grid entirely (floating_boats/cells/
        _occupied) -- e.g. when a special (Brésil) steals it onto another
        player's board.
        """
        self.floating_boats.remove(boat)
        for cell, _ in boat.cells:
            self.cells[cell] = 0
            self._occupied.discard(cell)

    def add_boat_at_random_position(self, boat, max_attempts=10000):
        """Place `boat` (already constructed elsewhere -- e.g. one just
        detached from another player's grid via remove_boat) at a random
        valid position on this grid, reusing its size/name/hit-state as-is,
        just at a fresh set of cells. Returns True if placed, False if no
        valid position was found within `max_attempts` (an essentially-full
        board).
        """
        for _ in range(max_attempts):
            x, y = random.randint(0, BOARD_SIZE - 1), random.randint(0, BOARD_SIZE - 1)
            direction = random.choice(DIRECTIONS)
            if self.can_place(x, y, boat.size, direction):
                dx, dy = direction
                cells = [(x + dx * i, y + dy * i) for i in range(boat.size)]
                for cell_entry, cell in zip(boat.cells, cells):
                    cell_entry[0] = cell
                for cx, cy in cells:
                    self.cells[cx, cy] = boat.size
                    self._occupied.add((cx, cy))
                self.floating_boats.append(boat)
                return True
        return False

    def revive_boat_with_cells(self, cells):
        """Move the sunk boat occupying exactly `cells` back to
        floating_boats, fully restored (unhit, hits_remaining reset to its
        true size). Used by specials that undo a sinking (e.g. URSS) -- both
        on the authoritative server grid and, via the same cell identity, on
        a client's local mirror of its own board. Returns the revived Boat,
        or None if no currently-sunk boat matches (e.g. a client that hasn't
        caught up to this event yet).
        """
        cells = set(cells)
        for boat in self.sunk_boats:
            if {cell for cell, _ in boat.cells} == cells:
                self.sunk_boats.remove(boat)
                for cell_entry in boat.cells:
                    cell_entry[1] = False
                boat.hits_remaining = boat.size
                self.floating_boats.append(boat)
                return boat
        return None

    def __str__(self):
        return str(self.cells)
