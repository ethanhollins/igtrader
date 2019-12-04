from numba import jit
import numpy as np

class SAR(object):

	def __init__(self, accel, maximum):
		self.accel = accel
		self.maximum = maximum
		self.min_period = 20
		self.type = 'overlay'

	@jit
	def calculate(ohlc, period):
		#####

	def getValue(self, ohlc):
		if ohlc.shape[0] > self.min_period:
			result = SAR.calculate(ohlc, self.accel, self.maximum)
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