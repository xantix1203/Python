from Game import *
from Server import *
from Client import *


class GameServerManager:
    def __init__(self):
        self.server = None
        self.client = None

        if self.init_get_is_server():
            self.init_server()
        else:
            self.init_client()

    def init_server(self):
        self.server = Server(self.get_number_of_player())
        self.game =

    def init_client(self):
        self.client = Client()

    @staticmethod
    def init_get_is_server():
        return True

    @staticmethod
    def get_number_of_player():
        return 2
