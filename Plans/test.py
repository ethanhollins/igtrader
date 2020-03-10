import Constants
from enum import Enum
import time

VARIABLES = {
	'PRODUCT': Constants.GBPUSD,
	'RETRY_ON_REJECTED': True,
	'num': 0
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
		chart = utils.getChart(VARIABLES['PRODUCT'], Constants.ONE_MINUTE)

def onNewBar(chart):
	''' Function called on every new bar '''
	utils.log("onNewBar",'{}'.format(VARIABLES['num']))
	utils.log('time', utils.getTime().strftime('%d/%m/%y %H:%M:%S'))
	utils.log('ohlc', str(chart.getCurrentBidOHLC(utils)))

# def onLoop():
	''' Function called on every program iteration '''
	# utils.log("onLoop",'')
	global count
	if count == 0:
		if utils.plan_state.value == 1:
			if VARIABLES['num'] == 1:
				pos = utils.sell(VARIABLES['PRODUCT'], 1, slRange=10, tpRange=10)
				pos.close()
			if VARIABLES['num'] == 2:
				pos = utils.buy(VARIABLES['PRODUCT'], 1, slRange=20, tpRange=20)
				pos.close()
			if VARIABLES['num'] == 3:
				pos = utils.buy(VARIABLES['PRODUCT'], 1, slRange=30, tpRange=30)
				pos.close()
			if VARIABLES['num'] == 4:
				pos = utils.sell(VARIABLES['PRODUCT'], 1, slRange=40, tpRange=40)
				pos.close()
			if VARIABLES['num'] == 5:
				pos = utils.sell(VARIABLES['PRODUCT'], 1, slRange=50, tpRange=50)
				pos.close()
			if VARIABLES['num'] == 6:
				pos = utils.buy(VARIABLES['PRODUCT'], 1, slRange=60, tpRange=60)
				pos.close()
			if VARIABLES['num'] == 7:
				pos = utils.sell(VARIABLES['PRODUCT'], 1, slRange=70, tpRange=70)
				pos.close()
			if VARIABLES['num'] == 8:
				pos = utils.buy(VARIABLES['PRODUCT'], 1, slRange=80, tpRange=80)
				pos = utils.stopAndReverse(VARIABLES['PRODUCT'], 1, slRange = 80)
				pos.close()
			if VARIABLES['num'] == 9:
				pos = utils.sell(VARIABLES['PRODUCT'], 1, slRange=90, tpRange=90)
				pos.close()
			if VARIABLES['num'] == 10:
				pos = utils.sell(VARIABLES['PRODUCT'], 1, slRange=100, tpRange=100)
				pos = utils.stopAndReverse(VARIABLES['PRODUCT'], 1, slRange = 100)



			# print(utils.getBank())
			# start = time.time()

			# for pos in utils.positions:
			# 	pos.close()
			# print(str(time.time() - start))

			# start = time.time()
			# pos = utils.sell(VARIABLES['PRODUCT'], 1, slRange=20, tpRange=20)
			# pos = utils.sell(VARIABLES['PRODUCT'], 1, slRange=20, tpRange=20)
			# print(str(time.time() - start))
			# # pos.close()
			# print(str(time.time() - start))
			# pos = utils.stopAndReverse(VARIABLES['PRODUCT'], 1, slRange = 30)
			# print(str(time.time() - start))
			# pos.close()
			# print('modify')
			# pos.modify(sl=1.3, tp=1.2)
			# time.sleep(2)
			# print('modifySL')
			# pos.modifySL(1.4)
			# time.sleep(2)
			# print('modifyTP')
			# pos.modifyTP(1.1)
			# time.sleep(2)
			# print('removeSL')
			# pos.removeSL()
			# time.sleep(2)
			# print('removeTP')
			# pos.removeTP()
			# time.sleep(2)
			# print('breakeven')
			# pos.breakeven()
			# time.sleep(2)
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
