from Bot import *

"""
bot1 = Bot()
print(bot1.grille)
for boat in bot1.grille.floating_boat:
    print(boat.type, boat.list)
"""
player = Player("Arnaud")
for boat in player.grille.floating_boat:
    print(boat.type, boat.list)
