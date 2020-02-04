from numba import jit
import numpy as np

class BOLL(object):

	def __init__(self, period, std):
		self.period = period
		self.std = std
		self.min_period = self.period
		self.type = 'overlay'

	@jit
	def calculate(ohlc, period, std):
		container = np.zeros((period), dtype=np.float32)
		for i in range(ohlc.shape[0]-period, ohlc.shape[0]):
			container[i-(ohlc.shape[0]-period)] = ohlc[i,3]
		mean = np.sum(container) / container.size
		d_sum = np.sum((container - mean) ** 2)
		sd = np.sqrt(d_sum/period)

		return np.array([
			mean + sd * (std),
			mean - sd * (std)
		], dtype=np.float32)

	def getValue(self, ohlc):
		if ohlc.shape[0] >= self.min_period:
			result = BOLL.calculate(ohlc, self.period, self.std)
			return np.round(result, decimals=5)
		else:
			return None

	def getCurrent(self, plan, chart):
		return self.getValue(chart.getBidOHLC(plan, 0, 1000))

	def get(self, plan, chart, shift, amount):
		vals = []
		c_idx = chart.getTsOffset(plan.c_ts)
		for i in range(c_idx+1-shift-amount, c_idx+1-shift):
			vals.append(self.getValue(chart.bids_ohlc[max(i+1-1000, 0):i+1]))
		return vals