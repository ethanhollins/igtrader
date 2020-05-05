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
	'exit_profit_one_points': 48,
	'exit_profit_one_perc': 2.0,
	'exit_profit_two_points': 24,
	'exit_profit_two_perc': 1.0,
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
	FIVE = 5
	SIX = 6
	SEVEN = 7
	COMPLETE = 8
	RE_ENTRY_ONE = 9
	RE_ENTRY_TWO = 10
	WAIT = 11

class ExitState(Enum):
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
		
		# Close AB Confirmation
		self.pivot_close_ab_count = 0
		self.pivot_consec_ab_count = 0
		self.entry_close = 0
		self.entry_hl = 0

		# Entry Setup
		self.below_check = False
		self.tag_check = False
		self.ema_tag_check = False
		self.cycle_complete = False
		self.is_non_doji = False

		# Exit Setup
		self.boll_check = False

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

	global cci, boll, ema
	cci = utils.CCI(5)
	boll = utils.BOLL(15, 2)
	ema = utils.EMA(12)

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

	for i in range(len(sess_positions)-1,-1,-1):
		pos = sess_positions[i]
		if not pos.closetime:
			del sess_positions[i]

def setGlobalVars():
	global long_trigger, short_trigger, is_onb
	global pending_entry, pending_entry_details
	global positions, trades
	global time_state, bank
	global sess_positions

	long_trigger = Trigger(direction=Direction.LONG)
	short_trigger = Trigger(direction=Direction.SHORT)
	is_onb = False

	pending_entry = None
	pending_entry_details = None
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
				is_exit = (
					getTotalProfit() >= VARIABLES['exit_profit_one_points'] or
					perc_profit >= VARIABLES['exit_profit_one_perc']
				)
			elif time_state == TimeState.EXIT_PROFIT_TWO:
				is_exit = (
					getTotalProfit() >= VARIABLES['exit_profit_two_points'] or
					perc_profit >= VARIABLES['exit_profit_two_perc']
				)
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
		global pending_entry_details
		pending_entry_details = tuple((entry.entry_type.value,))
		ref = utils.stopAndReverse(
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
		global pending_entry_details
		pending_entry_details = tuple((entry.entry_type.value,))
		if entry.direction == Direction.LONG:
			if entry.entry_type == EntryType.RE_ENTRY:
				tp_price = utils.getAsk(VARIABLES['PRODUCT']) + utils.convertToPrice(VARIABLES['profitrange'])
				tp_price = tp_price if tp_price > entry.tp_price else entry.tp_price
				tp_range = None
			else:
				tp_price = None
				tp_range = VARIABLES['profitrange']
			
			ref = utils.buy(
				VARIABLES['PRODUCT'], 
				utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
				slRange = VARIABLES['stoprange'],
				tpPrice = tp_price, tpRange = tp_range
			)

		else:
			if entry.entry_type == EntryType.RE_ENTRY:
				tp_price = utils.getBid(VARIABLES['PRODUCT']) - utils.convertToPrice(VARIABLES['profitrange'])
				tp_price = tp_price if tp_price < entry.tp_price else entry.tp_price
				tp_range = None
			else:
				tp_price = None
				tp_range = VARIABLES['profitrange']

			ref = utils.sell(
				VARIABLES['PRODUCT'], 
				utils.getLotsize(bank, VARIABLES['risk'], VARIABLES['stoprange']), 
				slRange = VARIABLES['stoprange'],
				tpPrice = tp_price, tpRange = tp_range
			)


def onEntry(pos):
	global pending_entry_details
	pos.data['stop_state'] = StopState.NONE.value
	pos.data['entry_type'] = pending_entry_details[0]

	utils.savePositions()
	sess_positions.append(pos)

	pending_entry_details = None

def closeAllPositions(direction, reverse=False):
	if direction:
		direction = convertToPositionDirection(direction)

	if reverse and direction:
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

		# Calculate Current Profits and other useful info
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
		# Get Dist from entry to tp
		tp_dist = utils.convertToPips(abs(pos.entryprice - pos.tp))

		# Calculate profit point one
		profit_point_one = tp_dist - (VARIABLES['profitrange'] - VARIABLES['profit_points'][0])
		stop_one = tp_dist - (VARIABLES['profitrange'] - VARIABLES['stops'][0])

		# Calculate profit point two
		profit_point_two = tp_dist - (VARIABLES['profitrange'] - VARIABLES['profit_points'][1])
		stop_two = tp_dist - (VARIABLES['profitrange'] - VARIABLES['stops'][1])

		# Calculate profit point three
		profit_point_three = tp_dist - (VARIABLES['profitrange'] - VARIABLES['profit_points'][2])
		stop_three = tp_dist - (VARIABLES['profitrange'] - VARIABLES['stops'][2])

		if pos.data['stop_state'] <= StopState.NONE.value:

			# Set new SL if max profit exceeds profit point
			if max_profit >= profit_point_one:
				if profit >= stop_one + min_dist:
					new_sl = calc_price(utils.convertToPrice(stop_one))
				pos.data['stop_state'] = StopState.BREAKEVEN.value

				utils.savePositions()

		if pos.data['stop_state'] <= StopState.BREAKEVEN.value:

			# If last sl not set, check to set new sl or exit at market
			if c_sl > -stop_one and pos.data['stop_state'] == StopState.BREAKEVEN.value:
				if profit >= stop_one + min_dist:
					new_sl = calc_price(utils.convertToPrice(stop_one))
				elif profit <= stop_one:
					pos.close()
					continue
				
			# Set new SL if max profit exceeds profit point
			if max_profit >= profit_point_two:
				if profit >= stop_two + min_dist:
					new_sl = calc_price(utils.convertToPrice(stop_two))
				pos.data['stop_state'] = StopState.ONE.value

				utils.savePositions()

		if pos.data['stop_state'] <= StopState.ONE.value:

			# If last sl not set, check to set new sl or exit at market
			if c_sl > -stop_two and pos.data['stop_state'] == StopState.ONE.value:
				if profit >= stop_two + min_dist:
					new_sl = calc_price(utils.convertToPrice(stop_two))
				elif profit <= stop_two:
					pos.close()
					continue

			# Set new SL if profit exceeds profit point
			if profit >= profit_point_three:
				new_sl = calc_price(utils.convertToPrice(stop_three))
				pos.data['stop_state'] = StopState.TWO.value

				utils.savePositions()
		
		# Set New Stop Loss
		if new_sl:
			pos.modifySL(
				new_sl			
			)

def pivotSetupOne(trigger):

	# Cross AB T `0`
	if trigger.pivot_state_one == PivotState.ONE:
		if isCciABX(trigger.direction, 0):
			trigger.pivot_state_one = PivotState.TWO
			setNextPivotOne(trigger)
			return pivotSetupOne(trigger)

	elif trigger.pivot_state_one == PivotState.TWO:
		# Set Current pivot
		setNextPivotOne(trigger)
		# Reset on Cross AB CT `0` or
		if isCciABX(trigger.direction, 0, reverse=True):
			trigger.pivot_state_one = PivotState.ONE
			trigger.next_pivot_one = 0
			return
		# Cross AB T `cci_t` and signal confirmation
		elif (
			isCciABX(trigger.direction, VARIABLES['cci_t']) and 
			isCciSignal(trigger.direction)
		):
			trigger.pivot_state_one = PivotState.THREE
			return

	# Cross AB CT `0` and signal angle confirmation
	elif trigger.pivot_state_one == PivotState.THREE:
		setNextPivotOne(trigger)
		if (
			isCciABX(trigger.direction, 0, reverse=True) and
			isCciSignalAngle(trigger.direction, reverse=True)
		):
			trigger.pivot_line = trigger.next_pivot_one

			# Reset
			trigger.pivot_state_one = PivotState.ONE
			trigger.next_pivot_one = 0
			resetPivot(trigger)
			return pivotSetupOne(trigger)

def pivotSetupTwo(trigger):

	# Cross AB CT `cci_t`
	if trigger.pivot_state_two == PivotState.ONE:
		if isCciABX(trigger.direction, 0, reverse=True):
			trigger.pivot_state_two = PivotState.TWO
			return

	# Cross AB T `0`
	elif trigger.pivot_state_two == PivotState.TWO:
		if isCciABX(trigger.direction, 0):
			trigger.pivot_state_two = PivotState.THREE
			return pivotSetupTwo(trigger)

	# Cross AB CT `cci_t`
	elif trigger.pivot_state_two == PivotState.THREE:
		setNextPivotTwo(trigger)
		if isCciABX(trigger.direction, 0, reverse=True):
			# Set if exceeds last pivot
			if trigger.direction == Direction.LONG:
				if not trigger.pivot_line or trigger.next_pivot_two > trigger.pivot_line:
					trigger.pivot_line = trigger.next_pivot_two
					resetPivot(trigger)
			else:
				if not trigger.pivot_line or trigger.next_pivot_two < trigger.pivot_line:
					trigger.pivot_line = trigger.next_pivot_two
					resetPivot(trigger)

			# Reset
			trigger.pivot_state_two = PivotState.ONE
			trigger.next_pivot_two = 0
			return pivotSetupTwo(trigger)

def entrySetup(trigger):

	if trigger.pivot_line:

		# Check for wholly AB candle after close confirmation
		if (
			trigger.entry_state != EntryState.ONE and
			trigger.entry_state != EntryState.COMPLETE
		):
			if isWhollyABEntryLine(trigger):
				trigger.below_check = True

		# Close AB confirmation
		if trigger.entry_state == EntryState.ONE:
			if trigger.pivot_close_ab_count > 0:
				setEntryHL(trigger)

			if isCloseABPivotLine(trigger.direction, trigger.pivot_line):
				# BB and non-doji (0.5) Candle Count
				if trigger.pivot_close_ab_count == 0:
					if not isDoji(0.5) and isBB(trigger.direction):
						trigger.pivot_close_ab_count += 1
						cancelPivot(trigger.direction, reverse=True)

						trigger.entry_close = round(m_chart.getCurrentBidOHLC()[3], 5)
						trigger.entry_hl = 0
						setEntryHL(trigger)
						return

				elif trigger.pivot_close_ab_count == 1:
					# Second BB and non-doji (0.5)
					if not isDoji(0.5) and isBB(trigger.direction):
						trigger.entry_state = EntryState.TWO
						trigger.entry_type = EntryType.REGULAR
						trigger.tp_price = 0
						resetEntry(trigger)
						return entrySetup(trigger)

					# Two consecutive non-doji (1.0)
					elif isWhollyABPivotLine(trigger) and not isBB(trigger.direction):

						# Check if at least one bar non-doji (1.0)
						if not isDoji(1.0):
							trigger.is_non_doji = True
							trigger.pivot_consec_ab_count += 1
						elif trigger.pivot_consec_ab_count == 1:
							if trigger.is_non_doji:
								trigger.pivot_consec_ab_count += 1
							else:
								trigger.pivot_consec_ab_count = 0
						else:
							trigger.pivot_consec_ab_count += 1

						if trigger.pivot_consec_ab_count == 2:
							trigger.entry_state = EntryState.TWO
							trigger.entry_type = EntryType.REGULAR
							trigger.tp_price = 0
							resetEntry(trigger)
							return entrySetup(trigger)
					# Reset consecutive count
					else:
						trigger.pivot_consec_ab_count = 0
			else:
				trigger.pivot_consec_ab_count = 0

		# Cross AB CT `cci_ct`
		elif trigger.entry_state == EntryState.TWO:
			if isCciABX(trigger.direction, VARIABLES['cci_ct'], reverse=True):
				trigger.entry_state = EntryState.THREE
				return
		
		elif trigger.entry_state == EntryState.THREE:
			# Tagging entry line
			if isTaggingEntryLine(trigger):
				trigger.tag_check = True
			# Tagging ema
			if isTaggingEma(trigger.direction) and not trigger.cycle_complete:
				trigger.ema_tag_check = True
			# Tag reset on cci CT cross
			if isCciABX(trigger.direction, VARIABLES['cci_ct'], reverse=True):
				trigger.tag_check = False
				trigger.ema_tag_check = False

			# T cci cross
			if isCciABX(trigger.direction, VARIABLES['cci_t']):
				trigger.entry_state = EntryState.FOUR
				return entrySetup(trigger)
		
		# Check qualifying factors
		elif trigger.entry_state == EntryState.FOUR:
			if (
				trigger.tag_check or
				trigger.below_check or
				trigger.ema_tag_check
			):
				trigger.entry_state = EntryState.FIVE
				return entrySetup(trigger)
			else:
				trigger.entry_state = EntryState.TWO
				trigger.cycle_complete = True
				return

		# Entry on BB and non-doji (0.2)
		elif trigger.entry_state == EntryState.FIVE:
			if isBB(trigger.direction) and not isDoji(0.2):
				trigger.entry_state = EntryState.COMPLETE
				if confirmation(trigger):
					trigger.entry_type = EntryType.RE_ENTRY
					return True

		# Reset once close below pivot
		elif trigger.entry_state == EntryState.COMPLETE:
			if isCloseABPivotLine(trigger.direction, trigger.pivot_line, reverse=True):
				trigger.entry_state = EntryState.ONE
				return entrySetup(trigger)

		# Re-entry Cross AB `cci_t`
		elif trigger.entry_state == EntryState.RE_ENTRY_ONE:
			if isCciABX(trigger.direction, VARIABLES['cci_t']):
				trigger.entry_state = EntryState.RE_ENTRY_TWO
				return entrySetup(trigger)

		# Re-entry on BB and non-doji (0.2)
		elif trigger.entry_state == EntryState.RE_ENTRY_TWO:
			if isBB(trigger.direction) and not isDoji(0.2):
				return confirmation(trigger)

# Exit on boll tag and close ab rev-pivot line
def exitSetup(trigger):

	if trigger.exit_state == ExitState.ONE:

		if isPosInDir(trigger.direction, reverse=True):
			if isBollTagged():
				trigger.boll_check = True

		if trigger.boll_check:
			if isCloseABPivotLine(trigger.direction, trigger.pivot_line):
				if not isDoji(0.5) and isBB(trigger.direction):
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

def resetEntry(trigger):
	trigger.below_check = False
	trigger.tag_check = False
	trigger.ema_tag_check = False
	trigger.cycle_complete = False
	trigger.is_non_doji = False

def resetPivot(trigger):
	trigger.pivot_close_ab_count = 0
	trigger.pivot_consec_ab_count = 0

	trigger.exit_state = ExitState.ONE

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

# Exit on finished session w/ CCI angle
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

def isWhollyABPivotLine(trigger):
	_, high, low, _ = m_chart.getCurrentBidOHLC()

	if trigger.direction == Direction.LONG:
		return low > trigger.pivot_line
	else:
		return high < trigger.pivot_line

def isWhollyABEntryLine(trigger):
	_, high, low, _ = m_chart.getCurrentBidOHLC()

	if trigger.direction == Direction.LONG:
		return (
			not isDoji(0.5) and
			high < trigger.entry_close
		)
	else:
		return (
			not isDoji(0.5) and
			low > trigger.entry_close
		)

def isTaggingEntryLine(trigger):
	_, high, low, _ = m_chart.getCurrentBidOHLC()

	if trigger.direction == Direction.LONG:
		return low <= trigger.entry_hl
	else:
		return high >= trigger.entry_hl

def isTaggingEma(direction):
	_, high, low, _ = m_chart.getCurrentBidOHLC()
	ema_val = ema.getCurrent(m_chart)

	if direction == Direction.LONG:
		return low <= ema_val
	else:
		return high >= ema_val

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
	
	long_trigger.boll_check = False
	short_trigger.boll_check = False
	utils.log("confirmation", '{0} {1}'.format(pending_entry.direction, pending_entry.entry_type))
	return True

def prettyPrintTrigger(trigger):
	per_line = 3
	indent = 2
	result = ''
	items = list(trigger.items())
	longest_str = max([len(i[0]) + len(str(i[1])) for i in items])

	for i in range(len(items)):
		if i % per_line == 0:
			result += '\n{}'.format(' '*indent)
		result += '\"{}\": {}, {}'.format(
			items[i][0], str(items[i][1]),
			' '*( longest_str - (len(items[i][0]) + len(str(items[i][1]))) ), 
		)
	return result

def report():
	''' Prints report for debugging '''
	if utils.plan_state.value in (1,):
		utils.log('', "\n[{}] Report:".format(utils.account.accountid))

	utils.log('', "")
	utils.log('', 'TS: {} OHLC: {}'.format(m_chart.c_ts, m_chart.getCurrentBidOHLC()))
	utils.log('IND','CCI: {:.5f} |EMA: {:.5f} |BOLL: {}'.format(
		cci.getCurrent(m_chart), ema.getCurrent(m_chart), boll.getCurrent(m_chart)
	))
	utils.log('', 'TimeState: {}\n'.format(time_state))
	utils.log('', "LONG Trigger:{}\n".format(prettyPrintTrigger(long_trigger)))
	utils.log('', "SHORT Trigger:{}".format(prettyPrintTrigger(short_trigger)))

	utils.log('', "\nPOSITIONS:")
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

			utils.log('', "{}: {} Profit: {:.1f} | {:.2f}%\tENTRY: {:.5f} | SL: {:.5f} -> {:.1f} | TP: {:.5f}".format(
				count,
				pos.direction,
				pos.getPipProfit(), 
				pos.getPercentageProfit(),
				pos.entryprice,
				pos.sl,
				sl_pips,
				pos.tp
			))

	utils.log('', utils.getTime().strftime('%d/%m/%y %H:%M:%S'))
	utils.log('', "--|\n")
