import datetime
import os

class Log(dict):

	def __init__(self, name, *data, **kwargs):
		self.name = name
		for d in data:
			for key in d: self[key] = d[key]
		for key in kwargs: self[key] = kwargs[key]

	def __getitem__(self, key):
		if type(key) == int or type(key) == slice:
			item = list(self.items())[key]
			return item
		else:
			return dict.__getitem__(self, key)

	def __setitem__(self, key, val):
		if len(self) > 0:
			item = self[-1]
			item[1].append((key, val))
			dict.__setitem__(self, item[0], item[1])
		else:
			dt = datetime.datetime.now().strftime('%d/%m/%y %H:%M:%S.%f')
			dict.__setitem__(self, dt, [(key, val)])

	'''
	PUSH to next timestamp
	'''
	def push(self):
		dt = datetime.datetime.now().strftime('%d/%m/%y %H:%M:%S.%f')
		if self[-1][0] == dt:
			dt = datetime.datetime.now() + datetime.timedelta(microseconds=1)
			dt = dt.strftime('%d/%m/%y %H:%M:%S.%f')
		dict.__setitem__(self, dt, [])

	def getStr(self, idx, flags=['INFO','DEBUG','WARNING','ERROR','CRITICAL']):
		item = self[idx]
		body = ''
		for i in item[1]:
			if i[0] in flags:
				body += ' {0}: {1}\n'.format(i[0], i[1])
		if body:
			return '{0}:\n{1}'.format(
				item[0],
				body
			)

		return body

	def save(self): #FIX THIS (APPEND)
		path = 'Logs/{0}.log'.format(self.name)
		with open(path, 'a') as f:
			for i in range(len(self)):
				f.write(self.getStr(i))

	'''
	INFO Log
	'''
	def i(self, msg):
		self['INFO'] = msg
		try:
			i.handle('INFO', msg)
		except:
			pass

	'''
	DEBUG Log
	'''
	def d(self, msg):
		self['DEBUG'] = msg
		try:
			d.handle('DEBUG', msg)
		except:
			pass

	'''
	WARNING Log
	'''
	def w(self, msg):
		self['WARNING'] = msg
		try:
			w.handle('WARNING', msg)
		except:
			pass

	'''
	ERROR Log
	'''
	def e(self, msg):
		self['ERROR'] = msg
		try:
			e.handle('ERROR', msg)
		except:
			pass

	'''
	CRITICAL Log
	'''
	def c(self, msg):
		self['CRITICAL'] = msg
		try:
			c.handle('CRITICAL', msg)
		except:
			pass
