from numba import jit
import numpy as np

class CCI(object):

	def __init__(self, period):
		self.period = period
		self.min_period = self.period
		self.type = 'study'

	@jit
	def calculate(ohlc, period):
		
		# Calculate Typical price
		c_typ = (ohlc[-1,1] + ohlc[-1,2] + ohlc[-1,3])/3.0
		typ_sma = 0.0
		for i in range(ohlc.shape[0]-period, ohlc.shape[0]):
			typ_sma += (ohlc[i,1] + ohlc[i,2] + ohlc[i,3])/3.0

		typ_sma /= period
		
		# Calculate Mean Deviation
		mean_dev = 0.0
		for i in range(ohlc.shape[0]-period, ohlc.shape[0]):
			mean_dev += np.absolute(
				((ohlc[i,1] + ohlc[i,2] + ohlc[i,3])/3.0) - typ_sma
			)

		mean_dev /= period
		const = .015

		if mean_dev == 0:
			return 0

		return (c_typ - typ_sma) / (const * mean_dev)

	def getValue(self, ohlc):
		if ohlc.shape[0] > self.min_period:
			result = CCI.calculate(ohlc, self.period)
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