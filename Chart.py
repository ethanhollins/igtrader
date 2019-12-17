from Plan import PlanState
from numba import jit
import os
import json
import numpy as np
import datetime
import pytz
import Constants
import traceback

class Chart(object):
	
	def __init__(self, root, product=None, period=None, chart=None):
		self.root = root
		self.manager = root.manager
		self.subscribed_plans = []
		self.reset = False
		self.c_bid = []
		self.c_ask = []

		if product and period != None:
			self.product = product
			self.period = period
			self.loadData()
		elif chart:
			self.product = chart.product
			self.period = chart.period
			self.bids_ts = chart.bids_ts
			self.bids_ohlc = chart.bids_ohlc
			self.asks_ts = chart.asks_ts
			self.asks_ohlc = chart.asks_ohlc
		else:
			raise Exception('Chart object requires a product and period or chart.')

		self.getPricePeriod()
		if self.root.root_name == "ethan_demo":
			self.updateValues()
		self.subscription = self.getLiveData()
		self.last_update = None

	def getPricePeriod(self):
		if self.period == Constants.FOUR_HOURS:
			self.price_period = Constants.PRICE_FOUR_HOURS
		elif self.period == Constants.DAILY:
			self.price_period = Constants.PRICE_DAILY
		elif self.period == Constants.ONE_MINUTE:
			self.price_period = Constants.PRICE_ONE_MINUTE

	def loadData(self):

		for i in ['bid', 'ask']:
			path = 'Data/{0}_{1}_{2}.json'.format(self.product, self.period, i)
			if os.path.exists(path):
				values = self.root.getJsonFromFile(path)

				if i == 'bid':
					self.bids_ts = np.array(
						[int(i[0]) for i in sorted(values.items(), key=lambda kv: kv[0])], 
					dtype=np.int32)
					self.bids_ohlc = np.round(np.array(
						[i[1] for i in sorted(values.items(), key=lambda kv: kv[0])], 
					dtype=np.float32), decimals=5)

					for plan in self.subscribed_plans:
						if self.bids_ts[-1] > plan.c_ts:
							plan.c_ts = self.bids_ts[-1]
				else:
					self.asks_ts = np.array(
						[int(i[0]) for i in sorted(values.items(), key=lambda kv: kv[0])],
					dtype=np.int32)
					self.asks_ohlc = np.round(np.array(
						[i[1] for i in sorted(values.items(), key=lambda kv: kv[0])],
					dtype=np.float32), decimals=5)
			else:
				self.bids_ts = np.array([], dtype=np.int32)
				self.bids_ohlc = np.array([], dtype=np.float32)
				self.asks_ts = np.array([], dtype=np.int32)
				self.asks_ohlc = np.array([], dtype=np.float32)
				break

	def updateValues(self):
		if self.bids_ts.size > 0:
			start_dt = self.manager.utils.convertTimestampToDatetime(self.getLatestTimestamp())
		else:
			start_dt = Constants.DT_START_DATE

		# if pytz.timezone('Australia/Melbourne').dst(start_dt).seconds:
		# 	start_dt -= datetime.timedelta(seconds=3600)

		# start_dt = datetime.datetime(year=2019, month=10, day=27)
		# end_dt = datetime.datetime(year=2019, month=11, day=2)
		end_dt = datetime.datetime.now()
		print('{} {}'.format(start_dt, end_dt))
		result = self.manager.getPricesByDate(self.product, self.price_period, start_dt, end_dt, 1, {})

		if len(result['bids']) == 0:
			return

		sorted_l = sorted(result['bids'].items(), key=lambda kv: kv[0])
		latest_ts = sorted_l[-1][0]

		if self.root.isWeekend():
			self.c_bid = []
			self.c_ask = []
		else:
			self.c_bid = result['bids'][latest_ts]
			self.c_ask = result['asks'][latest_ts]
			result['bids'].pop(latest_ts, None)
			result['asks'].pop(latest_ts, None)

		bids = {int(self.bids_ts[i]):[
			round(float(self.bids_ohlc[i,0]), 5),
			round(float(self.bids_ohlc[i,1]), 5),
			round(float(self.bids_ohlc[i,2]), 5),
			round(float(self.bids_ohlc[i,3]), 5)
		] for i in range(self.bids_ts.size)}
		asks = {int(self.asks_ts[i]):[
			round(float(self.asks_ohlc[i,0]), 5),
			round(float(self.asks_ohlc[i,1]), 5),
			round(float(self.asks_ohlc[i,2]), 5),
			round(float(self.asks_ohlc[i,3]), 5) 
		] for i in range(self.asks_ts.size)}
		bids = {**bids, **result['bids']}
		asks = {**asks, **result['asks']}

		self.bids_ts = np.array(
			[i[0] for i in sorted(bids.items(), key=lambda kv: kv[0])],
		dtype=np.int32)

		self.bids_ohlc = np.round(np.array(
			[i[1] for i in sorted(bids.items(), key=lambda kv: kv[0])],
		dtype=np.float32), decimals=5)

		self.asks_ts = np.array(
			[i[0] for i in sorted(asks.items(), key=lambda kv: kv[0])],
		dtype=np.int32)

		self.asks_ohlc = np.round(np.array(
			[i[1] for i in sorted(asks.items(), key=lambda kv: kv[0])],
		dtype=np.float32), decimals=5)

		print('curr bid:', str(self.c_bid))
		print('curr ask:', str(self.c_ask))

		path = 'Data/{0}_{1}_bid.json'.format(self.product, self.period)
		self.root.saveToFile(path, json.dumps(bids, indent=4))

		path = 'Data/{0}_{1}_ask.json'.format(self.product, self.period)
		self.root.saveToFile(path, json.dumps(asks, indent=4))

	def saveValues(self):
		bids = {int(self.bids_ts[i]):[
			round(float(self.bids_ohlc[i,0]), 5),
			round(float(self.bids_ohlc[i,1]), 5),
			round(float(self.bids_ohlc[i,2]), 5),
			round(float(self.bids_ohlc[i,3]), 5)
		] for i in range(self.bids_ts.size)}
		asks = {int(self.asks_ts[i]):[
			round(float(self.asks_ohlc[i,0]), 5),
			round(float(self.asks_ohlc[i,1]), 5),
			round(float(self.asks_ohlc[i,2]), 5),
			round(float(self.asks_ohlc[i,3]), 5)
		] for i in range(self.asks_ts.size)}

		path = 'Data/{0}_{1}_bid.json'.format(self.product, self.period)
		self.root.saveToFile(path, json.dumps(bids, indent=4))

		path = 'Data/{0}_{1}_ask.json'.format(self.product, self.period)
		self.root.saveToFile(path, json.dumps(asks, indent=4))

	def isChart(self, product, period):
		return product == self.product and period == self.period

	def getLiveData(self):
		period = ''
		if self.period == Constants.FOUR_HOURS or self.period == Constants.DAILY:
			period = Constants.PRICE_ONE_HOUR
		elif self.period == Constants.ONE_MINUTE:
			period = Constants.PRICE_LIVE_ONE_MINUTE

		items = ['Chart:{0}:{1}'.format(self.product, period)]

		fields = [
			'CONS_END',
			'BID_OPEN', 'BID_HIGH', 'BID_LOW', 'BID_CLOSE',
			'OFR_OPEN', 'OFR_HIGH', 'OFR_LOW', 'OFR_CLOSE'
		]

		self.last_update = datetime.datetime.now()
		self.root.controller.subscriptions.append(('MERGE', items, fields, self.onItemUpdate)) 
		return self.manager.subscribe(self.root.controller.ls_client, 'MERGE', items, fields, self.onItemUpdate)

	def onItemUpdate(self, item):
		self.last_update = datetime.datetime.now()

		if item['values']:
			b_open = item['values']['BID_OPEN']
			b_open = float(b_open) if b_open else 0
			
			b_high = item['values']['BID_HIGH']
			b_high = float(b_high) if b_high else 0
			
			b_low = item['values']['BID_LOW']
			b_low = float(b_low) if b_low else 0
			
			b_close = item['values']['BID_CLOSE']
			b_close = float(b_close) if b_close else 0

			if len(self.c_bid) == 0 or b_close == 0 or self.c_bid[3] == 0 or self.reset:
				self.c_bid = [b_open, b_high, b_low, b_close]
			else:
				self.c_bid = [
					self.c_bid[0],
					b_high if b_high > self.c_bid[1] else self.c_bid[1],
					b_low if b_low < self.c_bid[2] else self.c_bid[2],
					b_close
				]

			a_open = item['values']['OFR_OPEN']
			a_open = float(a_open) if a_open else 0
			
			a_high = item['values']['OFR_HIGH']
			a_high = float(a_high) if a_high else 0
			
			a_low = item['values']['OFR_LOW']
			a_low = float(a_low) if a_low else 0
			
			a_close = item['values']['OFR_CLOSE']
			a_close = float(a_close) if a_close else 0

			if len(self.c_ask) == 0 or a_close == 0 or self.c_ask[3] == 0 or self.reset:
				self.c_ask = [a_open, a_high, a_low, a_close]
				self.reset = False
			else:
				self.c_ask = [
					self.c_ask[0],
					a_high if a_high > self.c_ask[1] else self.c_ask[1],
					a_low if a_low < self.c_ask[2] else self.c_ask[2],
					a_close
				]

			if int(item['values']['CONS_END']) == 1:
				now = datetime.datetime.now()
				now = self.manager.utils.setTimezone(now, 'Australia/Melbourne')
				lon = self.manager.utils.convertTimezone(now, 'Europe/London')
				now = now.replace(tzinfo=None)

				if self.period == Constants.FOUR_HOURS:
					now = self.nearestHour(now)
					lon = self.nearestHour(lon)
					if lon.hour in Constants.FOUR_HOURS_BARS:
						self.reset = True
						
						prev_hour = Constants.FOUR_HOURS_BARS[Constants.FOUR_HOURS_BARS.index(lon.hour)-1]
						dist = 24 - (prev_hour - lon.hour) % 24

						new_ts = self.manager.utils.convertDatetimeToTimestamp(now - datetime.timedelta(hours=dist))
						
						self.addNewBar(new_ts)
				
				elif self.period == Constants.DAILY:
					now = self.nearestHour(now)
					lon = self.nearestHour(lon)
					if lon.hour in Constants.DAILY_BARS:
						self.reset = True
						new_ts = self.manager.utils.convertDatetimeToTimestamp(now - datetime.timedelta(hours=24))
						
						self.addNewBar(new_ts)

				elif self.period == Constants.ONE_MINUTE:
					self.reset = True
					now = self.nearestMinute(now)
					new_ts = self.manager.utils.convertDatetimeToTimestamp(now - datetime.timedelta(seconds=60))

					self.addNewBar(new_ts)

	def addNewBar(self, new_ts):
		print('Bid: {0}\nAsk: {1}'.format(self.c_bid, self.c_ask))

		self.bids_ts = np.append(self.bids_ts, new_ts)
		self.bids_ohlc = np.append(
			self.bids_ohlc, 
			np.round([self.c_bid], decimals=5), 
			axis=0
		)

		self.asks_ts = np.append(self.asks_ts, new_ts)
		self.asks_ohlc = np.append(
			self.asks_ohlc,
			np.round([self.c_ask], decimals=5),
			axis=0
		)

		for plan in self.subscribed_plans:
			if plan.plan_state == PlanState.STARTED:
				plan.c_ts = new_ts
				try:
					plan.module.onNewBar(self)
				except Exception as e:
					if not 'has no attribute \'onNewBar\'' in str(e):
						plan.plan_state = PlanState.STOPPED
						print('PlanError ({0}):\n {1}'.format(plan.account.accountid, traceback.format_exc()))
				
		self.saveValues()

	def nearestMinute(self, dt):
		return (
			dt.replace(second=0, microsecond=0, minute=dt.minute)
			+ datetime.timedelta(seconds=(dt.second//30)*60)
		)

	def nearestHour(self, dt):
		return (
			dt.replace(second=0, microsecond=0, minute=0, hour=dt.hour)
			+ datetime.timedelta(hours=dt.minute//30)
		)

	def getLatestTimestamp(self):
		return self.bids_ts[-1]

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

	def getTsOffset(self, ts):
		return Chart.getClosestIndex(self.bids_ts, ts)

	def getAllBidOHLC(self, plan):
		c_idx = Chart.getClosestIndex(self.bids_ts, plan.c_ts)
		return self.bids_ohlc[:c_idx+1]

	def getAllAskOHLC(self, plan):
		c_idx = Chart.getClosestIndex(self.asks_ts, plan.c_ts)
		return self.asks_ohlc[:c_idx+1]

	def getBidOHLC(self, plan, shift, amount):
		c_idx = Chart.getClosestIndex(self.bids_ts, plan.c_ts)
		return self.bids_ohlc[c_idx+1-shift-amount:c_idx+1-shift]

	def getAskOHLC(self, plan, shift, amount):
		c_idx = Chart.getClosestIndex(self.asks_ts, plan.c_ts)
		return self.asks_ohlc[c_idx+1-shift-amount:c_idx+1-shift]

	def getCurrentBidOHLC(self, plan):
		c_idx = Chart.getClosestIndex(self.bids_ts, plan.c_ts)
		return self.bids_ohlc[c_idx]

	def getCurrentAskOHLC(self, plan):
		c_idx = Chart.getClosestIndex(self.asks_ts, plan.c_ts)
		return self.asks_ohlc[c_idx]
