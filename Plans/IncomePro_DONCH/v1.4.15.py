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
	'donch': 4
}

class Direction(Enum):
	LONG = 1
	SHORT = 2

class EntryState(Enum):
	ONE = 1
	TWO = 2
	COMPLETE = 3

class AdEntryState(Enum):
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

class Trigger(dict):
	static_count = 0

	def __init__(self, direction):
		self.direction = direction
		
		self.entry_state = EntryState.ONE
		self.ad_entry_state = AdEntryState.ONE
		self.ad_entry_line = 0

		self.entry_type = None

		self.count = Trigger.static_count
		Trigger.static_count += 1

	def __getattr__(self, key):
		return self[key]

	def __setattr__(self, key, value):
		self[key] = value

def init(utilities):
	''' Initialize utilities and indicators '''

	setup(utilities)

	global donch

	donch = utils.DONCH(VARIABLES['donch'])
	
	setGlobalVars()

def setup(utilities):
	global utils, chart
	utils = utilities
	if len(utils.charts) > 0:
		chart = utils.charts[0]
	else:
		chart = utils.getChart(VARIABLES['PRODUCT'], Constants.FOUR_HOURS)

def setGlobalVars():
	global long_trigger, short_trigger
	global pending_entry, pending_breakevens, pending_exits
	global time_state

	long_trigger = Trigger(Direction.LONG)
	short_trigger = Trigger(Direction.SHORT)

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
		utils.log('checkTime', 'is TWENTY!')
		time_state = TimeState.TWENTY
	else:
		time_state = TimeState.TRADING

def runSequence():

	if time_state != TimeState.STOP:
		if entrySetup(long_trigger): return
		if entrySetup(short_trigger): return
		adEntrySetup(long_trigger)
		adEntrySetup(short_trigger)

def entrySetup(trigger):

	if trigger and not isPositionInDirection(trigger.direction):

		if trigger.entry_state == EntryState.ONE:
			if isDonchRet(trigger.direction, reverse=True):
				trigger.entry_state = EntryState.TWO
				return entrySetup(trigger)

		if trigger.entry_state == EntryState.TWO:
			if entryConfirmation(trigger.direction):
				return confirmation(trigger, EntryType.REGULAR)

def entryConfirmation(direction):
	if utils.plan_state.value in (4,):
		utils.log('entryConfirmation', 'Entry Conf: {0}'.format(
			isDonchExc(direction)
		))

	return (
		isDonchExc(direction)
	)

def adEntrySetup(trigger):

	if trigger and isPositionInDirection(trigger.direction):

		if trigger.ad_entry_state == AdEntryState.ONE:
			trigger.ad_entry_line = 0
			if isBB(trigger.direction, reverse=True) and not isDoji():
				trigger.ad_entry_line = getAdEntryLine(trigger)
				trigger.ad_entry_state = AdEntryState.TWO
				return

		elif trigger.ad_entry_state == AdEntryState.TWO:
			if adEntryConfirmation(trigger):
				trigger.ad_entry_state = AdEntryState.COMPLETE
				return confirmation(trigger, EntryType.ADDITIONAL)

def getAdEntryLine(trigger):
	_, high, low, _ = chart.getCurrentBidOHLC(utils)

	if trigger.direction == Direction.LONG:
		return high if not trigger.ad_entry_line or high < trigger.ad_entry_line else trigger.ad_entry_line
	else:
		return low if not trigger.ad_entry_line or low > trigger.ad_entry_line else trigger.ad_entry_line

def adEntryConfirmation(trigger):
	close = chart.getCurrentBidOHLC(utils)[3]

	if trigger.direction == Direction.LONG:
		if close > trigger.ad_entry_line and time_state.value == TimeState.TRADING.value:
			return True
	else:
		if close < trigger.ad_entry_line and time_state.value == TimeState.TRADING.value:
			return True

	trigger.ad_entry_line = getAdEntryLine(trigger)
	return False	

def resetOppositeTrigger(trigger):
	if trigger.entry_type == EntryType.REGULAR:
		short_trigger.entry_state = EntryState.ONE
		long_trigger.entry_state = EntryState.ONE
		short_trigger.ad_entry_state = AdEntryState.ONE
		long_trigger.ad_entry_state = AdEntryState.ONE

def isDonchRet(direction, reverse=False):
	vals = donch.get(utils, chart, 0, 2)
	if reverse:
		if direction == Direction.LONG:
			return vals[1][1] > vals[0][1]
		else:
			return vals[1][0] < vals[0][0]
	else:
		if direction == Direction.LONG:
			return vals[1][0] < vals[0][0]
		else:
			return vals[1][1] > vals[0][1]

def isDonchExc(direction, reverse=False):
	vals = donch.get(utils, chart, 0, 2)

	if reverse:
		if direction == Direction.LONG:
			return vals[1][1] < vals[0][1]
		else:
			return vals[1][0] > vals[0][0]
	else:
		if direction == Direction.LONG:
			return vals[1][0] > vals[0][0]
		else:
			return vals[1][1] < vals[0][1]

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

def isPositionInDirection(direction, reverse=False):
	for pos in utils.positions:
	
		if reverse:
			if pos.direction == Constants.BUY and direction == Direction.SHORT:
				return True
			elif pos.direction == Constants.SELL and direction == Direction.LONG:
				return True
		else:
			if pos.direction == Constants.BUY and direction == Direction.LONG:
				return True
			elif pos.direction == Constants.SELL and direction == Direction.SHORT:
				return True

def confirmation(trigger, entry_type, reverse=False):
	''' confirm entry '''

	global pending_entry

	utils.log("confirmation", '{0} {1}'.format(trigger.direction, reverse))
	trigger.entry_type = entry_type
	resetOppositeTrigger(trigger)
	pending_entry = trigger
	return True

def report():
	''' Prints report for debugging '''
	utils.log('', "\n")

	utils.log('', "L: {0}".format(long_trigger))
	utils.log('', "S: {0}".format(short_trigger))

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
