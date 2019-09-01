from numba import jit
import numpy as np

class SMA(object):

	def __init__(self, period):
		self.period = period
		self.min_period = self.period

	@jit
	def calculate(ohlc, period):
		ma = 0.0
		for i in range(ohlc.shape[0]-period, ohlc.shape[0]):
			ma += ohlc[i,3]
		return ma / period

	def getValue(self, ohlc):
		if ohlc.shape[0] >= self.min_period:
			result = SMA.calculate(ohlc, self.period)
			return np.round(result, decimals=5)
		else:
			return None
	
	def getCurrent(self, plan, chart):
		return self.getValue(chart.getAllBidOHLC(plan))

	def get(self, plan, chart, shift, amount):
		vals = []
		for i in range(chart.ts.size-shift-amount, chart.ts.size-shift):
			vals.append(self.getValue(chart.getAllBidOHLC(plan)[:i]))
		return vals