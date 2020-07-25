import numpy as np


def sigmoid(x):
    """the sigmoid function"""
    return 1.0 / (1.0 + np.exp(-x))


def sigmoid_prime(z):
    """Derivative of the sigmoid function."""
    return sigmoid(z) * (1 - sigmoid(z))
