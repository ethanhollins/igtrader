from numba import jit
import Constants
import os
import json
import numpy as np
import datetime

VARIABLES = {
	'PRODUCT': Constants.GBPUSD,
	'plan': 0,
	'risk': 1.0,
	'stoprange': 80.0
}

def init(utilities):
	global utils
	utils = utilities

	setup(utilities)

	global weights, biases, mean, std
	plan_name = '.'.join(os.path.basename(__file__).split('.')[:-1])
	weights_path = os.path.join('\\'.join(__file__.split('/')[:-1]), plan_name+'_100g_5l', '{}.json'.format(VARIABLES['plan']))
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
		chart = utils.getChart(VARIABLES['PRODUCT'], Constants.THIRTY_MINUTES)

	bank = utils.getTradableBank()

@jit
def convertToPips(x):
	return np.around(x * 10000, 2)

def normalize(x):
	return (x - mean) / std

# Get donchian data
@jit
def getInputs(high, low, period, lookup):
	X = []
	last_high = 0
	last_low = 0
	for i in range(period, high.shape[0]):
		c_high = 0.
		c_low = 0.
		x = []

		for j in range(i+1-period, i+1):
			if c_high == 0 or high[j] > c_high:
				c_high = high[j]
			if c_low == 0 or low[j] < c_low:
				c_low = low[j]

		if last_high and last_low:
			x.append(convertToPips(c_high - last_high))
			x.append(convertToPips(c_low - last_low))

			if len(X) > 0:
				X.append(X[-1][-(lookup-1):] + [x])
			else:
				X.append([x])

		last_high = c_high
		last_low = c_low

	return np.array(X[lookup-1:], dtype=np.float32)[-1]

def getDirection():
	for pos in utils.positions:
		return pos.direction
	return 0

def onNewBar(chart):

	data = np.array(chart.getBidOHLC(utils, 0, 500), dtype=np.float32)
	inputs = getInputs(data[:,1], data[:,2], 4, 5)
	inputs = normalize(inputs).reshape(1, inputs.shape[0], inputs.shape[1])
	out = fwd_prop(inputs)[0]
	c_dir = getDirection()

	if utils.plan_state.value in (1,):
		utils.log("", "\n[{} ({})] onNewBar ({}) {} / {}".format(
			utils.account.accountid, VARIABLES['plan'],
			utils.name, 
			utils.getTime().strftime('%H:%M:%S'), 
			chart.getCurrentBidOHLC(utils)
		))
		utils.log("", "({}) Inputs: {}\nOut: {}".format(VARIABLES['plan'], inputs, out))

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
				utils.log('', 'SELL (S&R)')

			if bank:
				pos = utils.stopAndReverse(
					VARIABLES['PRODUCT'], 
					utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
					slRange = VARIABLES['stoprange']
				)
		if out[3] > threshold:
			for pos in utils.positions:
				pos.close()

	elif c_dir == Constants.SELL:
		if out[1] > threshold:
			if utils.plan_state.value in (4,):
				utils.log('', 'BUY (S&R)')

			if bank:
				pos = utils.stopAndReverse(
					VARIABLES['PRODUCT'], 
					utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
					slRange = VARIABLES['stoprange']
				)
		if out[2] > threshold:
			for pos in utils.positions:
				pos.close()
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
	w = [np.copy(i) for i in weights]
	b = [np.copy(i) for i in biases]
	for i in range(inpt.shape[1]):
		c_i = inpt[:,i,:]
		c_i = c_i.reshape(c_i.shape[0], 1, c_i.shape[1])
		x = np.matmul(c_i, w[0])
		x = relu(x)

		if i+1 == inpt.shape[1]:
			break

		x = np.matmul(x.reshape(x.shape[0], x.shape[2], x.shape[1]), np.ones([1,c_i.shape[2]]))
		x = relu(x.reshape(x.shape[0], x.shape[2], x.shape[1]))
		w[0] = x
	
	x = np.matmul(x, w[1]) + b[1]
	x = relu(x)

	x = np.matmul(x, w[2]) + b[2]
	x = sigmoid(x).reshape(x.shape[0], x.shape[2])

	return x

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