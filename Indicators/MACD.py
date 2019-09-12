from numba import jit
import numpy as np

class MACD(object):

	def __init__(self, fastperiod, slowperiod, signalperiod):
		self.fastperiod = fastperiod
		self.slowperiod = slowperiod
		self.signalperiod = signalperiod
		self.min_period = self.slowperiod + self.signalperiod
		self.type = 'study'

	@jit
	def calculate(ohlc, fastperiod, slowperiod, signalperiod):
		
		fast_ema = np.zeros((ohlc.shape[0]-fastperiod), dtype=np.float32)
		multi = 2.0 / (fastperiod + 1.0)
		for x in range(fastperiod, ohlc.shape[0]):
			if x == fastperiod:
				fast_ema[x-fastperiod] = np.sum(ohlc[x-fastperiod:x,3]) / fastperiod
			else:
				fast_ema[x-fastperiod] = (ohlc[x,3] - fast_ema[x-fastperiod-1]) * multi + fast_ema[x-fastperiod-1]

		slow_ema = np.zeros((ohlc.shape[0]-slowperiod), dtype=np.float32)
		multi = 2.0 / (slowperiod + 1.0)
		for x in range(slowperiod, ohlc.shape[0]):
			if x == slowperiod:
				slow_ema[x-slowperiod] = np.sum(ohlc[x-slowperiod:x,3]) / slowperiod
			else:
				slow_ema[x-slowperiod] = (ohlc[x,3] - slow_ema[x-slowperiod-1]) * multi + slow_ema[x-slowperiod-1]

		macd = fast_ema[slowperiod-fastperiod:] - slow_ema

		signal = np.zeros((macd.shape[0]-signalperiod), dtype=np.float32)
		multi = 2.0 / (signalperiod + 1.0)
		for x in range(signalperiod, macd.shape[0]):
			if x == signalperiod:
				signal[x-signalperiod] = np.sum(macd[x-signalperiod:x]) / signalperiod
			else:
				signal[x-signalperiod] = (macd[x] - signal[x-signalperiod-1]) * multi + signal[x-signalperiod-1]

		hist = macd[-1] - signal[-1]

		return np.array([macd[-1], signal[-1], hist], dtype=np.float32)

	def getValue(self, ohlc):
		if ohlc.shape[0] > self.min_period:
			result = MACD.calculate(ohlc, self.fastperiod, self.slowperiod, self.signalperiod)
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