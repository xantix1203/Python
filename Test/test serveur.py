import socket
import time
import select
from random import choice

host = "25.138.5.142"
port = 12800
main_connexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
main_connexion.bind((host, port))
main_connexion.listen(5)
client_connexion, connexion_info = main_connexion.accept()
print(connexion_info)
time.sleep(1)
client_a_lire, wlist, xlist = select.select([client_connexion], [], [], 0.05)
message_recu = (choice(client_a_lire)).recv(1024)
client_connexion.close()
main_connexion.close()
