import numpy as np


def sigmoide(x):
    return 1.0 / (1.0 + np.exp(-x))
