import json

class Controller(object):

	'''
	Controls all prorgam operations
	'''

	def __init__(self):
		self.running = []
		self.queue = []
		self.complete = []

	def runQueue(self):
		while True:
			for i in range(len(self.queue)-1,-1,-1):
				item = self.queue[i]
				self.complete.append(
					(item[0], item[1](*item[2]))
				)
				del self.queue[i]


	def wait(self, root_name):
		result = False
		while not result:
			result = self.getComplete(root_name)
		return result

	def getComplete(self, root_name):
		for i in range(len(self.complete)-1,-1,-1):
			item = self.complete[i]
			if item[0] == root_name:
				del self.complete[i]
				return item[1]
		return False

	def saveToFile(self, root_name, path, data):
		self.queue.append((root_name, self.pSaveToFile, [path, data]))

	def getJsonFromFile(self, root_name, path):
		self.queue.append((root_name, self.pGetJsonFromFile, [path]))

	def pSaveToFile(self, path, data):
		with open(path, 'w') as f:
			f.write(data)
		return True

	def pGetJsonFromFile(self, path):
		with open(path, 'r') as f:
			data = json.load(f)
		return data