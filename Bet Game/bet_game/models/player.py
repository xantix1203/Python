class Player:
    def __init__(self, name, gender):
        self.name = name
        self.gender = gender
        self.starting_objects = set()  # object keys chosen at setup
        self.removed_objects = []  # (object_key, level) in removal order

    def __str__(self):
        return self.name
