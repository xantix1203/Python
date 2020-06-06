import os

solde = 1000
print("Vous commencer avec: ", solde, "€")
continuer = True
while continuer:
    condition = False
    while not condition:
        condition = True
        numero = input("Entrez le numéro sur lequel vous misez: ")
        mise = input("Entrez la somme misée: ")
        try:
            numero = int(numero)
            mise = int(mise)
        except ValueError:
            condition = False
            print("Entrez juste des nombres")
            continue
        if numero > 49 or numero < 0:
            condition = False
            print("la roulette ne contient que les nombres de 0 à 49")
            continue
        elif mise > solde:
            condition = False
            print("bien essayé mais ta mise est superieure a ton solde (=", solde, "€)")
            continue
        elif mise < 1:
            condition = False
            print("on doit miser une valeur superieure à 0")
            continue
    solde = solde - mise
    import math
    import random

    tirage = random.randrange(50)
    if numero % 2 == 0:
        couleure = 0
    else:
        couleure = 1
    if tirage % 2 == 0:
        couleur = 0
        print("Le numéro tiré est le: ", tirage, " noir")
    else:
        couleur = 1
        print("Le numero tiré est le: ", tirage, " rouge")
    if tirage == numero:
        solde = solde + mise * 3
        print("Vous gagnez !!! votre solde est: ", solde, "€")
    elif couleur == couleure:
        solde = solde + mise + math.ceil(mise / 2)
        print("La couleur est bonne, bien joué! Votre solde est: ", solde, "€")
    else:
        print("on ne gagne pas à tous les coups... votre solde est maintenant: ", solde, "€")
    if solde <= 0:
        print("Vous avez tout perdu")
        continuer = False
        continue
    quitter = input("voulez vous quitter (o/n)")
    if quitter == 'o':
        continuer = False
print("A bientôt...")

os.system("pause")
