# from Client import Client
import socket
import select
from random import choice

global host
global port

host = "25.138.5.142"
port = 12800


# host "25.138.5.142"
# port =12800
class Server:
    def __init__(self, number_of_players):
        self.host = host
        self.port = port
        self.connexion_list = []
        self.main_connexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.main_connexion.bind((host, port))
        self.main_connexion.listen(5)
        for i in range(number_of_players - 1):
            self.connexion_list.append(self.main_connexion.accept()[0])
            print("connexion client {}".format(i + 1))

    def receive(self):
        try:
            to_read_clients, wlist, xlist = select.select(
                self.connexion_list,
                [], [], 0.05)
        except select.error:
            pass
        else:
            client = choice(to_read_clients)
            return client, client.recv(1024).decode()


"""
server = Server("25.138.5.142", 12800, 3)
for connexion in server.connexion_list:
    connexion.close()
    print("deconnexion client")
"""
