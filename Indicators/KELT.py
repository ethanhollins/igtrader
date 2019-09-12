from numba import jit
import numpy as np
import Chart

class KELT(object):

	def __init__(self, period, atr_period, multi):
		self.period = period
		self.atr_period = atr_period
		self.multi = multi
		self.min_period = self.period
		self.type = 'overlay'

	@jit
	def calculate(ohlc, period, atr_period, multi):
		tr = np.zeros((ohlc.shape[0]-1), dtype=np.float32)
		for i in range(1, ohlc.shape[0]):
			tr_sum = 0.0
			high = ohlc[i,1]

			low = ohlc[i,2]

			p_close = ohlc[i-1,3]

			if p_close > high:
				tr_sum += p_close - low
			elif p_close < low:
				tr_sum += high - p_close
			else:
				tr_sum += high - low

			tr[i-1] = round(tr_sum, 5)

		tr_ema = np.zeros((tr.size-atr_period), dtype=np.float32)
		ema_multi = 2.0 / (atr_period + 1.0)
		for x in range(atr_period, tr.size):
			if x == atr_period:
				tr_ema[x-atr_period] = np.sum(tr[x-atr_period:x]) / atr_period
			else:
				tr_ema[x-atr_period] = (tr[x] - tr_ema[x-atr_period-1]) * ema_multi + tr_ema[x-atr_period-1]


		ma = 0.0
		for i in range(ohlc.shape[0]-period, ohlc.shape[0]):
			ma += (ohlc[i,1] + ohlc[i,2] + ohlc[i,3])/3.0

		ma /= period

		return np.array([
			ma + (multi * tr_ema[-1]),
			ma,
			ma - (multi * tr_ema[-1])
		], dtype=np.float32)

	def getValue(self, ohlc):
		if ohlc.shape[0] >= self.min_period:
			result = KELT.calculate(ohlc, self.period, self.atr_period, self.multi)
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