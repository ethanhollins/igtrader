import Constants
from enum import Enum

VARIABLES = {
	'PRODUCT': Constants.GBPUSD,
	'BANK': None,
	'risk': 1.0,
	'stoprange': 17.0,
	'm_targets': [100, 130, 150, 180, 204],
	'm_stops': [51, 85, 102, 153],
	'add_target': 51,
	'close_target': 17,
	'RSI': None,
	'rsi_long': 52,
	'rsi_short': 48,
	'MACD': None,
	'macdz_conf': 2.0,
	'CCI': None,
	'cci_conf': 100.0, 
}

class Direction(Enum):
	LONG = 1
	SHORT = 2

class DirectionState(Enum):
	ONE = 1
	TWO = 2
	THREE = 3
	COMPLETE = 4

class EntryState(Enum):
	ONE = 1
	TWO = 2
	THREE = 3
	COMPLETE = 4

class EntryType(Enum):
	M_TRADE = 1
	ADDITIONAL = 2
	RE_ENTRY = 3
	CLOSE = 4

class TimeState(Enum):
	TRADING = 1
	STOP = 2
	EXIT_ONLY = 3
	EXIT = 4

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
		
		self.ds_long = DirectionState.ONE
		self.ds_short = DirectionState.ONE

		self.est_direction = None

		self.entry_state = EntryState.ONE
		self.entry_type = EntryType.ADDITIONAL
		self.re_entry = None

		self.pivot_line = 0
		self.is_stopped = False

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
	
	global rsi, macd_z, cci, d_pivots, prev_d_pivots

	rsi = utils.RSI(10)
	macd_z = utils.MACD(4, 40, 3)
	cci = utils.CCI(5)
	d_pivots = None
	prev_d_pivots = None

def setup(utilities):
	global utils, m_chart, h4_chart, d_chart, bank
	utils = utilities
	if len(utils.charts) > 0:
		for chart in utils.charts:
			if chart.period == Constants.ONE_MINUTE:
				m_chart = chart
			elif chart.period == Constants.FOUR_HOURS:
				h4_chart = chart
			elif chart.period == Constants.DAILY:
				d_chart = chart
	else:
		m_chart = utils.getChart(VARIABLES['PRODUCT'], Constants.ONE_MINUTE)
		h4_chart = utils.getChart(VARIABLES['PRODUCT'], Constants.FOUR_HOURS)
		d_chart = utils.getChart(VARIABLES['PRODUCT'], Constants.DAILY)

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

	trigger = Trigger()
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
	time = utils.convertTimestampToDatetime(utils.getLatestTimestamp())
	london_time = utils.convertTimezone(time, 'Europe/London')
	if chart.period == Constants.ONE_MINUTE:
		if utils.plan_state.value in (4,):
			utils.log("\nTime", time.strftime('%d/%m/%y %H:%M:%S'))
			utils.log("London Time", london_time.strftime('%d/%m/%y %H:%M:%S') + '\n')
		elif utils.plan_state.value in (1,):
			utils.log("\n[{0}] onNewBar ({1})".format(utils.account.accountid, utils.name), utils.getTime().strftime('%d/%m/%y %H:%M:%S'))
		
		checkTime()

		runSequence()

		if utils.plan_state.value in (4,):
			report()

	elif chart.period == Constants.FOUR_HOURS:
		if utils.plan_state.value in (4,):
			utils.log('H4 OHLC', h4_chart.getCurrentBidOHLC(utils))
		setPivot()
	elif chart.period == Constants.DAILY:
		if utils.plan_state.value in (4,):
			utils.log('D OHLC', d_chart.getCurrentBidOHLC(utils))

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
		
		if pending_entry.entry_type == EntryType.CLOSE or time_state != TimeState.TRADING:
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
	global trades
	if bank:
		if trigger.entry_state == EntryType.M_TRADE:
			tp = getTargetProfit(VARIABLES['m_targets'][-1], getCurrentProfit())
		else:
			tp = getTargetProfit(VARIABLES['add_target'], getCurrentProfit())

		c_profit = getCurrentProfit()

		pos = utils.stopAndReverse(
			VARIABLES['PRODUCT'], 
			utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
			slRange = VARIABLES['stoprange'],
			tpRange = tp
		)

		if entry.entry_type != EntryType.RE_ENTRY:
			trades += 1

		pos.data['is_m_trade'] = trigger.entry_state == EntryType.M_TRADE
		pos.data['c_profit'] = c_profit
		pos.data['stop_state'] = 0

		utils.savePositions()

		positions.append(pos)

def handleRegularEntry(entry):
	''' 
	Handle regular entries 
	and check if tradable conditions are met.
	'''

	global trades
	if bank:
		if trigger.entry_state == EntryType.M_TRADE:
			tp = getTargetProfit(VARIABLES['m_targets'][-1], getCurrentProfit())
		else:
			tp = getTargetProfit(VARIABLES['add_target'], getCurrentProfit())
		
		c_profit = getCurrentProfit()

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

		if entry.entry_type != EntryType.RE_ENTRY:
			trades += 1
		
		pos.data['is_m_trade'] = trigger.entry_state == EntryType.M_TRADE
		pos.data['c_profit'] = c_profit
		pos.data['stop_state'] = 0

		utils.savePositions()

		positions.append(pos)


def closeAllPositions():
	for pos in positions:
		if not pos.closetime:
			pos.close()

def setSL17():
	target = getTargetProfit(17, getCurrentProfit(get_open=False))
	for pos in utils.positions:
		sl_price = pos.calculateSLPrice(-target)
		pos.modifySL(sl_price)

def setMTradeStop(is_close=False):
	_, high, low, close = m_chart.getCurrentBidOHLC(utils)

	for pos in utils.positions:
		if 'stop_state' in pos.data and 'is_m_trade' in pos.data and pos.data['is_m_trade']:
			if pos.data['stop_state'] == 0:
				if is_close:
					pivot_sl = getPossiblePivotSL(trigger.pivot_line, pos.direction)
					if pivot_sl:
						pos.modifySL(pivot_sl)
						pos.data['stop_state'] = 1
						utils.savePositions()
						utils.log('setMTradeStop', "isClose")

			else:
				if 'stop_state' in pos.data and 'c_profit' in pos.data:
					for i in range(len(VARIABLES['m_stops'])):
						if pos.data['stop_state'] >= i+2:
							continue

						target = getTargetProfit(VARIABLES['m_targets'][i], VARIABLES['c_profit'])
						if isPositionProfit(pos, target):
							stop = getTargetProfit(VARIABLES['m_stops'][i], VARIABLES['c_profit'])
							if pos.direction == Constants.BUY:
								sl_price = pos.calculateSLPrice(-stop)
								pos.modifySL(sl_price)
								pos.data['stop_state'] = i+2
								utils.savePositions()
								utils.log('setMTradeStop', "TP Level {}".format(i))
							else:
								sl_price = pos.calculateSLPrice(-stop)
								pos.modifySL(sl_price)
								pos.data['stop_state'] = i+2
								utils.savePositions()
								utils.log('setMTradeStop', "TP Level {}".format(i))

def getPossiblePivotSL(x, pos):
	close = m_chart.getCurrentBidOHLC(utils)[3]

	if pos.direction == Constants.BUY:
		sl = min(
			x - utils.convertToPrice(1.0),
			close - utils.convertToPrice(5.0)
		)
		if sl > pos.sl:
			return sl
	else:
		sl = max(
			x + utils.convertToPrice(2.7),
			close + utils.convertToPrice(5.0)
		)
		if sl < pos.sl:
			return sl

	return None

def onTakeProfit(pos):
	utils.log("onTakeProfit ", '')
	global time_state
	if 'is_m_trade' in pos.data and not pos.data['is_m_trade']:
		time_state = TimeState.EXIT

def onStopLoss(pos):
	utils.log("onStopLoss", '')
	if ('is_m_trade' in pos.data and pos.data['is_m_trade']
		and 'stop_state' in pos.data and pos.data['stop_state'] <= 1):
		trigger.is_stopped = True

def checkTime():
	''' 
	Checks current time and initiates 
	closing sequence where necessary.
	'''
	global time_state

	time = utils.convertTimestampToDatetime(utils.getLatestTimestamp())
	london_time = utils.convertTimezone(time, 'Europe/London')

	if (
		time_state != TimeState.STOP 
		and ((london_time.hour == 19 and london_time.minute == 59) or
			london_time.hour == 20)
	):
		time_state = TimeState.STOP
		setMTradeStop(is_close=True)
	elif (
		time_state == TimeState.TRADING
		and (london_time.hour == 19 and london_time.minute >= 30)
	):
		time_state = TimeState.EXIT_ONLY

def runSequence():

	if utils.plan_state.value in (4,):
		utils.log('M1 OHLC', m_chart.getCurrentBidOHLC(utils))
		stridx = rsi.getCurrent(utils, m_chart)
		hist = macd_z.getCurrent(utils, m_chart)[2]
		ch_idx = cci.getCurrent(utils, m_chart)

		utils.log('IND', 'RSI: {:.2f} |HIST: {:.5f} |CCI: {:.5f}\n| D PIVOTS: {}\n| PREV PIVS: {}'.format(
			stridx, hist, ch_idx, d_pivots, prev_d_pivots
		))

	time = utils.convertTimestampToDatetime(utils.getLatestTimestamp())
	london_time = utils.convertTimezone(time, 'Europe/London')

	setMTradeStop()

	if not trigger.pivot_line: return

	if time_state == TimeState.TRADING or time_state == TimeState.EXIT_ONLY:
		directionSetup(Direction.LONG)
		directionSetup(Direction.SHORT)
		if entrySetup(): return
		if reEntrySetup(): return

	elif time_state == TimeState.STOP or time_state == TimeState.EXIT:
		directionSetup(Direction.LONG)
		directionSetup(Direction.SHORT)
		entrySetup()

		if not trigger.entry_state == EntryType.ADDITIONAL:
			exitSetup()

def setPivot():
	global time_state
	time = utils.convertTimestampToDatetime(h4_chart.c_ts)
	m_time = utils.convertTimestampToDatetime(utils.getLatestTimestamp())
	london_time = utils.convertTimezone(time, 'Europe/London')
	london_m_time = utils.convertTimezone(m_time, 'Europe/London')
	close = h4_chart.getCurrentBidOHLC(utils)[3]

	if (trigger.is_stopped 
		and time_state == TimeState.TRADING 
		and trigger.entry_type == EntryType.ADDITIONAL):
		trigger.pivot_line = close
		trigger.entry_state = EntryType.M_TRADE
		trigger.is_stopped = False

	if london_time.hour == 4:
		global d_pivots, prev_d_pivots
		ohlc = d_chart.getBidOHLC(utils, 0, 2)
		d_pivots = getDailyPivots(ohlc[1])
		prev_d_pivots = getDailyPivots(ohlc[0])


		global positions, trades, bank
		time_state = TimeState.TRADING
		positions = []
		trades = 0
		bank = utils.getTradableBank()

		m_trade = getMTrade()
		if not m_trade or isIndecisivePivots() or isOppPivots(m_trade.direction):
			trigger.entry_type = EntryType.M_TRADE
		else:
			trigger.entry_type = EntryType.ADDITIONAL

		trigger.pivot_line = close
		trigger.est_direction = None
		trigger.re_entry = None
		trigger.is_stopped = False

def getCurrentProfit(get_open=True):
	profit = 0
	close = m_chart.getCurrentBidOHLC(utils)[3]
	
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
	_, high, low, _ = m_chart.getCurrentBidOHLC(utils)
	
	for pos in positions:
		if pos.closetime:
			profit += pos.getPipProfit()
		else:
			if pos.direction == Constants.BUY:
				profit += utils.convertToPips(high - pos.entryprice)
			else:
				profit += utils.convertToPips(pos.entryprice - low)

	return profit >= target

def isPositionProfit(pos, target):
	_, high, low, _ = m_chart.getCurrentBidOHLC(utils)
	if pos.direction == Constants.BUY:
		return utils.convertToPips(high - pos.entryprice) >= target
	else:
		return utils.convertToPips(pos.entryprice - low) >= target

def getDailyPivots(ohlc):
	_open, high, low, close = ohlc

	cp = float(round((high + low + close) / 3, 5))
	r1 = float(round(cp*2 - low, 5))
	s1 = float(round(cp*2 - high, 5))
	r2 = float(round(cp + (high - low), 5))
	s2 = float(round(cp - (high - low), 5))
	r3 = float(round(high + 2*(cp-low), 5))
	s3 = float(round(low - 2*(high-cp), 5))

	return cp, r1, r2, r3, s1, s2, s3

def directionSetup(direction):

	if getDirectionState(direction) == DirectionState.ONE:
		if isRsiConf(direction) and isMacdzPosConf(direction):
			setDirectionState(direction, DirectionState.TWO)
			return

	elif getDirectionState(direction) == DirectionState.TWO:
		if isMacdzPosConf(direction, reverse=True):
			setDirectionState(direction, DirectionState.THREE)
			return

	elif getDirectionState(direction) == DirectionState.THREE:
		if isMacdzPosConf(direction):
			if isRsiConf(direction):
				setDirectionState(direction, DirectionState.ONE)
				
				if trigger.est_direction != direction:
					trigger.entry_state = EntryState.ONE
					if time_state == TimeState.TRADING and trigger.pivot_line:
						trigger.est_direction = direction
				return
			else:
				setDirectionState(direction, DirectionState.ONE)
				return

def setDirectionState(direction, state):
	if direction == Direction.LONG:
		trigger.ds_long = state
	else:
		trigger.ds_short = state

def getDirectionState(direction):
	if direction == Direction.LONG:
		return trigger.ds_long
	else:
		return trigger.ds_short

def entrySetup():

	if trigger.est_direction:
		if trigger.entry_state == EntryState.ONE:
			if entryConfirmation(trigger.est_direction):
				trigger.entry_state = EntryState.COMPLETE
				trigger.re_entry = None
				return confirmation(trigger)

def entryConfirmation(direction):
	if utils.plan_state.value in (4,):
		utils.log('entryConfirmation', 'Entry ONE Conf: {0} {1} {2}'.format(
			isABPivotLine(trigger.est_direction),
			isCciConf(trigger.est_direction),
			isBB(trigger.est_direction)
		))

	return (
		isABPivotLine(trigger.est_direction) and
		isCciConf(trigger.est_direction) and
		isBB(trigger.est_direction)
	)

def reEntrySetup():
	if trigger.re_entry != None:
		if isMacdzConf(trigger.re_entry):
			return confirmation(trigger)

def exitSetup():
	if len(utils.positions) > 0:
		direction = Direction.LONG if utils.positions[0].direction == Constants.BUY else Direction.SHORT

		if isMacdzPosConf(direction, reverse=True):
			closeAllPositions()

def getMTrade():
	for pos in utils.positions:
		if 'is_m_trade' in pos.data and pos.data['is_m_trade']:
			return pos

	return None

def isIndecisivePivots():
	return (
		d_pivots[0] < close < prev_d_pivots[0]
		or prev_d_pivots[0] < close < d_pivots[0]
	)

def isOppPivots(direction, reverse=False):
	if reverse:
		if direction == Constants.BUY:
			return close > d_pivots[0] and close > prev_d_pivots[0]
		else:
			return close < d_pivots[0] and close < prev_d_pivots[0]
	else:
		if direction == Constants.BUY:
			return close < d_pivots[0] and close < prev_d_pivots[0]
		else:
			return close > d_pivots[0] and close > prev_d_pivots[0]

def isMacdzConf(direction, reverse=False):
	hist = round(float(macd_z.getCurrent(utils, m_chart)[2]), 5)

	if reverse:
		if direction == Direction.LONG:
			return hist <= round(-VARIABLES['macdz_conf'] * 1e-05, 5)
		else:
			return hist >= round(VARIABLES['macdz_conf'] * 1e-05, 5)
	else:
		if direction == Direction.LONG:
			return hist >= round(VARIABLES['macdz_conf'] * 1e-05, 5)
		else:
			return hist <= round(-VARIABLES['macdz_conf'] * 1e-05, 5)

def isMacdzPosConf(direction, reverse=False):
	hist = round(float(macd_z.getCurrent(utils, m_chart)[2]), 5)

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

def isCciConf(direction, reverse=False):
	chidx = round(float(cci.getCurrent(utils, m_chart)), 2)

	if reverse:
		if direction == Direction.LONG:
			return chidx <= -VARIABLES['cci_conf']
		else:
			return chidx >= VARIABLES['cci_conf']
	else:
		if direction == Direction.LONG:
			return chidx >= VARIABLES['cci_conf']
		else:
			return chidx <= -VARIABLES['cci_conf']

def isRsiConf(direction, reverse=False):
	stridx = round(float(rsi.getCurrent(utils, m_chart)), 2)

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

def isABPivotLine(direction, reverse=False):
	close = m_chart.getCurrentBidOHLC(utils)[3]
	
	if reverse:
		if direction == Direction.LONG:
			return close < trigger.pivot_line - utils.convertToPrice(1.0)
		else:
			return close > trigger.pivot_line + utils.convertToPrice(1.0)
	else:
		if direction == Direction.LONG:
			return close > trigger.pivot_line + utils.convertToPrice(1.0)
		else:
			return close < trigger.pivot_line - utils.convertToPrice(1.0)

def isBB(direction, reverse=False):
	_open, _, _, close = m_chart.getCurrentBidOHLC(utils)

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
	_open, _, _, close = m_chart.getCurrentBidOHLC(utils)
	return not utils.convertToPips(abs(round(_open - close, 5))) >= VARIABLES['doji_range']

def isPosInDir(direction):
	for pos in positions:
		if not pos.closetime:
			if pos.direction == Constants.BUY and direction == Direction.LONG:
				return True
			elif pos.direction == Constants.SELL and direction == Direction.SHORT:
				return True

	return False

def confirmation(trigger, reverse=False):
	''' confirm entry '''

	global pending_entry

	if trigger.entry_type == EntryType.M_TRADE:
		pending_entry = Trigger(direction=trigger.est_direction)
		pending_entry.entry_type = trigger.entry_type

	elif trigger.entry_type == EntryType.ADDITIONAL:
		pending_entry = None
		return

	if time_state == TimeState.EXIT_ONLY:
		pending_entry.entry_type = EntryType.CLOSE

	if (
		not trigger.pivot_line 
		or time_state == TimeState.STOP 
		or (isPosInDir(pending_entry.direction)
			and pending_entry.entry_type != EntryType.CLOSE)
	):
		pending_entry = None
		return False
		
	utils.log("confirmation", '{0} {1} {2}'.format(trigger.direction, pending_entry.entry_type, time_state))
	return True

def report():
	''' Prints report for debugging '''
	utils.log('', "\n")

	utils.log('', "Time State: {}".format(time_state))
	utils.log('', "T: {0}".format(trigger))

	utils.log('', "\nALL POSITIONS:")
	count = 0
	for pos in utils.positions:
		count += 1
		utils.log('', "{}: {} Profit: {} | {}% | State: {}".format(
			count,
			pos.direction,
			pos.getPipProfit(), 
			pos.getPercentageProfit(),
			pos.data['stop_state']
		))

	utils.log('', "---\n")
	utils.log('', "\nSESSIONS:\nCLOSED:")
	count = 0
	for pos in positions:
		count += 1
		utils.log('', "{}{}: {} Profit: {} | {}% | State: {}".format(
			'(OPEN): ' if pos.closetime == None else '',
			count, pos.direction,
			pos.getPipProfit(), 
			pos.getPercentageProfit(),
			pos.data['stop_state']
		))


	utils.log('', utils.getTime().strftime('%d/%m/%y %H:%M:%S'))
	utils.log('', "--|\n")
