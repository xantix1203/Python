import socket


class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_connexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_connexion.connect((host, port))
        print("connexion client ok")

"""
client1 = Client("25.138.5.142", 12800)
client2 = Client("25.138.5.142", 12800)
client1.server_connexion.close()
client2.server_connexion.close()
"""
