from Position import Position
from enum import Enum
from Backtester import Backtester
import importlib.util
import Constants
import time
import json
import traceback

from Indicators.ATR import ATR
from Indicators.BOLL import BOLL
from Indicators.KELT import KELT
from Indicators.MACD import MACD
from Indicators.MAE import MAE
from Indicators.RSI import RSI
from Indicators.SMA import SMA

class PlanState(Enum):
	STOPPED = 0
	STARTED = 1
	BACKTEST = 2

class Plan(object):

	def __init__(self, account, name, variables, storage):
		self.account = account
		self.name = name

		self.positions = []
		self.closed_positions = []
		self.charts = []
		self.indicators = []

		self.plan_state = PlanState.STOPPED
		self.variables = variables
		self.storage = storage

		self.c_ts = 0

		self.initialize()
	
	'''
	Utilities
	'''

	def initialize(self):
		self.plan_state = PlanState.BACKTEST

		self.module = self.execPlan()
		self.setPlanVariables()
		self.module.init(self)

		bt = Backtester(self.name, self.variables)
		self.module, _ = bt.backtest(plan=self)

		self.updatePositions()
		self.getSavedPositions()
		self.savePositions()
		
		self.c_ts = bt.c_ts
		self.module.setup(self)

		self.plan_state = PlanState.STARTED

	def execPlan(self):
		path = 'Plans/{0}.py'.format(self.name)
		spec = importlib.util.spec_from_file_location(self.name, path)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
		return module

	def setPlanVariables(self):
		for k in self.variables:
			if k in self.module.VARIABLES:
				self.module.VARIABLES[k] = self.variables[k]
			else:
				self.variables.pop(k, None)

	def getSavedPositions(self):
		info = self.account.getRootDict()
		found_positions = []
		for i in info['accounts'][self.account.accountid][self.name]['positions']:
			for pos in self.positions:
				if pos.orderid == i['orderid']:
					pos.data = i['data']
					found_positions.append(pos)

		for i in range(len(self.positions)-1,-1,-1):
			pos = self.positions[i]
			if not pos in found_positions:
				del self.positions[i]

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
				'data': pos.data
			})
		info = self.account.getRootDict()
		root_path = 'Accounts/{0}.json'.format(self.account.root.root_name)
		with open(root_path, 'w') as f:
			info['accounts'][self.account.accountid][self.name]['positions'] = save
			f.write(json.dumps(info, indent=4))

	def saveStorage(self):
		info = self.account.getRootDict()
		root_path = 'Accounts/{0}.json'.format(self.account.root.root_name)
		with open(root_path, 'w') as f:
			info['accounts'][self.account.accountid][self.name]['storage'] = self.storage
			f.write(json.dumps(info, indent=4))

	def saveVariables(self):
		info = self.account.getRootDict()
		root_path = 'Accounts/{0}.json'.format(self.account.root.root_name)
		with open(root_path, 'w') as f:
			info['accounts'][self.account.accountid][self.name]['variables'] = self.variables
			f.write(json.dumps(info, indent=4))

	def onStopLoss(self, pos):
		if self.plan_state == PlanState.STARTED:
			try:
				self.module.onStopLoss(pos)
			except Exception as e:
				if not 'has no attribute \'onStopLoss\'' in str(e):
					print('PlanError ({0}):\n{1}'.format(self.account.accountid, traceback.format_exc()))
					self.plan_state = PlanState.STOPPED

	def onTakeProfit(self, pos):
		if self.plan_state == PlanState.STARTED:
			try:
				self.module.onTakeProfit(pos)
			except Exception as e:
				if not 'has no attribute \'onTakeProfit\'' in str(e):
					print('PlanError ({0}):\n{1}'.format(self.account.accountid, traceback.format_exc()))
					self.plan_state = PlanState.STOPPED

	def onClose(self, pos):
		if self.plan_state == PlanState.STARTED:
			try:
				self.module.onClose(pos)
			except Exception as e:
				if not 'has no attribute \'onClose\'' in str(e):
					print('PlanError ({0}):\n{1}'.format(self.account.accountid, traceback.format_exc()))
					self.plan_state = PlanState.STOPPED

	def onRejected(self, pos):
		if self.plan_state == PlanState.STARTED:
			try:
				self.module.onRejected(pos)
			except Exception as e:
				if not 'has no attribute \'onRejected\'' in str(e):
					print('PlanError ({0}):\n{1}'.format(self.account.accountid, traceback.format_exc()))
					self.plan_state = PlanState.STOPPED

	def onModified(self, pos):
		if self.plan_state == PlanState.STARTED:
			try:
				self.module.onModified(pos)
			except Exception as e:
				if not 'has no attribute \'onModified\'' in str(e):
					print('PlanError ({0}):\n{1}'.format(self.account.accountid, traceback.format_exc()))
					self.plan_state = PlanState.STOPPED

	'''
	Plan Utilities
	'''

	def buy(self, 
		product, lotsize, orderType='MARKET', 
		slPrice=None, slRange=None, 
		tpPrice=None, tpRange=None
	):
		result = self.account.manager.createPosition(
			self.account.accountid,
			product, Constants.BUY, lotsize, 
			orderType = orderType, 
			slPrice = slPrice, slRange = slRange,
			tpPrice = tpPrice, tpRange = tpRange
		)

		orderid = result['dealId']
		pos = None
		start = time.time()
		while True:
			for i in self.account.position_queue:
				if i.orderid == orderid:
					del self.account.position_queue[self.account.position_queue.index(i)]
					self.positions.append(i)
					i.plan = self
					pos = i
					break

			if pos:
				break
			elif time.time() - start > 10:
				print('PlanError ({0}): Unable to retrieve position.'.format(self.account.accountid))
				return None
			time.sleep(0.01)

		try:
			self.module.onEntry(pos)
		except Exception as e:
			if not 'has no attribute \'onEntry\'' in str(e):
				print('PlanError ({0}):\n{1}'.format(self.account.accountid, traceback.format_exc()))
				self.plan_state = PlanState.STOPPED

		self.savePositions()
		return pos

	def sell(self,
		product, lotsize, orderType='MARKET', 
		slPrice=None, slRange=None, 
		tpPrice=None, tpRange=None
	):
		result = self.account.manager.createPosition(
			self.account.accountid,
			product, Constants.SELL, lotsize, 
			orderType = orderType, 
			slPrice = slPrice, slRange = slRange,
			tpPrice = tpPrice, tpRange = tpRange
		)
		
		orderid = result['dealId']
		pos = None
		start = time.time()
		while True:
			for i in self.account.position_queue:
				if i.orderid == orderid:
					del self.account.position_queue[self.account.position_queue.index(i)]
					i.plan = self
					self.positions.append(i)
					pos = i
					break
			if pos:
				break
			elif time.time() - start > 10:
				print('PlanError ({0}): Unable to retrieve position.'.format(self.account.accountid))
				return None
			time.sleep(0.01)

		try:
			self.module.onEntry(pos)
		except Exception as e:
			if not 'has no attribute \'onEntry\'' in str(e):
				print('PlanError ({0}):\n{1}'.format(self.account.accountid, traceback.format_exc()))
				self.plan_state = PlanState.STOPPED

		self.savePositions()
		return pos

	def stopAndReverse(self, 
		product, lotsize,
		slPrice=None, slRange=None, 
		tpPrice=None, tpRange=None
	):
		direction = None
		for i in range(len(self.positions)-1, -1,-1):
			pos = self.positions[i]
			if pos.product == product:
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

	def getBid(self, product):
		for chart in self.charts:
			if chart.product == product:
				return chart.c_bid[3]
		print('Error: Must be subscribed to chart to get bid.')
		return None

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

	def getLotsize(self, bank, risk, stoprange):
		return round(bank * (risk / 100) / stoprange, 2)

	def getBankSize(self): # TODO
		return self.account.manager.accountInfo(self.account.accountid)['balance']

	def getTime(self):
		return self.account.manager.utils.convertTimestampToDatetime(self.c_ts)

	def getLatestTimestamp(self):
		return self.c_ts

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

	def ATR(self, period):
		atr = ATR(period)
		self.indicators.append(atr)
		return atr

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