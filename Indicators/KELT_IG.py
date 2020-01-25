from numba import jit
import numpy as np
import Chart

class KELT_IG(object):

	def __init__(self, period, atr_period, multi):
		self.period = period
		self.atr_period = atr_period
		self.multi = multi
		self.min_period = self.period
		self.type = 'overlay'

	@jit
	def calculate(ohlc, period, atr_period, multi):
		MAX_SIZE = 1000

		# ATR
		tr_ma = 0.0
		for i in range(ohlc.shape[0]-atr_period, ohlc.shape[0]):
			tr_ma += (ohlc[i,1] - ohlc[i,2])
		atr_val = tr_ma / atr_period

		# EMA
		ma = 0.0
		for i in range(ohlc.shape[0]-period, ohlc.shape[0]):
			ma += (ohlc[i,1] + ohlc[i,2] + ohlc[i,3])/3.0

		ma /= period

		return np.array([
			ma + (multi * atr_val),
			ma,
			ma - (multi * atr_val)
		], dtype=np.float32)

	def getValue(self, ohlc):
		if ohlc.shape[0] >= self.min_period:
			result = KELT_IG.calculate(ohlc, self.period, self.atr_period, self.multi)
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