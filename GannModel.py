from GannNode import GannNode

import numpy as np
import json

class GannModel(object):

	def __init__(self,
		name='',
		metrics=['abs_percent', 'abs_drawdown']
	):
		self.nodes = []
		if name:
			self.load(name)

	def load(self, name):
		path = '???/' + name

		if os.path.exists(path):
			with open(path, 'r') as f:
				props = json.load(f)

				# TODO: LOAD ALL VARIABLES FROM props FILE
		else:
			self.init() # MAYBE RAISE ERROR

	def save(self, name):
		# TODO: SAVE WITH NAME/EPOCH/DATE
		path = '???/' + name

		with open(path, 'w') as f:
			f.write(json.dumps(...))

		return

	def init(self):

		''' 
		TODO: 
			SET INPUTS
			SET WEIGHTS AND BIASES AS RANDOM
			SET HIDDEN LAYERS
			SET FITNESS FUNCTIONS ETC.
		'''

		return

	def getFitnessFunc(self, fitness):
		return

	def getMetricsFunc(self, metrics):
		return

	def loadNode(self, fitness, module, weights, biases):

		# node = GannNode(weights, biases, fitness, module)
		# self.nodes.append(node)
		return node

	def createNode(self, fitness, module, layers):
		
		# TODO: LOAD LAYERS


		node = GannNode(weights, biases, fitness, module)
		self.nodes.append(node)
		return node

	def result(self):
		return

	def gpr(self):
		return