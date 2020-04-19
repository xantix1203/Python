import socket

host = "25.138.5.142"
port = 12800
main_connexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
main_connexion.bind((host, port))
main_connexion.listen(5)
client_connexion, connexion_info = main_connexion.accept()
print(connexion_info)
client_connexion.close()
main_connexion.close()
