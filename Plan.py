from Position import Position
from enum import Enum
from Backtester import Backtester
import importlib.util
import Constants
import time
import json
import traceback
import sys

from Indicators.ATR import ATR
from Indicators.BOLL import BOLL
from Indicators.CCI import CCI
from Indicators.KELT import KELT
from Indicators.MACD import MACD
from Indicators.MAE import MAE
from Indicators.RSI import RSI
from Indicators.SMA import SMA
from Indicators.DONCH import DONCH
from Indicators.DONCH_CMC import DONCH_CMC

START_OFF = 1000

class PlanState(Enum):
	STOPPED = 0
	STARTED = 1
	BACKTEST = 2

class Plan(object):

	def __init__(self, account, idx, name, variables, storage):
		self.account = account
		self.idx = idx
		self.name = name

		self.positions = []
		self.closed_positions = []
		self.charts = []
		self.indicators = []

		self.plan_state = PlanState.STOPPED
		self.variables = variables
		self.storage = storage

		self.c_ts = 0
		self.needs_save = False

		self.initialize()
	
	'''
	Utilities
	'''

	def initialize(self):
		self.plan_state = PlanState.BACKTEST

		self.getBankConfig()

		self.module = self.execPlan()
		self.setPlanVariables()
		self.module.init(self)

		chart = self.getLowestPeriodChart()
		start_ts = chart.getTimestampAtOffset(max(chart.bids_ts.size-START_OFF, 0))

		bt = Backtester(self.account.root, self.name, self.variables)
		self.module, _ = bt.backtestRun(start=start_ts, plan=self)
		
		self.c_ts = bt.c_ts
		while self.c_ts < self.getLatestChartTimestamp():
			bt = Backtester(self.account.root, self.name, self.variables)
			self.module, _ = bt.backtestRun(start=self.c_ts, start_off=1, plan=self)
			self.c_ts = bt.c_ts
		self.module.setup(self)

		self.updatePositions()
		self.getSavedPositions()
		self.savePositions()
		self.plan_state = PlanState.STARTED

	def execPlan(self):
		path = 'Plans/{0}.py'.format(self.name)
		spec = importlib.util.spec_from_file_location(self.name, path)
		module = importlib.util.module_from_spec(spec)
		sys.modules[spec.name] = module
		spec.loader.exec_module(module)
		return module

	def setPlanVariables(self):
		for k in self.variables:
			if k in self.module.VARIABLES:
				self.module.VARIABLES[k] = self.variables[k]
			else:
				self.variables.pop(k, None)

	def getSavedPositions(self):
		info = self.account.getRootDict(name=str(self.idx))
		found_positions = []
		for i in info['accounts'][self.account.accountid]['plans'][self.idx]['positions']:
			if 'is_dummy' in i and i['is_dummy']:
				pos = Position(self.account, None, None, None)
				pos.setDict(i)
				pos.plan = self
				self.positions.append(pos)
				found_positions.append(pos)
			else:
				for pos in self.positions:
					if pos.orderid == i['orderid']:
						pos.data = i['data']
						pos.plan = self
						found_positions.append(pos)

		for i in range(len(self.positions)-1,-1,-1):
			pos = self.positions[i]
			if not pos in found_positions:
				del self.positions[i]

	def getBankConfig(self):
		info = self.account.getRootDict(name=str(self.idx))
		self.external_bank = float(info['accounts'][self.account.accountid]['external_bank'])
		self.maximum_bank = float(info['accounts'][self.account.accountid]['maximum_bank'])
		self.minimum_bank = float(info['accounts'][self.account.accountid]['minimum_bank'])
		self.lotsize_min = float(info['accounts'][self.account.accountid]['lotsize_min'])
		self.is_gslo = info['accounts'][self.account.accountid]['gslo']

	def updatePositions(self):
		result = self.account.manager.getPositions(self.account.accountid)
		print(result)
		if result:
			for pos in result['positions']:
				found = False
				for l_pos in self.positions:
					if pos['position']['dealId'] == l_pos.orderid:
						found = True
						break

				if not found:
					new_pos = Position(self.account, 
						pos['position']['dealId'], 
						pos['market']['epic'], 
						pos['position']['direction']
					)
					new_pos.lotsize = float(pos['position']['size'])
					new_pos.entryprice = float(pos['position']['level'])
					new_pos.opentime = self.account.manager.utils.convertUTCSnapshotToTimestamp(pos['position']['createdDateUTC'])
					if pos['position']['stopLevel']:
						new_pos.sl = float(pos['position']['stopLevel'])
					if pos['position']['limitLevel']:
						new_pos.tp = float(pos['position']['limitLevel'])

					self.positions.append(new_pos)

	def savePositions(self):
		save = []
		for pos in self.positions:
			save.append({
				'orderid': pos.orderid,
				'direction': pos.direction,
				'data': pos.data,
				'is_dummy': pos.is_dummy
			})
		info = self.account.getRootDict(name=str(self.idx))
		root_path = 'Accounts/{0}.json'.format(self.account.root.root_name)
		info['accounts'][self.account.accountid]['plans'][self.idx]['positions'] = save
		self.account.root.saveJsonToFile(root_path, info, name=str(self.idx))

	def saveStorage(self):
		info = self.account.getRootDict(name=str(self.idx))
		root_path = 'Accounts/{0}.json'.format(self.account.root.root_name)
		info['accounts'][self.account.accountid]['plans'][self.idx]['storage'] = self.storage
		self.account.root.saveJsonToFile(root_path, info, name=str(self.idx))

	def saveVariables(self):
		info = self.account.getRootDict(name=str(self.idx))
		root_path = 'Accounts/{0}.json'.format(self.account.root.root_name)
		info['accounts'][self.account.accountid]['plans'][self.idx]['variables'] = self.variables
		self.account.root.saveJsonToFile(root_path, info, name=str(self.idx))

	def onStopLoss(self, pos):
		if self.plan_state == PlanState.STARTED:
			if pos:
				print('[{0}] StopLoss {1} at {2}'.format(
					pos.orderid, pos.direction, pos.closeprice
				))

			try:
				self.module.onStopLoss(pos)
			except Exception as e:
				if not 'has no attribute \'onStopLoss\'' in str(e):
					self.plan_state = PlanState.STOPPED
					print('PlanError ({0}):\n{1}'.format(self.account.accountid, traceback.format_exc()))

	def onTakeProfit(self, pos):
		if self.plan_state == PlanState.STARTED:
			if pos:
				print('[{0}] TakeProfit {1} at {2}'.format(
					pos.orderid, pos.direction, pos.closeprice
				))

			try:
				self.module.onTakeProfit(pos)
			except Exception as e:
				if not 'has no attribute \'onTakeProfit\'' in str(e):
					self.plan_state = PlanState.STOPPED
					print('PlanError ({0}):\n{1}'.format(self.account.accountid, traceback.format_exc()))

	def onClose(self, pos):
		if self.plan_state == PlanState.STARTED:
			if pos:
				print('[{0}] Closed {1} at {2}'.format(
					pos.orderid, pos.direction, pos.closeprice
				))

			try:
				self.module.onClose(pos)
			except Exception as e:
				if not 'has no attribute \'onClose\'' in str(e):
					self.plan_state = PlanState.STOPPED
					print('PlanError ({0}):\n{1}'.format(self.account.accountid, traceback.format_exc()))

	def onRejected(self, pos):
		if self.plan_state == PlanState.STARTED:
			if pos:
				print('[{0}] Rejected {1}'.format(
					pos.orderid, pos.direction
				))

			try:
				self.module.onRejected(pos)
			except Exception as e:
				if not 'has no attribute \'onRejected\'' in str(e):
					self.plan_state = PlanState.STOPPED
					print('PlanError ({0}):\n{1}'.format(self.account.accountid, traceback.format_exc()))

	def onModified(self, pos):
		if self.plan_state == PlanState.STARTED:
			if pos:
				print('[{0}] Modified {1} sl: {2} tp: {3}'.format(
					pos.orderid, pos.direction, pos.sl, pos.tp
				))

			try:
				self.module.onModified(pos)
			except Exception as e:
				if not 'has no attribute \'onModified\'' in str(e):
					self.plan_state = PlanState.STOPPED
					print('PlanError ({0}):\n{1}'.format(self.account.accountid, traceback.format_exc()))

	'''
	Plan Utilities
	'''

	def convertPosition(self, pos):
		new_pos = Position(
			self, pos.orderid, 
			pos.product, pos.direction
		)

		new_pos.setDict(dict(pos))
		return new_pos

	def buy(self, 
		product, lotsize, orderType='MARKET', 
		slPrice=None, slRange=None, 
		tpPrice=None, tpRange=None,
		attempts=0
	):
		if self.account.root.broker == 'ig':
			product = self.getIGProduct(product)

		ref = self.account.manager.createPosition(
			self.account.accountid,
			product, Constants.BUY, lotsize, 
			orderType = orderType, 
			slPrice = slPrice, slRange = slRange,
			tpPrice = tpPrice, tpRange = tpRange,
			is_gslo = self.is_gslo
		)
		
		pos = None
		start = time.time()
		while True:
			for i in self.account.position_queue:
				if i.ref == ref:
					del self.account.position_queue[self.account.position_queue.index(i)]
					self.positions.append(i)
					i.plan = self
					pos = i
					break
			
			for i in self.account.rejected_queue:
				if i == ref:
					if attempts >= 5:
						raise Exception('PlanError ({0}): Exceeded max position attempts ({1}).\n{2}'.format(
							self.account.accountid, attempts, result
						))
						return

					elif 'RETRY_ON_REJECTED' in self.module.VARIABLES and self.module.VARIABLES['RETRY_ON_REJECTED']:
						return self.buy(
							product, lotsize, orderType=orderType, 
							slPrice=slPrice, slRange=slRange, 
							tpPrice=tpPrice, tpRange=tpRange,
							attempts= attempts + 1
						)
					else:
						raise Exception('PlanError ({0}): Position REJECTED.\n{2}'.format(
							self.account.accountid, result
						))
						return

			if pos:
				break
			elif time.time() - start > 10:
				print('PlanError ({0}): Unable to retrieve position.'.format(self.account.accountid))
				return None
			time.sleep(0.01)

		if pos:
			print('[{0}] Confirmed {1} ({2}) at {3} sl: {4} tp: {5}'.format(
				pos.orderid, pos.direction, pos.lotsize, pos.entryprice, pos.sl, pos.tp
			))

		try:
			self.module.onEntry(pos)
		except Exception as e:
			if not 'has no attribute \'onEntry\'' in str(e):
				self.plan_state = PlanState.STOPPED
				print('PlanError ({0}):\n{1}'.format(self.account.accountid, traceback.format_exc()))

		self.needs_save = True
		return pos

	def sell(self,
		product, lotsize, orderType='MARKET', 
		slPrice=None, slRange=None, 
		tpPrice=None, tpRange=None,
		attempts=0
	):
		if self.account.root.broker == 'ig':
			product = self.getIGProduct(product)

		ref = self.account.manager.createPosition(
			self.account.accountid,
			product, Constants.SELL, lotsize, 
			orderType = orderType, 
			slPrice = slPrice, slRange = slRange,
			tpPrice = tpPrice, tpRange = tpRange,
			is_gslo = self.is_gslo
		)

		pos = None
		start = time.time()
		while True:
			for i in self.account.position_queue:
				if i.ref == ref:
					del self.account.position_queue[self.account.position_queue.index(i)]
					i.plan = self
					self.positions.append(i)
					pos = i
					break
			
			for i in self.account.rejected_queue:
				if i == ref:
					if attempts >= 5:
						raise Exception('PlanError ({0}): Exceeded max position attempts ({1}).\n{2}'.format(
							self.account.accountid, attempts, result
						))
						return

					elif 'RETRY_ON_REJECTED' in self.module.VARIABLES and self.module.VARIABLES['RETRY_ON_REJECTED']:
						return self.sell(
							product, lotsize, orderType=orderType, 
							slPrice=slPrice, slRange=slRange, 
							tpPrice=tpPrice, tpRange=tpRange,
							attempts= attempts + 1
						)
					else:
						raise Exception('PlanError ({0}): Position REJECTED.\n{2}'.format(
							self.account.accountid, result
						))
						return

			if pos:
				break
			elif time.time() - start > 10:
				print('PlanError ({0}): Unable to retrieve position.'.format(self.account.accountid))
				return None
			time.sleep(0.01)

		if pos:
			print('[{0}] Confirmed {1} ({2}) at {3} sl: {4} tp: {5}'.format(
				pos.orderid, pos.direction, pos.lotsize, pos.entryprice, pos.sl, pos.tp
			))

		try:
			self.module.onEntry(pos)
		except Exception as e:
			if not 'has no attribute \'onEntry\'' in str(e):
				self.plan_state = PlanState.STOPPED
				print('PlanError ({0}):\n{1}'.format(self.account.accountid, traceback.format_exc()))

		self.needs_save = True
		return pos

	def stopAndReverse(self, 
		product, lotsize,
		slPrice=None, slRange=None, 
		tpPrice=None, tpRange=None
	):
		if self.account.root.broker == 'ig':
			ig_product = self.getIGProduct(product)

		direction = None
		for i in range(len(self.positions)-1, -1,-1):
			pos = self.positions[i]
			if pos.product == ig_product:
				direction = pos.direction
				pos.close()

		new_pos = None
		if direction:
			if direction == Constants.BUY:
				new_pos = self.sell(
					product, lotsize, 
					slPrice=slPrice, slRange=slRange, 
					tpPrice=tpPrice, tpRange=tpRange
				)
			else:
				new_pos = self.buy(
					product, lotsize, 
					slPrice=slPrice, slRange=slRange, 
					tpPrice=tpPrice, tpRange=tpRange
				)

		self.closed_positions.sort(key=lambda x: x.opentime)

		return new_pos

	def subscribeChart(self, product, period):
		chart = self.account.root.manager.subscribeChart(self, product, period)
		if chart:
			self.charts.append(chart)

	def unsubscribeChart(self, product, period):
		chart = self.account.root.manager.unsubscribeChart(self, product, period)
		if chart:
			del self.charts[self.charts.index(chart)]

	def getChart(self, product, period):
		chart = self.account.root.manager.getChart(self, product, period)
		if chart:
			self.charts.append(chart)
		return chart

	def getChartFromChart(self, chart):
		chart = self.account.root.manager.getChartFromChart(self, chart)
		if chart:
			self.charts.append(chart)
		return chart

	def getIGProduct(self, product):
		if product == Constants.GBPUSD:
			return Constants.IG_GBPUSD_MINI

	def getIGPricePeriod(self, period):
		if period == Constants.ONE_MINUTE:
			return Constants.IG_ONE_MINUTE
		elif period == Constants.TEN_MINUTES:
			return Constants.IG_TEN_MINUTES
		elif period == Constants.ONE_HOUR:
			return Constants.IG_ONE_HOUR
		elif period == Constants.FOUR_HOURS:
			return Constants.IG_FOUR_HOURS
		elif period == Constants.DAILY:
			return Constants.IG_DAILY

	def getBid(self, product):
		for chart in self.charts:
			if chart.product == product:
				return chart.c_bid[3]
		print('Error: Must be subscribed to chart to get bid.')
		return None

	def getAUDUSDBid(self):
		return self.account.audusd_bid

	def getAsk(self, product):
		for chart in self.charts:
			if chart.product == product:
				return chart.c_ask[3]
		print('Error: Must be subscribed to chart to get ask.')
		return None


	def getLowestPeriodChart(self):
		low_chart = None
		for chart in self.charts:
			if low_chart:
				low_chart = chart if chart.period < low_chart.period else low_chart
			else:
				low_chart = chart
		return low_chart

	def getTotalProfit(self):
		total = 0.0
		for pos in self.closed_positions:
			total += pos.getPercentageProfit()
		return total

	def getLotsize(self, bank, risk, stoprange):
		if self.getAUDUSDBid():
			return max(round((bank * (risk / 100) / stoprange) * self.getAUDUSDBid(), 2), self.lotsize_min)
		
		return 0	

	def getBank(self):
		return (
			self.account.manager.accountInfo(self.account.accountid)['balance']['balance']
			+ self.account.manager.accountInfo(self.account.accountid)['balance']['profitLoss']
		)

	def getTotalBank(self):
		return self.getBank() + self.external_bank

	def getTradableBank(self):
		bank = self.getTotalBank()
		return min(bank, self.maximum_bank) if bank > self.minimum_bank else 0

	def convertTimezone(self, dt, tz):
		return self.account.manager.utils.convertTimezone(dt, tz)

	def convertToLondonTimezone(self, dt):
		return self.account.manager.utils.convertToLondonTimezone(dt)

	def setTimezone(self, dt, tz):
		return self.account.manager.utils.setTimezone(dt, tz)
		
	def convertTimestampToDatetime(self, ts):
		return self.account.manager.utils.convertTimestampToDatetime(ts)
		
	def convertDatetimeToTimestamp(self, dt):
		return self.account.manager.utils.convertDatetimeToTimestamp(dt)

	def getTime(self):
		return self.account.manager.utils.convertTimestampToDatetime(self.c_ts)

	def convertToPips(self, price):
		return self.account.manager.utils.convertToPips(price)

	def convertToPrice(self, pips):
		return self.account.manager.utils.convertToPrice(pips)

	def getLatestTimestamp(self):
		return self.c_ts

	def getLatestChartTimestamp(self):
		return max([i.getLatestTimestamp() for i in self.charts])

	def SMA(self, period):
		sma = SMA(period)
		self.indicators.append(sma)
		return sma

	def MAE(self, period, offset, ma_type='sma'):
		mae = MAE(period, offset, ma_type=ma_type)
		self.indicators.append(mae)
		return mae

	def BOLL(self, period, std):
		boll = BOLL(period, std)
		self.indicators.append(boll)
		return boll

	def KELT(self, period, atr_period, multi):
		kelt = KELT(period, atr_period, multi)
		self.indicators.append(kelt)
		return kelt

	def DONCH(self, period):
		donch = DONCH(period)
		self.indicators.append(donch)
		return donch

	def DONCH_CMC(self, period):
		donch = DONCH_CMC(period)
		self.indicators.append(donch)
		return donch

	def ATR(self, period):
		atr = ATR(period)
		self.indicators.append(atr)
		return atr

	def CCI(self, period):
		cci = CCI(period)
		self.indicators.append(cci)
		return cci

	def RSI(self, period):
		rsi = RSI(period)
		self.indicators.append(rsi)
		return rsi

	def MACD(self, fastperiod, slowperiod, signalperiod):
		macd = MACD(fastperiod, slowperiod, signalperiod)
		self.indicators.append(macd)
		return macd

	def log(self, tag, msg):
		if not tag:
			print('{0}'.format(msg))
		else:
			print('{0}: {1}'.format(tag, msg))