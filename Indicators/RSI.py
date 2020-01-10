from numba import jit
import numpy as np

class RSI(object):

	def __init__(self, period):
		self.period = period
		self.min_period = self.period
		self.type = 'study'

	@jit
	def calculate(ohlc, period):

		MAX_SIZE = 1000
		if ohlc.shape[0]-MAX_SIZE > period:
			start_off = ohlc.shape[0]-MAX_SIZE
		else:
			start_off = period

		if ohlc.shape[0]-MAX_SIZE > period:
			start_shape = MAX_SIZE
		else:
			start_shape = ohlc.shape[0]-period

		result = np.zeros((start_shape), dtype=np.float32)
		gain = np.zeros((start_shape), dtype=np.float32)
		loss = np.zeros((start_shape), dtype=np.float32)
		
		for i in range(start_off, ohlc.shape[0]):

			gain_sum = 0.0
			loss_sum = 0.0
			if i > start_off:
				p_gain = gain[i-start_off-1]
				p_loss = loss[i-start_off-1]

				chng = ohlc[i,3] - ohlc[i-1,3]
				if chng >= 0:
					gain_sum += chng
				else:
					loss_sum += np.absolute(chng)

				gain_avg = (p_gain * (period-1) + gain_sum)/period
				loss_avg = (p_loss * (period-1) + loss_sum)/period

			else:
				for j in range(0, i):
					if j != 0:
						chng = ohlc[j,3] - ohlc[j-1,3]

						if chng >= 0:
							gain_sum += chng
						else:
							loss_sum += np.absolute(chng)

				gain_avg = gain_sum / period
				loss_avg = loss_sum / period

			gain[i-start_off] = gain_avg
			loss[i-start_off] = loss_avg

			if loss_avg == 0.0:
				result[i-start_off] = 100
			else:
				result[i-start_off] = 100 - (100 / (1 + gain_avg/loss_avg))

		return result[-1]

	def getValue(self, ohlc):
		if ohlc.shape[0] > self.min_period:
			result = RSI.calculate(ohlc, self.period)
			return np.round(result, decimals=2)
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