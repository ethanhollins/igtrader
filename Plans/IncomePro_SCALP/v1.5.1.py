import Constants
from enum import Enum

VARIABLES = {
	'TIMEZONE': 'America/New_York',
	'PRODUCT': Constants.GBPUSD,
	'BANK': None,
	'risk': 1.0,
	'stoprange': 17.0,
	'safety_target': 45,
	'fri_safety_target': 35,
	'tp_target': 51,
	'init_tp_target': 204,
	'init_mid_target': 150,
	'init_mid_tp': 102,
	'max_loss': -34,
	'MISC': None,
	'trade_limit': 3,
	'RSI': None,
	'rsi_long': 52,
	'rsi_short': 48,
	'overbought': 70,
	'oversold': 30,
	'overbought_2': 75,
	'oversold_2': 25,
	'MACD': None,
	'macdz_conf': 2.0,
	'CCI': None,
	'cci_conf': 120.0, 
	'DONCH': None,
	'donch': 4,
	'BOLL': None,
	'boll': 2.2
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
	REGULAR = 1
	RE_ENTRY = 2
	CLOSE = 3

class TimeState(Enum):
	TRADING = 1
	STOP = 2
	EXIT_ONLY = 3
	EXIT = 4

class PivotState(Enum):
	NONE = 1
	REVERSE = 2
	CPP = 3

class TradeState(Enum):
	INITIAL = 1
	NORMAL = 2

class StopState(Enum):
	NONE = 1
	BREAKEVEN = 2
	MID = 3

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
		
		self.macd_ds_long = DirectionState.ONE
		self.macd_ds_short = DirectionState.ONE

		# self.cci_ds_long = DirectionState.ONE
		# self.cci_ds_short = DirectionState.ONE

		self.est_direction = None

		self.entry_state = EntryState.ONE
		self.entry_type = None
		
		self.re_entry = None

		self.zero_close = 0
		self.pivot_direction = None
		self.pivot_line = 0
		self.pivot_state = PivotState.NONE

		self.trade_state = TradeState.INITIAL

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
	
	global rsi, macd_z, boll_one, donch, cci, d_pivots

	rsi = utils.RSI(10)
	macd_z = utils.MACD(4, 40, 3)
	# boll_one = utils.BOLL(10, VARIABLES['boll'])
	# donch = utils.DONCH(VARIABLES['donch'])
	# cci = utils.CCI(5)
	d_pivots = None

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
		
		if (
			getCurrentProfit() <= VARIABLES['max_loss']
		):
			closeAllPositions()
			pending_entry = None
			time_state = TimeState.EXIT
			return
		elif pending_entry.entry_type == EntryType.CLOSE or time_state != TimeState.TRADING:
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
		if trigger.trade_state == TradeState.INITIAL:
			tp = getTargetProfit(VARIABLES['init_tp_target'], getCurrentProfit())
		else:
			tp = getTargetProfit(VARIABLES['tp_target'], getCurrentProfit())

		mid_target = getTargetProfit(VARIABLES['init_mid_target'], getCurrentProfit())
		mid_tp = getTargetProfit(VARIABLES['init_mid_tp'], getCurrentProfit())

		pos = utils.stopAndReverse(
			VARIABLES['PRODUCT'], 
			utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
			slRange = VARIABLES['stoprange'],
			tpRange = tp
		)

		if entry.entry_type != EntryType.RE_ENTRY:
			trades += 1

		pos.data['initial'] = trigger.trade_state == TradeState.INITIAL
		pos.data['mid_target'] = mid_target
		pos.data['mid_tp'] = mid_tp
		pos.data['stop_state'] = StopState.NONE.value

		utils.savePositions()

		positions.append(pos)

def handleRegularEntry(entry):
	''' 
	Handle regular entries 
	and check if tradable conditions are met.
	'''

	global trades
	if bank:
		if trigger.trade_state == TradeState.INITIAL:
			tp = getTargetProfit(VARIABLES['init_tp_target'], getCurrentProfit())
		else:
			tp = getTargetProfit(VARIABLES['tp_target'], getCurrentProfit())
		
		mid_target = getTargetProfit(VARIABLES['init_mid_target'], getCurrentProfit())
		mid_tp = getTargetProfit(VARIABLES['init_mid_tp'], getCurrentProfit())

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
		
		pos.data['initial'] = trigger.trade_state == TradeState.INITIAL
		pos.data['mid_target'] = mid_target
		pos.data['mid_tp'] = mid_tp
		pos.data['stop_state'] = StopState.NONE.value

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

def setInitialBE(force=False, is_fri=False):
	_, high, low, close = m_chart.getCurrentBidOHLC(utils)

	for pos in utils.positions:
		if 'stop_state' in pos.data and 'initial' in pos.data and pos.data['initial']:
			if pos.data['stop_state'] == StopState.NONE.value:
				if is_fri:
					if not pos.getPipProfit() >= VARIABLES['fri_safety_target']:
						pos.close()
						utils.log('setInitialBE', "Fri Close")

				if isTargetProfit(VARIABLES['safety_target']):
					pos.modifySL(pos.entryprice)
					pos.data['stop_state'] = StopState.BREAKEVEN.value
					utils.savePositions()
					utils.log('setInitialBE', "Breakeven")

			elif pos.data['stop_state'] == StopState.BREAKEVEN.value:
				if 'mid_tp' in pos.data and 'mid_target' in pos.data:
					if isPositionProfit(pos, pos.data['mid_target']):
						if pos.direction == Constants.BUY:
							sl_price = pos.calculateSLPrice(-pos.data['mid_tp'])
							pos.modifySL(sl_price)
							pos.data['stop_state'] = StopState.MID.value
							utils.savePositions()
							utils.log('setInitialBE', "Mid TP")
						else:
							sl_price = pos.calculateSLPrice(-pos.data['mid_tp'])
							pos.modifySL(sl_price)
							pos.data['stop_state'] = StopState.MID.value
							utils.savePositions()
							utils.log('setInitialBE', "Mid TP")

def onTakeProfit(pos):
	utils.log("onTakeProfit ", '')
	global time_state
	if 'initial' in pos.data and not pos.data['initial']:
		time_state = TimeState.EXIT

def onStopLoss(pos):
	utils.log("onStopLoss", '')
	# if pos.direction == Constants.BUY:
	# 	trigger.re_entry = Direction.LONG
	# else:
	# 	trigger.re_entry = Direction.SHORT

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
		setInitialBE(force=True, is_fri=london_time.weekday() == 4)
	elif (
		time_state == TimeState.TRADING
		and (london_time.hour == 19 and london_time.minute >= 30)
	):
		time_state = TimeState.EXIT_ONLY

def runSequence():

	if utils.plan_state.value in (4,):
		utils.log('M1 OHLC', m_chart.getCurrentBidOHLC(utils))
		
		stridx = rsi.getCurrent(utils, m_chart)
		hist = round(float(macd_z.getCurrent(utils, m_chart)[2]), 5)

		utils.log('IND', 'RSI: {} HIST: {} \n| D PIVOTS: {}'.format(
			stridx, hist, d_pivots
		))

	time = utils.convertTimestampToDatetime(utils.getLatestTimestamp())
	london_time = utils.convertTimezone(time, 'Europe/London')

	setInitialBE()
	global time_state
	if time_state == TimeState.TRADING:
		if isTargetProfit(VARIABLES['safety_target']):
			if trigger.trade_state == TradeState.NORMAL:
				time_state = TimeState.EXIT

	if isNewPivot(): trigger.pivot_state = PivotState.CPP
	if not trigger.pivot_line: return

	if time_state == TimeState.TRADING or time_state == TimeState.EXIT_ONLY:
		macdDirectionSetup(Direction.LONG)
		macdDirectionSetup(Direction.SHORT)
		if entrySetup(): return
		if reEntrySetup(): return

	elif time_state == TimeState.STOP or time_state == TimeState.EXIT:
		macdDirectionSetup(Direction.LONG)
		macdDirectionSetup(Direction.SHORT)
		entrySetup()

		if trigger.trade_state == TradeState.INITIAL:
			pass
			# setInitialBE(force=True, is_fri=london_time.weekday() == 4)
		else:
			exitSetup()

def setPivot():
	time = utils.convertTimestampToDatetime(h4_chart.c_ts)
	m_time = utils.convertTimestampToDatetime(utils.getLatestTimestamp())
	london_time = utils.convertTimezone(time, 'Europe/London')
	london_m_time = utils.convertTimezone(m_time, 'Europe/London')

	if london_time.hour == 4:
		global d_pivots
		if london_m_time.weekday() == 0:
			d_pivots = getDailyPivots(d_chart.getBidOHLC(utils, 1, 1)[0])
		else:
			d_pivots = getDailyPivots(d_chart.getCurrentBidOHLC(utils))

		global time_state, positions, trades, bank
		time_state = TimeState.TRADING
		positions = []
		trades = 0
		bank = utils.getTradableBank()

		if not getPivotDirection() or getPivotDirection() == trigger.pivot_direction and isInitialTrade():
			trigger.pivot_direction = getPivotDirection()
			trigger.trade_state = TradeState.NORMAL
		else:
			trigger.pivot_direction = getPivotDirection()
			trigger.trade_state = TradeState.INITIAL

		trigger.zero_close = h4_chart.getCurrentBidOHLC(utils)[3]
		trigger.pivot_line = 0
		trigger.pivot_state = PivotState.NONE
		trigger.est_direction = None
		trigger.re_entry = None

	if not d_pivots:
		return

	if london_time.hour in [4, 8, 12] and trigger.pivot_state.value < PivotState.REVERSE.value:
		if isReverseBar(trigger.pivot_direction):
			close = h4_chart.getCurrentBidOHLC(utils)[3]
			if trigger.pivot_direction == Direction.LONG:
				trigger.pivot_line = close if close < trigger.zero_close else trigger.zero_close
			else:
				trigger.pivot_line = close if close > trigger.zero_close else trigger.zero_close
			
			trigger.pivot_state = PivotState.REVERSE

	if trigger.pivot_state.value < PivotState.CPP.value:
		if isABCpp(trigger.pivot_direction, reverse=True):
			close = h4_chart.getCurrentBidOHLC(utils)[3]
			trigger.pivot_line = close
			trigger.pivot_state = PivotState.CPP

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

def getPivotDirection():
	close = h4_chart.getCurrentBidOHLC(utils)[3]

	if close > d_pivots[0]:
		return Direction.LONG
	elif close < d_pivots[0]:
		return Direction.SHORT
	else:
		return None

def isNewPivot():
	if d_pivots:
		_, high, low, _ = m_chart.getCurrentBidOHLC(utils)

		if trigger.pivot_direction == Direction.LONG:
			if trigger.pivot_line > d_pivots[6] and low <= d_pivots[6]:
				trigger.pivot_line = d_pivots[6]
				return True
			elif trigger.pivot_line > d_pivots[5] and low <= d_pivots[5]:
				trigger.pivot_line = d_pivots[5]
				return True
			elif trigger.pivot_line > d_pivots[4] and low <= d_pivots[4]:
				trigger.pivot_line = d_pivots[4]
				return True
		else:
			if trigger.pivot_line < d_pivots[3] and high >= d_pivots[3]:
				trigger.pivot_line = d_pivots[3]
				return True
			elif trigger.pivot_line < d_pivots[2] and high >= d_pivots[2]:
				trigger.pivot_line = d_pivots[2]
				return True
			elif trigger.pivot_line < d_pivots[1] and high >= d_pivots[1]:
				trigger.pivot_line = d_pivots[1]
				return True

	return False

def macdDirectionSetup(direction):

	if getMacdDirectionState(direction) == DirectionState.ONE:
		if isRsiConf(direction) and isMacdzPosConf(direction):
			setMacdDirectionState(direction, DirectionState.TWO)
			return

	elif getMacdDirectionState(direction) == DirectionState.TWO:
		if isMacdzPosConf(direction, reverse=True):
			setMacdDirectionState(direction, DirectionState.THREE)
			return

	elif getMacdDirectionState(direction) == DirectionState.THREE:
		if isMacdzPosConf(direction):
			if isRsiConf(direction):
				setMacdDirectionState(direction, DirectionState.ONE)
				
				if trigger.est_direction != direction:
					trigger.entry_state = EntryState.ONE
					if time_state == TimeState.TRADING and trigger.pivot_line:
						trigger.est_direction = direction
				return
			else:
				setMacdDirectionState(direction, DirectionState.ONE)
				return

def cciDirectionSetup(direction):

	if getCciDirectionState(direction) == DirectionState.ONE:
		if isRsiConf(direction) and isCciConf(direction):
			setCciDirectionState(direction, DirectionState.TWO)
			return

	elif getCciDirectionState(direction) == DirectionState.TWO:
		if isCciConf(direction, reverse=True):
			setCciDirectionState(direction, DirectionState.THREE)
			return

	elif getCciDirectionState(direction) == DirectionState.THREE:
		if isCciConf(direction):
			if isRsiConf(direction):
				setCciDirectionState(direction, DirectionState.ONE)

				if trigger.est_direction != direction:
					trigger.entry_state = EntryState.ONE
					if time_state == TimeState.TRADING and trigger.pivot_line:
						trigger.est_direction = direction
				return
			else:
				setCciDirectionState(direction, DirectionState.ONE)
				return

def setMacdDirectionState(direction, state):
	if direction == Direction.LONG:
		trigger.macd_ds_long = state
	else:
		trigger.macd_ds_short = state

def getMacdDirectionState(direction):
	if direction == Direction.LONG:
		return trigger.macd_ds_long
	else:
		return trigger.macd_ds_short

def setCciDirectionState(direction, state):
	if direction == Direction.LONG:
		trigger.cci_ds_long = state
	else:
		trigger.cci_ds_short = state

def getCciDirectionState(direction):
	if direction == Direction.LONG:
		return trigger.cci_ds_long
	else:
		return trigger.cci_ds_short

def entrySetup():

	if trigger.est_direction:
		
		if trigger.entry_state == EntryState.ONE:
			if entryConfirmation(trigger.est_direction):
				trigger.entry_state = EntryState.COMPLETE
				trigger.re_entry = None
				return confirmation(trigger, EntryType.REGULAR)

def entryConfirmation(direction):
	if utils.plan_state.value in (4,):
		utils.log('entryConfirmation', 'Entry ONE Conf: {0}'.format(
			isABPivotLine(trigger.est_direction)
		))

	return (
		isABPivotLine(trigger.est_direction)
	)

def isBollConfirmation(direction):
	if utils.plan_state.value in (4,):
		utils.log('bollConfirmation', 'Boll Conf: {0}'.format(
			not isCloseABBollOne(trigger.est_direction)
		))

	return (
		not isCloseABBollOne(trigger.est_direction)
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

def isInitialTrade():
	for pos in utils.positions:
		if 'initial' in pos.data and pos.data['initial']:
			return True

	return False

def isReverseBar(direction, reverse=False):
	_open, _, _, close = h4_chart.getCurrentBidOHLC(utils)

	if reverse:
		if direction == Direction.LONG:
			return close > _open
		else:
			return close < _open
	else:
		if direction == Direction.LONG:
			return close < _open
		else:
			return close > _open

def isABCpp(direction, reverse=False):
	_open, _, _, close = h4_chart.getCurrentBidOHLC(utils)

	if reverse:
		if direction == Direction.LONG:
			return close < d_pivots[0]
		else:
			return close > d_pivots[0]
	else:
		if direction == Direction.LONG:
			return close > d_pivots[0]
		else:
			return close < d_pivots[0]

def isMacdzConf(direction, reverse=False):
	hist = round(float(macd_z.getCurrent(utils, m_chart)[2]), 5)

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

def isCloseABBollOne(direction, reverse=False):
	upper, lower = boll_one.getCurrent(utils, m_chart)
	close = m_chart.getCurrentBidOHLC(utils)[3]
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

def isDonchRet(direction, reverse=False):
	high, low = donch.getCurrent(utils, m_chart)
	mid = round(float((high+low)/2), 5)
	_, high, low, _ = m_chart.getCurrentBidOHLC(utils)

	if reverse:
		if direction == Direction.LONG:
			return high > mid
		else:
			return low < mid
	else:
		if direction == Direction.LONG:
			return low < mid
		else:
			return high > mid

def isABPivotLine(direction, reverse=False):
	close = m_chart.getCurrentBidOHLC(utils)[3]
	
	if reverse:
		if direction == Direction.LONG:
			return close < trigger.pivot_line
		else:
			return close > trigger.pivot_line
	else:
		if direction == Direction.LONG:
			return close > trigger.pivot_line
		else:
			return close < trigger.pivot_line

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

def confirmation(trigger, entry_type, reverse=False):
	''' confirm entry '''

	global pending_entry


	if entry_type == EntryType.REGULAR:
		pending_entry = Trigger(direction=trigger.est_direction)

	else:
		pending_entry = Trigger(direction=trigger.re_entry)
		trigger.re_entry = None
		
	if pending_entry.direction != trigger.pivot_direction or time_state == TimeState.EXIT_ONLY:
		entry_type = EntryType.CLOSE

	if (
		not trigger.pivot_line 
		or time_state == TimeState.STOP 
		or (isPosInDir(pending_entry.direction)
			and entry_type != EntryType.CLOSE)
	):
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

	utils.log('', "\nALL POSITIONS:")
	count = 0
	for pos in utils.positions:
		count += 1
		utils.log('', "{}: {} Profit: {} | {}%".format(
			count,
			pos.direction,
			pos.getPipProfit(), 
			pos.getPercentageProfit()
		))

	utils.log('', "---\n")
	utils.log('', "\nSESSIONS:\nCLOSED:")
	count = 0
	for pos in positions:
		count += 1
		utils.log('', "{}{}: {} Profit: {} | {}%".format(
			'\nOPEN:\n' if pos.closetime == None else '',
			count, pos.direction,
			pos.getPipProfit(), 
			pos.getPercentageProfit()
		))


	utils.log('', utils.getTime().strftime('%d/%m/%y %H:%M:%S'))
	utils.log('', "--|\n")
