class Boat:
    def __init__(self, size, points):
        # self.sunk = False
        self.type = ["torpilleur", "sous-marin", "croiseur", "porte-avion"][size - 2]
        self.state = size
        self.size = size
        self.list = [[points[i], 0] for i in range(size)]

    def evaluate_shot(self, shot):
        for i in range(self.size):
            if self.list[i] == shot:
                self.state -= 1
                self.list[i][1] = -1
                return True, self.state == 0  # hit, sunk
        return False, False
