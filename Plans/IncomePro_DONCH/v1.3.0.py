import Constants
from enum import Enum

VARIABLES = {
	'TIMEZONE': 'America/New_York',
	'PRODUCT': Constants.GBPUSD,
	'BANK': None,
	'risk': 1.0,
	'stoprange': 130.0
}

class Direction(Enum):
	LONG = 1
	SHORT = 2

class TimeState(Enum):
	TRADING = 1
	NCT = 2
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

	donch = utils.DONCH(10)
	
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
	utils.log("\nonNewBar",'')
	utils.log('time', utils.getTime().strftime('%d/%m/%y %H:%M:%S'))
	
	# checkTime()

	runSequence()

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
	utils.log('checkTime', 'London Time: {0}'.format(london_time))
	if london_time.weekday() == 4 and london_time.hour >= 20:
		utils.log('checkTime', 'is STOP!')
		time_state = TimeState.STOP
	elif london_time.weekday() == 4 and london_time.hour >= 12:
		utils.log('checkTime', 'is NCT!')
		time_state = TimeState.NCT
	else:
		time_state = TimeState.TRADING

def runSequence():
	entrySetup(long_trigger)
	entrySetup(short_trigger)

def entrySetup(trigger):

	if trigger and not isPositionInDirection(trigger.direction):

		if entryConfirmation(trigger.direction):
			return confirmation(trigger)

def entryConfirmation(direction):
	if utils.plan_state.value in (1,4):
		utils.log('entryConfirmation', 'Entry Conf: {0}'.format(
			isDonchExc(direction, reverse=True)
		))

	return isDonchExc(direction, reverse=True)

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

def confirmation(trigger, reverse=False):
	''' confirm entry '''

	global pending_entry

	utils.log("confirmation", '{0} {1}'.format(trigger.direction, reverse))
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
