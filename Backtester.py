from numba import jit
import importlib.util
import Constants
import random
import string
import datetime
import pytz
import os
import json
import numpy as np
import traceback
import random
import pandas as pd
import sys
from timeit import default_timer as timer
from enum import Enum
from matplotlib import dates as mpl_dates

from Indicators.ATR import ATR
from Indicators.BOLL import BOLL
from Indicators.CCI import CCI
from Indicators.KELT import KELT
from Indicators.KELT_IG import KELT_IG
from Indicators.MACD import MACD
from Indicators.MAE import MAE
from Indicators.RSI import RSI
from Indicators.SMA import SMA
from Indicators.DONCH import DONCH
from Indicators.DONCH_CMC import DONCH_CMC

class Chart(object):

	__slots__ = (
		'product', 'period',
		'bids_ts', 'bids_ohlc',
		'asks_ts', 'asks_ohlc',
		'c_ts'
	)
	def __init__(self,
		product, period,
		bids_ts, bids_ohlc,
		asks_ts, asks_ohlc
	):
		self.product = product
		self.period = period

		self.bids_ts = bids_ts
		self.bids_ohlc = bids_ohlc
		self.asks_ts = asks_ts
		self.asks_ohlc = asks_ohlc
		self.c_ts = 0

	@jit
	def tsExists(l, search):
		start = 0
		end = len(l)
		idx = int((start+end)/2)
		m_ts = l[idx]

		while (
			not m_ts == search and 
			not start+1 == end and 
			not start == end
		):
			idx = int((start+end)/2)
			m_ts = l[idx]
			if search > m_ts:
				start = idx
			elif search < m_ts:
				end = idx
		
		return m_ts == search

	@jit
	def getClosestIndex(l, search):
		start = 0
		end = len(l)
		idx = int((start+end)/2)
		m_ts = l[idx]

		while (
			not m_ts == search and 
			not start+1 == end and 
			not start == end
		):
			idx = int((start+end)/2)
			m_ts = l[idx]
			if search > m_ts:
				start = idx
			elif search < m_ts:
				end = idx
		return idx

	def doesTsExist(self, ts):
		return np.where(self.bids_ts==ts)[0].shape[0] > 0

	def getTsOffset(self, ts):
		return (np.abs(self.bids_ts - ts)).argmin()-1

	def getLatestTimestamp(self):
		return self.bids_ts[-1]

	def getAllBidOHLC(self, backtester):
		c_idx = (np.abs(self.bids_ts - self.c_ts)).argmin()-1
		return self.bids_ohlc[:c_idx+1]

	def getAllAskOHLC(self, backtester):
		c_idx = (np.abs(self.asks_ts - self.c_ts)).argmin()-1
		return self.asks_ohlc[:c_idx+1]

	def getBidOHLC(self, backtester, shift, amount):
		c_idx = (np.abs(self.bids_ts - self.c_ts)).argmin()-1
		return self.bids_ohlc[c_idx+1-shift-amount:c_idx+1-shift]

	def getAskOHLC(self, backtester, shift, amount):
		c_idx = (np.abs(self.asks_ts - self.c_ts)).argmin()-1
		return self.asks_ohlc[c_idx+1-shift-amount:c_idx+1-shift]

	def getCurrentBidOHLC(self, backtester):
		c_idx = (np.abs(self.bids_ts - self.c_ts)).argmin()-1
		return self.bids_ohlc[c_idx]

	def getCurrentAskOHLC(self, backtester):
		c_idx = (np.abs(self.asks_ts - self.c_ts)).argmin()-1
		return self.asks_ohlc[c_idx]

	def isChart(self, product, period):
		return product == self.product and period == self.period

class Position(object):

	__slots__ = (
		'backtester', 'orderid', 'product',
		'direction', 'opentime', 'closetime',
		'lotsize', 'entryprice', 'closeprice',
		'sl', 'tp', 'data', 'is_dummy', 'risk', 'ref'
	)
	def __init__(self, 
		backtester, orderid, 
		product, direction
	):
		self.backtester = backtester
		self.orderid = orderid
		self.product = product
		self.direction = direction

		self.opentime = None
		self.closetime = None

		self.ref = None
		self.lotsize = 0

		self.entryprice = 0
		self.closeprice = 0
		self.sl = 0
		self.tp = 0

		self.risk = 0

		self.is_dummy = False

		self.data = {}

	def __iter__(self):
		for key in self.__dict__:
			ignore = ['account', 'utils', 'plan']
			if not key in ignore:
				yield (key, self.__dict__[key])

	def setDict(self, pos):
		for key in pos:
			self.__dict__[key] = pos[key]

	def stopAndReverse(self, 
		lotsize, 
		slPrice=None, slRange=None, 
		tpPrice=None, tpRange=None
	):
		self.close()

		if self.direction == Constants.BUY:
			pos = self.backtester.buy(
				self.product, lotsize, 
				slPrice=slPrice, slRange=slRange,
				tpPrice=tpPrice, tpRange=tpRange
			)
		else:
			pos = self.backtester.sell(
				self.product, lotsize, 
				slPrice=slPrice, slRange=slRange,
				tpPrice=tpPrice, tpRange=tpRange
			)

		return pos

	def modifySL(self, sl):
		self.sl = sl
		try:
			self.backtester.module.onModified(pos)
		except Exception as e:
			if not 'has no attribute \'onModified\'' in str(e):
				print('PlanError ({0}):\n{1}'.format('Backtester', traceback.format_exc()))
		return True

	def removeSL(self):
		self.sl = 0
		try:
			self.backtester.module.onModified(pos)
		except Exception as e:
			if not 'has no attribute \'onModified\'' in str(e):
				print('PlanError ({0}):\n{1}'.format('Backtester', traceback.format_exc()))
		return True

	def modifyTP(self, tp):
		self.tp = tp
		try:
			self.backtester.module.onModified(pos)
		except Exception as e:
			if not 'has no attribute \'onModified\'' in str(e):
				print('PlanError ({0}):\n{1}'.format('Backtester', traceback.format_exc()))
		return True

	def removeTP(self):
		self.tp = 0
		try:
			self.backtester.module.onModified(pos)
		except Exception as e:
			if not 'has no attribute \'onModified\'' in str(e):
				print('PlanError ({0}):\n{1}'.format('Backtester', traceback.format_exc()))
		return True

	def breakeven(self):
		min_price = 0.00040
		if self.direction == Constants.BUY:
			if self.backtester.getBid(self.product) > self.entryprice + min_price:
				self.sl = self.entryprice
			elif self.backtester.getBid(self.product) < self.entryprice - min_price:
				self.tp = self.entryprice
			else:
				print('Error: Breakeven must be atleast 4 pips from entry.')
				return False

		else:
			if self.backtester.getAsk(self.product) < self.entryprice - min_price:
				self.sl = self.entryprice
			elif self.backtester.getAsk(self.product) > self.entryprice + min_price:
				self.tp = self.entryprice
			else:
				print('Error: Breakeven must be atleast 4 pips from entry.')
				return False

		try:
			self.backtester.module.onModified(pos)
		except Exception as e:
			if not 'has no attribute \'onModified\'' in str(e):
				print('PlanError ({0}):\n{1}'.format('Backtester', traceback.format_exc()))
		return True

	def close(self):
		self.closetime = self.backtester.c_ts
		if self.direction == Constants.BUY:
			self.closeprice = self.backtester.getBid(self.product)
		else:
			self.closeprice = self.backtester.getAsk(self.product)

		del self.backtester.positions[self.backtester.positions.index(self)]
		self.backtester.closed_positions.append(self)

		try:
			self.backtester.module.onClose(pos)
		except Exception as e:
			if not 'has no attribute \'onClose\'' in str(e):
				print('PlanError ({0}):\n{1}'.format('Backtester', traceback.format_exc()))
		
		return True

	def isBreakeven(self):
		return self.sl == self.entryprice or self.tp == self.entryprice

	def calculateSLPoints(self, price):
		if self.direction == Constants.BUY:
			points = self.entryprice - price
		else:
			points = price - self.entryprice
		
		return self.backtester.convertToPips(points)

	def calculateSLPrice(self, points):
		price = self.backtester.convertToPrice(points)
		if self.direction == Constants.BUY:
			return round(self.entryprice - price, 5)
		else:
			return round(self.entryprice + price, 5)

	def isSLPoints(self, points):
		sl_price = self.backtester.convertToPrice(points)

		if self.direction == Constants.BUY:
			check_sl = round(self.entryprice - sl_price, 5)
		else:
			check_sl = round(self.entryprice + sl_price, 5)
			
		return self.sl == check_sl

	def isSLPrice(self, price):
		return self.sl == price

	def calculateTPPoints(self, price):
		if self.direction == Constants.BUY:
			points = round(price - self.entryprice, 5)
		else:
			points = round(self.entryprice - price, 5)
		
		return self.backtester.convertToPips(points)

	def calculateTPPrice(self, points):
		price = self.backtester.convertToPrice(points)
		if self.direction == Constants.BUY:
			return round(self.entryprice + price, 5)
		else:
			return round(self.entryprice - price, 5)

	def isTPPoints(self, points):
		tp_price = self.backtester.convertToPrice(points)

		if self.direction == Constants.BUY:
			check_tp = round(self.entryprice + tp_price, 5)
		else:
			check_tp = round(self.entryprice - tp_price, 5)
			
		return self.tp == check_tp

	def isTPPrice(self, price):
		return self.tp == price

	def getPipProfit(self):
		if not self.closeprice:
			if self.direction == Constants.BUY:
				profit = self.backtester.getBid(self.product) - self.entryprice
			else:
				profit = self.entryprice - self.backtester.getAsk(self.product)
		else:
			if self.direction == Constants.BUY:
				profit = self.closeprice - self.entryprice
			else:
				profit = self.entryprice - self.closeprice
		
		return self.backtester.convertToPips(profit)

	def getPercentageProfit(self):
		if not self.closeprice:
			if self.direction == Constants.BUY:
				profit = self.backtester.getBid(self.product) - self.entryprice
			else:
				profit = self.entryprice - self.backtester.getAsk(self.product)
		else:
			if self.direction == Constants.BUY:
				profit = self.closeprice - self.entryprice
			else:
				profit = self.entryprice - self.closeprice
			
		profit = self.backtester.convertToPips(profit)

		variables = self.backtester.module.VARIABLES
		risk = variables['risk'] if 'risk' in variables else None
		stoprange = variables['stoprange'] if 'stoprange' in variables else None
		
		if stoprange and self.risk:
			profit = profit / stoprange * self.risk
		elif stoprange and risk:
			profit = profit / stoprange * risk
		else:
			profit = 0

		return round(profit, 2)

class PlanState(Enum):
	BACKTEST = 2
	RUN = 3
	STEP = 4

class Backtester(object):

	__slots__ = (
		'root', 'name', 'variables', 
		'module', 'indicators', 'charts',
		'positions', 'closed_positions',
		'c_ts', 'storage', 'method',
		'external_bank', 'maximum_bank', 'minimum_bank',
		'last_time', 'max_ret', 'source', 'plan_state',
		'last_ret', 'split', 'seed', 'batch', 'padding',
		'dropout'
	)
	def __init__(self, root, name, variables, source='ig'):
		self.root = root
		self.name = name
		self.variables = variables
		self.source = source
		self.indicators = []
		self.charts = []

		self.positions = []
		self.closed_positions = []

		self.c_ts = 0
		self.storage = {}

		self.plan_state = PlanState.BACKTEST

		self.external_bank = 0
		self.maximum_bank = 10000
		self.minimum_bank = 0

		self.last_time = None
		self.max_ret = None
		self.last_ret = None

		self.split = 0.7
		self.seed = None
		self.batch = 0
		self.padding = 0
		self.dropout = 0

	def load(self, product, period):
		start = Constants.TS_START_DATE
		end = datetime.datetime.now()

		data_dir = os.path.join('Data/', '{}/{}/{}/'.format(self.source, product, period))
		frags = []
		for y in range(start.year, end.year+1):
			data_path = os.path.join(data_dir, '{}-{}.csv'.format(y, y+1))
			if os.path.exists(data_path):
				t_data = self.root.readCsv(data_path)
				if y == start.year:
					ts_start = self.convertDatetimeToTimestamp(start)
					t_data = t_data.loc[t_data['timestamp'] >= ts_start]
				elif y == end.year:
					ts_end = self.convertDatetimeToTimestamp(end)
					t_data = t_data.loc[t_data['timestamp'] <= ts_end]
				frags.append(t_data)
		data = pd.concat(frags).set_index('timestamp')

		ask_keys = ['ask_open', 'ask_high', 'ask_low', 'ask_close']
		bid_keys = ['bid_open', 'bid_high', 'bid_low', 'bid_close']
		
		bids_ts = data.index.values
		asks_ts = np.copy(bids_ts)
		bids_ohlc = data[bid_keys].values
		asks_ohlc = data[ask_keys].values

		return Chart(
			product, period,
			bids_ts, bids_ohlc,
			asks_ts, asks_ohlc
		)

	def saveToFile(self, path, data):
		return self.root.saveToFile(path, data)

	def getJsonFromFile(self, path):
		return self.root.getJsonFromFile(path)

	def backtestRun(self, start=None, start_off=0, end=None, end_off=0, method='run', plan=None):
		print('Running backtest ({0})...'.format(self.name))
		start_time = timer()

		self.method = method
		if not plan:
			self.module = self.execPlan()
			self.setPlanVariables()
			self.module.init(self)
		else:
			self.module = plan.module
			self.indicators = plan.indicators

			for chart in plan.charts:
				self.charts.append(self.getChartFromChart(chart))

			self.module.setup(self)

		all_ts = np.sort(np.unique(np.concatenate([
			chart.bids_ts
			for chart in self.charts
		])))

		if start:
			start_idx = max(Chart.getClosestIndex(all_ts, start) + start_off, self.getMinPeriod())
		else:
			start_idx = self.getMinPeriod()

		if end:
			end_idx = Chart.getClosestIndex(all_ts, end)+end_off+1
		else:
			end_idx = all_ts.size

		all_ts = all_ts[start_idx:end_idx]

		for chart in self.charts:
			start_idx = max(Chart.getClosestIndex(chart.bids_ts, all_ts[0])-1000, 0)
			end_idx = Chart.getClosestIndex(chart.bids_ts, all_ts[-1])+1

			chart.bids_ts = chart.bids_ts[start_idx:end_idx]
			chart.bids_ohlc = chart.bids_ohlc[start_idx:end_idx]
			chart.asks_ts = chart.asks_ts[start_idx:end_idx]
			chart.asks_ohlc = chart.asks_ohlc[start_idx:end_idx]

		all_charts = []
		for i in range(all_ts.size):
			charts = []
			for chart in self.charts:
				if chart.doesTsExist(all_ts[i]):
					charts.append(chart)
			all_charts.append(charts)

		data = {}
		if self.method == 'step':
			self.plan_state = PlanState.STEP
		else:
			self.plan_state = PlanState.RUN

		print('Pre-processing complete ({0})... {1:.2f}s'.format(self.name, timer() - start_time))

		# CMD Vars
		next_p = None

		start_time = timer()
		for i in range(all_ts.size):
			self.c_ts = all_ts[i]
			self.runloop(all_charts[i])

			if self.method == 'step':
				if not next_p:
					cmd = input('Enter cmd or step: ')
					if cmd.lower().startswith('next'):
						period = cmd.split(' ')[1]
						if self.isPeriod(period):
							next_p = period
				else:
					for c in all_charts[i]:
						if c.period == next_p:
							next_p = None


			elif self.method == 'compare':
				data = self.getInterimData(data)
				progress = int((i+1)/all_ts.size * 50.0)
				print('[{}{}]'.format(
					'='*(progress), 
					('>' if 50-progress > 0 else '')+('-'*int(50-progress-1))
				), end='\n' if i == all_ts.size-1 else '\r', flush=True)

		if self.method == 'compare':
			data = self.getCompletedData(data)
		elif self.method == 'show':
			data = self.getCompletedChartData(data, all_ts, all_charts)

		print('Backtest DONE ({0}) {1:.2f}s'.format(self.name, timer() - start_time))

		if self.method == 'analyse':
			try:
				self.module.onEnd()
			except Exception as e:
				print('Error: {}'.format(e))
				pass

		return self.module, data

	def backtestTrainTest(self, 
		method,	start=None, end=None
	):
		'''
		PRE-PROCESSING
		'''

		print('Running backtest ({0})...'.format(self.name))

		self.module = self.execPlan()
		self.setPlanVariables()
		self.module.init(self)

		# Get chart timestamps
		all_ts = np.sort(np.unique(np.concatenate([
			chart.bids_ts
			for chart in self.charts
		])))

		assert 0.0 <= self.split <= 1.0

		if self.padding:
			assert type(self.padding) == int and self.padding >= 0

		if start:
			start_idx = max(Chart.getClosestIndex(all_ts, start), self.getMinPeriod())
		else:
			start_idx = max(self.getMinPeriod(), self.padding)

		if end:
			end_idx = Chart.getClosestIndex(all_ts, end)+1
		else:
			end_idx = all_ts.size

		all_ts = all_ts[start_idx:end_idx]

		# Get correlating charts to all_ts
		all_charts = []
		for i in range(all_ts.size):
			charts = []
			for chart in self.charts:
				if chart.doesTsExist(all_ts[i]):
					charts.append(chart)
			all_charts.append(charts)

		padded_ts = all_ts[self.padding:]
		padded_size = padded_ts.size

		test_batches = []
		train_batches = []
		if self.batch:
			batches = []

			assert type(self.batch) == int
			batch_size = self.batch
			batch_points = [i for i in range(padded_size-1, -1, -batch_size) if i >= batch_size]

			for i in range(len(batch_points)-1, -1, -1):
				pt = batch_points[i]
				nxt_pt = batch_points[i-1]
				batches.append((all_ts[pt-self.padding:nxt_pt], all_charts[pt-self.padding:nxt_pt]))

			# Get Test Batch
			if self.seed:
				assert type(self.seed) == int
				random.seed(self.seed)

			random.shuffle(batches)
			test_split = int(len(batches) * (1-self.split))
			for i in range(test_split):
				idx = random.randint(0, len(batches)-1)
				test_batches.append(batches[idx])
				del batches[idx]

			# Get Train Batch
			random.seed(None)
			random.shuffle(batches)
			if self.dropout:
				assert 0 <= self.dropout <= 1.0
				dropout_amt = int(len(batches) * self.dropout)
				for i in range(dropout_amt):
					del batches[random.randint(0, len(batches)-1)]

			train_batches = batches
		else:
			test_start_idx = int(padded_size * self.split)

			train_ts = (all_ts[:test_start_idx], all_charts[:test_start_idx])
			train_batches.append(train_ts)

			test_ts = (all_ts[test_start_idx:], all_charts[test_start_idx:])
			test_batches.append(test_ts)
		
		dataset = None
		if method == 'train':
			dataset = train_batches
		else:
			dataset = test_batches
		
		'''
		TESTING
		'''

		start_time = timer()
		batch_data = []
		for i in range(len(dataset)):
			batch = dataset[i]

			self.reset()
			data = {}

			self.module = self.execPlan()
			self.setPlanVariables()
			self.module.init(self)

			all_ts = batch[0]
			all_charts = batch[1]
			for j in range(all_ts.size):
				self.c_ts = all_ts[j]
				self.runloop(all_charts[j])

				data = self.getInterimData(data)
				# TODO: GET RESULTS AND SAVE FOR BATCH
			data = self.getCompletedData(data)
			batch_data.append(data)
			print('Batch {}/{}\t{:.2f}s'.format(i+1, len(dataset), timer() - start_time))
		print('\nFinished.\t{:.2f}s'.format(timer() - start_time))

		return batch_data

	def reset(self):
		self.c_ts = 0
		self.storage = {}

		self.positions = []
		self.closed_positions = []

		self.last_time = None
		self.max_ret = None
		self.last_ret = None

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

	def runloop(self, charts):
		for chart in charts:
			chart.c_ts = self.c_ts
			
		self.checkSl()
		self.checkTp()

		for chart in charts:
			try:
				self.module.onNewBar(chart)
			except Exception as e:
				if not 'has no attribute \'onNewBar\'' in str(e):
					print('PlanError ({0}):\n {1}'.format('Backtester', traceback.format_exc()))

		try:
			self.module.onLoop()
		except Exception as e:
			if not 'has no attribute \'onLoop\'' in str(e):
				print('PlanError ({0}):\n {1}'.format('Backtester', traceback.format_exc()))

	def getInterimData(self, data):
		time = self.convertTimestampToDatetime(self.c_ts)
		new_day = False

		if self.last_time:
			if time.day != self.last_time.day and not time.weekday() in (6,0):
				self.last_time = time
				new_day = True
		else:
			self.last_time = time

		if new_day:
			perc_ret = 0
			pip_ret = 0

			for i in self.closed_positions + self.positions:
				perc_ret += i.getPercentageProfit()
				pip_ret += i.getPipProfit()

			if self.max_ret:
				if perc_ret > self.max_ret:
					self.max_ret = perc_ret
			else:
				self.max_ret = perc_ret

			if Constants.DAILY_PERC_RET in data:
				data[Constants.DAILY_PERC_RET][self.last_time] = perc_ret
			else:
				data[Constants.DAILY_PERC_RET] = {self.last_time: perc_ret}

			if Constants.DAILY_PIP_RET in data:
				data[Constants.DAILY_PIP_RET][self.last_time] = pip_ret
			else:
				data[Constants.DAILY_PIP_RET] = {self.last_time: pip_ret}

			if Constants.DAILY_PERC_DD in data:
				data[Constants.DAILY_PERC_DD][self.last_time] = self.max_ret - perc_ret
			else:
				data[Constants.DAILY_PERC_DD] = {self.last_time: self.max_ret - perc_ret}

			if not Constants.DAILY_WINS in data:
				data[Constants.DAILY_WINS] = 0
			if not Constants.DAILY_LOSSES in data:
				data[Constants.DAILY_LOSSES] = 0

			if self.last_ret:
				if pip_ret - self.last_ret >= 0:
					data[Constants.DAILY_WINS] += 1
				else:

					data[Constants.DAILY_LOSSES] += 1
			else:
				if pip_ret >= 0:
					data[Constants.DAILY_WINS] += 1
				else:

					data[Constants.DAILY_LOSSES] += 1

			self.last_ret = pip_ret
			
		return data

	def getCompletedData(self, data):
		perc_ret = 0
		pip_ret = 0
		max_ret = 0
		perc_dd = 0

		pos_equity_ret = {}
		pos_equity_dd = {}
		
		wins = 0
		losses = 0
		gain = 0
		loss = 0
		
		bank = 100000
		max_bank = bank
		max_cmp_dd = 0
		compound_positions = []

		for i in self.closed_positions + self.positions:
			if i.closetime:
				time = self.convertTimestampToDatetime(i.closetime)
			else:
				time = self.convertTimestampToDatetime(self.c_ts)

			perc_profit = i.getPercentageProfit()
			perc_ret += perc_profit
			pip_ret += i.getPipProfit()

			if perc_ret > max_ret:
				max_ret = perc_ret

			if max_ret - perc_ret > perc_dd:
				perc_dd = max_ret - perc_ret

			pos_equity_ret[time] = perc_ret
			pos_equity_dd[time] = max_ret - perc_ret

			if perc_profit >= 0:
				wins += 1
				gain += perc_profit
			else:
				losses += 1
				loss += abs(perc_profit)

			if len(compound_positions) > 0:
				if i.opentime > compound_positions[-1].opentime:
					total_profit = 0
					for j in compound_positions:
						total_profit += j.getPercentageProfit()
						bank += (bank * (total_profit/100))

					if bank > max_bank:
						max_bank = bank
					else:
						dd = (max_bank - bank) / max_bank
						max_cmp_dd = dd if dd > max_cmp_dd else max_cmp_dd
					compound_positions = []
			compound_positions.append(i)

		d_bank = 100000
		d_max_bank = d_bank
		d_max_cmp_dd = 0
		last_ret = None

		if Constants.DAILY_PERC_RET in data:
			for k, perc in data[Constants.DAILY_PERC_RET].items():
				if last_ret:
					d_ret = perc - last_ret
					d_bank += (d_bank * (d_ret/100))

					if d_bank > d_max_bank:
						d_max_bank = d_bank
					else:
						dd = (d_max_bank - d_bank) / d_max_bank
						d_max_cmp_dd = dd if dd > d_max_cmp_dd else d_max_cmp_dd

				last_ret = perc

		data[Constants.POS_PERC_RET] = round(perc_ret, 2)
		data[Constants.POS_PIP_RET] = round(pip_ret, 1)
		data[Constants.POS_PERC_DD] = round(perc_dd, 2)

		data[Constants.POS_EQUITY_RET] = pos_equity_ret
		data[Constants.POS_EQUITY_DD] = pos_equity_dd

		data[Constants.POS_COMPOUND_RET] = round(((bank / 100000) - 1) * 100, 2)
		data[Constants.POS_COMPOUND_DD] = round(max_cmp_dd * 100, 2)

		data[Constants.DAY_COMPOUND_RET] = round(((d_bank / 100000) - 1) * 100, 2)
		data[Constants.DAY_COMPOUND_DD] = round(d_max_cmp_dd * 100, 2)

		data[Constants.WINS] = wins
		data[Constants.LOSSES] = losses

		data[Constants.WIN_PERC] = round(wins/(wins+losses), 2)
		data[Constants.LOSS_PERC] = round(losses/(wins+losses), 2)
		data[Constants.GAIN] = round(gain, 2)
		data[Constants.LOSS] = round(loss, 2)
		data[Constants.GPR] = round(gain/loss, 2)

		return data

	def getCompletedChartData(self, data, all_ts, all_charts):
		data['positions'] = {}
		for i in self.closed_positions + self.positions:
			opentime = mpl_dates.date2num(self.convertTimestampToDatetime(i.opentime))
			data['positions'][opentime] = (i.direction, i.entryprice, i.data)


		data['quotes'] = []
		overlays = [i for i in self.indicators if i.type == 'overlay']
		studies = [i for i in self.indicators if i.type == 'study']
		data['overlays'] = [[] for i in overlays]
		data['studies'] = [[] for i in studies]

		for i in range(all_ts.size):
			self.c_ts = all_ts[i]
			time = mpl_dates.date2num(self.convertTimestampToDatetime(self.c_ts))
			
			for chart in all_charts[i]:
				ohlc = chart.getCurrentBidOHLC(self)
			
			for i in range(len(overlays)):
				ind = overlays[i]
				data['overlays'][i].append(ind.getCurrent(self, chart))

			for i in range(len(studies)):
				ind = studies[i]
				data['studies'][i].append(ind.getCurrent(self, chart))
				
			data['quotes'].append([time, ohlc[0], ohlc[1], ohlc[2], ohlc[3]])

		return data

	def checkSl(self):
		chart = self.getLowestPeriodChart()
		_, _, bid_low, _ = chart.getCurrentBidOHLC(self)
		_, ask_high, _, _ = chart.getCurrentAskOHLC(self)

		for i in range(len(self.positions)-1, -1, -1):
			pos = self.positions[i]
			if pos.direction == Constants.BUY:
				if pos.sl and bid_low <= pos.sl:
					del self.positions[self.positions.index(pos)]
					self.closed_positions.append(pos)

					pos.closeprice = pos.sl
					pos.closetime = self.c_ts

					try:
						self.module.onStopLoss(pos)
					except Exception as e:
						if not 'has no attribute \'onStopLoss\'' in str(e):
							print('PlanError ({0}):\n{1}'.format('Backtester', traceback.format_exc()))

			else:
				if pos.sl and ask_high >= pos.sl:
					del self.positions[self.positions.index(pos)]
					self.closed_positions.append(pos)

					pos.closeprice = pos.sl
					pos.closetime = self.c_ts

					try:
						self.module.onStopLoss(pos)
					except Exception as e:
						if not 'has no attribute \'onStopLoss\'' in str(e):
							print('PlanError ({0}):\n{1}'.format('Backtester', traceback.format_exc()))

	def checkTp(self):
		chart = self.getLowestPeriodChart()
		_, bid_high, _, _ = chart.getCurrentBidOHLC(self)
		_, _, ask_low, _ = chart.getCurrentAskOHLC(self)

		for i in range(len(self.positions)-1, -1, -1):
			pos = self.positions[i]
			if pos.direction == Constants.BUY:
				if pos.tp and bid_high >= pos.tp:
					del self.positions[self.positions.index(pos)]
					self.closed_positions.append(pos)

					pos.closeprice = pos.tp
					pos.closetime = self.c_ts

					try:
						self.module.onTakeProfit(pos)
					except Exception as e:
						if not 'has no attribute \'onTakeProfit\'' in str(e):
							print('PlanError ({0}):\n{1}'.format('Backtester', traceback.format_exc()))

			else:
				if pos.tp and ask_low <= pos.tp:
					del self.positions[self.positions.index(pos)]
					self.closed_positions.append(pos)

					pos.closeprice = pos.tp
					pos.closetime = self.c_ts

					try:
						self.module.onTakeProfit(pos)
					except Exception as e:
						if not 'has no attribute \'onTakeProfit\'' in str(e):
							print('PlanError ({0}):\n{1}'.format('Backtester', traceback.format_exc()))

	def isPeriod(self, period):
		for chart in self.charts:
			if chart.period == period:
				return True

		return False

	'''
	Utilities
	'''

	def convertPosition(self, pos):
		new_pos = Position(
			self, pos.orderid, 
			pos.product, pos.direction
		)

		new_pos.setDict(dict(pos))
		return new_pos

	def convertTimezone(self, dt, tz):
		return dt.astimezone(pytz.timezone(tz))

	def convertToLondonTimezone(self, dt):
		dst_start = self.findFirstWeekday(
			datetime.datetime(year=dt.year, month=3, day=31, hour=1),
			6,
			reverse=True
		)
		dst_end = self.findFirstWeekday(
			datetime.datetime(year=dt.year, month=10, day=31, hour=1),
			6,
			reverse=True
		)
		if dst_start <= dt < dst_end:
			return dt + datetime.timedelta(hours=1)
		else:
			return dt

	def findFirstWeekday(self, dt, weekday, reverse=False):
		while dt.weekday() != weekday:
			if reverse:
				dt -= datetime.timedelta(days=1)
			else:
				dt += datetime.timedelta(days=1)
		return dt

	def setTimezone(self, dt, tz):
		return pytz.timezone(tz).localize(dt)

	def convertTimestampToDatetime(self, ts):
		return Constants.DT_START_DATE + datetime.timedelta(seconds=int(ts))
		
	def convertDatetimeToTimestamp(self, dt):
		# dt = self.convertTimezone(dt, 'Australia/Melbourne')
		if self.source == 'ig' or self.source == 'oanda':
			return int((dt - Constants.DT_START_DATE).total_seconds())
		elif self.source == 'mt':
			return int((dt - Constants.MT_DT_START_DATE).total_seconds())
		

	def getTime(self):
		return self.convertTimestampToDatetime(self.c_ts)

	def getLatestTimestamp(self):
		return self.c_ts

	def convertToPips(self, price):
		return round(price * 10000, 1)

	def convertToPrice(self, pips):
		return round(pips / 10000, 5)

	def getMinPeriod(self):
		if len(self.indicators) > 0:
			return max([i.min_period for i in self.indicators])
		else:
			return 0

	def savePositions(self):
		return

	def setSplit(self, split):
		self.split = split

	def setSeed(self, seed):
		self.seed = seed

	def setBatch(self, batch):
		self.batch = batch

	def setPadding(self, padding):
		self.padding = padding

	def setDropout(self, dropout):
		self.dropout = dropout

	'''
	Plan Utilities
	'''

	def buy(self, 
		product, lotsize, orderType='MARKET', 
		slPrice=None, slRange=None, 
		tpPrice=None, tpRange=None
	):
		letters = string.ascii_lowercase
		order_id = ''.join(random.choice(letters) for i in range(10))

		pos = Position(
			self, order_id, 
			product, Constants.BUY
		)
		pos.opentime = self.c_ts
		pos.lotsize = lotsize
		pos.entryprice = self.getAsk(product)

		if slPrice:
			pos.sl = slPrice
		elif slRange:
			pos.sl = pos.calculateSLPrice(slRange)
		
		if tpPrice:
			pos.tp = tpPrice
		elif tpRange:
			pos.tp = pos.calculateTPPrice(tpRange)
		
		self.positions.append(pos)

		try:
			self.module.onEntry(pos)
		except Exception as e:
			if not 'has no attribute \'onEntry\'' in str(e):
				print('PlanError {0}:\n{1}'.format('Backtester', traceback.format_exc()))
		
		return pos

	def sell(self,
		product, lotsize, orderType='MARKET', 
		slPrice=None, slRange=None, 
		tpPrice=None, tpRange=None
	):
		letters = string.ascii_lowercase
		order_id = ''.join(random.choice(letters) for i in range(10))

		pos = Position(
			self, order_id, 
			product, Constants.SELL
		)
		pos.opentime = self.c_ts
		pos.lotsize = lotsize

		pos.entryprice = self.getBid(product)

		if slPrice:
			pos.sl = slPrice
		elif slRange:
			pos.sl = pos.calculateSLPrice(slRange)
		
		if tpPrice:
			pos.tp = tpPrice
		elif tpRange:
			pos.tp = pos.calculateTPPrice(tpRange)

		self.positions.append(pos)

		try:
			self.module.onEntry(pos)
		except Exception as e:
			if not 'has no attribute \'onEntry\'' in str(e):
				print('PlanError {0}:\n{1}'.format('Backtester', traceback.format_exc()))

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

		self.closed_positions.sort(key=lambda x: x.opentime)

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

		return new_pos

	def getChart(self, product, period):
		for chart in self.charts:
			if chart.isChart(product, period):
				return chart

		return self.createChart(product, period)

	def getChartFromChart(self, chart):
		return Chart(
			chart.product, chart.period,
			chart.bids_ts, chart.bids_ohlc,
			chart.asks_ts, chart.asks_ohlc
		)

	def createChart(self, product, period):
		chart = self.load(product, period)
		self.charts.append(chart)
		return chart

	def getLowestPeriodChart(self):
		low_chart = None
		for chart in self.charts:
			low_period = None
			if low_chart:
				low_period = self.getPeriodNumber(low_chart.period)
			period = self.getPeriodNumber(chart.period)
			if low_period:
				low_chart = chart if period < low_period else low_chart
			else:
				low_chart = chart
		return low_chart

	def getPeriodNumber(self, period):
		if period == Constants.ONE_MINUTE:
			return 1
		elif period == Constants.TWO_MINUTES:
			return 2
		elif period == Constants.THREE_MINUTES:
			return 3
		elif period == Constants.FIFTEEN_MINUTES:
			return 5
		elif period == Constants.THIRTY_MINUTES:
			return 30
		elif period == Constants.ONE_HOUR:
			return 60
		elif period == Constants.TWO_HOURS:
			return 60*2
		elif period == Constants.THREE_HOURS:
			return 60*3
		elif period == Constants.FOUR_HOURS:
			return 60*4
		elif period == Constants.DAILY:
			return 60*24
		elif period == Constants.WEEKLY:
			return 60*24*7
		elif period == Constants.MONTHLY:
			return 60*24*7*4
		else:
			None

	def getBid(self, product):
		chart = self.getLowestPeriodChart()
		return chart.getCurrentBidOHLC(self)[3]

	def getAsk(self, product):
		chart = self.getLowestPeriodChart()
		return chart.getCurrentAskOHLC(self)[3]

	def getLotsize(self, bank, risk, stoprange):
		return round(bank * (risk / 100) / stoprange, 2)

	def getBank(self):
		return 10000

	def getTotalBank(self):
		return 10000

	def getTradableBank(self):
		return 10000

	def getTotalProfit(self):
		total = 0.0
		for pos in self.closed_positions:
			total += pos.getPercentageProfit()
		return total

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

	def KELT_IG(self, period, atr_period, multi):
		kelt_ig = KELT_IG(period, atr_period, multi)
		self.indicators.append(kelt_ig)
		return kelt_ig

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
		if self.plan_state == PlanState.STEP:
			if not tag:
				print('{0}'.format(msg))
			else:
				print('{0}: {1}'.format(tag, msg))



