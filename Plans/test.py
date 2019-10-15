import Constants
from enum import Enum
import time

VARIABLES = {
	'PRODUCT': Constants.GBPUSD,
	'RETRY_ON_REJECTED': True
}


def init(utilities):
	''' Initialize utilities and indicators '''
	setup(utilities)
	utils.log("init",'')
	global count
	count = 0


def setup(utilities):
	global utils, chart
	utils = utilities
	if len(utils.charts) > 0:
		chart = utils.charts[0]
	else:
		chart = utils.getChart(VARIABLES['PRODUCT'], Constants.FOUR_HOURS)

def onNewBar(chart):
	''' Function called on every new bar '''
	utils.log("onNewBar",'')
	utils.log('time', utils.getTime().strftime('%d/%m/%y %H:%M:%S'))
	utils.log('ohlc', str(chart.getCurrentBidOHLC(utils)))

def onLoop():
	''' Function called on every program iteration '''
	# utils.log("onLoop",'')
	global count
	if count == 0:
		if utils.plan_state.value == 1:
			print(utils.getBank())
			start = time.time()

			for pos in utils.positions:
				pos.close()
			print(str(time.time() - start))

			start = time.time()
			utils.sell(VARIABLES['PRODUCT'], 1, slRange=20, tpRange=20)
			print(str(time.time() - start))
			# utils.sell(VARIABLES['PRODUCT'], 2, slPrice=1.45, tpPrice=1.16)
			# time.sleep(2)
			# # print('modify')
			# # pos.modify(sl=1.3, tp=1.2)
			# # time.sleep(2)
			# # print('modifySL')
			# # pos.modifySL(1.4)
			# # time.sleep(2)
			# # print('modifyTP')
			# # pos.modifyTP(1.1)
			# # time.sleep(2)
			# # print('removeSL')
			# # pos.removeSL()
			# # time.sleep(2)
			# # print('removeTP')
			# # pos.removeTP()
			# # time.sleep(2)
			# # print('breakeven')
			# # pos.breakeven()
			# # time.sleep(2)
			# print('sar')
			# pos = utils.stopAndReverse(VARIABLES['PRODUCT'], 1.5, slPrice='1.2', tpPrice='1.3')
			# pos.data['hello'] = 'lolol'
			# # print(type(utils))
			# print(dict(pos))
			# utils.savePositions()
			count += 1

def onEntry(pos):
	utils.log("onEntry", str(dict(pos)))

def onStopLoss(pos):
	utils.log("onStopLoss", str(dict(pos)))

def onTakeProfit(pos):
	utils.log("onTakeProfit", str(dict(pos)))

def onClose(pos):
	utils.log("onClose", str(dict(pos)))

def onRejected(pos):
	utils.log("onRejected", str(dict(pos)))

def onModified(pos):
	utils.log("onModified", str(dict(pos)))
