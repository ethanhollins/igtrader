from numba import jit
import numpy as np

class ATR(object):

	def __init__(self, period):
		self.period = period
		self.min_period = self.period
		self.type = 'study'

	@jit
	def calculate(ohlc, period):
		result = np.zeros((ohlc.shape[0]-period), dtype=np.float32)
		for i in range(period, ohlc.shape[0]):
			if i > period:
				p_atr = result[i-period-1]

				high = ohlc[i,1]
				p_high = ohlc[i-1,1]

				low = ohlc[i,2]
				p_low = ohlc[i-1,2]

				p_close = ohlc[i-1,3]

				tr = 0.0
				if p_close > high:
					tr = p_close - low
				elif p_close < low:
					tr = high - p_close
				else:
					tr = high - low

				result[i-period] = round((p_atr * (period-1) + tr) / period, 5)
			else:
				tr_sum = 0.0
				for j in range(0, i):
					if j == 0:
						tr_sum += (ohlc[i,1] - ohlc[i,2])
					else:
						high = ohlc[j,1]
						p_high = ohlc[j-1,1]

						low = ohlc[j,2]
						p_low = ohlc[j-1,2]

						p_close = ohlc[j-1,3]

						if p_close > high:
							tr_sum += p_close - low
						elif p_close < low:
							tr_sum += high - p_close
						else:
							tr_sum += high - low

				result[i-period] = round(tr_sum/period, 5)

		return result[-1]

	def getValue(self, ohlc):
		if ohlc.shape[0] > self.min_period:
			result = ATR.calculate(ohlc, self.period)
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