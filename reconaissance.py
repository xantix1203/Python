import os

nom = input("quel est ton nom: ")
if nom == ("cotten"):
    age = input("quel est ton age: ")
    age = int(age)
    if age == 13:
        print("Tu es céline ou son double, ou le double de son double, ou le double du double de son double...")
    elif age == 46:
        print("Tu es mamouna")
    elif age == 47:
        print("Bonjour sylvain")
    elif age == 9:
        print("Coucou audrey, arnaud m'a beaucoup parlé de toi")
    elif age == 8:
        print("Tu dois etre charlotte")

else:
    print("Sors tout de suite de cette ordi tu n'a pas le doit d'y toucher")

os.system("pause")
