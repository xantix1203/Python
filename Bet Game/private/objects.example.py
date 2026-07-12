"""Template for private/objects.py (git-ignored). Copy this file to
objects.py — without the .example — and edit freely; that copy will never
be committed. An object stacked on top of another (`requires`) can't be
removed until the one underneath already has been. `noun_gender` is the
French grammatical gender of the noun (drives "ton"/"ta" and "le"/"la" in
the generated dare text), independent of which player's pool it's in.
"""

from bet_game.engine.objects import NounGender, ObjectSpec, register
from bet_game.models.gender import Gender

register(ObjectSpec(key="verre", gender=Gender.MALE, noun_gender=NounGender.MASCULINE))
register(ObjectSpec(key="assiette", gender=Gender.MALE, noun_gender=NounGender.FEMININE, requires="verre"))
register(ObjectSpec(key="cuillere", gender=Gender.MALE, noun_gender=NounGender.FEMININE))
register(ObjectSpec(key="bol", gender=Gender.MALE, noun_gender=NounGender.MASCULINE))

register(ObjectSpec(key="Pierre", gender=Gender.FEMALE, noun_gender=NounGender.FEMININE))
register(ObjectSpec(key="Feuille", gender=Gender.FEMALE, noun_gender=NounGender.FEMININE, requires="Pierre"))
register(ObjectSpec(key="Collier", gender=Gender.FEMALE, noun_gender=NounGender.MASCULINE))
register(ObjectSpec(key="Plateau", gender=Gender.FEMALE, noun_gender=NounGender.MASCULINE, requires="Collier"))
