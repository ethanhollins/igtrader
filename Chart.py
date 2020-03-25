from Plan import PlanState
from numba import jit
import os
import json
import numpy as np
import datetime
import pytz
import Constants
import traceback
import pandas as pd
from threading import Thread

class Chart(object):
	
	def __init__(self, root, product=None, period=None, chart=None):
		self.root = root
		self.manager = root.manager
		self.subscribed_plans = []
		self.reset = False
		self.c_bid = []
		self.c_ask = []
		
		self.last_update = None
		self.is_open = False

		if product and period != None:
			self.product = product
			self.period = period

			data_path = os.path.join('Data/', '{}/{}/{}'.format(self.root.broker, product, period))
			if os.path.exists(data_path) and len(os.listdir(data_path)) > 0:
				load_data = self.load()
			else:
				load_data = None
			self.update(load_data)
		elif chart:
			self.product = chart.product
			self.period = chart.period

			ask_keys = ['ask_open', 'ask_high', 'ask_low', 'ask_close']
			bid_keys = ['bid_open', 'bid_high', 'bid_low', 'bid_close']
			load_data = pd.DataFrame(
				data=np.concatenate((chart.ask_ohlc, chart.bid_ohlc), axis=1),
				columns=ask_keys + bid_keys,
				index=chart.bids_ts
			)
			self.update(load_data)
		else:
			raise Exception('Chart object requires a product and period or chart.')

		if self.root.broker == 'ig':
			self.getLiveIGData()
		elif self.root.broker == 'fxcm':
			self.getLiveFXCMData()


	def load(self, start=None, end=None):
		if not start:
			start = datetime.datetime.now()
			start = start.replace(
				year=start.year-1, month=1, day=1,
				hour=0, minute=0, second=0, microsecond=0
			)
		if not end:
			end = datetime.datetime.now()

		data_dir = os.path.join('Data/', '{}/{}/{}/'.format(self.root.broker, self.product, self.period))
		frags = []
		for y in range(start.year, end.year+1):
			data_path = os.path.join(data_dir, '{}-{}.csv'.format(y, y+1))
			if os.path.exists(data_path):
				t_data = self.root.readCsv(data_path)
				if y == start.year:
					ts_start = self.root.utils.convertDatetimeToTimestamp(start)
					t_data = t_data.loc[t_data['timestamp'] >= ts_start]
				elif y == end.year:
					ts_end = self.root.utils.convertDatetimeToTimestamp(end)
					t_data = t_data.loc[t_data['timestamp'] <= ts_end]
				frags.append(t_data)
		data = pd.concat(frags).set_index('timestamp')
		data.index = data.index.astype(np.int32)
		return data

	def download(self, start=None, end=None, count=None, save=False):
		
		if self.root.broker == 'oanda':
			if not count:
				if not start:
					start = Constants.TS_START_DATE
				if not end:
					end = datetime.datetime.now()
			data = self.manager.getPrices(self.product, self.period, start_dt=start, end_dt=end, count=count, result={})

		elif self.root.broker == 'ig':
			if not count:
				if not start:
					start = Constants.TS_START_DATE
				if not end:
					end = datetime.datetime.now()
			product = self.getIGProduct()
			period = self.getIGPricePeriod()
			data = self.manager.getPrices(product, period, start_dt=start, end_dt=end, count=count, result={})
		else:
			raise Exception('Broker `{}` not found.'.format(self.root.broker))

		data = data[~data.index.duplicated(keep='first')]	
		if save:
			if not start:
				start = self.root.utils.convertTimestampToDatetime(data.index[0])
				end = self.root.utils.convertTimestampToDatetime(data.index[-1])
			self.save(data, start, end)
		return data

	def save(self, data, start, end):
		data_dir = os.path.join('Data/', '{}/{}/{}/'.format(self.root.broker, self.product, self.period))
		if not os.path.exists(data_dir):
			os.makedirs(data_dir)

		data = data.round(pd.Series([5]*8, index=data.columns))
		data.index = data.index.astype(np.int32)
		data.index.name = 'timestamp'
		for y in range(start.year, end.year+1):
			ts_start = self.root.utils.convertDatetimeToTimestamp(datetime.datetime(year=y, month=1, day=1))
			ts_end = self.root.utils.convertDatetimeToTimestamp(datetime.datetime(year=y+1, month=1, day=1))
			t_data = data.loc[(ts_start <= data.index) & (data.index < ts_end)]
			if t_data.size == 0:
				continue
			data_path = os.path.join(data_dir, '{}-{}.csv'.format(y, y+1))
			self.root.saveCsv(data_path, t_data)

	def update(self, load_data):
		end = datetime.datetime.now()
		if type(load_data) == pd.DataFrame:
			start = self.root.utils.convertTimestampToDatetime(load_data.index[-1])

			data = self.download(start=start, end=end)
			data = pd.concat((load_data, data))
			data = data.loc[~data.index.duplicated(keep='first')]
		else:
			start = Constants.TS_START_DATE

			if self.root.broker == 'ig':
				data = self.download(count=100)
			elif self.root.broker == 'oanda':
				data = self.download(start=start, end=end)
			else:
				raise Exception('Broker `{}` not found.'.format(self.root.broker))

		ask_keys = ['ask_open', 'ask_high', 'ask_low', 'ask_close']
		bid_keys = ['bid_open', 'bid_high', 'bid_low', 'bid_close']

		self.c_ask = data.iloc[-1][ask_keys].values.tolist()
		self.c_bid = data.iloc[-1][bid_keys].values.tolist()

		data = data.drop(data.index[-1])
		self.save(data, start, end)

		self.bids_ts = data.index.values.astype(np.int32)
		self.bids_ohlc = data[bid_keys].values.astype(np.float32)
		self.asks_ts = data.index.values.astype(np.int32)
		self.asks_ohlc = data[ask_keys].values.astype(np.float32)

		n = min(
			self.bids_ts.size, self.bids_ohlc.shape[0], 
			self.asks_ts.size, self.asks_ohlc.shape[0]
		)

		self.bids_ts = self.bids_ts[-n:]
		self.bids_ohlc = self.bids_ohlc[-n:]
		self.asks_ts = self.asks_ts[-n:]
		self.asks_ohlc = self.asks_ohlc[-n:]

		print('Current Bid: %s' % self.c_bid)
		print('Current Ask: %s' % self.c_ask)

	def isChart(self, product, period, broker):
		return product == self.product and period == self.period and self.root.broker == broker

	def getLiveData(self):
		if self.root.broker == 'ig':
			self.getLiveIGData()
		elif self.root.broker == 'fxcm':
			self.getLiveFXCMData()

	def getLiveIGData(self):
		period = self.getIGLivePricePeriod()
		product = self.getIGProduct()

		items = ['Chart:{0}:{1}'.format(product, period)]
		print(items)
		fields = [
			'CONS_END', 'UTM',
			'BID_OPEN', 'BID_HIGH', 'BID_LOW', 'BID_CLOSE',
			'OFR_OPEN', 'OFR_HIGH', 'OFR_LOW', 'OFR_CLOSE'
		]

		self.last_update = datetime.datetime.now()
		self.root.controller.subscriptions[self.root.username].append(('MERGE', items, fields, self.onItemUpdateIG))
		self.manager.subscribe(
			self.root.controller.ls_clients[self.root.username], 
			'MERGE', items, fields, 
			self.onItemUpdateIG
		)

		items = ['MARKET:{0}'.format(product)]

		fields = ['MARKET_STATE']
		print(items)

		self.root.controller.subscriptions[self.root.username].append(('MERGE', items, fields, self.onStatusUpdate))
		self.manager.subscribe(
			self.root.controller.ls_clients[self.root.username], 
			'MERGE', items, fields, 
			self.onStatusUpdate
		)

	def getLiveFXCMData(self):
		self.manager.con.subscribe_market_data(self.product, (self.onItemUpdateFXCM,))

	def onStatusUpdate(self, item):
		if 'values' in item:
			if not self.is_open and item['values']['MARKET_STATE'] == 'TRADEABLE':
				self.is_open = True
				print('[{}] Opened.'.format(self.product))
			elif (
				self.is_open and
				(item['values']['MARKET_STATE'] == 'CLOSED' 
					or item['values']['MARKET_STATE'] == 'OFFLINE'
					or item['values']['MARKET_STATE'] == 'EDIT')
			):
				self.is_open = False
				print('[{}] Closed.'.format(self.product))

	def onItemUpdateIG(self, item):
		self.last_update = datetime.datetime.now()
		if 'values' in item:
			b_open = item['values']['BID_OPEN']
			b_open = float(b_open) if b_open else 0
			
			b_high = item['values']['BID_HIGH']
			b_high = float(b_high) if b_high else 0
			
			b_low = item['values']['BID_LOW']
			b_low = float(b_low) if b_low else 0
			
			b_close = item['values']['BID_CLOSE']
			b_close = float(b_close) if b_close else 0

			if len(self.c_bid) == 0 or self.c_bid[3] == 0 or self.reset:
				self.c_bid = [b_open, b_high, b_low, b_close]
			elif b_close:
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

			if len(self.c_ask) == 0 or self.c_ask[3] == 0 or self.reset:
				self.c_ask = [a_open, a_high, a_low, a_close]
				self.reset = False
			elif a_close:
				self.c_ask = [
					self.c_ask[0],
					a_high if a_high > self.c_ask[1] else self.c_ask[1],
					a_low if a_low < self.c_ask[2] else self.c_ask[2],
					a_close
				]

			cons_end = int(item['values']['CONS_END']) if item['values']['CONS_END'] else None

			if cons_end == 1:
				now = datetime.datetime.now()
				now = self.root.utils.setTimezone(now, 'Australia/Melbourne')
				lon = self.root.utils.convertTimezone(now, 'Europe/London')
				now = now.replace(tzinfo=None)

				if self.period == Constants.ONE_MINUTE:
					self.reset = True
					now = Constants.IG_START_DATE + datetime.timedelta(milliseconds=int(item['values']['UTM']))
					new_ts = self.root.utils.convertDatetimeToTimestamp(now)

					self.addNewBar(new_ts)

				elif self.period == Constants.TEN_MINUTES:
					now = Constants.IG_START_DATE + datetime.timedelta(milliseconds=int(item['values']['UTM']))
					if (now.minute+1) % 10 == 0:
						self.reset = True
						new_ts = self.root.utils.convertDatetimeToTimestamp((now - datetime.timedelta(minutes=(10-1))))

						self.addNewBar(new_ts)

				elif self.period == Constants.FOUR_HOURS:
					now = Constants.IG_START_DATE + datetime.timedelta(milliseconds=int(item['values']['UTM']))
					lon = self.root.utils.convertTimezone(now, 'Europe/London')
					if (lon.hour+1) in Constants.FOUR_HOURS_BARS:
						self.reset = True
						new_ts = self.root.utils.convertDatetimeToTimestamp(now - datetime.timedelta(hours=(4-1)))
						
						self.addNewBar(new_ts)
				
				elif self.period == Constants.DAILY:
					now = self.nearestHour(now)
					lon = self.nearestHour(lon)
					if lon.hour in Constants.DAILY_BARS:
						self.reset = True
						new_ts = self.root.utils.convertDatetimeToTimestamp(now - datetime.timedelta(hours=24))
						
						self.addNewBar(new_ts)


	def onItemUpdateFXCM(self, data, dataframe):
		# print(data)
		# print(dataframe)
		print(pd.to_datetime(int(data['Updated']), unit='ms'))
		print(type(pd.to_datetime(int(data['Updated']), unit='ms')))
		print('bid: {0:.5f}, ask: {1:.5f}'.format(data['Rates'][0], data['Rates'][1]))
		print('--------')

	def addNewBar(self, new_ts):
		last_n = self.bids_ts.size

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

		new_n = min(
			self.bids_ts.size, self.bids_ohlc.shape[0], 
			self.asks_ts.size, self.asks_ohlc.shape[0]
		)

		self.bids_ts = self.bids_ts[:new_n]
		self.bids_ohlc = self.bids_ohlc[:new_n]
		self.asks_ts = self.asks_ts[:new_n]
		self.asks_ohlc = self.asks_ohlc[:new_n]

		if new_n > last_n:
			threads = []
			for plan in self.subscribed_plans:
				t = Thread(target=self.onNewBar, args=(plan, new_ts))
				t.start()
				threads.append(t)
			
			for t in threads:
				t.join()

			ask_keys = ['ask_open', 'ask_high', 'ask_low', 'ask_close']
			bid_keys = ['bid_open', 'bid_high', 'bid_low', 'bid_close']
			data = pd.DataFrame(
				data=np.concatenate(
					(self.bids_ts.reshape(self.bids_ts.size, 1), self.asks_ohlc, self.bids_ohlc),
					axis=1
				),
				columns=['timestamp'] + ask_keys + bid_keys
			).set_index('timestamp')
			start = self.root.utils.convertTimestampToDatetime(data.index[0])
			end = self.root.utils.convertTimestampToDatetime(data.index[-1])
			self.save(data, start, end)
		else:
			print("ERROR: Size difference. {} | {}".format(last_n, new_n))

	def onNewBar(self, plan, new_ts):
		if plan.plan_state == PlanState.STARTED:
			plan.c_ts = new_ts
			try:
				plan.module.onNewBar(self)
			except Exception as e:
				if not 'has no attribute \'onNewBar\'' in str(e):
					plan.plan_state = PlanState.STOPPED
					print('PlanError ({0}):\n {1}'.format(plan.account.accountid, traceback.format_exc()))

	'''
	IG Specific Keywords
	'''

	def getIGPricePeriod(self):
		if self.period == Constants.ONE_MINUTE:
			return Constants.IG_ONE_MINUTE
		elif self.period == Constants.TEN_MINUTES:
			return Constants.IG_TEN_MINUTES
		elif self.period == Constants.ONE_HOUR:
			return Constants.IG_ONE_HOUR
		elif self.period == Constants.FOUR_HOURS:
			return Constants.IG_FOUR_HOURS
		elif self.period == Constants.DAILY:
			return Constants.IG_DAILY

	def getIGLivePricePeriod(self):
		if self.period == Constants.ONE_MINUTE:
			return Constants.IG_LIVE_ONE_MINUTE
		elif self.period == Constants.TEN_MINUTES:
			return Constants.IG_LIVE_ONE_MINUTE
		elif self.period == Constants.FOUR_HOURS:
			return Constants.IG_ONE_HOUR
		elif self.period == Constants.DAILY:
			return Constants.IG_ONE_HOUR

	def getIGProduct(self):
		if self.product == Constants.GBPUSD:
			return Constants.IG_GBPUSD_MINI

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

	def getTimestampAtOffset(self, off):
		return self.bids_ts[off]

	def getTsOffset(self, ts):
		return (np.abs(self.bids_ts - ts)).argmin()

	def getAllBidOHLC(self, plan):
		c_idx = (np.abs(self.bids_ts - plan.c_ts)).argmin()
		return self.bids_ohlc[:c_idx+1]

	def getAllAskOHLC(self, plan):
		c_idx = (np.abs(self.asks_ts - plan.c_ts)).argmin()
		return self.asks_ohlc[:c_idx+1]

	def getBidOHLC(self, plan, shift, amount):
		c_idx = (np.abs(self.bids_ts - plan.c_ts)).argmin()
		return self.bids_ohlc[c_idx+1-shift-amount:c_idx+1-shift]

	def getAskOHLC(self, plan, shift, amount):
		c_idx = (np.abs(self.asks_ts - plan.c_ts)).argmin()
		return self.asks_ohlc[c_idx+1-shift-amount:c_idx+1-shift]

	def getCurrentBidOHLC(self, plan):
		c_idx = (np.abs(self.bids_ts - plan.c_ts)).argmin()
		return self.bids_ohlc[c_idx]

	def getCurrentAskOHLC(self, plan):
		c_idx = (np.abs(self.asks_ts - plan.c_ts)).argmin()
		return self.asks_ohlc[c_idx]
