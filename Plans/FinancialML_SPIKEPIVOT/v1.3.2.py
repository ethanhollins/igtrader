from numba import jit
import Constants
import os
import json
import numpy as np
import datetime

VARIABLES = {
	'PRODUCT': Constants.GBPUSD,
	'risk': 1.0,
	'stoprange': 55.0
}

def init(utilities):
	global utils
	utils = utilities

	setup(utilities)

	global weights, biases, mean, std
	plan_name = '.'.join(os.path.basename(__file__).split('.')[:-1])
	weights_path = os.path.join('\\'.join(__file__.split('/')[:-1]), plan_name+'_0_weights', 'weights.json')
	with open(weights_path, 'r') as f:
		info = json.load(f)
		weights = [np.array(i, np.float32) for i in info['weights'][:3]]
		biases = [np.array(i, np.float32) for i in info['weights'][3:]]
		mean = info['mean']
		std = info['std']

	global threshold, sl
	threshold = 0.5

def setup(utilities):
	global utils, chart, bank
	utils = utilities
	if len(utils.charts) > 0:
		chart = utils.charts[0]
	else:
		chart = utils.getChart(VARIABLES['PRODUCT'], Constants.TEN_MINUTES)

	bank = utils.getTradableBank()

@jit
def convertToPips(x):
	return np.around(x * 10000, 2)

def normalize(x):
	return (x - mean) / std

@jit
def isLongSpike(data, threshold):
	s_idx = int((data.shape[0]-1)/2)
	s_high = convertToPips(data[s_idx, 1]) - threshold

	for j in range(data.shape[0]):
		if j == s_idx:
			continue
		c_high = convertToPips(data[j, 1])
		if c_high > s_high:
			return False
	return True

@jit
def isShortSpike(data, threshold):
	s_idx = int((data.shape[0]-1)/2)
	s_low = convertToPips(data[s_idx, 2]) + threshold

	for j in range(data.shape[0]):
		if j == s_idx:
			continue
		c_low = convertToPips(data[j, 2])
		if c_low < s_low:
			return False
	return True

@jit
def getInputs(data):
	spike_threshold = 1.0
	lookback = 3
	c_data = np.array([0,0], dtype=np.float32) # LONG DIST, SHORT DIST

	# Spike LONG, Swing LONG, Spike SHORT, Swing SHORT, Current High, Current Low
	ad_data = [0,0,0,0, max(data[:lookback,1]), min(data[:lookback,2])] 
	X = []

	for i in range(lookback, data.shape[0]):
		c_data = np.copy(c_data)

		ad_data[4] = data[i,1] if data[i,1] > ad_data[4] else ad_data[4]
		ad_data[5] = data[i,2] if data[i,2] < ad_data[5] else ad_data[5]

		if c_data[0]:
			c_data[0] = convertToPips((data[i,3] - ad_data[0]) * (ad_data[1] / ad_data[0]))

		if c_data[1]:
			c_data[1] = convertToPips((ad_data[2] - data[i,3]) * (ad_data[2] / ad_data[3]))

		# Get Current Spike Info
		if isLongSpike(
			data[i+1-lookback:i+1],
			spike_threshold
		):
			s_idx = int((lookback-1)/2)
			ad_data[0] = data[i-s_idx, 1]
			ad_data[1] = ad_data[5]
			ad_data[5] = min(data[i+1-lookback:i+1, 2])
 
			c_data[0] = convertToPips((data[i,3] - ad_data[0]) * (ad_data[1] / ad_data[0]))

		if isShortSpike(
			data[i+1-lookback:i+1],
			spike_threshold
		):
			s_idx = int((lookback-1)/2)
			ad_data[2] = data[i-s_idx, 2]
			ad_data[3] = ad_data[4] 
			ad_data[4] = max(data[i+1-lookback:i+1, 1])

			c_data[1] = convertToPips((ad_data[2] - data[i,3]) * (ad_data[2] / ad_data[3]))

		# print(ad_data)
		# print(c_data)
		X.append(c_data)
	# print(data)
	return X[-1]

def getDirection():
	for pos in utils.positions:
		return pos.direction
	return 0

global count
count = 0

def onNewBar(chart):
	ohlc = np.concatenate((chart.getCurrentAskOHLC(utils), chart.getCurrentBidOHLC(utils)))
	data = np.array(chart.getBidOHLC(utils, 0, 500), dtype=np.float32)

	inputs = getInputs(data)
	inputs = normalize(inputs)
	out = fwd_prop(inputs)
	c_dir = getDirection()

	if utils.plan_state.value in (4,):
		time = utils.convertTimestampToDatetime(utils.getLatestTimestamp())
		london_time = utils.convertToLondonTimezone(time)
		utils.log("\nTime", time.strftime('%d/%m/%y %H:%M:%S'))
		utils.log("London Time", london_time.strftime('%d/%m/%y %H:%M:%S') + '\n')

		utils.log('', 'ASK: {}'.format(chart.getCurrentAskOHLC(utils)))
		utils.log('', 'BID: {}'.format(chart.getCurrentBidOHLC(utils)))
		utils.log('', 'Inputs: {}'.format(inputs))
		utils.log('', 'Out: {}'.format(out))

	if c_dir == Constants.BUY:
		if out[0] > threshold:
			if utils.plan_state.value in (4,):
				utils.log('', 'BUY (S&R)')

			if bank:
				pos = utils.stopAndReverse(
					VARIABLES['PRODUCT'], 
					utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
					slRange = VARIABLES['stoprange']
				)

	elif c_dir == Constants.SELL:
		if out[1] > threshold:
			if utils.plan_state.value in (4,):
				utils.log('', 'SELL (S&R)')

			if bank:
				pos = utils.stopAndReverse(
					VARIABLES['PRODUCT'], 
					utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
					slRange = VARIABLES['stoprange']
				)
	else:
		if out[0] > out[1]:
			if out[0] > threshold:
				if utils.plan_state.value in (4,):
					utils.log('', 'SELL (REG)')

				if bank:
					pos = utils.sell(
						VARIABLES['PRODUCT'], 
						utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
						slRange = VARIABLES['stoprange']
					)
		else:
			if out[1] > threshold:
				if utils.plan_state.value in (4,):
					utils.log('', 'BUY (REG)')
				
				if bank:
					pos = utils.buy(
						VARIABLES['PRODUCT'], 
						utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
						slRange = VARIABLES['stoprange']
					)

	if utils.plan_state.value in (4,):
		report()

@jit
def relu(x):
	return np.maximum(0, x)

@jit
def sigmoid(x):
	return 1 / (1 + np.exp(-x))

@jit(forceobj=True)
def fwd_prop(inpt):
	x = np.matmul(inpt, weights[0]) + biases[0]
	for i in range(1, len(weights)):
		x = relu(x)		
		x = np.matmul(x, weights[i]) + biases[i]
	return sigmoid(x)

def report():
	utils.log('', "POSITIONS:\nCLOSED:")
	count = 0
	for pos in utils.closed_positions:
		count += 1
		utils.log('', "{}: {} Profit: {} | {}% {} - {}".format(
			count, pos.direction,
			pos.getPipProfit(), 
			pos.getPercentageProfit(),
			pos.entryprice,
			pos.closeprice
		))
	utils.log('', 'OPENED:')
	for pos in utils.positions:
		count += 1
		utils.log('', "{}: {} Profit: {} | {}% {}".format(
			count, pos.direction,
			pos.getPipProfit(), 
			pos.getPercentageProfit(),
			pos.entryprice
		))