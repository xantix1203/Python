"""Turn/round resolution for a local multiplayer match.

Deliberately has no knowledge of Pygame or the console: `play_round` takes a
`get_shot(player, opponent)` callback, so the same engine drives both bot
opponents and interactive (mouse-driven) human turns.
"""


class Game:
    def __init__(self, players):
        self.remaining_players = list(players)
        self.eliminated_players = []
        for player in self.remaining_players:
            for opponent in self.remaining_players:
                if opponent is not player:
                    player.register_opponent(opponent)

    @property
    def is_over(self):
        return len(self.remaining_players) <= 1

    @property
    def winner(self):
        return self.remaining_players[0] if len(self.remaining_players) == 1 else None

    def play_round(self, get_shot, on_result=None):
        players_snapshot = list(self.remaining_players)
        eliminated_this_round = []
        for player in players_snapshot:
            if player in eliminated_this_round:
                continue
            for opponent in players_snapshot:
                if opponent is player or opponent in eliminated_this_round:
                    continue
                shot = get_shot(player, opponent)
                hit, sunk_boat = player.fire(opponent, shot)
                player.record_shot_result(opponent, shot, hit, sunk_boat)
                if on_result is not None:
                    on_result(player, opponent, shot, hit, sunk_boat)
                if not opponent.grid.floating_boats:
                    eliminated_this_round.append(opponent)
        for opponent in eliminated_this_round:
            self.remaining_players.remove(opponent)
            self.eliminated_players.append(opponent)
