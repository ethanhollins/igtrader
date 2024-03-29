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
	'macdz_conf': 2,
	'macd_conf': 2,
}

class Direction(Enum):
	LONG = 1
	SHORT = 2

class EntryState(Enum):
	ONE = 1
	TWO = 2
	COMPLETE = 3
	RENTER = 4

class EntryType(Enum):
	REGULAR = 1
	RE_ENTRY = 2

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

	def __init__(self, direction=None):
		self.direction = direction

		self.entry_state = EntryState.ONE
		self.entry_type = None

		self.re_entry = None

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
	
	global rsi, macd, macd_z

	rsi = utils.RSI(10)
	macd = utils.MACD(12, 26, 9)
	macd_z = utils.MACD(4, 40, 3)

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

	time_state = TimeState.STOP

def onNewBar(chart):
	''' Function called on every new bar '''
	if utils.plan_state.value in (4,):
		time = utils.convertTimestampToDatetime(utils.getLatestTimestamp())
		london_time = utils.convertTimezone(time, 'Europe/London')
		utils.log("\nTime", time.strftime('%d/%m/%y %H:%M:%S'))
		utils.log("London Time", london_time.strftime('%d/%m/%y %H:%M:%S') + '\n')
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

def closeAllPositions():
	for pos in utils.positions:
		pos.close()

def onStopLoss(pos):
	utils.log("onStopLoss", '')
	if pos.direction == Constants.BUY:
		trigger.re_entry = Direction.LONG
	else:
		trigger.re_entry = Direction.SHORT

def checkTime():
	''' 
	Checks current time and initiates 
	closing sequence where necessary.
	'''
	global time_state

	time = utils.convertTimestampToDatetime(utils.getLatestTimestamp())
	london_time = utils.convertTimezone(time, 'Europe/London')
	# utils.log('checkTime', 'London Time: {0}'.format(london_time))
	if time_state != TimeState.TRADING and 7 <= london_time.hour <= 23:
		time_state = TimeState.TRADING
		global trigger
		trigger = Trigger()
	elif time_state != TimeState.STOP and 0 <= london_time.hour <= 6:
		utils.log('checkTime', 'is STOP!')
		time_state = TimeState.STOP

def runSequence():

	if utils.plan_state.value in (4,):
		utils.log('OHLC:', chart.getCurrentBidOHLC(utils))
		
		hist = macd.getCurrent(utils, chart)[2]
		histz = macd_z.getCurrent(utils, chart)[2]
		stridx = rsi.getCurrent(utils, chart)

		utils.log('IND', 'MACDH: {} |MACDZ: {} |RSI {}'.format(round(float(hist), 5), round(float(histz), 5), stridx))

	if time_state == TimeState.TRADING:
		if utils.plan_state.value in (4,):
			utils.log('time', 'TRADING')
		getDirection()
		if reEntrySetup(): return
		if entrySetup(): return
	else:
		if utils.plan_state.value in (4,):
			utils.log('time', 'DOWNTIME')
		exitSetup()

def getDirection():

	if trigger.direction == None:
		if isMacdConf(Direction.LONG) and isMacdzZeroConf(Direction.LONG):
			trigger.direction = Direction.LONG
		elif isMacdConf(Direction.SHORT) and isMacdzZeroConf(Direction.SHORT):
			trigger.direction = Direction.SHORT

	elif isMacdConf(trigger.direction, reverse=True) and isMacdzZeroConf(trigger.direction, reverse=True):
		trigger.entry_state = EntryState.ONE
		trigger.setDirection(trigger.direction, reverse=True)
		if trigger.direction != trigger.re_entry:
			trigger.re_entry = None


def entrySetup():

	if trigger.direction:
		if trigger.entry_state == EntryState.ONE:
			if isMacdzZeroConf(trigger.direction, reverse=True):
				trigger.entry_state = EntryState.TWO
				return

		elif trigger.entry_state == EntryState.TWO:
			if entryConfirmation(trigger.direction):
				trigger.entry_state = EntryState.COMPLETE
				trigger.re_entry = None
				return confirmation(trigger, EntryType.REGULAR)

def entryConfirmation(direction):
	if utils.plan_state.value in (4,):
		utils.log('entryConfirmation', 'Entry Conf: {0} {1}'.format(
			isMacdzConf(trigger.direction),
			isRsiConf(trigger.direction)
		))

	return (
		isMacdzConf(trigger.direction) and
		isRsiConf(trigger.direction)
	)

def reEntrySetup():
	if trigger.re_entry != None:
		if isMacdzConf(trigger.re_entry):
			return confirmation(trigger, EntryType.RE_ENTRY)
		elif isMacdConf(trigger.re_entry, reverse=True):
			trigger.re_entry = None

def exitSetup():
	if len(utils.positions) > 0:
		direction = Direction.LONG if utils.positions[0].direction == Constants.BUY else Direction.SHORT

		if isMacdzZeroConf(direction, reverse=True):
			closeAllPositions()

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

def isMacdzConf(direction, reverse=False):
	hist = macd_z.getCurrent(utils, chart)[2]

	if reverse:
		if direction == Direction.LONG:
			return hist < round(-VARIABLES['macdz_conf'] * 0.00001, 5)
		else:
			return hist > round(VARIABLES['macdz_conf'] * 0.00001, 5)
	else:
		if direction == Direction.LONG:
			return hist > round(VARIABLES['macdz_conf'] * 0.00001, 5)
		else:
			return hist < round(-VARIABLES['macdz_conf'] * 0.00001, 5)

def isMacdzPosConf(direction, reverse=False):
	hist = macd_z.getCurrent(utils, chart)[2]

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

def isMacdzZeroConf(direction, reverse=False):
	hist = macd_z.getCurrent(utils, chart)[2]

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

	utils.log("confirmation", '{0} {1}'.format(trigger.direction, entry_type))

	if entry_type == EntryType.REGULAR:
		pending_entry = Trigger(direction=trigger.direction)
	else:
		pending_entry = Trigger(direction=trigger.re_entry)
		
	if isPosInDir(pending_entry.direction):
		pending_entry = None
		return False
		
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
