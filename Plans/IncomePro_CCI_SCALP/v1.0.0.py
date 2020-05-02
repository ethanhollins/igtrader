import Constants
from enum import Enum
import numpy as np
import datetime

VARIABLES = {
	'PRODUCT': Constants.GBPUSD,
	'BANK': None,
	'risk': 0.5,
	'stoprange': 12.0,
	'profitrange': 16.0,
	'stops': [0,5,10],
	'profit_points': [12,14,15],
	'exit_profit_one': 2.0,
	'exit_profit_two': 1.0,
	'profit_target': 48,
	'loss_multi': 4,
	'CCI': None,
	'cci_t': 100,
	'cci_ct': 25,
	'MISC': None,
	'doji': 0.5,
}

class Direction(Enum):
	LONG = 1
	SHORT = 2

class EntryState(Enum):
	ONE = 1
	TWO = 2
	THREE = 3
	FOUR = 4
	FIVE_A = 5
	FIVE_B = 6
	SIX = 7
	SEVEN = 8
	COMPLETE = 9
	RE_ENTRY_ONE = 10
	RE_ENTRY_TWO = 11
	WAIT = 12

class EntryState(Enum):
	ONE = 1
	COMPLETE = 2

class PivotState(Enum):
	ONE = 1
	TWO = 2
	THREE = 3
	COMPLETE = 4

class EntryType(Enum):
	REGULAR = 1
	RE_ENTRY = 2

class StopState(Enum):
	NONE = 1
	BREAKEVEN = 2
	ONE = 3
	TWO = 4

class TimeState(Enum):
	TRADING = 1
	EXIT_PROFIT_ONE = 2
	EXIT_PROFIT_TWO = 3
	STOPPED = 4

class Trigger(dict):

	def __init__(self, direction=None):
		self.direction = direction

		self.entry_state = EntryState.ONE
		self.exit_state = ExitState.ONE
		self.pivot_state_one = PivotState.ONE
		self.pivot_state_two = PivotState.ONE
		self.entry_type = EntryType.REGULAR
		self.tp_price = 0

		self.next_pivot_one = 0
		self.next_pivot_two = 0
		self.pivot_line = 0
		
		self.pivot_close_ab_count = 0
		self.entry_close = 0
		self.entry_hl = 0

		# Entry Setup
		self.below_check = False
		self.tag_check = False

		# Exit Setup
		self.boll_check = False
		self.close_check = False

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

	global cci, boll
	cci = utils.CCI(5)
	boll = utils.BOLL(15, 2)

def setup(utilities):
	global utils, m_chart, bank
	utils = utilities
	if len(utils.charts) > 0:
		for chart in utils.charts:
			if chart.period == Constants.ONE_MINUTE:
				m_chart = chart
	else:
		m_chart = utils.getChart(VARIABLES['PRODUCT'], Constants.ONE_MINUTE)

	bank = utils.getTradableBank()

def setGlobalVars():
	global long_trigger, short_trigger, is_onb
	global pending_entry
	global positions, trades
	global time_state, bank
	global sess_positions

	long_trigger = Trigger(direction=Direction.LONG)
	short_trigger = Trigger(direction=Direction.SHORT)
	is_onb = False

	pending_entry = None
	bank = utils.getTradableBank()
	time_state = TimeState.TRADING

	sess_positions = []

def onNewBar(chart):
	global is_onb
	is_onb = True

	if chart.period == Constants.ONE_MINUTE:
		
		if utils.plan_state.value in (4,):
			time = utils.convertTimestampToDatetime(utils.getLatestTimestamp())
			london_time = utils.convertTimezone(time, 'Europe/London')


			utils.log("\nTime", time.strftime('%d/%m/%y %H:%M:%S'))
			utils.log("London Time", london_time.strftime('%d/%m/%y %H:%M:%S') + '\n')
			utils.log('OHLC', m_chart.getCurrentBidOHLC())
			utils.log('IND','CCI: {}'.format(round(float(cci.getCurrent(m_chart)),5)))
		elif utils.plan_state.value in (1,):
			utils.log("\n[{}] onNewBar ({})".format(
				utils.account.accountid, utils.name), 
				'{} {}'.format(utils.getTime().strftime('%d/%m/%y %H:%M:%S'), m_chart.getCurrentBidOHLC())
			)

		checkTime()
		runSequence()
		if utils.plan_state.value in (4,1):
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
		
		is_exit = False
		perc_profit = (getTotalProfit() / VARIABLES['stoprange']) * VARIABLES['risk']
		if getTotalProfit() >= VARIABLES['profit_target']:
			is_exit = True

		elif perc_profit <= -(VARIABLES['risk'] * VARIABLES['loss_multi']):
			is_exit = True

		elif time_state.value >= TimeState.EXIT_PROFIT_ONE.value:
			if time_state == TimeState.EXIT_PROFIT_ONE:
				is_exit = perc_profit >= VARIABLES['exit_profit_one']
			elif time_state == TimeState.EXIT_PROFIT_TWO:
				is_exit = perc_profit >= VARIABLES['exit_profit_two']
			else:
				is_exit = True

		if is_exit:
			closeAllPositions(None)
			pending_entry = None

			time_state = TimeState.STOPPED
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
		utils.stopAndReverse(
			VARIABLES['PRODUCT'], 
			utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
			slRange = VARIABLES['stoprange'],
			tpRange = VARIABLES['profitrange']
		)

def handleRegularEntry(entry):
	''' 
	Handle regular entries 
	and check if tradable conditions are met.
	'''

	if bank:

		if entry.direction == Direction.LONG:
			if entry.entry_type == EntryType.RE_ENTRY:
				tp = utils.getAsk(VARIABLES['PRODUCT']) + utils.convertToPrice(VARIABLES['profitrange'])
				tp = tp if tp > entry.tp_price else entry.tp_price
			else:
				tp = VARIABLES['profitrange']
			
			utils.buy(
				VARIABLES['PRODUCT'], 
				utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
				slRange = VARIABLES['stoprange'],
				tpRange = tp
			)

		else:
			if entry.entry_type == EntryType.RE_ENTRY:
				tp = utils.getBid(VARIABLES['PRODUCT']) - utils.convertToPrice(VARIABLES['profitrange'])
				tp = tp if tp < entry.tp_price else entry.tp_price
			else:
				tp = VARIABLES['profitrange']

			utils.sell(
				VARIABLES['PRODUCT'], 
				utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
				slRange = VARIABLES['stoprange'],
				tpPrice = tp
			)

def onEntry(pos):
	pos.data['stop_state'] = StopState.NONE.value
	pos.data['entry_type'] = entry.entry_type.value
	utils.savePositions()

	sess_positions.append(pos)

def closeAllPositions(direction, reverse=False):
	direction = convertToPositionDirection(direction)

	if reverse:
		if direction == Constants.BUY:
			direction = Constants.SELL
		else:
			direction = Constants.BUY

	for pos in utils.positions:
		if direction == None:
			pos.close()

		elif pos.direction == direction:
			pos.close()

def getTotalProfit():
	result = 0
	for pos in sess_positions:
		result += pos.getPipProfit()
	return result

def onTakeProfit(pos):
	utils.log("onTakeProfit ", '')

	if pos.direction == Constants.BUY:
		long_trigger.entry_state = EntryState.WAIT
	else:
		short_trigger.entry_state = EntryState.WAIT

def onStopLoss(pos):
	utils.log("onStopLoss", '')

	if (
		pos.data['entry_type'] == EntryType.REGULAR.value and 
		pos.data['stop_state'] == StopState.NONE.value
	):
		if pos.direction == Constants.BUY:
			if long_trigger.entry_type == EntryType.RE_ENTRY:
				long_trigger.entry_state = EntryState.RE_ENTRY_ONE
				long_trigger.tp_price = pos.tp
		else:
			if short_trigger.entry_type == EntryType.RE_ENTRY:
				short_trigger.entry_state = EntryState.RE_ENTRY_ONE
				short_trigger.tp_price = pos.tp
	elif pos.data['stop_state'] > StopState.NONE.value:
		if pos.direction == Constants.BUY:
			long_trigger.entry_state = EntryState.WAIT
		else:
			short_trigger.entry_state = EntryState.WAIT

def checkTime():
	''' 
	Checks current time and initiates 
	closing sequence where necessary.
	'''
	global time_state

	time = utils.convertTimestampToDatetime(utils.getLatestTimestamp())
	london_time = utils.convertTimezone(time, 'Europe/London')

	start = london_time.replace(hour=6,minute=0,second=0,microsecond=0)
	exit_profit_one = london_time.replace(hour=15,minute=0,second=0,microsecond=0)
	exit_profit_two = london_time.replace(hour=17,minute=30,second=0,microsecond=0)
	stopped = london_time.replace(hour=19,minute=30,second=0,microsecond=0)

	if start <= london_time < stopped:
		if london_time >= exit_profit_two:
			time_state = TimeState.EXIT_PROFIT_TWO
		elif london_time >= exit_profit_one:
			time_state = TimeState.EXIT_PROFIT_ONE
		elif time_state != TimeState.TRADING:
			global sess_positions, bank
			sess_positions = []
			bank = utils.getTradableBank()
			time_state = TimeState.TRADING
	else:
		time_state = TimeState.STOPPED

def runSequence():
	
	pivotSetupOne(long_trigger)
	pivotSetupOne(short_trigger)

	pivotSetupTwo(long_trigger)
	pivotSetupTwo(short_trigger)

	entrySetup(long_trigger)
	entrySetup(short_trigger)

	exitSetup(long_trigger)
	exitSetup(short_trigger)

	if time_state == TimeState.STOPPED:
		isStoppedExit()

	positionStopIncrement()

def positionStopIncrement():
	bid = m_chart.getCurrentBidOHLC()
	ask = m_chart.getCurrentAskOHLC()

	min_dist = 5.0

	for pos in utils.positions:
		if not 'stop_state' in pos.data:
			continue

		if pos.direction == Constants.BUY:
			max_profit = utils.convertToPips(bid[1] - pos.entryprice)
			c_sl = utils.convertToPips(pos.entryprice - pos.sl)
			profit = utils.convertToPips(bid[3] - pos.entryprice)
			calc_price = lambda x: round(pos.entryprice + x, 5)
		else:
			max_profit = utils.convertToPips(pos.entryprice - ask[2])
			c_sl = utils.convertToPips(pos.sl - pos.entryprice)
			profit = utils.convertToPips(pos.entryprice - ask[3])
			calc_price = lambda x: round(pos.entryprice - x, 5)


		new_sl = None
		if pos.data['stop_state'] <= StopState.NONE.value:
			if max_profit >= VARIABLES['profit_points'][0]:
				if profit >= VARIABLES['stops'][0] + min_dist:
					new_sl = calc_price(utils.convertToPrice(VARIABLES['stops'][0]))
				pos.data['stop_state'] = StopState.BREAKEVEN.value

				utils.savePositions()

		if pos.data['stop_state'] <= StopState.BREAKEVEN.value:
			if c_sl > -VARIABLES['stops'][0] and pos.data['stop_state'] == StopState.BREAKEVEN.value:
				if profit >= VARIABLES['stops'][0] + min_dist:
					new_sl = calc_price(utils.convertToPrice(VARIABLES['stops'][0]))

			if max_profit >= VARIABLES['profit_points'][1]:
				if profit >= VARIABLES['stops'][1] + min_dist:
					new_sl = calc_price(utils.convertToPrice(VARIABLES['stops'][1]))
				pos.data['stop_state'] = StopState.ONE.value

				utils.savePositions()

		if pos.data['stop_state'] <= StopState.ONE.value:
			if c_sl > -VARIABLES['stops'][1] and pos.data['stop_state'] == StopState.ONE.value:
				if profit >= VARIABLES['stops'][1] + min_dist:
					new_sl = calc_price(utils.convertToPrice(VARIABLES['stops'][1]))

			# Get Dist from entry to tp
			tp_dist = utils.convertToPips(abs(pos.entryprice - pos.tp))
			profit_point = tp_dist - (VARIABLES['profitrange'] - VARIABLES['profit_points'][2])
			stop = tp_dist - (VARIABLES['profitrange'] - VARIABLES['stops'][2])

			if profit >= profit_point:
				new_sl = calc_price(utils.convertToPrice(stop))
				pos.data['stop_state'] = StopState.TWO.value

				utils.savePositions()
		
		if new_sl:
			pos.modifySL(
				new_sl			
			)

def pivotSetupOne(trigger):

	if trigger.pivot_state_one == PivotState.ONE:
		if isCciABX(trigger.direction, 0):
			trigger.pivot_state_one = PivotState.TWO
			setNextPivotOne(trigger)
			return pivotSetupOne(trigger)

	elif trigger.pivot_state_one == PivotState.TWO:
		setNextPivotOne(trigger)
		if isCciABX(trigger.direction, 0, reverse=True):
			trigger.pivot_state_one = PivotState.ONE
			trigger.next_pivot_one = 0
			return
		elif (
			isCciABX(trigger.direction, VARIABLES['cci_t']) and 
			isCciSignal(trigger.direction)
		):
			trigger.pivot_state_one = PivotState.THREE
			return

	elif trigger.pivot_state_one == PivotState.THREE:
		setNextPivotOne(trigger)
		if (
			isCciABX(trigger.direction, 0, reverse=True) and
			isCciSignalAngle(trigger.direction, reverse=True)
		):
			trigger.pivot_line = trigger.next_pivot_one

			trigger.pivot_state_one = PivotState.ONE
			trigger.next_pivot_one = 0
			resetPivot(trigger)
			return pivotSetupOne(trigger)

def pivotSetupTwo(trigger):

	if trigger.pivot_state_two == PivotState.ONE:
		if isCciABX(trigger.direction, VARIABLES['cci_t'], reverse=True):
			trigger.pivot_state_two = PivotState.TWO
			return

	elif trigger.pivot_state_two == PivotState.TWO:
		if isCciABX(trigger.direction, 0):
			trigger.pivot_state_two = PivotState.THREE
			return pivotSetupTwo(trigger)

	elif trigger.pivot_state_two == PivotState.THREE:
		setNextPivotTwo(trigger)
		if isCciABX(trigger.direction, VARIABLES['cci_t'], reverse=True):
			if trigger.direction == Direction.LONG:
				if not trigger.pivot_line or trigger.next_pivot_two > trigger.pivot_line:
					trigger.pivot_line = trigger.next_pivot_two
					resetPivot(trigger)
			else:
				if not trigger.pivot_line or trigger.next_pivot_two < trigger.pivot_line:
					trigger.pivot_line = trigger.next_pivot_two
					resetPivot(trigger)

			trigger.pivot_state_two = PivotState.ONE
			trigger.next_pivot_two = 0
			return pivotSetupTwo(trigger)

def entrySetup(trigger):

	if trigger.pivot_line:

		if (
			trigger.entry_state != EntryState.ONE and
			trigger.entry_state != EntryState.COMPLETE
		):
			if isWhollyABEntryLine(trigger):
				trigger.below_check = True

		if trigger.entry_state == EntryState.ONE:
			if isCloseABPivotLine(trigger.direction, trigger.pivot_line):

				if not isDoji(0.5) and isBB(trigger.direction):
					trigger.pivot_close_ab_count += 1
					if trigger.pivot_close_ab_count == 1:
						cancelPivot(trigger.direction, reverse=True)
						trigger.close_check = True

						trigger.entry_close = round(m_chart.getCurrentBidOHLC()[3], 5)
						trigger.entry_hl = 0
						setEntryHL(trigger)
						return

					elif trigger.pivot_close_ab_count == 2:
						trigger.entry_state = EntryState.TWO
						trigger.entry_type = EntryType.REGULAR
						trigger.tp_price = 0
						setEntryHL(trigger)
						return entrySetup(trigger)

		elif trigger.entry_state == EntryState.TWO:
			if isCciABX(trigger.direction, VARIABLES['cci_ct'], reverse=True):
				trigger.entry_state = EntryState.THREE
				return
		
		elif trigger.entry_state == EntryState.THREE:
			if isTaggingEntryLine(trigger):
				trigger.tag_check = True
			if isCciABX(trigger.direction, VARIABLES['cci_ct'], reverse=True):
				trigger.tag_check = False

			if isCciABX(trigger.direction, VARIABLES['cci_t']):
				trigger.entry_state = EntryState.FOUR
				return entrySetup(trigger)
		
		elif trigger.entry_state == EntryState.FOUR:
			if trigger.tag_check:
				trigger.entry_state = EntryState.FIVE_A
				return entrySetup(trigger)
			if trigger.below_check:
				trigger.entry_state = EntryState.FIVE_B
				return entrySetup(trigger)
			else:
				trigger.entry_state = EntryState.TWO
				return

		elif trigger.entry_state == EntryState.FIVE_A:
			if isBB(trigger.direction) and not isDoji(0.2):
				trigger.entry_state = EntryState.COMPLETE
				if confirmation(trigger):
					trigger.entry_type = EntryType.RE_ENTRY
					return True

		elif trigger.entry_state == EntryState.FIVE_B:
			if isBB(trigger.direction) and not isDoji(0.5):
				trigger.entry_state = EntryState.COMPLETE
				if confirmation(trigger):
					trigger.entry_type = EntryType.RE_ENTRY
					return True

		elif trigger.entry_state == EntryState.COMPLETE:
			if isCloseABPivotLine(trigger.direction, trigger.pivot_line, reverse=True):
				trigger.entry_state = EntryState.ONE
				return entrySetup(trigger)

		elif trigger.entry_state == EntryState.RE_ENTRY_ONE:
			if isCciABX(trigger.direction, VARIABLES['cci_t']):
				trigger.entry_state = EntryState.RE_ENTRY_TWO
				return entrySetup(trigger)

		elif trigger.entry_state == EntryState.RE_ENTRY_TWO:
			if isBB(trigger.direction) and not isDoji(0.2):
				return confirmation(trigger)

def exitSetup(trigger):

	if trigger.exit_state == ExitState.ONE:

		if isPosInDir(trigger.direction, reverse=True):
			if isBollTagged():
				trigger.boll_check = True

		if trigger.boll_check and trigger.close_check:
			closeAllPositions(trigger.direction, reverse=True)
			trigger.exit_state = ExitState.COMPLETE
			return

def setNextPivotOne(trigger):
	_, high, low, _ = m_chart.getCurrentBidOHLC()

	if trigger.direction == Direction.LONG:
		new_pl = round(high + utils.convertToPrice(0.5), 5)
		if trigger.next_pivot_one == 0 or new_pl > trigger.next_pivot_one:
			trigger.next_pivot_one = new_pl
	else:
		new_pl = round(low - utils.convertToPrice(0.5), 5)
		if trigger.next_pivot_one == 0 or new_pl < trigger.next_pivot_one:
			trigger.next_pivot_one = new_pl

def setNextPivotTwo(trigger):
	_, high, low, _ = m_chart.getCurrentBidOHLC()

	if trigger.direction == Direction.LONG:
		new_pl = round(high + utils.convertToPrice(0.5), 5)
		if trigger.next_pivot_two == 0 or new_pl > trigger.next_pivot_two:
			trigger.next_pivot_two = new_pl
	else:
		new_pl = round(low - utils.convertToPrice(0.5), 5)
		if trigger.next_pivot_two == 0 or new_pl < trigger.next_pivot_two:
			trigger.next_pivot_two = new_pl

def setEntryHL(trigger):
	ohlc = m_chart.getCurrentBidOHLC()

	if trigger.direction == Direction.LONG:
		if trigger.entry_hl == 0 or ohlc[1] > trigger.entry_hl:
			trigger.entry_hl = round(ohlc[1], 5)
	else:
		if trigger.entry_hl == 0 or ohlc[2] < trigger.entry_hl:
			trigger.entry_hl = round(ohlc[2], 5)

def resetPivot(trigger):
	trigger.below_check = False
	trigger.tag_check = False
	trigger.pivot_close_ab_count = 0

	trigger.exit_state = ExitState.ONE
	trigger.boll_check = False
	trigger.close_check = False

def cancelPivot(direction, reverse=False):
	if reverse:
		if direction == Direction.LONG:
			short_trigger.entry_state = EntryState.COMPLETE
			short_trigger.entry_type = EntryType.REGULAR
			resetPivot(short_trigger)
			entrySetup(short_trigger)
		else:
			long_trigger.entry_state = EntryState.COMPLETE
			long_trigger.entry_type = EntryType.REGULAR
			resetPivot(long_trigger)
			entrySetup(long_trigger)
	else:
		if direction == Direction.LONG:
			if long_trigger.entry_state != EntryState.WAIT:
				long_trigger.entry_state = EntryState.ONE
				resetPivot(long_trigger)
		else:
			if short_trigger.entry_state != EntryState.WAIT:
				short_trigger.entry_state = EntryState.ONE
				resetPivot(short_trigger)

def isStoppedExit():
	for pos in utils.positions:
		if pos.getPipProfit() >= 0:
			direction = convertToPlanDirection(pos.direction)
			if isCciRevAngle(direction):
				closeAllPositions(None)

def isCloseABPivotLine(direction, pivot_line, reverse=False):
	close = m_chart.getCurrentBidOHLC()[3]

	if reverse:
		if direction == Direction.LONG:
			return close < pivot_line
		else:
			return close > pivot_line
	else:
		if direction == Direction.LONG:
			return close > pivot_line
		else:
			return close < pivot_line

def isWhollyABEntryLine(trigger):
	_open, _, _, close = m_chart.getCurrentBidOHLC()

	if trigger.direction == Direction.LONG:
		return (
			not isDoji(0.5) and
			_open < trigger.entry_close and close < trigger.entry_close
		)
	else:
		return (
			not isDoji(0.5) and
			_open > trigger.entry_close and close > trigger.entry_close
		)

def isTaggingEntryLine(trigger):
	_, high, low, _ = m_chart.getCurrentBidOHLC()

	if trigger.direction == Direction.LONG:
		return low <= trigger.entry_hl
	else:
		return high >= trigger.entry_hl

def isCciABX(direction, x, reverse=False):
	chidx = round(float(cci.getCurrent(m_chart)),5)

	if reverse:
		if direction == Direction.LONG:
			return chidx < -x
		else:
			return chidx > x
	else:
		if direction == Direction.LONG:
			return chidx > x
		else:
			return chidx < -x

def isCciRevAngle(direction, reverse=False):
	chidx = cci.get(m_chart, 0, 2)
	prev = chidx[0]
	curr = chidx[1]

	if reverse:
		if direction == Direction.LONG:
			return prev < curr
		else:
			return prev > curr
	else:
		if direction == Direction.LONG:
			return prev > curr
		else:
			return prev < curr

def isCciSignal(direction, reverse=False):
	chidx = cci.get(m_chart, 0, 2)
	signal = sum(chidx) / len(chidx)

	if reverse:
		if direction == Direction.LONG:
			return signal < 0
		else:
			return signal > 0
	else:
		if direction == Direction.LONG:
			return signal > 0
		else:
			return signal < 0

def isCciSignalAngle(direction, reverse=False):
	chidx = cci.get(m_chart, 0, 4)
	signal_prev = sum(chidx[:2]) / 2
	signal_curr = sum(chidx[2:4]) / 2

	if reverse:
		if direction == Direction.LONG:
			return signal_curr < signal_prev
		else:
			return signal_curr > signal_prev
	else:
		if direction == Direction.LONG:
			return signal_curr > signal_prev
		else:
			return signal_curr < signal_prev

def isBollTagged():
	_, high, low, _ = m_chart.getCurrentBidOHLC()
	upper, lower = boll.getCurrent(m_chart)

	return (
		high >= upper or
		low <= lower
	)

def isBB(direction, reverse=False):
	_open, _, _, close = m_chart.getCurrentBidOHLC()

	if reverse:
		if direction == Direction.LONG:
			return _open > close
		else:
			return close > _open
	else:
		if direction == Direction.LONG:
			return close > _open
		else:
			return _open > close

def isDoji(size):
	_open, _, _, close = m_chart.getCurrentBidOHLC()
	return utils.convertToPips(abs(_open - close)) < size

def convertToPlanDirection(direction):
	if direction == Constants.BUY:
		return Direction.LONG
	else:
		return Direction.SHORT

def convertToPositionDirection(direction):
	if direction == Direction.LONG:
		return Constants.BUY
	else:
		return Constants.SELL

def isPosInDir(direction, reverse=False):
	for pos in utils.positions:
		pos_direction = convertToPlanDirection(pos.direction)

		if reverse:
			if pos_direction != direction:
				return True
		else:
			if pos_direction == direction:
				return True

	return False

def confirmation(trigger, reverse=False):
	''' confirm entry '''

	global pending_entry

	if reverse:
		pending_entry = Trigger(direction=trigger.direction)
		pending_entry.setDirection(trigger.direction, reverse=True)
		pending_entry.entry_type = trigger.entry_type
		pending_entry.tp_price = trigger.tp_price
	else:
		pending_entry = Trigger(direction=trigger.direction)
		pending_entry.entry_type = trigger.entry_type
		pending_entry.tp_price = trigger.tp_price

	if (isPosInDir(pending_entry.direction)):
		pending_entry = None
		return False
		
	utils.log("confirmation", '{0} {1}'.format(pending_entry.direction, pending_entry.entry_type))
	return True

def report():
	''' Prints report for debugging '''
	if utils.plan_state.value in (1,):
		utils.log('', "\n[{}] Report:".format(utils.account.accountid))

	utils.log('', "")
	utils.log('IND','CCI: {:.5f}'.format(cci.getCurrent(m_chart)))
	utils.log('', 'TS: {} OHLC: {}'.format(m_chart.c_ts, m_chart.getCurrentBidOHLC()))
	utils.log('', 'TimeState: {}\n'.format(time_state))
	utils.log('', "LONG T: {}\n".format(long_trigger))
	utils.log('', "SHORT T: {}".format(short_trigger))

	utils.log('', "\nSESSION POSITIONS:")
	count = 0
	for pos in sess_positions:
		count += 1

		if pos.closetime:
			utils.log('', "{}: {} Profit: {} | {}%".format(
				count,
				pos.direction,
				pos.getPipProfit(), 
				pos.getPercentageProfit()
			))
		else:
			if pos.direction == Constants.BUY:
				sl_pips = utils.convertToPips(pos.entryprice - pos.sl)
			else:
				sl_pips = utils.convertToPips(pos.sl - pos.entryprice)

			utils.log('', "{}: {} Profit: {} | {}% ENTRY: {} SL: {} | {}".format(
				count,
				pos.direction,
				pos.getPipProfit(), 
				pos.getPercentageProfit(),
				pos.entryprice,
				pos.sl,
				sl_pips
			))

	utils.log('', utils.getTime().strftime('%d/%m/%y %H:%M:%S'))
	utils.log('', "--|\n")
