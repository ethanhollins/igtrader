import json
import time
import os
import pandas as pd

class Controller(object):

	'''
	Controls all prorgam operations
	'''

	__slots__ = (
		'running', 'queue', 'complete',
		'ls_clients', 'subscriptions',
		'is_queue', 'run_next', 'charts',
		'restarting'
	)
	def __init__(self):
		self.running = []
		self.run_next = True
		self.queue = []
		self.complete = []

		self.is_queue = False

		self.ls_clients = {}
		self.charts = []
		self.subscriptions = {}

		self.restarting = False

	def runQueue(self):
		self.is_queue = True
		update_charts = []
		sorted_queue = sorted(self.queue, key=lambda x: x[3], reverse=True)
		for i in range(len(self.queue)-1,-1,-1):
			item = self.queue[i]

			self.complete.append(
				(item[0], item[1](*item[2]))
			)
			del self.queue[i]

		self.is_queue = False

	def wait(self, root_name):
		if not self.is_queue:
			self.runQueue()
		
		result = False
		while result == False:
			result = self.getComplete(root_name)
			if type(result) == pd.DataFrame:
				break
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

	def saveToFile(self, root_name, path, data, priority=0, **kwargs):
		self.queue.append((root_name, self.pSaveToFile, [path, data], priority, kwargs))
		return True

	def getJsonFromFile(self, root_name, path, priority=0, **kwargs):
		self.queue.append((root_name, self.pGetJsonFromFile, [path], priority, kwargs))

	def saveCsv(self, root_name, path, data, priority=0, **kwargs):
		self.queue.append((root_name, self.pSaveCsv, [path, data], priority, kwargs))
		return True

	def readCsv(self, root_name, path, priority=0, **kwargs):
		self.queue.append((root_name, self.pReadCsv, [path], priority, kwargs))
		return True

	def pSaveToFile(self, path, data):
		with open(path, 'w') as f:
			f.write(data)

		return True

	def pGetJsonFromFile(self, path):
		with open(path, 'r') as f:
			data = json.load(f)
		return data

	def pSaveCsv(self, path, data):
		data.to_csv(path, sep=' ', header=True)
		return True

	def pReadCsv(self, path):
		data = pd.read_csv(path, sep=' ')
		return data

	def performScheduledRestart(self):
		if not self.restarting:
			self.restarting = True
			os.system("shutdown -t 0 -r -f")
