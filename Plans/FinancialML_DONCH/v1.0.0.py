import Constants
import os
import json
import numpy as np

VARIABLES = {
	'PRODUCT': Constants.GBPUSD,
	'risk': 1.0,
	'stoprange': 130.0
}

def init(utilities):
	global utils
	utils = utilities

	setup(utilities)

	global weights, biases
	plan_name = '.'.join(os.path.basename(__file__).split('.')[:-1])
	weights_path = os.path.join('\\'.join(__file__.split('/')[:-1]), plan_name, 'weights.json')
	with open(weights_path, 'r') as f:
		info = json.load(f)
		weights = [np.array(i, np.float32) for i in info['weights'][:3]]
		biases = [np.array(i, np.float32) for i in info['weights'][3:]]

	global donch, threshold, sl
	donch = utils.DONCH(4)
	threshold = 0.5

def setup(utilities):
	global utils, chart, bank
	utils = utilities
	if len(utils.charts) > 0:
		chart = utils.charts[0]
	else:
		chart = utils.getChart(VARIABLES['PRODUCT'], Constants.FOUR_HOURS)

	bank = utils.getTradableBank()

	# global positions
	# for pos in utils.positions:
	# 	if not pos.closeprice:
	# 		del positions[positions.index(pos)]
	# for pos in utils.positions:
	# 	positions.append(pos)

def getDonchInputs():
	ohlc = chart.getBidOHLC(utils, 0, 6)
	# print(ohlc[-1])
	ohlc = ohlc[:-1]
	
	last_high = 0
	last_low = 0
	for i in ohlc[:-1]:
		if last_high == 0 or i[1] > last_high:
			last_high = i[1]
		if last_low == 0 or i[2] < last_low:
			last_low = i[2]

	c_high = 0
	c_low = 0
	for i in ohlc[1:]:
		if c_high == 0 or i[1] > c_high:
			c_high = i[1]
		if c_low == 0 or i[2] < c_low:
			c_low = i[2]

	x = []

	if c_high > last_high:
		x.append(1)
	elif c_high == last_high:
		x.append(0)
	elif c_high < last_high:
		x.append(-1)

	if c_low > last_low:
		x.append(1)
	elif c_low == last_low:
		x.append(0)
	elif c_low < last_low:
		x.append(-1)

	return x

def getDirection():
	for pos in utils.positions:
		return pos.direction
	return 0

def onNewBar(chart):
	ohlc = chart.getCurrentBidOHLC(utils)
	inputs = getDonchInputs()
	out = fwd_prop(inputs)

	if utils.plan_state.value in (4,):
		time = utils.convertTimestampToDatetime(utils.getLatestTimestamp())
		london_time = utils.convertToLondonTimezone(time)
		utils.log("\nTime", time.strftime('%d/%m/%y %H:%M:%S'))
		utils.log("London Time", london_time.strftime('%d/%m/%y %H:%M:%S') + '\n')

		utils.log('', 'Inputs: {}'.format(inputs))
		utils.log('', 'Out: {}'.format(out))

	# print(inputs)

	if out[1] > (1 - threshold):
		c_dir = getDirection()
		if not c_dir:
			if utils.plan_state.value in (4,):
				utils.log('', 'BUY (REG)')
				
			if bank:
				pos = utils.buy(
					VARIABLES['PRODUCT'], 
					utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
					slRange = VARIABLES['stoprange']
				)
		elif c_dir != Constants.BUY:
			if utils.plan_state.value in (4,):
				utils.log('', 'BUY (S&R)')

			if bank:
				pos = utils.stopAndReverse(
					VARIABLES['PRODUCT'], 
					utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
					slRange = VARIABLES['stoprange']
				)

	elif out[0] < threshold:
		c_dir = getDirection()
		if not c_dir:
			if utils.plan_state.value in (4,):
				utils.log('', 'SELL (REG)')

			if bank:
				pos = utils.sell(
					VARIABLES['PRODUCT'], 
					utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
					slRange = VARIABLES['stoprange']
				)
		elif c_dir != Constants.SELL:
			if utils.plan_state.value in (4,):
				utils.log('', 'SELL (S&R)')

			if bank:
				pos = utils.stopAndReverse(
					VARIABLES['PRODUCT'], 
					utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
					slRange = VARIABLES['stoprange']
				)

	if utils.plan_state.value in (4,):
		report()

def relu(x):
	return np.maximum(0, x)

def sigmoid(x):
	return 1 / (1 + np.exp(-x))

def fwd_prop(inpt):
	x = np.matmul(inpt, weights[0]) + biases[0]
	for i in range(1, len(weights)):
		x = relu(x)		
		x = np.matmul(x, weights[i]) + biases[i]
	return sigmoid(x)

def report():
	utils.log('', "POSITIONS:\nCLOSED:")
	count = 0
	for pos in utils.positions:
		count += 1
		utils.log('', "{}{}: {} Profit: {} | {}%".format(
			'OPEN:\n' if pos.closetime == None else '',
			count, pos.direction,
			pos.getPipProfit(), 
			pos.getPercentageProfit()
		))