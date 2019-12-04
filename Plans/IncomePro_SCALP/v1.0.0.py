import Constants
from enum import Enum

VARIABLES = {
	'TIMEZONE': 'America/New_York',
	'PRODUCT': Constants.GBPUSD,
	'BANK': None,
	'risk': 1.0,
	'stoprange': 17.0,
	'MISC': None,
	'RSI': None,
	'rsi_long': 52,
	'rsi_short': 48,
	'MACD': None,
	'macd_conf': 2,
}

class Direction(Enum):
	LONG = 1
	SHORT = 2

class EntryState(Enum):
	ONE = 1
	TWO = 2
	COMPLETE = 3

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

		self.entry_state = EntryState.ONE
		self.entry_type = None

	def setDirection(self, direction, reverse=False):
		if reverse:
			if direction == Direction.LONG:
				self.direction = Direction.SHORT
			else:
				self.direction = Direction.LONG
		else:
			self.direction = direction

	def __getattr__(self, key):
		return self[key]

	def __setattr__(self, key, value):
		self[key] = value

def init(utilities):
	''' Initialize utilities and indicators '''

	setup(utilities)
	
	global rsi, macd

	rsi = utils.RSI(10)
	boll_two = utils.MACD(4, 40, 3)
	sar = utils.SAR(0.017, 0.04)

	setGlobalVars()

def setup(utilities):
	global utils, chart
	utils = utilities
	if len(utils.charts) > 0:
		chart = utils.charts[0]
	else:
		chart = utils.getChart(VARIABLES['PRODUCT'], Constants.ONE_MINUTE)

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

	bank = utils.getTradableBank()
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
	# utils.log('checkTime', 'London Time: {0}'.format(london_time))
	if 7 <= london_time.hour <= 23:
		time_state = TimeState.TRADING
	else:
		utils.log('checkTime', 'is STOP!')
		time_state = TimeState.STOP

def runSequence():

	if entrySetup(): return

def getDirection():
	if sar.isHit():
		trigger.entry_state = EntryState.ONE
		if isMacdPosConf(trigger.direction, reverse=True):
			trigger.setDirection(trigger.direction, reverse=True)


def entrySetup():
	if trigger.entry_state == EntryState.ONE:
		if isMacdZeroConf(trigger.direction, reverse=True):
			trigger.entry_state = EntryState.TWO
			return

	elif trigger.entry_state == EntryState.TWO:
		if entryConfirmation(trigger.direction):

def entryConfirmation(direction):
	if utils.plan_state.value in (4,):
		utils.log('entryConfirmation', 'Entry Conf: {0} {1}'.format(
			isMacdConf(trigger.direction),
			isRsiConf(trigger.direction)
		))

	return (
		isMacdConf(trigger.direction) and
		isRsiConf(trigger.direction)
	)

def isMacdConf(direction, reverse=False):
	hist = macd.getCurrent(utils, chart)[2]

	if reverse:
		if direction == Direction.LONG:
			return hist < round(-VARIABLES['macd_conf'] * 0.00001, 5)
		else:
			return hist > round(VARIABLES['macd_conf'] * 0.00001, 5)
	else:
		if direction == Direction.LONG:
			return hist > round(VARIABLES['macd_conf'] * 0.00001, 5)
		else:
			return hist < round(-VARIABLES['macd_conf'] * 0.00001, 5)

def isMacdPosConf(direction, reverse=False):
	hist = macd.getCurrent(utils, chart)[2]

	if reverse:
		if direction == Direction.LONG:
			return hist < 0
		else:
			return hist > 0
	else:
		if direction == Direction.LONG:
			return hist > 0
		else:
			return hist < 0

def isMacdZeroConf(direction, reverse=False):
	hist = macd.getCurrent(utils, chart)[2]

	if reverse:
		if direction == Direction.LONG:
			return hist <= 0
		else:
			return hist >= 0
	else:
		if direction == Direction.LONG:
			return hist >= 0
		else:
			return hist <= 0

def isRsiConf(direction, reverse=False):
	stridx = rsi.getCurrent(utils, chart)

	if reverse:
		if direction == Direction.LONG:
			return stridx < VARIABLES['rsi_short']
		else:
			return stridx > VARIABLES['rsi_long']
	else:
		if direction == Direction.LONG:
			return stridx > VARIABLES['rsi_long']
		else:
			return stridx < VARIABLES['rsi_short']

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

def confirmation(trigger, entry_type, reverse=False):
	''' confirm entry '''

	global pending_entry

	utils.log("confirmation", '{0} {1}'.format(trigger.direction, entry_type))
	pending_entry = Trigger(direction=trigger.direction)
	pending_entry.entry_type = entry_type
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
