import Constants
from enum import Enum

VARIABLES = {
	'TIMEZONE': 'America/New_York',
	'PRODUCT': Constants.GBPUSD,
	'BANK': None,
	'risk': 1.0,
	'stoprange': 130,
	'RSI': None,
	'rsi_long': 52,
	'rsi_short': 48,
	'MACD': None,
	'macd_main': 18,
	'macd_reverse': 10,
	'MISC': None,
	'doji_range': 1,
	'pos_layoff_count': 3,
	'pos_layoff_profit': 80,
}

class Direction(Enum):
	LONG = 1
	SHORT = 2

class PreTEntryState(Enum):
	ONE = 1
	TWO = 2
	THREE = 3
	CONFIRMED = 4
	RESET = 5
	REVERSE = 6
	REVERT = 7
	COMPLETE = 8

class TEntryState(Enum):
	ONE = 1
	WAIT = 2
	COMPLETE = 3

class AdEntryOneState(Enum):
	ONE = 1
	TWO = 2
	THREE = 3
	COMPLETE = 4

class AdEntryTwoState(Enum):
	ONE = 1
	TWO = 2
	COMPLETE = 3

class EntryType(Enum):
	PreTEntry = 1
	TEntry = 2
	AdOneEntry = 3
	AdTwoEntry = 4

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
		
		self.pre_t_entry_state = PreTEntryState.ONE
		self.t_entry_state = TEntryState.ONE
		self.ad_entry_one_state = AdEntryOneState.ONE
		self.ad_entry_two_state = AdEntryTwoState.ONE
 
		self.entry_type = None
		self.can_so_reenter = True

		self.count = Trigger.static_count
		Trigger.static_count += 1

	def __getattr__(self, key):
		return self[key]

	def __setattr__(self, key, value):
		self[key] = value

def init(utilities):
	''' Initialize utilities and indicators '''

	setup(utilities)

	global sma, limit_one, limit_two, limit_three, boll_one, boll_two, rsi, macd, macd, kelt_ch, kelt_mae

	sma = utils.SMA(10)
	limit_one = utils.MAE(10, 0.2)
	limit_two = utils.MAE(10, 0.25)
	limit_three = utils.MAE(10, 0.09)
	boll_one = utils.BOLL(10, 2.2)
	boll_two = utils.BOLL(20, 1.9)
	rsi = utils.RSI(10)
	macd = utils.MACD(4, 40, 3)
	kelt_ch = utils.KELT(20, 20, 1.5)
	kelt_mae = utils.MAE(20, 0.02, ma_type='typ')
	
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
	global c_direction
	global pending_entry, pending_breakevens, pending_exits
	global istemp
	global time_state, stop_state

	long_trigger = Trigger(Direction.LONG)
	short_trigger = Trigger(Direction.SHORT)
	c_direction = None

	pending_entry = None
	pending_breakevens = []
	pending_exits = []

	istemp = False

	time_state = TimeState.TRADING

def onNewBar(chart):
	''' Function called on every new bar '''
	utils.log("\nonNewBar",'')
	utils.log('time', utils.getTime().strftime('%d/%m/%y %H:%M:%S'))
	
	checkTime()

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

	bank = utils.getBankSize() + utils.external_bank
	if bank > utils.maximum_bank:
		bank = utils.maximum_bank

	if utils.getBankSize() <= utils.minimum_bank:
		utils.log('', 'Bank is below minimum {0:.2f}'.format(utils.minimum_bank))
		return

	pos = utils.stopAndReverse(
		VARIABLES['PRODUCT'], 
		utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
		slRange = VARIABLES['stoprange']
	)

	pos.data = {
		'idx': len(utils.positions),
		'type': entry.entry_type.value,
	}

	if entry.entry_type == EntryType.AdTwoEntry:
		pos.data['boll_ret'] = False

def handleRegularEntry(entry):
	''' 
	Handle regular entries 
	and check if tradable conditions are met.
	'''

	bank = utils.getBankSize() + utils.external_bank
	if bank > utils.maximum_bank:
		bank = utils.maximum_bank

	if utils.getBankSize() <= utils.minimum_bank:
		utils.log('', 'Bank is below minimum {0:.2f}'.format(utils.minimum_bank))
		return

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
	
	# if not pos:
	# 	utils.setStopped()
	# 	print('SOMETHING WENT WRONG WITH POSITION ENTRY!')
	# 	return
	pos.data = {
		'idx': len(utils.positions),
		'type': entry.entry_type.value,
	}

	if entry.entry_type == EntryType.AdTwoEntry:
		pos.data['boll_ret'] = False

def onStopLoss(pos):
	utils.log("onStopLoss", '')

	if pos.data['type'] == EntryType.AdTwoEntry.value:
		if pos.direction == Constants.BUY:
			if (not pos.data['boll_ret'] and
					long_trigger.can_so_reenter):
				long_trigger.ad_entry_two_state = AdEntryTwoState.TWO
				long_trigger.can_so_reenter = False
		else:
			if (not pos.data['boll_ret'] and
					short_trigger.can_so_reenter):
				short_trigger.ad_entry_two_state = AdEntryTwoState.TWO
				short_trigger.can_so_reenter = False

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
	''' Main trade plan sequence '''
	utils.log(
		'runSequence',
		"\n OHLC: {0} SMA: {1} L_ONE: {2} L_TWO: {3}\n L_THREE: {4} B_ONE: {5} B_TWO: {6}\n MACD: {7} KELT_CH: {8} KELT_MAE: {9}".format(
			chart.getCurrentBidOHLC(utils), sma.getCurrent(utils, chart), limit_one.getCurrent(utils, chart),
			limit_two.getCurrent(utils, chart), limit_three.getCurrent(utils, chart),
			boll_one.getCurrent(utils, chart), boll_two.getCurrent(utils, chart),
			macd.getCurrent(utils, chart), kelt_ch.getCurrent(utils, chart),
			kelt_mae.getCurrent(utils, chart)
	))

	if time_state == TimeState.STOP:
		return

	# checkOutsideKelt()

	global istemp
	blocked = False
	reloop = False
	if c_direction == Direction.LONG:
		if isPreEntryConfirmed(c_direction, reverse=True):
			if adEntryTwo(long_trigger): blocked = True
		if isPreEntryConfirmed(c_direction, reverse=True):
			if adEntryOne(long_trigger, blocked): blocked = True

		t_entry_result = tEntrySetup(short_trigger, blocked)
		if t_entry_result == 'c_dir':
			reloop = True
			istemp = True
		elif t_entry_result: blocked = True

		if istemp:
			tEntrySetup(long_trigger, blocked)
			preEntrySetup(long_trigger, blocked)

		if isPreEntryConfirmed(c_direction, reverse=True):
			if (not checkTag(long_trigger.direction) and
					not checkBoll(long_trigger.direction)):
				preEntrySetup(short_trigger, blocked)
		else:
			preEntrySetup(short_trigger, blocked)

	elif c_direction == Direction.SHORT:
		if isPreEntryConfirmed(c_direction, reverse=True):
			if adEntryTwo(short_trigger): blocked = True
		if isPreEntryConfirmed(c_direction, reverse=True):
			if adEntryOne(short_trigger, blocked): blocked = True

		t_entry_result = tEntrySetup(long_trigger, blocked)
		if t_entry_result == 'c_dir': 
			reloop = True
			istemp = True
		elif t_entry_result: blocked = True

		if istemp:
			tEntrySetup(short_trigger, blocked)
			preEntrySetup(short_trigger, blocked)

		if isPreEntryConfirmed(c_direction, reverse=True):
			if (not checkTag(short_trigger.direction) and
					not checkBoll(short_trigger.direction)):
				preEntrySetup(long_trigger, blocked)
		else:
			preEntrySetup(long_trigger, blocked)

	else:
		tEntrySetup(long_trigger)
		tEntrySetup(short_trigger)

		preEntrySetup(long_trigger)
		preEntrySetup(short_trigger)

	if reloop:
		return runSequence()

def preEntrySetup(trigger, blocked=False):

	if trigger and (c_direction != trigger.direction or istemp) and not blocked:

		if trigger.pre_t_entry_state == PreTEntryState.ONE:
			if isRetHitKSma(trigger.direction):
				trigger.pre_t_entry_state = PreTEntryState.TWO
				return preEntrySetup(trigger, blocked)

		elif trigger.pre_t_entry_state == PreTEntryState.TWO:
			if not isKeltOutside() and preEntryConfirmation(trigger.direction):
				if istemp:
					trigger.pre_t_entry_state = PreTEntryState.ONE
					setCDirection(trigger.direction)
				else:
					trigger.pre_t_entry_state = PreTEntryState.REVERSE

				if trigger.direction == Direction.LONG:
					short_trigger.ad_entry_one_state = AdEntryOneState.ONE
					short_trigger.ad_entry_two_state = AdEntryTwoState.ONE
				else:
					long_trigger.ad_entry_one_state = AdEntryOneState.ONE
					long_trigger.ad_entry_two_state = AdEntryTwoState.ONE

				return confirmation(trigger, EntryType.PreTEntry)

		elif trigger.pre_t_entry_state == PreTEntryState.REVERSE:
			if isCloseABKeltOut(trigger.direction) or isBollInterupt(trigger.direction, reverse=True):
				trigger.pre_t_entry_state = PreTEntryState.ONE
				setCDirection(trigger.direction)
				return

			elif preEntryReverseConfirmation(trigger.direction):
				trigger.pre_t_entry_state = PreTEntryState.REVERT
				
				return confirmation(trigger, EntryType.PreTEntry, reverse=True)

		elif trigger.pre_t_entry_state == PreTEntryState.REVERT:
			if isCloseABKeltOut(trigger.direction, reverse=True) or isBollInterupt(trigger.direction):
				trigger.pre_t_entry_state = PreTEntryState.ONE
				setCDirection(trigger.direction, reverse=True)
				return

			elif preEntryReverseConfirmation(trigger.direction, reverse=True):
				trigger.pre_t_entry_state = PreTEntryState.REVERSE
				
				return confirmation(trigger, EntryType.PreTEntry)

def preEntryConfirmation(direction):
	utils.log('preEntryConfirmation', 'Pre T-Entry Conf: {0} {1} {2} {3} {4} {5}'.format(
		isWithinKMae(direction), isWithinCtKelt(direction),
		isMacdzDirConf(direction), isRsiDirConf(direction),
		isBB(direction), not isDoji()
	))

	return (
		isWithinKMae(direction) and
		isWithinCtKelt(direction) and
		isMacdzDirConf(direction) and
		isRsiDirConf(direction) and
		isBB(direction) and
		not isDoji()
	)

def preEntryReverseConfirmation(direction, reverse=False):
	utils.log('preEntryReverseConfirmation', 'Pre T-Entry Reverse Conf: {0} ({1} or {2}) {3} {4}'.format(
		isCloseABSma(direction, reverse=not reverse),
		isCloseABLThreeOut(direction, reverse=not reverse),
		isCloseABKSma(direction, reverse=not reverse),
		isBB(direction, reverse=not reverse), not isDoji()
	))

	return (
		isCloseABSma(direction, reverse=not reverse) and
		(isCloseABLThreeOut(direction, reverse=not reverse) or
			isCloseABKSma(direction, reverse=not reverse)) and
		isBB(direction, reverse=not reverse) and
		not isDoji()
	)

def isPreEntryConfirmed(direction, reverse=False):
	if reverse:
		if direction == Direction.LONG:
			return short_trigger.pre_t_entry_state.value < PreTEntryState.REVERSE.value
		else:
			return long_trigger.pre_t_entry_state.value < PreTEntryState.REVERSE.value
	else:
		if direction == Direction.LONG:
			return long_trigger.pre_t_entry_state.value < PreTEntryState.REVERSE.value
		else:
			return short_trigger.pre_t_entry_state.value < PreTEntryState.REVERSE.value



def tEntrySetup(trigger, blocked=False):

	if trigger:

		if trigger.t_entry_state == TEntryState.ONE:
			if isCloseABKeltOut(trigger.direction):
				if isBollInterupt(trigger.direction) and isPreEntryConfirmed(trigger.direction):
					exitExceptBoll(trigger.direction)
					trigger.t_entry_state = TEntryState.WAIT
					return
				else:
					blocked = False

				if (c_direction != trigger.direction or istemp) and tEntryConfimation(trigger.direction):
					if not blocked:
						trigger.t_entry_state = TEntryState.COMPLETE
						confirmation(trigger, EntryType.TEntry)
						setCDirection(trigger.direction)
						return True
			elif (c_direction == trigger.direction and istemp) and isCloseABLTwoOut(trigger.direction):
				if not blocked and tEntryConfimation(trigger.direction):
					trigger.t_entry_state = TEntryState.COMPLETE
					confirmation(trigger, EntryType.TEntry)
					setCDirection(trigger.direction)
					return True
				
		elif trigger.t_entry_state == TEntryState.WAIT:
			if isRetHitCtLTwo(trigger.direction):
				trigger.t_entry_state = TEntryState.ONE
				return setCDirection(trigger.direction)

def tEntryConfimation(direction):
	utils.log('tEntryConfimation', 'T-Entry Conf: {0} {1} {2} {3}'.format(
		isMacdzDirConf(direction), isRsiDirConf(direction),
		isBB(direction), not isDoji()
	))

	return (
		isMacdzDirConf(direction) and
		isRsiDirConf(direction) and
		isBB(direction) and
		not isDoji()
	)

def isBollInterupt(direction, reverse=False):

	return (
		isHitBollOne(direction, reverse=reverse) and 
		isHitBollTwo(direction, reverse=reverse)
	)

def isBollRet(direction):

	if direction == Direction.LONG:
		return not short_trigger.ad_entry_two_state == AdEntryTwoState.COMPLETE

	else:
		return not long_trigger.ad_entry_two_state == AdEntryTwoState.COMPLETE

def setPosBollRet():
	for pos in utils.positions:
		if 'boll_ret' in pos.data:
			pos.data['boll_ret'] = True

def exitExceptBoll(direction):
	for i in range(len(utils.positions) - 1, -1, -1):
		pos = utils.positions[i]
		if 'boll_ret' in pos.data and pos.data['boll_ret']:
			continue
		elif pos.getPipProfit() > 0:
			pos.close()

def setCDirection(direction, reverse=False):
	global c_direction
	
	if direction != c_direction:
		setPosBollRet()
		long_trigger.can_so_reenter = True
		short_trigger.can_so_reenter = True
		if reverse:
			if direction == Direction.LONG:
				c_direction = Direction.SHORT
				long_trigger.pre_t_entry_state = PreTEntryState.ONE
				long_trigger.t_entry_state = TEntryState.ONE
				short_trigger.ad_entry_one_state = AdEntryOneState.TWO
				short_trigger.ad_entry_two_state = AdEntryTwoState.TWO
			else:
				c_direction = Direction.LONG
				short_trigger.pre_t_entry_state = PreTEntryState.ONE
				short_trigger.t_entry_state = TEntryState.ONE
				long_trigger.ad_entry_one_state = AdEntryOneState.TWO
				long_trigger.ad_entry_two_state = AdEntryTwoState.TWO
		else:	
			if direction == Direction.LONG:
				c_direction = Direction.LONG
				short_trigger.pre_t_entry_state = PreTEntryState.ONE
				short_trigger.t_entry_state = TEntryState.ONE
				long_trigger.ad_entry_one_state = AdEntryOneState.TWO
				long_trigger.ad_entry_two_state = AdEntryTwoState.TWO
			else:
				c_direction = Direction.SHORT
				long_trigger.pre_t_entry_state = PreTEntryState.ONE
				long_trigger.t_entry_state = TEntryState.ONE
				short_trigger.ad_entry_one_state = AdEntryOneState.TWO
				short_trigger.ad_entry_two_state = AdEntryTwoState.TWO

	return 'c_dir'

def adEntryOne(trigger, blocked=False):

	if trigger and c_direction == trigger.direction and not blocked:
		if trigger.ad_entry_one_state == AdEntryOneState.ONE:
			if (
				isRetHitKelt(trigger.direction) or 
				isRetHitLThree(trigger.direction)
			):
				trigger.ad_entry_one_state = AdEntryOneState.TWO
				return

		elif trigger.ad_entry_one_state == AdEntryOneState.TWO:
			if isCloseABKSma(trigger.direction, reverse=True):
				trigger.ad_entry_one_state = AdEntryOneState.THREE
				return

		elif trigger.ad_entry_one_state == AdEntryOneState.THREE:
			if adEntryOneConfirmation(trigger.direction) and not isKeltOutside():
				trigger.ad_entry_one_state = AdEntryOneState.ONE
				trigger.ad_entry_two_state = AdEntryTwoState.ONE

				resetPreEntry(trigger.direction, reverse=True)
				confirmation(trigger, EntryType.AdOneEntry)
				return True

		if isCloseABLOneOut(trigger.direction):
			trigger.ad_entry_one_state = AdEntryOneState.TWO
			return

def adEntryOneConfirmation(direction):
	utils.log('adEntryOneConfirmation', 'Ad Entry One Conf: {0} {1} {2}'.format(
		isCloseABLOneIn(direction, reverse=True),
		isBB(direction), not isDoji()
	))

	return (
		isCloseABLOneIn(direction, reverse=True) and
		isBB(direction) and
		not isDoji()
	)

def adEntryTwo(trigger):

	if trigger and c_direction == trigger.direction:

		if trigger.ad_entry_two_state == AdEntryTwoState.ONE:
			if (
				isRetHitKelt(trigger.direction) or 
				isRetHitLThree(trigger.direction)
			):
				trigger.ad_entry_two_state = AdEntryTwoState.TWO
				return adEntryTwo(trigger)

		elif trigger.ad_entry_two_state == AdEntryTwoState.TWO:
			if adEntryTwoConfirmation(trigger.direction):

				trigger.ad_entry_two_state = AdEntryTwoState.COMPLETE
				trigger.ad_entry_one_state = AdEntryOneState.ONE

				resetPreEntry(trigger.direction, reverse=True)
				confirmation(trigger, EntryType.AdTwoEntry)
				return True

		elif trigger.ad_entry_two_state == AdEntryTwoState.COMPLETE:
			if isRetHitCtLTwo(trigger.direction, reverse=True):
				trigger.ad_entry_two_state = AdEntryTwoState.ONE
				return adEntryTwo(trigger)

def adEntryTwoConfirmation(direction):
	utils.log('adEntryTwoConfirmation', 'Ad Entry Two Conf: {0} {1}'.format(
		isBollConfirmation(direction),
		isCloseABLThreeOut(direction, reverse=True)
	))

	return (
		isBollConfirmation(direction) and
		isCloseABLThreeOut(direction, reverse=True)
	)

def isBollConfirmation(direction):


	if (isHitBollOne(direction, reverse=True) and 
		isHitBollTwo(direction, reverse=True)):
		return True

	elif isCloseABBollTwo(direction, reverse=True):
		return True

	elif isCloseABBollOne(direction, reverse=True):
		return time_state.value < TimeState.NCT.value

	return False

def checkTag(direction): 
	if isRetHitKelt(direction):
		resetPreEntry(direction)

		# for pos in utils.positions:
		# 	if (
		# 		'idx' in pos.data and 
		# 		(pos.data['idx'] >= VARIABLES['pos_layoff_count'] or
		# 			pos.data['type'] == EntryType.AdTwoEntry.value) and
		# 		abs(pos.entryprice - chart.getCurrentBidOHLC(utils)[3]) >= VARIABLES['pos_layoff_profit']
		# 	):
		# 		pos.close()
		return True

	return False

def checkBoll(direction):
	if isBollConfirmation(direction):
		resetPreEntry(direction)
		return True
	return False

def checkOutsideKelt():
	if isKeltOutside():
		if long_trigger.pre_t_entry_state.value < PreTEntryState.REVERSE.value:
			long_trigger.pre_t_entry_state = PreTEntryState.ONE
		long_trigger.ad_entry_one_state = AdEntryOneState.ONE

		if short_trigger.pre_t_entry_state.value < PreTEntryState.REVERSE.value:
			short_trigger.pre_t_entry_state = PreTEntryState.ONE
		short_trigger.ad_entry_one_state = AdEntryOneState.ONE

def resetPreEntry(direction, reverse=True):
	if reverse:
		if direction == Direction.LONG:
			short_trigger.pre_t_entry_state = PreTEntryState.ONE
		else:
			long_trigger.pre_t_entry_state = PreTEntryState.ONE
	else:
		if direction == Direction.LONG:
			long_trigger.pre_t_entry_state = PreTEntryState.ONE
		else:
			short_trigger.pre_t_entry_state = PreTEntryState.ONE

def isRsiDirConf(direction, reverse=False):
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

def isRsiPosConf(direction, reverse=False):
	stridx = rsi.getCurrent(utils, chart)

	if reverse:
		if direction == Direction.LONG:
			return stridx < 50
		else:
			return stridx > 50
	else:
		if direction == Direction.LONG:
			return stridx > 50
		else:
			return stridx < 50

def isPriorRsiConf(direction, reverse=False):
	stridx = rsi.get(chart, 1, 1)[0]

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

def isMacdzDirConf(direction, reverse=False):
	hist = macd.getCurrent(utils, chart)[2]

	if reverse:
		if direction == Direction.LONG:
			return hist < round(-VARIABLES['macd_main'] * 0.00001, 5)
		else:
			return hist > round(VARIABLES['macd_main'] * 0.00001, 5)
	else:
		if direction == Direction.LONG:
			return hist > round(VARIABLES['macd_main'] * 0.00001, 5)
		else:
			return hist < round(-VARIABLES['macd_main'] * 0.00001, 5)

def isMacdzReverseConf(direction, reverse=False):
	hist = macd.getCurrent(utils, chart)[2]

	if reverse:
		if direction == Direction.LONG:
			return hist < round(-VARIABLES['macd_reverse'] * 0.00001, 5)
		else:
			return hist > round(VARIABLES['macd_reverse'] * 0.00001, 5)
	else:
		if direction == Direction.LONG:
			return hist > round(VARIABLES['macd_reverse'] * 0.00001, 5)
		else:
			return hist < round(-VARIABLES['macd_reverse'] * 0.00001, 5)

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

def isCloseABSma(direction, reverse=False):
	val = sma.getCurrent(utils, chart)
	close = chart.getCurrentBidOHLC(utils)[3]

	if reverse:
		if direction == Direction.LONG:
			return close < val
		else:
			return close > val
	else:
		if direction == Direction.LONG:
			return close > val
		else:
			return close < val

def isCloseABKSma(direction, reverse=False):
	_, val, _ = kelt_ch.getCurrent(utils, chart)
	close = chart.getCurrentBidOHLC(utils)[3]

	if reverse:
		if direction == Direction.LONG:
			return close < val
		else:
			return close > val
	else:
		if direction == Direction.LONG:
			return close > val
		else:
			return close < val

def isCloseABKeltOut(direction, reverse=False):
	upper, _, lower = kelt_ch.getCurrent(utils, chart)
	close = chart.getCurrentBidOHLC(utils)[3]

	if reverse:
		if direction == Direction.LONG:
			return close < lower
		else:
			return close > upper
	else:
		if direction == Direction.LONG:
			return close > upper
		else:
			return close < lower

def isCloseABLThreeOut(direction, reverse=False):
	upper, lower = limit_three.getCurrent(utils, chart)
	close = chart.getCurrentBidOHLC(utils)[3]

	if reverse:
		if direction == Direction.LONG:
			return close < lower
		else:
			return close > upper
	else:
		if direction == Direction.LONG:
			return close > upper
		else:
			return close < lower

def isCloseABLTwoOut(direction, reverse=False):
	upper, lower = limit_two.getCurrent(utils, chart)
	close = chart.getCurrentBidOHLC(utils)[3]

	if reverse:
		if direction == Direction.LONG:
			return close < lower
		else:
			return close > upper
	else:
		if direction == Direction.LONG:
			return close > upper
		else:
			return close < lower

def isCloseABLOneOut(direction, reverse=False):
	upper, lower = limit_one.getCurrent(utils, chart)
	close = chart.getCurrentBidOHLC(utils)[3]

	if reverse:
		if direction == Direction.LONG:
			return close < lower
		else:
			return close > upper
	else:
		if direction == Direction.LONG:
			return close > upper
		else:
			return close < lower

def isCloseABLOneIn(direction, reverse=False):
	upper, lower = limit_one.getCurrent(utils, chart)
	close = chart.getCurrentBidOHLC(utils)[3]
	if reverse:
		if direction == Direction.LONG:
			return close < upper
		else:
			return close > lower
	else:
		if direction == Direction.LONG:
			return close > lower
		else:
			return close < upper

def isWithinCtLOne(direction, reverse=False):
	upper, lower = limit_one.getCurrent(utils, chart)
	_, high, low, _ = chart.getCurrentBidOHLC(utils)

	if reverse:
		if direction == Direction.LONG:
			return high < upper
		else:
			return low > lower
	else:
		if direction == Direction.LONG:
			return low > lower
		else:
			return high < upper

def isWithinKMae(direction, reverse=False):
	upper, lower = kelt_mae.getCurrent(utils, chart)
	_, high, low, _ = chart.getCurrentBidOHLC(utils)

	if reverse:
		if direction == Direction.LONG:
			return high < lower
		else:
			return low > upper
	else:
		if direction == Direction.LONG:
			return low > upper
		else:
			return high < lower

def isWithinKelt(direction, reverse=False):
	upper, _, lower = kelt_ch.getCurrent(utils, chart)
	_, high, low, _ = chart.getCurrentBidOHLC(utils)

	if reverse:
		if direction == Direction.LONG:
			return high < lower
		else:
			return low > upper
	else:
		if direction == Direction.LONG:
			return low > upper
		else:
			return high < lower

def isWithinKSma(direction, reverse=False):
	_, val, _ = kelt_ch.getCurrent(utils, chart)
	_, high, low, _ = chart.getCurrentBidOHLC(utils)

	if reverse:
		if direction == Direction.LONG:
			return high < val
		else:
			return low > val
	else:
		if direction == Direction.LONG:
			return low > val
		else:
			return high < val

def isWithinCtKelt(direction, reverse=False):
	upper, _, lower = kelt_ch.getCurrent(utils, chart)
	_, high, low, _ = chart.getCurrentBidOHLC(utils)

	if reverse:
		if direction == Direction.LONG:
			return high < upper
		else:
			return low > lower
	else:
		if direction == Direction.LONG:
			return low > lower
		else:
			return high < upper

def isRetHitKMae(direction, reverse=False):
	upper, lower = kelt_mae.getCurrent(utils, chart)
	_, high, low, _ = chart.getCurrentBidOHLC(utils)

	if reverse:
		if direction == Direction.LONG:
			return high >= lower
		else:
			return low <= upper
	else:
		if direction == Direction.LONG:
			return low <= upper
		else:
			return high >= lower

def isRetHitKelt(direction, reverse=False):
	upper, _, lower = kelt_ch.getCurrent(utils, chart)
	_, high, low, _ = chart.getCurrentBidOHLC(utils)

	if reverse:
		if direction == Direction.LONG:
			return low <= lower
		else:
			return high >= upper
	else:
		if direction == Direction.LONG:
			return high >= upper
		else:
			return low <= lower

def isRetHitKSma(direction, reverse=False):
	_, val, _ = kelt_ch.getCurrent(utils, chart)
	_, high, low, _ = chart.getCurrentBidOHLC(utils)

	if reverse:
		if direction == Direction.LONG:
			return high >= val
		else:
			return low <= val
	else:
		if direction == Direction.LONG:
			return low <= val
		else:
			return high >= val

def isRetHitLThree(direction, reverse=False):
	upper, lower = limit_three.getCurrent(utils, chart)
	_, high, low, _ = chart.getCurrentBidOHLC(utils)

	if reverse:
		if direction == Direction.LONG:
			return low <= lower
		else:
			return high >= upper
	else:
		if direction == Direction.LONG:
			return high >= upper
		else:
			return low <= lower

def isRetHitLTwo(direction, reverse=False):
	upper, lower = limit_two.getCurrent(utils, chart)
	_, high, low, _ = chart.getCurrentBidOHLC(utils)

	if reverse:
		if direction == Direction.LONG:
			return low <= lower
		else:
			return high >= upper
	else:
		if direction == Direction.LONG:
			return high >= upper
		else:
			return low <= lower

def isRetHitLOne(direction, reverse=False):
	upper, lower = limit_one.getCurrent(utils, chart)
	_, high, low, _ = chart.getCurrentBidOHLC(utils)

	if reverse:
		if direction == Direction.LONG:
			return low <= lower
		else:
			return high >= upper
	else:
		if direction == Direction.LONG:
			return high >= upper
		else:
			return low <= lower

def isRetHitCtLTwo(direction, reverse=False):
	upper, lower = limit_two.getCurrent(utils, chart)
	_, high, low, _ = chart.getCurrentBidOHLC(utils)

	if reverse:
		if direction == Direction.LONG:
			return high >= lower
		else:
			return low <= upper
	else:
		if direction == Direction.LONG:
			return low <= upper
		else:
			return high >= lower

def isBollAboveCtLThree(direction, reverse=False):
	one_upper, one_lower = boll_one.getCurrent(utils, chart)
	two_upper, two_lower = boll_two.getCurrent(utils, chart)
	l_one_upper, l_one_lower = limit_three.getCurrent(utils, chart)

	if reverse:
		if direction == Direction.LONG:
			return one_lower < l_one_lower and two_lower < l_one_lower
		else:
			return one_upper > l_one_upper and two_upper > l_one_upper
	else:
		if direction == Direction.LONG:
			return one_upper > l_one_upper and two_upper > l_one_upper
		else:
			return one_lower < l_one_lower and two_lower < l_one_lower

def isHitBoll(direction, reverse=False):
	return isHitBollTwo(direction, reverse=reverse) or isHitBollOne(direction, reverse=reverse)

def isHitBollTwo(direction, reverse=False):
	upper, lower = boll_two.getCurrent(utils, chart)
	_, high, low, _ = chart.getCurrentBidOHLC(utils)

	if reverse:
		if direction == Direction.LONG:
			return low <= lower
		else:
			return high >= upper
	else:
		if direction == Direction.LONG:
			return high >= upper
		else:
			return low <= lower

def isHitBollOne(direction, reverse=False):
	upper, lower = boll_one.getCurrent(utils, chart)
	_, high, low, _ = chart.getCurrentBidOHLC(utils)

	if reverse:
		if direction == Direction.LONG:
			return low <= lower
		else:
			return high >= upper
	else:
		if direction == Direction.LONG:
			return high >= upper
		else:
			return low <= lower

def isCloseABBollTwo(direction, reverse=False):
	upper, lower = boll_two.getCurrent(utils, chart)
	close = chart.getCurrentBidOHLC(utils)[3]

	if reverse:
		if direction == Direction.LONG:
			return close <= lower
		else:
			return close >= upper
	else:
		if direction == Direction.LONG:
			return close >= upper
		else:
			return close <= lower

def isCloseABBollOne(direction, reverse=False):
	upper, lower = boll_one.getCurrent(utils, chart)
	close = chart.getCurrentBidOHLC(utils)[3]
	if reverse:
		if direction == Direction.LONG:
			return close <= lower
		else:
			return close >= upper
	else:
		if direction == Direction.LONG:
			return close >= upper
		else:
			return close <= lower

def isBollTwoABBollOne(direction, reverse=False):
	l_upper, l_lower = boll_two.getCurrent(utils, chart)
	s_upper, s_lower = boll_one.getCurrent(chart)

	if reverse:
		if direction == Direction.LONG:
			return l_upper < s_upper
		else:
			return l_lower > s_lower
	else:
		if direction == Direction.LONG:
			return l_upper > s_upper
		else:
			return l_lower < s_lower

def isKeltOutside():
	one_upper, one_lower = boll_one.getCurrent(utils, chart)
	two_upper, two_lower = boll_two.getCurrent(utils, chart)
	l_one_upper, l_one_lower = limit_one.getCurrent(utils, chart)
	k_upper, _, k_lower = kelt_ch.getCurrent(utils, chart)

	return (
		k_upper > one_upper and k_upper > two_upper and k_upper > l_one_upper and
		k_lower < one_lower and k_lower < two_lower and k_lower < l_one_lower
	)

def confirmation(trigger, entry_type, reverse=False):
	''' confirm entry '''

	global pending_entry, istemp

	utils.log('confirmation', 'confirmation init')

	if reverse:
		if trigger.direction == Direction.LONG:
			trigger = short_trigger
		else:
			trigger = long_trigger

	if entry_type == EntryType.PreTEntry or entry_type == EntryType.TEntry:
		for pos in utils.positions:
			if pos.direction == Constants.BUY and trigger.direction == Direction.LONG:
				return
			elif pos.direction == Constants.SELL and trigger.direction == Direction.SHORT:
				return

	istemp = False
	trigger.entry_type = entry_type
	utils.log("confirmation", '{0} {1} {2}'.format(trigger.direction, entry_type, reverse))
	pending_entry = trigger

def report():
	''' Prints report for debugging '''
	utils.log('', "\n")
	utils.log('', "c_direction: {0}".format(c_direction))

	utils.log('', "L: {0}".format(long_trigger))
	utils.log('', "S: {0}".format(short_trigger))
	utils.log('', "istemp: {0}".format(istemp))

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
