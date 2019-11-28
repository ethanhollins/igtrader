import Constants
from enum import Enum

VARIABLES = {
	'TIMEZONE': 'America/New_York',
	'PRODUCT': Constants.GBPUSD,
	'BANK': None,
	'risk': 1.0,
	'stoprange': 130.0,
	'tprange': 130.0,
	'MISC': None,
	'doji_range': 1,
	'min_entry': 2
}

class Direction(Enum):
	LONG = 1
	SHORT = 2

class EntryType(Enum):
	REGULAR = 1
	ADDITIONAL = 2

class TimeState(Enum):
	TRADING = 1
	TWENTY = 2
	STOP = 3

class SortedList(list):
	def __getitem__(self, row):
		return sorted(list(self), key=lambda x: x.count, reverse = True)[row]

	def getSorted(self):
		return sorted(list(self), key=lambda x: x.count, reverse = True)

	def getUnsorted(self):
		return self

class Pivot(dict):

	def __init__(self):
		self.is_init = True
		
		self.high = 0
		self.low = 0
		self.close = 0

	def set(self, high, low, close):
		self.high = high
		self.low = low
		self.close = close

	def __getattr__(self, key):
		return self[key]

	def __setattr__(self, key, value):
		self[key] = value

class Trigger(dict):

	def __init__(self, direction=Direction.LONG):
		self.direction = direction
		self.pivot = Pivot()

		self.entry_type = None

	def setDirection(self, direction):
		self.direction = direction

	def __getattr__(self, key):
		return self[key]

	def __setattr__(self, key, value):
		self[key] = value

def init(utilities):
	''' Initialize utilities and indicators '''

	setup(utilities)
	
	global boll_one, boll_two

	boll_one = utils.BOLL(10, 2.2)
	boll_two = utils.BOLL(20, 1.9)

	setGlobalVars()

def setup(utilities):
	global utils, chart
	utils = utilities
	if len(utils.charts) > 0:
		chart = utils.charts[0]
	else:
		chart = utils.getChart(VARIABLES['PRODUCT'], Constants.FOUR_HOURS)

def setGlobalVars():
	global trigger
	global pending_entry, pending_breakevens, pending_exits
	global time_state

	trigger = Trigger()

	pending_entry = None
	pending_breakevens = []
	pending_exits = []

	time_state = TimeState.TRADING

def onNewBar(chart):
	''' Function called on every new bar '''
	if utils.plan_state.value in (4,):
		utils.log("\nonNewBar", utils.getTime().strftime('%d/%m/%y %H:%M:%S'))
	elif utils.plan_state.value in (1,):
		utils.log("\n[{0}] onNewBar ({1})".format(utils.account.accountid, utils.name), utils.getTime().strftime('%d/%m/%y %H:%M:%S'))
	
	checkTime()

	runSequence()

	if utils.plan_state.value in (4,):
		report()

def onDownTime():
	''' Function called outside of trading time '''

	utils.log("onDownTime", '')
	ausTime = utils.printTime(utils.getAustralianTime())

def onLoop():
	''' Function called on every program iteration '''

	handleEntries()

def handleEntries():
	''' Handle all pending entries '''
	global pending_entry

	if pending_entry:
		
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

	bank = utils.getTradableBank()
	if bank:
		tp = VARIABLES['tprange'] if entry.entry_type == EntryType.ADDITIONAL else None

		pos = utils.stopAndReverse(
			VARIABLES['PRODUCT'], 
			utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
			slRange = VARIABLES['stoprange'],
			tpRange = tp
		)


def handleRegularEntry(entry):
	''' 
	Handle regular entries 
	and check if tradable conditions are met.
	'''

	bank = utils.getTradableBank()
	if bank:
		tp = VARIABLES['tprange'] if entry.entry_type == EntryType.ADDITIONAL else None
		
		if entry.direction == Direction.LONG:
			pos = utils.buy(
				VARIABLES['PRODUCT'], 
				utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
				slRange = VARIABLES['stoprange'],
				tpRange = tp
			)
		else:
			pos = utils.sell(
				VARIABLES['PRODUCT'], 
				utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
				slRange = VARIABLES['stoprange'],
				tpRange = tp
			)

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
	utils.log('checkTime', 'London Time: {0}'.format(london_time))
	if london_time.weekday() == 4 and london_time.hour >= 20:
		utils.log('checkTime', 'is STOP!')
		time_state = TimeState.STOP
	elif london_time.hour == 20 and not london_time.weekday() == 6:
		time_state = TimeState.TWENTY
	else:
		time_state = TimeState.TRADING

def runSequence():

	getPivot()

	if entrySetup(): return

def getPivot():
	_, high, low, close = chart.getCurrentBidOHLC(utils)
	if trigger.pivot.high == 0:
		trigger.pivot.set(high, low, close)

	if trigger.direction == Direction.LONG:
		if trigger.pivot.is_init:
			if high < trigger.pivot.low:
				if not isBB(trigger.direction) and not isInside() and not isDoji():
					trigger.pivot.set(high, low, close)
					trigger.pivot.is_init = False
		else:
			if close <= trigger.pivot.close and low <= trigger.pivot.low:
				if not isBB(trigger.direction) and not isInside() and not isDoji():
					trigger.pivot.set(high, low, close)
	else:
		if trigger.pivot.is_init:
			if low > trigger.pivot.high:
				if not isBB(trigger.direction) and not isInside() and not isDoji():
					trigger.pivot.set(high, low, close)
					trigger.pivot.is_init = False
		else:
			if close >= trigger.pivot.close and high >= trigger.pivot.high:
				if not isBB(trigger.direction) and not isInside() and not isDoji():
					trigger.pivot.set(high, low, close)

def entrySetup():
	if entryConfirmation(trigger.direction):
		trigger.pivot.is_init = True
		return confirmation(trigger, EntryType.REGULAR)

def entryConfirmation(direction):
	if utils.plan_state.value in (4,):
		utils.log('entryConfirmation', 'Entry Conf: {0} {1}'.format(
			exceedsMin(direction),
			time_state.value < TimeState.STOP.value
		))

	return (
		exceedsMin(direction) and
		time_state.value < TimeState.STOP.value
	)

def setOppDirection():
	if trigger.direction == Direction.LONG:
		trigger.setDirection(Direction.SHORT)
	else:
		trigger.setDirection(Direction.LONG)

def exceedsMin(direction):
	close = chart.getCurrentBidOHLC(utils)[3]
	# print('em: {0} {1} {2}'.format(close, trigger.pivot.high, trigger.pivot.low))
	# print(close - trigger.pivot.high)
	# print(trigger.pivot.low - close)
	# print(round(VARIABLES['min_entry'] * 0.0001, 5))
	if direction == Direction.LONG:
		return (close - trigger.pivot.high) > round(VARIABLES['min_entry'] * 0.0001, 5)
	else:
		return (trigger.pivot.low - close) > round(VARIABLES['min_entry'] * 0.0001, 5)

def isBB(direction, reverse=False):
	_open, _, _, close = chart.getCurrentBidOHLC(utils)

	if reverse:
		if direction == Direction.LONG:
			return close < _open
		else:
			return close > _open

	else:
		if direction == Direction.LONG:
			return close > _open
		else:
			return close < _open

def isDoji():
	_open, _, _, close = chart.getCurrentBidOHLC(utils)
	return not utils.convertToPips(abs(round(_open - close, 5))) >= VARIABLES['doji_range']

def isInside():
	bids = chart.getBidOHLC(utils, 0, 2)
	return bids[1][1] < bids[0][1] and bids[1][2] > bids[0][2]

def confirmation(trigger, entry_type, reverse=False):
	''' confirm entry '''

	global pending_entry

	utils.log("confirmation", '{0} {1}'.format(trigger.direction, entry_type))
	pending_entry = Trigger(direction=trigger.direction)
	pending_entry.entry_type = entry_type
	setOppDirection()
	return True

def report():
	''' Prints report for debugging '''
	utils.log('', "\n")

	utils.log('', "T: {0}".format(trigger))

	utils.log('', "CLOSED POSITIONS:")
	count = 0
	for pos in utils.closed_positions:
		count += 1
		utils.log('', "{0}: {1} Profit: {2} | {3}%".format(
			count, pos.direction,
			pos.getPipProfit(), 
			pos.getPercentageProfit()
		))

	utils.log('', "POSITIONS:")
	count = 0
	for pos in utils.positions:
		count += 1
		utils.log('', "{0}: {1} Profit: {2} | {3}%".format(
			count, pos.direction,
			pos.getPipProfit(), 
			pos.getPercentageProfit()
		))

	utils.log('', utils.getTime().strftime('%d/%m/%y %H:%M:%S'))
	utils.log('', "--|\n")
