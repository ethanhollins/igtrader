import Constants
from enum import Enum
import numpy as np

VARIABLES = {
	'PRODUCT': Constants.GBPUSD,
	'BANK': None,
	'risk': 1.0,
	'stoprange': 55.0,
	'tp_increment': 55.0
}

class Direction(Enum):
	LONG = 1
	SHORT = 2

class EntryState(Enum):
	ONE = 1
	COMPLETE = 2

class EntryType(Enum):
	REGULAR = 1

class TimeState(Enum):
	TRADING = 1

class SortedList(list):
	def __getitem__(self, row):
		return sorted(list(self), key=lambda x: x.count, reverse = True)[row]

	def getSorted(self):
		return sorted(list(self), key=lambda x: x.count, reverse = True)

	def getUnsorted(self):
		return self

class Trigger(dict):

	def __init__(self, direction=None):
		self.direction = direction

		self.entry_state = EntryState.ONE
		self.entry_type = EntryType.REGULAR

		self.pivot_line = 0
		self.c_swing = 0
		self.next_swing = 0

	def setDirection(self, direction, reverse=False):
		if reverse:
			if direction == Direction.LONG:
				self.direction = Direction.SHORT
			elif direction == Direction.SHORT:
				self.direction = Direction.LONG
			else:
				self.direction = None
		else:
			self.direction = direction

	def __getattr__(self, key):
		return self[key]

	def __setattr__(self, key, value):
		self[key] = value

def init(utilities):
	''' Initialize utilities and indicators '''
	global utils
	utils = utilities

	setGlobalVars()
	setup(utilities)

def setup(utilities):
	global utils, m_chart, h4_chart, bank
	utils = utilities
	if len(utils.charts) > 0:
		for chart in utils.charts:
			if chart.period == Constants.ONE_MINUTE or chart.period == Constants.FIVE_MINUTES:
				m_chart = chart
				
			elif chart.period == Constants.FOUR_HOURS:
				h4_chart = chart
	else:
		if utils.plan_state.value in (2,):
			m_chart = utils.getChart(VARIABLES['PRODUCT'], Constants.FIVE_MINUTES)
		else:
			m_chart = utils.getChart(VARIABLES['PRODUCT'], Constants.ONE_MINUTE)

		h4_chart = utils.getChart(VARIABLES['PRODUCT'], Constants.FOUR_HOURS)

	bank = utils.getTradableBank()

def setGlobalVars():
	global long_trigger, short_trigger, is_onb
	global pending_entry
	global positions, trades
	global time_state, bank

	long_trigger = Trigger(direction=Direction.LONG)
	short_trigger = Trigger(direction=Direction.SHORT)
	is_onb = False

	pending_entry = None
	bank = utils.getTradableBank()

def onNewBar(chart):
	global is_onb
	is_onb = True

	if chart.period == Constants.ONE_MINUTE or chart.period == Constants.FIVE_MINUTES:
		if utils.plan_state.value in (1,):
			print('.', end='', flush=True)

		if not utils.plan_state.value in (3,):
			getTakeProfit()

	elif chart.period == Constants.FOUR_HOURS:
		
		if utils.plan_state.value in (4,):
			time = utils.convertTimestampToDatetime(utils.getLatestTimestamp())
			london_time = utils.convertTimezone(time, 'Europe/London')


			utils.log("\nTime", time.strftime('%d/%m/%y %H:%M:%S'))
			utils.log("London Time", london_time.strftime('%d/%m/%y %H:%M:%S') + '\n')
			utils.log('H4 OHLC', h4_chart.getCurrentBidOHLC())
		elif utils.plan_state.value in (1,):
			utils.log("\n[{0}] onNewBar ({1})".format(utils.account.accountid, utils.name), utils.getTime().strftime('%d/%m/%y %H:%M:%S'))

		runSequence()
		if utils.plan_state.value in (4,1):
			report()

	is_onb = False

def onDownTime():
	''' Function called outside of trading time '''

	utils.log("onDownTime", '')
	ausTime = utils.printTime(utils.getAustralianTime())

def onLoop():
	''' Function called on every program iteration '''
	if not is_onb:
		handleEntries()

def handleEntries():
	''' Handle all pending entries '''
	global pending_entry, time_state

	if pending_entry:
		
		# if time_state != TimeState.TRADING:
		# 	closeAllPositions()
		# 	pending_entry = None
		# 	return

		if isOppDirectionPositionExists(pending_entry.direction):
			utils.log('handleEntries', "Attempting position enter {0}: stop and reverse".format(pending_entry.direction))
			handleStopAndReverse(pending_entry)
		else:
			utils.log('handleEntries', "Attempting position enter {0}: regular".format(pending_entry.direction))
			handleRegularEntry(pending_entry)

		pending_entry = None

def isOppDirectionPositionExists(direction):
	for pos in utils.positions:
		if pos.direction == Constants.BUY and direction == Direction.SHORT:
			return True
		elif pos.direction == Constants.SELL and direction == Direction.LONG:
			return True

	return False

def handleStopAndReverse(entry):
	''' 
	Handle stop and reverse entries 
	and check if tradable conditions are met.
	'''
	if bank:

		pos = utils.stopAndReverse(
			VARIABLES['PRODUCT'], 
			utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
			slRange = VARIABLES['stoprange']
		)

def handleRegularEntry(entry):
	''' 
	Handle regular entries 
	and check if tradable conditions are met.
	'''

	if bank:

		if entry.direction == Direction.LONG:
			pos = utils.buy(
				VARIABLES['PRODUCT'], 
				utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
				slRange = VARIABLES['stoprange']
			)
		else:
			pos = utils.sell(
				VARIABLES['PRODUCT'], 
				utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
				slRange = VARIABLES['stoprange']
			)

def onTakeProfit(pos):
	utils.log("onTakeProfit ", '')

def onStopLoss(pos):
	utils.log("onStopLoss", '')

def checkTime():
	''' 
	Checks current time and initiates 
	closing sequence where necessary.
	'''
	global time_state

	time = utils.convertTimestampToDatetime(utils.getLatestTimestamp())
	london_time = utils.convertTimezone(time, 'Europe/London')

def getTakeProfit():
	_, high, low, _ = np.around(m_chart.getCurrentBidOHLC(), 5)

	for pos in utils.positions:
		if pos.direction == Constants.BUY:
			profit = utils.convertToPips(high - pos.entryprice)
			profit_multi = (profit/VARIABLES['tp_increment'])

			if profit_multi >= 2.0:
				sl_pips = (np.floor(profit_multi) - 1) * VARIABLES['tp_increment']
				sl = round(pos.entryprice + utils.convertToPrice(sl_pips), 5)
				if sl > pos.sl:
					return pos.modifySL(sl)
		else:
			profit = utils.convertToPips(pos.entryprice - low)
			profit_multi = (profit/VARIABLES['tp_increment'])

			if profit_multi >= 2.0:
				sl_pips = (np.floor(profit_multi) - 1) * VARIABLES['tp_increment']
				sl = round(pos.entryprice - utils.convertToPrice(sl_pips), 5)
				if sl < pos.sl:
					return pos.modifySL(sl)

def runSequence():
	
	entrySetup(long_trigger)
	entrySetup(short_trigger)

	getSpikePivot(long_trigger)
	getSpikePivot(short_trigger)

	getSwing(long_trigger)
	getSwing(short_trigger)


def getSwing(trigger):
	_, high, low, _ = np.around(h4_chart.getCurrentBidOHLC(), 5)

	if trigger.direction == Direction.LONG:
		trigger.next_swing = low if low < trigger.next_swing or trigger.next_swing == 0 else trigger.next_swing
	else:
		trigger.next_swing = high if high > trigger.next_swing or trigger.next_swing == 0 else trigger.next_swing

def getSpikePivot(trigger):
	ohlc = np.around(h4_chart.getBidOHLC(0, 3), 5)
	if ohlc.shape[0] < 3:
		return

	if trigger.direction == Direction.LONG:
		spike = ohlc[1][1] - utils.convertToPrice(1.0)
		if ohlc[0][1] <= spike and ohlc[2][1] <= spike:
			trigger.pivot_line = ohlc[1][1]
			trigger.c_swing = trigger.next_swing
			trigger.next_swing = min(ohlc[1][2], ohlc[2][2])
			trigger.entry_state = EntryState.ONE
	else:
		spike = ohlc[1][2] + utils.convertToPrice(1.0)
		if ohlc[0][2] >= spike and ohlc[2][2] >= spike:
			trigger.pivot_line = ohlc[1][2]
			trigger.c_swing = trigger.next_swing
			trigger.next_swing = max(ohlc[1][1], ohlc[2][1])
			trigger.entry_state = EntryState.ONE

def entrySetup(trigger):
	if trigger.pivot_line:
		if trigger.entry_state == EntryState.ONE:
			if cancelConfirmation(trigger):
				trigger.pivot_line = 0
				return

			elif entryConfirmation(trigger):
				trigger.entry_state = EntryState.COMPLETE
				return confirmation(trigger, EntryType.REGULAR)

def entryConfirmation(trigger):
	if utils.plan_state.value in (4,):
		utils.log('entryConfirmation', 'Entry Conf:'.format(
			isPivotLineConf(trigger)
		))

	return isPivotLineConf(trigger)

def cancelConfirmation(trigger):
	if utils.plan_state.value in (4,):
		utils.log('cancelConfirmation', 'Cancel Conf: {}'.format(
			isSwingCancelConf(trigger)
		))

	return isSwingCancelConf(trigger)

def isPivotLineConf(trigger):
	close = np.around(h4_chart.getCurrentBidOHLC()[3], 5)

	if trigger.direction == Direction.LONG:
		return close > trigger.pivot_line
	else:
		return close < trigger.pivot_line

def isSwingCancelConf(trigger):
	close = np.around(h4_chart.getCurrentBidOHLC()[3], 5)

	if trigger.direction == Direction.LONG:
		return close < trigger.c_swing
	else:
		return close > trigger.c_swing

def isPosInDir(direction):
	for pos in utils.positions:
		if pos.direction == Constants.BUY and direction == Direction.LONG:
			return True
		elif pos.direction == Constants.SELL and direction == Direction.SHORT:
			return True

	return False

def confirmation(trigger, entry_type, reverse=False):
	''' confirm entry '''

	global pending_entry

	if reverse:
		pending_entry = Trigger(direction=trigger.direction)
		pending_entry.setDirection(trigger.direction, reverse=True)
		pending_entry.entry_type = entry_type
	else:
		pending_entry = Trigger(direction=trigger.direction)
		pending_entry.entry_type = entry_type

	if (isPosInDir(pending_entry.direction)):
		pending_entry = None
		return False
		
	utils.log("confirmation", '{0} {1}'.format(trigger.direction, pending_entry.entry_type))
	return True

def report():
	''' Prints report for debugging '''
	if utils.plan_state.value in (1,):
		utils.log('', "\n[{}] Report:".format(utils.account.accountid))

	utils.log('', "\n")

	utils.log('', h4_chart.c_ts)
	utils.log('', "LONG T: {0}".format(long_trigger))
	utils.log('', "SHORT T: {0}".format(short_trigger))

	utils.log('', "\nCLOSED POSITIONS:")
	count = 0
	for pos in utils.closed_positions:
		count += 1

		utils.log('', "{}: {} Profit: {} | {}%".format(
			count,
			pos.direction,
			pos.getPipProfit(), 
			pos.getPercentageProfit()
		))

	utils.log('', "\nOPEN POSITIONS:")
	count = 0
	for pos in utils.positions:
		count += 1

		if pos.direction == Constants.BUY:
			sl_pips = utils.convertToPips(pos.entryprice - pos.sl)
		else:
			sl_pips = utils.convertToPips(pos.sl - pos.entryprice)

		utils.log('', "{}: {} Profit: {} | {}% ENTRY: {} SL: {} | {}".format(
			count,
			pos.direction,
			pos.getPipProfit(), 
			pos.getPercentageProfit(),
			pos.entryprice,
			pos.sl,
			sl_pips
		))

	utils.log('', utils.getTime().strftime('%d/%m/%y %H:%M:%S'))
	utils.log('', "--|\n")
