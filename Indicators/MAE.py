from numba import jit
import numpy as np

class MAE(object):

	def __init__(self, period, offset, ma_type='sma'):
		self.period = period
		self.offset = offset
		self.min_period = self.period
		self.ma_type = ma_type
		self.type = 'overlay'

	@jit
	def calculate(ohlc, period, offset):
		ma = 0.0
		for i in range(ohlc.shape[0]-period, ohlc.shape[0]):
			ma += ohlc[i,3]

		ma /= period
		return np.array([
			ma + ma * (offset/100),
			ma - ma * (offset/100)
		], dtype=np.float32)

	@jit
	def calculateTyp(ohlc, period, offset):
		ma = 0.0
		for i in range(ohlc.shape[0]-period, ohlc.shape[0]):
			ma += (ohlc[i,1] + ohlc[i,2] + ohlc[i,3])/3.0

		ma /= period
		return np.array([
			ma + ma * (offset/100),
			ma - ma * (offset/100)
		], dtype=np.float32)

	def getValue(self, ohlc):
		if ohlc.shape[0] >= self.min_period:
			if self.ma_type == 'typ':
				result = MAE.calculateTyp(ohlc, self.period, self.offset)
			else:
				result = MAE.calculate(ohlc, self.period, self.offset)
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