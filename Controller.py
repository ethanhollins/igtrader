import json
import time

class Controller(object):

	'''
	Controls all prorgam operations
	'''

	__slots__ = (
		'running', 'queue', 'complete',
		'ls_clients', 'subscriptions',
		'is_queue', 'run_next'
	)
	def __init__(self):
		self.running = []
		self.run_next = True
		self.queue = []
		self.complete = []

		self.is_queue = False

		self.ls_clients = {}
		self.subscriptions = []

	def runQueue(self):
		self.is_queue = True
		for i in range(len(self.queue)-1,-1,-1):
			item = self.queue[i]
			
			if 'info' in item[3]:
				info = item[3]['info']

				if info == 'onNewBar':
					charts = [chart for root in self.running for chart in root.manager.charts]
					while not all(i.is_updated == True for i in charts):
						time.sleep(1)
						pass

			self.complete.append(
				(item[0], item[1](*item[2]))
			)
			del self.queue[i]
		self.is_queue = False

	def wait(self, root_name):
		if not self.is_queue:
			self.runQueue()
		
		result = False
		while not result:
			result = self.getComplete(root_name)
		return result

	def getComplete(self, root_name):
		try:
			for item in self.complete:
				if item[0] == root_name:
					del self.complete[self.complete.index(item)]
					return item[1]
			return False
		except:
			return self.getComplete(root_name)

	def saveToFile(self, root_name, path, data, **kwargs):
		self.queue.append((root_name, self.pSaveToFile, [path, data], kwargs))

	def getJsonFromFile(self, root_name, path, **kwargs):
		self.queue.append((root_name, self.pGetJsonFromFile, [path], kwargs))

	def pSaveToFile(self, path, data):
		with open(path, 'w') as f:
			f.write(data)

		return True

	def pGetJsonFromFile(self, path):
		with open(path, 'r') as f:
			data = json.load(f)
		return data