from Chart import Chart

import Constants
import json
import requests
import datetime
import pandas as pd

class OandaManager(object):

	def __init__(self, root):
		self.root = root
		self.utils = self.root.utils
		
		self.key = self.root.key

		self.headers = {
			'Authorization': 'Bearer '+self.key
		}

		self.url = (
			'https://api-fxpractice.oanda.com/v3/'
			if self.root.is_demo else
			'https://api-fxtrade.oanda.com/v3/'
		)

	def getRootDict(self):
		root_path = 'Accounts/{0}.json'.format(self.root.root_name)
		with open(root_path, 'r') as f:
			root_dict = json.load(f)
		return root_dict

	def streamCheck(self):
		return

	'''
	Chart helper functions
	'''
	def subscribeChart(self, plan, product, period):
		for chart in self.root.controller.charts:
			if chart.isChart(product, period, self.root.broker):
				if not account in chart.subscribed_accounts:
					chart.subscribed_plans.append(plan)
					return chart
		return None

	def unsubscribeChart(self, plan, product, period):
		for chart in self.root.controller.charts:
			if chart.isChart(product, period, self.root.broker):
				if account in chart.subscribed_accounts:
					del chart.subscribed_accounts[
						chart.subscribed_plans.index(plan)
					]
					return chart
		return None

	def getChart(self, plan, product, period):
		for chart in self.root.controller.charts:
			if chart.isChart(product, period, self.root.broker):
				chart.subscribed_plans.append(plan)
				return chart

		chart = self.createChart(product, period)
		chart.subscribed_plans.append(plan)
		return chart

	def getChartFromChart(self, plan, chart):
		chart = Chart(self.root, chart=chart)
		self.root.controller.charts.append(chart)
		chart.subscribed_plans.append(plan)
		return chart

	def createChart(self, product, period):
		chart = Chart(self.root, product=product, period=period)
		self.root.controller.charts.append(chart)
		return chart

	def getPrices(self, product, period, tz='Europe/London', start_dt=None, end_dt=None, count=None, result={}):
		if count:
			if start_dt:
				start_str = start_dt.strftime('%Y-%m-%dT%H:%M:%S.000000000Z')
				endpoint = 'instruments/{}/candles?price=BA' \
							'&from={}&count={}&granularity={}&alignmentTimezone={}&dailyAlignment=0'.format(
								product, start_str, count, period, tz
							)
			else:
				endpoint = 'instruments/{}/candles?price=BA' \
							'&count={}&granularity={}&alignmentTimezone={}&dailyAlignment=0'.format(
								product, count, period, tz
							)
		else:
			start_str = start_dt.strftime('%Y-%m-%dT%H:%M:%S.000000000Z')
			end_str = end_dt.strftime('%Y-%m-%dT%H:%M:%S.000000000Z')
			endpoint = 'instruments/{}/candles?price=BA' \
						'&from={}&to={}&granularity={}&alignmentTimezone={}&dailyAlignment=0'.format(
							product, start_str, end_str, period, tz
						)
		print(endpoint)
		res = requests.get(
			self.url + endpoint,
			headers=self.headers
		)

		if res.status_code == 200:
			if len(result) == 0:
				result['timestamp'] = []
				result['ask_open'] = []
				result['ask_high'] = []
				result['ask_low'] = []
				result['ask_close'] = []
				result['bid_open'] = []
				result['bid_high'] = []
				result['bid_low'] = []
				result['bid_close'] = []

			data = res.json()
			candles = data['candles']

			for i in candles:

				time = datetime.datetime.strptime(i['time'], '%Y-%m-%dT%H:%M:%S.000000000Z')
				ts = self.utils.convertUTCTimeToTimestamp(time)

				result['timestamp'].append(ts)
				asks = list(map(float, i['ask'].values()))
				bids = list(map(float, i['bid'].values()))
				result['ask_open'].append(asks[0])
				result['ask_high'].append(asks[1])
				result['ask_low'].append(asks[2])
				result['ask_close'].append(asks[3])
				result['bid_open'].append(bids[0])
				result['bid_high'].append(bids[1])
				result['bid_low'].append(bids[2])
				result['bid_close'].append(bids[3])

			if count:
				if not self.isLastCandleFound(period, start_dt, end_dt, count):
					last_dt = datetime.datetime.strptime(candles[-1]['time'], '%Y-%m-%dT%H:%M:%S.000000000Z')
					return self.getPrices(product, period, start_dt=last_dt, end_dt=end_dt, count=5000, result=result)

			return pd.DataFrame(data=result).set_index('timestamp')
		if res.status_code == 400:
			print('({}) Bad Request: {}'.format(res.status_code, res.json()['errorMessage']))
			if 'Maximum' in res.json()['errorMessage'] or 'future' in res.json()['errorMessage']:
				return self.getPrices(product, period, start_dt=start_dt, end_dt=end_dt, count=5000, result={})
			else:
				return pd.DataFrame(data=result).set_index('timestamp')
		else:
			print('Error:\n{0}'.format(res.json()))
			return None

	def isLastCandleFound(self, period, start_dt, end_dt, count):
		if period == Constants.ONE_MINUTE:
			return start_dt + datetime.timedelta(minutes=count) >= end_dt
		elif period == Constants.TWO_MINUTES:
			return start_dt + datetime.timedelta(minutes=count*2) >= end_dt
		elif period == Constants.THREE_MINUTES:
			return start_dt + datetime.timedelta(minutes=count*3) >= end_dt
		elif period == Constants.FIVE_MINUTES:
			return start_dt + datetime.timedelta(minutes=count*5) >= end_dt
		elif period == Constants.TEN_MINUTES:
			return start_dt + datetime.timedelta(minutes=count*10) >= end_dt
		elif period == Constants.FIFTEEN_MINUTES:
			return start_dt + datetime.timedelta(minutes=count*15) >= end_dt
		elif period == Constants.THIRTY_MINUTES:
			return start_dt + datetime.timedelta(minutes=count*30) >= end_dt
		elif period == Constants.ONE_HOUR:
			return start_dt + datetime.timedelta(hours=count) >= end_dt
		elif period == Constants.FOUR_HOURS:
			return start_dt + datetime.timedelta(hours=count*4) >= end_dt
		elif period == Constants.DAILY:
			return start_dt + datetime.timedelta(hours=count*24) >= end_dt
		else:
			raise Exception('Period not found.')

	'''
	REST API helper functions
	'''

	def getAccounts(self):
		endpoint = 'accounts'
		res = requests.get(
			self.url + endpoint,
			headers=self.headers
		)

		if res.status_code == 200:
			return res.json()
		else:
			print('Error:\n{0}'.format(res.json()))
			return None

	def getEquity(self, accountid):
		return
	
	def getBalance(self, accountid):
		return

	def getPositions(self, accountid):
		return 
		
	def getPosition(self, orderid):
		return

	def createPosition(self,
		accountid,
		product, direction, lotsize, 
		orderType = 'MARKET', 
		slPrice = None, slRange = None,
		tpPrice = None, tpRange = None,
		is_gslo = False
	):
		return

	def modifyPosition(self, orderid, slPrice=None, tpPrice=None):
		return

	def closePosition(self, orderid):
		return

	def closeAllPositions(self):
		return	