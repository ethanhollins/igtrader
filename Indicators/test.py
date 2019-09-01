from numba import jit
import numpy as np
import json

from timeit import default_timer as timer

# path = '../Data/CS.D.GBPUSD.MINI.IP_4_bid.json'
# with open(path, 'r') as f:
# 	values = json.load(f)

# # @jit
# def getClosest(l, start, end, search):
# 	idx = int((start+end)/2)
# 	m_ts = l[idx][0]
# 	if m_ts == search or start+1 == end:
# 		return idx
# 	elif search > m_ts:
# 		return getClosest(l, idx, end, search)
# 	elif search < m_ts:
# 		return getClosest(l, start, idx, search)

# # def getClosestJit(l, search):
# # 	start = 0
# # 	end = len(l)
# # 	idx = int((start+end)/2)
# # 	m_ts = l[idx][0]

# # 	while not m_ts == search and not start+1 == end:
# # 		idx = int((start+end)/2)
# # 		m_ts = l[idx][0]
# # 		if search > m_ts:
# # 			start = idx
# # 		elif search < m_ts:
# # 			end = idx
# # 	return idx

# def getClosest(l, search):
# 	start = 0
# 	end = len(l)
# 	idx = int((start+end)/2)
# 	m_ts = l[idx]

# 	while not m_ts == search and not start+1 == end:
# 		idx = int((start+end)/2)
# 		m_ts = l[idx]
# 		if search > m_ts:
# 			start = idx
# 		elif search < m_ts:
# 			end = idx
# 	return idx

# @jit
# def getClosestJit(l, search):
# 	start = 0
# 	end = l.size
# 	idx = np.int16((start+end)/2)
# 	m_ts = l[idx]

# 	while not m_ts == search and not start+1 == end:
# 		idx = np.int16((start+end)/2)
# 		m_ts = l[idx]
# 		if search > m_ts:
# 			start = idx
# 		elif search < m_ts:
# 			end = idx
# 	return idx

# # def getOhlcList()

# a = {int(k):v for k,v in values.items()}

# # n = sorted({int(k):v for k,v in values.items()}.items(), key=lambda kv:kv[0])
# x = np.array([i[0] for i in sorted(a.items(), key=lambda kv:kv[0])], dtype=np.int32)
# y = np.round(np.array([i[1] for i in sorted(a.items(), key=lambda kv:kv[0])], dtype=np.float32), decimals=5)
# print(y)
# # m = sortedset({int(k):v for k,v in values.items()}.items())
# # print(np.append(y, [[1.,1.,1.,1.]], axis=0))
# # getClosest.ts = 
# # result = getClosestJit(np.array(x, dtype=np.int32), 160000000)
# # xy = y[:result]
# # print(xy)
# # print(result)
# di = {int(x[i]):list(y[i]) for i in range(x.size)}
# # print(m[-1])
# # m._key = lambda kv: kv[0] < 170000000
# # print(m[-1])

# start = timer()
# for i in range(10000):
# 	x = np.append(x, 180000000 + i)
# 	y = np.append(y, [[1.,1.,1.,1.]], axis=0)
# 	result = getClosestJit(x, 180000000)
# 	xy = y[:result]
# 	for i in range(20):
# 		np.array(xy, dtype=np.float32)
# print('{0:.2f}'.format(timer() - start))

# # start = timer()
# # for i in range(100):
# # 	# result = getClosestJit(m, 180000000)
# # 	z = [i[1] for i in sorted(a.items(), key=lambda kv:kv[0]) if i[0] < 180000000]
# # 	for i in range(20):
# # 		np.array(z, dtype=np.float32)
		
# # print('{0:.2f}'.format(timer() - start))
import datetime
import os
class LogDict(dict):

	def __init__(self, *data, **kwargs):
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

	def push(self):
		dt = datetime.datetime.now().strftime('%d/%m/%y %H:%M:%S.%f')
		if self[-1][0] == dt:
			dt = datetime.datetime.now() + datetime.timedelta(microseconds=1)
			dt = dt.strftime('%d/%m/%y %H:%M:%S.%f')
		dict.__setitem__(self, dt, [])

	def printLog(self, idx, flags=['INFO','DEBUG','WARNING','ERROR','CRITICAL']):
		item = self[idx]
		body = ''
		for i in item[1]:
			if i[0] in flags:
				body += ' {0}: {1}\n'.format(i[0], i[1])
		if body:
			print('{0}:\n{1}'.format(
				item[0],
				body
			))

ld = LogDict()
ld['INFO'] = 'hello'
ld['INFO'] = 'hello2'

ld.push()
ld['WARNING'] = 'hello3'

for i in range(len(ld)):
	ld.printLog(i)
# print(ld['as'])