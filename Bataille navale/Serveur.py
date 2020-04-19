# from Client import Client
import socket


# host "25.138.5.142"
# port =12800
class Serveur:
    def __init__(self, host, port, number_of_players):
        self.host = host
        self.port = port
        self.connexion_list = []
        self.main_connexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.main_connexion.bind((host, port))
        self.main_connexion.listen(5)
        for i in range(number_of_players - 1):
            self.connexion_list.append(self.main_connexion.accept()[0])
            print("connexion client {} ok".format(i))


serveur = Serveur("25.138.5.142", 12800, 3)
for connexion in serveur.connexion_list:
    connexion.close()
