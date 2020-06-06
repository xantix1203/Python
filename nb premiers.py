import math

nb = int(input("nombres premiers à trouver: "))
liste_des_nb_prems = [1, 2, 3, 5, 7]
nb_trouves = 5
i = 7
while nb_trouves < nb:
    i += 4
    j = 3
    e = 0
    while j <= math.sqrt(i):
        if (i % j) == 0:
            e = 1
        j += 2
    if e == 0:
        liste_des_nb_prems.append(i)
        nb_trouves += 1
    i += 2
    j = 3
    e = 0
    while j <= math.sqrt(i):
        if (i % j) == 0:
            e = 1
        j += 2
    if e == 0:
        liste_des_nb_prems.append(i)
        nb_trouves += 1

print(liste_des_nb_prems)
print(((len(liste_des_nb_prems)) / (liste_des_nb_prems[len(liste_des_nb_prems) - 1])) * 100)
