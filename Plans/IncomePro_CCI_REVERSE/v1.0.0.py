import Constants
from enum import Enum

VARIABLES = {
	'TIMEZONE': 'America/New_York',
	'PRODUCT': Constants.GBPUSD,
	'BANK': None,
	'risk': 1.0,
	'stoprange': 17.0,
	'exit_target': 45,
	'tp_target': 51,
	'set_safety': 40,
	'max_loss': -34,
	'MACD': None,
	'macdz_conf': 2.0,
	'CCI': None,
	'cci_conf_strong': 120.0,
	'cci_conf_weak': 100.0,
}

class Direction(Enum):
	LONG = 1
	SHORT = 2

class EntryState(Enum):
	ONE = 1
	TWO = 2
	THREE = 3
	FOUR = 4
	COMPLETE = 5

class EntryType(Enum):
	REGULAR = 1
	RE_ENTRY = 2

class TimeState(Enum):
	TRADING = 1
	STOP = 2
	EXIT = 3
	SAFETY = 4

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

		self.init_entry_state = EntryState.ONE
		self.is_init_entry = False

		self.entry_state = EntryState.ONE
		self.entry_type = None

		self.rap = 0
		self.fap = 0
		self.rsp = 0
		
		self.re_entry = None

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
	
	global macd_z, cci, kelt_ch

	macd_z = utils.MACD(4, 40, 3)
	cci = utils.CCI(5)
	kelt_ch = utils.KELT_IG(10, 10, 1.0)

def setup(utilities):
	global utils, chart, bank
	utils = utilities
	if len(utils.charts) > 0:
		chart = utils.charts[0]
	else:
		chart = utils.getChart(VARIABLES['PRODUCT'], Constants.ONE_MINUTE)

	bank = utils.getTradableBank()

	global positions
	for pos in positions:
		if not pos.closeprice:
			del positions[positions.index(pos)]
	for pos in utils.positions:
		positions.append(pos)

def setGlobalVars():
	global trigger, is_onb
	global pending_entry
	global positions, trades
	global time_state, bank

	trigger = Trigger(direction=Direction.LONG)
	is_onb = False

	pending_entry = None

	positions = []
	trades = 0

	time_state = TimeState.STOP
	bank = utils.getTradableBank()

def onNewBar(chart):
	global is_onb
	is_onb = True
	''' Function called on every new bar '''
	if utils.plan_state.value in (4,):
		time = utils.convertTimestampToDatetime(utils.getLatestTimestamp())
		london_time = utils.convertToLondonTimezone(time)
		utils.log("\nTime", time.strftime('%d/%m/%y %H:%M:%S'))
		utils.log("London Time", london_time.strftime('%d/%m/%y %H:%M:%S') + '\n')
	elif utils.plan_state.value in (1,):
		utils.log("\n[{0}] onNewBar ({1})".format(utils.account.accountid, utils.name), utils.getTime().strftime('%d/%m/%y %H:%M:%S'))
	
	checkTime()

	runSequence()

	if utils.plan_state.value in (4,):
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
		
		if (
			getCurrentProfit() <= VARIABLES['max_loss'] or
			getCurrentProfit() >= VARIABLES['tp_target']
		):
			closeAllPositions()
			pending_entry = None
			time_state = TimeState.EXIT
			return
		elif time_state != TimeState.TRADING:
			closeAllPositions()
			pending_entry = None
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
	if bank:
		pos = utils.stopAndReverse(
			VARIABLES['PRODUCT'], 
			utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
			slRange = VARIABLES['stoprange'],
			tpRange = getTargetProfit(VARIABLES['tp_target'], getCurrentProfit())
		)

		global trades
		trades += 1
		positions.append(pos)

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
				slRange = VARIABLES['stoprange'],
				tpRange = getTargetProfit(VARIABLES['tp_target'], getCurrentProfit())
			)
		else:
			pos = utils.sell(
				VARIABLES['PRODUCT'], 
				utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
				slRange = VARIABLES['stoprange'],
				tpRange = getTargetProfit(VARIABLES['tp_target'], getCurrentProfit())
			)

		global trades
		trades += 1
		positions.append(pos)


def closeAllPositions():
	for pos in utils.positions:
		pos.close()

def onTakeProfit(pos):
	utils.log("onTakeProfit ", '')
	global time_state
	time_state = TimeState.EXIT

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

	if time_state == TimeState.STOP:
		if london_time.hour == 6 and london_time.minute == 59:
			global bank
			bank = utils.getTradableBank()
			getInitEntryState()

		elif 7 <= london_time.hour < 20:
			time_state = TimeState.TRADING

			global positions, trades
			positions = []
			trades = 0

			trigger.is_init_entry = True
			trigger.re_entry = None

	elif (
		time_state != TimeState.STOP 
		and ((london_time.hour == 19 and london_time.minute == 59) or
			london_time.hour == 20)
	):
		time_state = TimeState.STOP

def runSequence():

	if utils.plan_state.value in (4,):
		utils.log('OHLC', chart.getCurrentBidOHLC(utils))
		
		hist = round(macd_z.getCurrent(utils, chart)[2], 5)
		chidx = round(cci.getCurrent(utils, chart), 5)
		k_ch = kelt_ch.getCurrent(utils, chart)

		utils.log('IND', 'MACD: {0:.5f} |CCI: {1:.5f} |KELT: {2}'.format(
			hist, chidx, k_ch
		))

	global time_state

	if time_state == TimeState.TRADING:
		if isTargetProfit(VARIABLES['exit_target']):
			time_state = TimeState.EXIT
		else:
			if entrySetup(): return
			if trigger.is_init_entry:
				if initEntrySetup(): return
			
			if reEntrySetup(): return

	elif time_state == TimeState.STOP or time_state == TimeState.EXIT:
		entrySetup()
		exitSetup()

def getCurrentProfit(get_open=True):
	profit = 0
	close = chart.getCurrentBidOHLC(utils)[3]
	
	for pos in positions:
		if pos.closetime:
			profit += pos.getPipProfit()
		elif get_open:
			if pos.direction == Constants.BUY:
				profit += utils.convertToPips(close - pos.entryprice)
			else:
				profit += utils.convertToPips(pos.entryprice - close)
	
	return profit

def getTargetProfit(target, profit):
	return target - profit

def isTargetProfit(target):
	profit = 0
	_, high, low, _ = chart.getCurrentBidOHLC(utils)
	
	for pos in positions:
		if pos.closetime:
			profit += pos.getPipProfit()
		else:
			if pos.direction == Constants.BUY:
				profit += utils.convertToPips(high - pos.entryprice)
			else:
				profit += utils.convertToPips(pos.entryprice - low)

	return profit >= target

def getInitEntryState():
	macd_vals = macd_z.get(utils, chart, 0, 300)
	cci_vals = cci.get(utils, chart, 0, 300)

	for i in range(len(macd_vals)-1, -1, -1):
		hist = macd_vals[i][2]
		ch_idx = cci_vals[i]

		if trigger.direction == Direction.LONG:
			if hist > 0:
				trigger.init_entry_state = EntryState.ONE
				return
			elif ch_idx < -VARIABLES['cci_conf_weak']:
				trigger.init_entry_state = EntryState.TWO
				return
		else:
			if hist < 0:
				trigger.init_entry_state = EntryState.ONE
				return
			elif ch_idx > VARIABLES['cci_conf_weak']:
				trigger.init_entry_state = EntryState.TWO
				return

def initEntrySetup():
	if trigger.init_entry_state == EntryState.ONE:
		if not isMacdzPosConf(trigger.direction):
			trigger.init_entry_state = EntryState.TWO
			return
	elif trigger.init_entry_state == EntryState.TWO:
		if isCciWeakConf(trigger.direction, reverse=True):
			trigger.init_entry_state = EntryState.THREE
			return initEntrySetup()
	elif trigger.init_entry_state == EntryState.THREE:
		if isMacdzPosConf(trigger.direction):
			trigger.init_entry_state = EntryState.COMPLETE
			trigger.is_init_entry = False
			confirmation(trigger, EntryType.REGULAR)
			return

def entrySetup():
	
	if trigger.entry_state == EntryState.ONE:
		trigger.fap = getHLPrice(trigger.direction, trigger.fap)
		if isCciStrongConf(trigger.direction):
			trigger.entry_state = EntryState.TWO
			return entrySetup()

	elif trigger.entry_state == EntryState.TWO:
		trigger.fap = getHLPrice(trigger.direction, trigger.fap)
		if isCciStrongConf(trigger.direction, reverse=True):
			trigger.entry_state = EntryState.THREE
			return entrySetup()

	elif trigger.entry_state == EntryState.THREE:
		trigger.rsp = getHLPrice(trigger.direction, trigger.rsp, reverse=True)
		if (isCciWeakConf(trigger.direction)
			and isKeltHitConf(trigger.direction)):
			trigger.entry_state = EntryState.FOUR
			return entrySetup()

	elif trigger.entry_state == EntryState.FOUR:
		if entryConfirmation(trigger.direction):
			trigger.setDirection(trigger.direction, reverse=True)
			if not isPosInDir(trigger.direction):
				trigger.rap = trigger.fap
				confirmation(trigger, EntryType.REGULAR)
			
			trigger.fap = 0
			trigger.rsp = 0
			trigger.is_init_entry = False
			trigger.entry_state = EntryState.ONE
			
			return entrySetup()

		elif cancelConfirmation(trigger.direction):
			trigger.fap = 0
			trigger.rsp = 0
			trigger.entry_state = EntryState.TWO
			return entrySetup()

	if trigger.rap:
		if rapConfirmation(trigger.direction):
			trigger.setDirection(trigger.direction, reverse=True)
			if not isPosInDir(trigger.direction):
				trigger.rap = trigger.fap
				confirmation(trigger, EntryType.REGULAR)
			
			trigger.fap = 0
			trigger.rsp = 0
			trigger.is_init_entry = False
			trigger.entry_state = EntryState.ONE
			
			return entrySetup()

def entryConfirmation(direction):
	if utils.plan_state.value in (4,):
		utils.log('entryConfirmation', 'Entry Conf: {0}'.format(
			isCloseAB(trigger.direction, trigger.rsp, reverse=True)
		))

	return (
		isCloseAB(trigger.direction, trigger.rsp, reverse=True)
	)

def cancelConfirmation(direction):
	if utils.plan_state.value in (4,):
		utils.log('cancelConfirmation', 'Cancel Conf: {0}'.format(
			isHit(trigger.direction, trigger.fap)
		))

	return (
		isHit(trigger.direction, trigger.fap)
	)

def rapConfirmation(direction):
	if utils.plan_state.value in (4,):
		utils.log('rapConfirmation', 'Rap Conf: {0}'.format(
			isCloseAB(trigger.direction, trigger.rap, reverse=True)
		))

	return (
		isCloseAB(trigger.direction, trigger.rap, reverse=True)
	)

def reEntrySetup():
	if trigger.re_entry != None:
		if isMacdzConf(trigger.re_entry):
			return confirmation(trigger, EntryType.RE_ENTRY)

def exitSetup():
	if len(utils.positions) > 0:
		direction = Direction.LONG if utils.positions[0].direction == Constants.BUY else Direction.SHORT

		if isMacdzPosConf(direction, reverse=True):
			closeAllPositions()

def getHLPrice(direction, x, reverse=False):
	if reverse:
		if direction == Direction.LONG:
			low = chart.getCurrentBidOHLC(utils)[2]
			return low if low < x or x == 0 else x
		else:
			high = chart.getCurrentBidOHLC(utils)[1]
			return high if high > x or x == 0 else x
	else:
		if direction == Direction.LONG:
			high = chart.getCurrentBidOHLC(utils)[1]
			return high if high > x or x == 0 else x
		else:
			low = chart.getCurrentBidOHLC(utils)[2]
			return low if low < x or x == 0 else x

def isCloseAB(direction, x, reverse=False):
	close = chart.getCurrentBidOHLC(utils)[3]

	if reverse:
		if direction == Direction.LONG:
			return close < x
		else:
			return close > x
	else:
		if direction == Direction.LONG:
			return close > x
		else:
			return close < x

def isHit(direction, x, reverse=False):
	_, high, low, _ = chart.getCurrentBidOHLC(utils)

	if reverse:
		if direction == Direction.LONG:
			return low < x
		else:
			return high > x
	else:
		if direction == Direction.LONG:
			return high > x
		else:
			return low < x

def isMacdzConf(direction, reverse=False):
	hist = round(float(macd_z.getCurrent(utils, chart)[2]), 5)

	if reverse:
		if direction == Direction.LONG:
			return hist <= round(-VARIABLES['macdz_conf'] * 0.00001, 5)
		else:
			return hist >= round(VARIABLES['macdz_conf'] * 0.00001, 5)
	else:
		if direction == Direction.LONG:
			return hist >= round(VARIABLES['macdz_conf'] * 0.00001, 5)
		else:
			return hist <= round(-VARIABLES['macdz_conf'] * 0.00001, 5)

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

def isCciWeakConf(direction, reverse=False):
	chidx = round(float(cci.getCurrent(utils, chart)), 5)

	if reverse:
		if direction == Direction.LONG:
			return chidx <= -VARIABLES['cci_conf_weak']
		else:
			return chidx >= VARIABLES['cci_conf_weak']
	else:
		if direction == Direction.LONG:
			return chidx >= VARIABLES['cci_conf_weak']
		else:
			return chidx <= -VARIABLES['cci_conf_weak']

def isCciStrongConf(direction, reverse=False):
	chidx = round(float(cci.getCurrent(utils, chart)), 5)

	if reverse:
		if direction == Direction.LONG:
			return chidx <= -VARIABLES['cci_conf_strong']
		else:
			return chidx >= VARIABLES['cci_conf_strong']
	else:
		if direction == Direction.LONG:
			return chidx >= VARIABLES['cci_conf_strong']
		else:
			return chidx <= -VARIABLES['cci_conf_strong']

def isKeltHitConf(direction, reverse=False):
	_, high, low, _ = chart.getCurrentBidOHLC(utils)
	upper, _, lower = kelt_ch.getCurrent(utils, chart)

	if reverse:
		if direction == Direction.LONG:
			return round(float(low), 5) <= round(float(lower), 5)
		else:
			return round(float(high), 5) >= round(float(upper), 5)
	else:
		if direction == Direction.LONG:
			return round(float(high), 5) >= round(float(upper), 5)
		else:
			return round(float(low), 5) <= round(float(lower), 5)

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

def isPosInDir(direction, reverse=False):
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

	return False

def confirmation(trigger, entry_type, reverse=False):
	''' confirm entry '''

	global pending_entry

	if entry_type == EntryType.REGULAR:
		pending_entry = Trigger(direction=trigger.direction)
		if reverse:
			pending_entry.setDirection(pending_entry.direction, reverse=True)
	else:
		pending_entry = Trigger(direction=trigger.re_entry)
		trigger.re_entry = None
		
	if time_state == TimeState.STOP or isPosInDir(pending_entry.direction):
		pending_entry = None
		return False
		
	utils.log("confirmation", '{0} {1} {2}'.format(trigger.direction, entry_type, time_state))
	pending_entry.entry_type = entry_type
	return True

def report():
	''' Prints report for debugging '''
	utils.log('', "\n")

	utils.log('', "Time State: {}".format(time_state))
	utils.log('', "T: {0}".format(trigger))

	utils.log('', "POSITIONS:\nCLOSED:")
	count = 0
	for pos in positions:
		count += 1
		utils.log('', "{}{}: {} Profit: {} | {}%".format(
			'OPEN:\n' if pos.closetime == None else '',
			count, pos.direction,
			pos.getPipProfit(), 
			pos.getPercentageProfit()
		))

	utils.log('', utils.getTime().strftime('%d/%m/%y %H:%M:%S'))
	utils.log('', "--|\n")
