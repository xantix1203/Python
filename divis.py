import os
import math

liste_diviseurs = []
nb = int(input("nombre ?"))
diviseur = 1
v = 1
while nb % 2 == 0:
    liste_diviseurs.append(2)
    nb /= 2

while diviseur <= math.sqrt(nb):
    diviseur += 2
    if nb % diviseur == 0:
        j = 3
        e = 0
        while j <= math.sqrt(diviseur):
            if diviseur % j == 0:
                e = 1
            j += 2
        if e == 0:
            liste_diviseurs.append(diviseur)
            nb = int(nb / diviseur)
            while nb % diviseur == 0:
                liste_diviseurs.append(diviseur)
                nb = int(nb / diviseur)
if nb != 1:
    liste_diviseurs.append(nb)
print(liste_diviseurs)
os.system("pause")
