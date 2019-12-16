import json

class Controller(object):

	'''
	Controls all prorgam operations
	'''

	def __init__(self):
		self.running = []
		self.queue = []
		self.complete = []
		self.wait_list = []

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
			print(result != False)
		return result

	def getComplete(self, root_name):
		try:
			for item in self.complete:
				if item[0] == root_name:
					del self.complete[self.complete.index(item)]
					return item[1]
			return False
		except:
			print('nope')
			return self.getComplete(root_name)

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