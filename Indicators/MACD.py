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
		
		MAX_SIZE = 1000
		if ohlc.shape[0]-MAX_SIZE > slowperiod:
			start_off_fast = ohlc.shape[0]-MAX_SIZE
		else:
			start_off_fast = fastperiod

		if ohlc.shape[0]-MAX_SIZE > slowperiod:
			start_shape = MAX_SIZE
		else:
			start_shape = ohlc.shape[0]-fastperiod

		fast_ema = np.zeros((start_shape), dtype=np.float32)
		multi = 2.0 / (fastperiod + 1.0)
		for x in range(start_off_fast, ohlc.shape[0]):
			if x == start_off_fast:
				fast_ema[x-start_off_fast] = np.sum(ohlc[x-start_off_fast:x,3]) / fastperiod
			else:
				fast_ema[x-start_off_fast] = (ohlc[x,3] - fast_ema[x-start_off_fast-1]) * multi + fast_ema[x-start_off_fast-1]

		if ohlc.shape[0]-MAX_SIZE > slowperiod:
			start_off_slow = ohlc.shape[0]-MAX_SIZE
		else:
			start_off_slow = slowperiod

		if ohlc.shape[0]-MAX_SIZE > slowperiod:
			start_shape = MAX_SIZE
		else:
			start_shape = ohlc.shape[0]-slowperiod

		slow_ema = np.zeros((start_shape), dtype=np.float32)
		multi = 2.0 / (slowperiod + 1.0)
		for x in range(start_off_slow, ohlc.shape[0]):
			if x == start_off_slow:
				slow_ema[x-start_off_slow] = np.sum(ohlc[x-start_off_slow:x,3]) / slowperiod
			else:
				slow_ema[x-start_off_slow] = (ohlc[x,3] - slow_ema[x-start_off_slow-1]) * multi + slow_ema[x-start_off_slow-1]

		macd = fast_ema[start_off_slow-start_off_fast:] - slow_ema

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