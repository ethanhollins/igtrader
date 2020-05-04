from numba import jit
import numpy as np

class EMA(object):

	def __init__(self, period):
		self.period = period
		self.min_period = self.period
		self.type = 'overlay'

	@jit
	def calculate(ohlc, period):
		ema = np.zeros((ohlc.shape[0]-period), dtype=np.float32)
		multi = 2.0 / (period + 1.0)
		for x in range(period, ohlc.shape[0]):
			if x == period:
				ema[x-period] = np.sum(ohlc[x-period:x,3]) / period
			else:
				ema[x-period] = (ohlc[x,3] - ema[x-period-1]) * multi + ema[x-period-1]

		return ema[-1]

	def getValue(self, ohlc):
		if ohlc.shape[0] >= self.min_period:
			result = EMA.calculate(ohlc, self.period)
			return np.round(result, decimals=5)
		else:
			return None

	def getCurrent(self, chart):
		return self.getValue(chart.getBidOHLC(0, 1000))

	def get(self, chart, shift, amount):
		vals = []
		c_idx = chart.getTsOffset(chart.c_ts)
		for i in range(c_idx+1-shift-amount, c_idx+1-shift):
			vals.append(self.getValue(chart.bids_ohlc[max(i+1-1000, 0):i+1]))
		return vals