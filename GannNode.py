

# HAS WEIGHTS AND BIASES, CROSSOVER, MUTATE, FITNESS

class GannNode(object):

	__slots__ = (
		'weights', 'biases', 'fitness', 'module'
	)
 	def __init__(self, layers, weights, biases, fitness, module):
 		self.layers = layers
 		self.weights = weights
 		self.biases = biases
 		self.fitness = fitness
 		self.module = module

 	def evaluate(self, inpt):
		out = inpt
		for i in range(1, len(self.weights)):
			shape = self.weights[i].shape
			out = GannModel.matmul(out, self.weights[i].T)
			out = GannModel.sumRow(out.T).reshape(shape)
			out = GannModel.sum(out, biases[i-1])

		return out

	# TODO: Convert to numba jit functions
	def matmul(x, y):
		return np.matmul(x, y)

	def sumRow(x):
		return np.sum(x, axis=1)

	def sum(x, y):
		return np.add(x, y)

	def crossover(self, y):
		for x in self.weights + self.biases:
			for i in range(x.shape[0]):
				for j in range(x.shape[1]):
					if np.random.random() < 0.5:
						x[i,j] = y[i,j]

	def mutate(self):
		for x in self.weights + self.biases:
			for i in range(x.shape[0]):
				for j in range(x.shape[1]):
					if np.random.random() < self.mutation_chance:
						x[i,j] = np.random.randn()
