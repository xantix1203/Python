import numpy as np


class NeuralNetwork:
    def __init__(self,
                 input_size=3,
                 output_size=1,
                 hidden_size=3):
        self.inputSize = input_size
        self.outputSize = output_size
        self.hiddenSize = hidden_size
