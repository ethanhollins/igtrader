from numba import jit
import numpy as np

class DONCH(object):

	def __init__(self, period):
		self.period = period
		self.min_period = self.period
		self.type = 'overlay'

	@jit
	def calculate(ohlc, period):
		high = 0.0
		low = 0.0
		for i in range(ohlc.shape[0]-period-1, ohlc.shape[0]-1):
			t_high = ohlc[i,1]
			t_low = ohlc[i,2]
			if high == 0:
				high = t_high
			elif t_high > high:
				high = t_high

			if low == 0:
				low = t_low
			elif t_low < low:
				low = t_low

		return np.array([high, low], dtype=np.float32)

	def getValue(self, ohlc):
		if ohlc.shape[0] >= self.min_period:
			result = DONCH.calculate(ohlc, self.period)
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