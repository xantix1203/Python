import socket

host = ''
port = 12800
server_connexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_connexion.connect((host, port))
print("connexion établie")

server_connexion.close()
