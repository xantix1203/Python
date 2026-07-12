"""Player state and firing rules. No rendering/input here — see battleship.ui."""

from .grid import Grid


class Player:
    species = "human"

    def __init__(self, name, score=0, country=None):
        self.name = name
        self.score = score
        self.country = country
        self.grid = Grid()
        self.shots_fired = {}  # opponent -> list of (x, y) already fired at

    def register_opponent(self, opponent):
        self.shots_fired[opponent] = []

    def has_fired_at(self, opponent, shot):
        return shot in self.shots_fired[opponent]

    def record_shot_result(self, opponent, shot, hit, sunk_boat):
        """Hook for subclasses (e.g. Bot) to react to their own shot's outcome."""

    def receive_shot(self, shot):
        return self.grid.register_shot(shot)

    def fire(self, opponent, shot):
        self.shots_fired[opponent].append(shot)
        hit, sunk_boat = opponent.receive_shot(shot)
        if hit:
            self.score += 1
            if sunk_boat is not None:
                self.score += 1
        return hit, sunk_boat

    def __str__(self):
        return self.name
