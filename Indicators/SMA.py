from numba import jit
import numpy as np

class SMA(object):

	def __init__(self, period):
		self.period = period
		self.min_period = self.period
		self.type = 'overlay'

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
		c_idx = chart.getTsOffset(plan.c_ts)
		for i in range(c_idx+1-shift-amount, c_idx+1-shift):
			vals.append(self.getValue(chart.bids_ohlc[:i+1]))
		return vals