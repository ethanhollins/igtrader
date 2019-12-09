import Constants
from enum import Enum

VARIABLES = {
	'TIMEZONE': 'America/New_York',
	'PRODUCT': Constants.GBPUSD,
	'BANK': None,
	'risk': 1.0,
	'stoprange': 17.0,
	'target': 50,
	'max_loss': -34,
	'MISC': None,
	'RSI': None,
	'rsi_long': 52,
	'rsi_short': 48,
	'MACD': None,
	'macd_conf': 2,
	'macdz_conf': 2,
	'macdt_conf': 2
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
	RE_ENTRY = 2

class TimeState(Enum):
	TRADING = 1
	STOP = 2
	EXIT = 3

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
	
	global rsi, macd, macd_z, macd_t

	rsi = utils.RSI(10)
	macd = utils.MACD(12, 26, 9)
	macd_z = utils.MACD(4, 40, 3)
	macd_t = utils.MACD(35, 70, 24)

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
	global pending_entry, time_state

	if pending_entry:
		
		if getCurrentProfit() <= VARIABLES['max_loss']:
			closeAllPositions()
			pending_entry = None
			time_state = TimeState.EXIT
			return

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
	if time_state != TimeState.TRADING and time_state != TimeState.EXIT and 7 <= london_time.hour <= 23:
		time_state = TimeState.TRADING
		utils.positions = []
	elif time_state != TimeState.STOP and 0 <= london_time.hour <= 6:
		time_state = TimeState.STOP

def runSequence():

	if utils.plan_state.value in (4,):
		utils.log('OHLC', chart.getCurrentBidOHLC(utils))
		
		hist = macd.getCurrent(utils, chart)[2]
		histz = macd_z.getCurrent(utils, chart)[2]
		histt = macd_t.getCurrent(utils, chart)[2]
		stridx = rsi.getCurrent(utils, chart)

		utils.log('IND', 'MACDH: {} |MACDZ: {} |MACDT: {} |RSI {}'.format(
			round(float(hist), 5), 
			round(float(histz), 5), 
			round(float(histt), 5),
			stridx)
		)

	global time_state
	if time_state == TimeState.TRADING and isTakeProfit():
		time_state = TimeState.EXIT

	if time_state == TimeState.TRADING:
		getDirection()
		if reEntrySetup(): return
		if entrySetup(): return

	elif time_state == TimeState.STOP or time_state == TimeState.EXIT:
		getDirection()
		entrySetup()
		exitSetup()

def getCurrentProfit():
	profit = 0
	for pos in utils.closed_positions:
		profit += pos.getPipProfit()
	
	close = chart.getCurrentBidOHLC(utils)[3]
	for pos in utils.positions:
		if pos.direction == Constants.BUY:
			profit += utils.convertToPips(close - pos.entryprice)
		else:
			profit += utils.convertToPips(pos.entryprice - close)
	return profit

def isTakeProfit():
	profit = 0
	for pos in utils.closed_positions:
		profit += pos.getPipProfit()

	_, high, low, _ = chart.getCurrentBidOHLC(utils)

	for pos in utils.positions:
		if pos.direction == Constants.BUY:
			profit += utils.convertToPips(high - pos.entryprice)
		else:
			profit += utils.convertToPips(pos.entryprice - low)
	
	return profit >= VARIABLES['target']

def getDirection():

	if trigger.direction == None:
		if isDirectionConf(Direction.LONG):
			trigger.direction = Direction.LONG
			trigger.entry_state = EntryState.ONE
		elif isDirectionConf(Direction.SHORT):
			trigger.direction = Direction.SHORT
			trigger.entry_state = EntryState.ONE

	elif isDirectionConf(trigger.direction, reverse=True):
		trigger.entry_state = EntryState.ONE
		trigger.setDirection(trigger.direction, reverse=True)
		if trigger.direction != trigger.re_entry:
			trigger.re_entry = None

def isDirectionConf(direction, reverse=False):
	return (
		isMacdzPosConf(direction, reverse=reverse) and
		isMacdPosConf(direction, reverse=reverse) and
		isMacdtConf(direction, reverse=reverse)
	)

def entrySetup():

	if trigger.direction:
		if isMacdtPosConf(trigger.direction, reverse=True):
			trigger.direction = None
			return True

		if trigger.entry_state == EntryState.ONE:
			if isMacdzPosConf(trigger.direction, reverse=True):
				trigger.entry_state = EntryState.TWO
				return False

		elif trigger.entry_state == EntryState.TWO:
			if entryConfirmation(trigger.direction):
				trigger.entry_state = EntryState.COMPLETE
				trigger.re_entry = None
				return confirmation(trigger, EntryType.REGULAR)

def entryConfirmation(direction):
	if utils.plan_state.value in (4,):
		utils.log('entryConfirmation', 'Entry Conf: {0} {1} {2} {3}'.format(
			isMacdzPosConf(trigger.direction),
			(isMacdzConf(trigger.direction) 
				or isMacdConf(trigger.direction)),
			not isMacdConf(trigger.direction, reverse=True),
			isRsiConf(trigger.direction)
		))

	return (
		isMacdzPosConf(trigger.direction) and
		(isMacdzConf(trigger.direction) 
			or isMacdConf(trigger.direction)) and
		not isMacdConf(trigger.direction, reverse=True) and
		isRsiConf(trigger.direction)
	)

def reEntrySetup():
	if trigger.re_entry != None:
		if isMacdzPosConf(trigger.re_entry):
			return confirmation(trigger, EntryType.RE_ENTRY)

def exitSetup():
	if len(utils.positions) > 0:
		direction = Direction.LONG if utils.positions[0].direction == Constants.BUY else Direction.SHORT

		if isMacdzZeroConf(direction, reverse=True):
			closeAllPositions()

def isMacdConf(direction, reverse=False):
	hist = round(float(macd.getCurrent(utils, chart)[2]), 5)

	if reverse:
		if direction == Direction.LONG:
			return hist <= round(-VARIABLES['macd_conf'] * 0.00001, 5)
		else:
			return hist >= round(VARIABLES['macd_conf'] * 0.00001, 5)
	else:
		if direction == Direction.LONG:
			return hist >= round(VARIABLES['macd_conf'] * 0.00001, 5)
		else:
			return hist <= round(-VARIABLES['macd_conf'] * 0.00001, 5)

def isMacdPosConf(direction, reverse=False):
	hist = round(float(macd.getCurrent(utils, chart)[2]), 5)

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

def isMacdzConf(direction, reverse=False):
	hist = round(float(macd_z.getCurrent(utils, chart)[2]), 5)

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
	hist = round(float(macd_z.getCurrent(utils, chart)[2]), 5)

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
	hist = round(float(macd_z.getCurrent(utils, chart)[2]), 5)

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

def isMacdtConf(direction, reverse=False):
	hist = round(float(macd_t.getCurrent(utils, chart)[2]), 5)

	if reverse:
		if direction == Direction.LONG:
			return hist < round(-VARIABLES['macdt_conf'] * 0.00001, 5)
		else:
			return hist > round(VARIABLES['macdt_conf'] * 0.00001, 5)
	else:
		if direction == Direction.LONG:
			return hist > round(VARIABLES['macdt_conf'] * 0.00001, 5)
		else:
			return hist < round(-VARIABLES['macdt_conf'] * 0.00001, 5)

def isMacdtPosConf(direction, reverse=False):
	hist = round(float(macd_t.getCurrent(utils, chart)[2]), 5)

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

def isRsiConf(direction, reverse=False):
	stridx = round(float(rsi.getCurrent(utils, chart)), 2)

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


	if entry_type == EntryType.REGULAR:
		pending_entry = Trigger(direction=trigger.direction)
	else:
		pending_entry = Trigger(direction=trigger.re_entry)
		
	if time_state == TimeState.STOP or time_state == TimeState.EXIT or isPosInDir(pending_entry.direction):
		pending_entry = None
		return False
		
	utils.log("confirmation", '{0} {1}'.format(trigger.direction, entry_type))
	pending_entry.entry_type = entry_type
	return True

def report():
	''' Prints report for debugging '''
	utils.log('', "\n")

	utils.log('', "Time State: {}".format(time_state))
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
