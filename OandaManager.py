from Chart import Chart

import Constants
import json
import requests
import datetime

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

	def getPrices(self, product, period, start_dt=None, end_dt=None, count=None, result={}):
		if count:
			if start_dt:
				start_str = start_dt.strftime('%Y-%m-%dT%H:%M:%S.000000000Z')
				endpoint = 'instruments/{}/candles?price=BA' \
							'&from={}&count={}&granularity={}&alignmentTimezone=Europe/London'.format(
								product, start_str, count, period
							)
			else:
				endpoint = 'instruments/{}/candles?price=BA' \
							'&count={}&granularity={}&alignmentTimezone=Europe/London'.format(
								product, count, period
							)
		else:
			start_str = start_dt.strftime('%Y-%m-%dT%H:%M:%S.000000000Z')
			end_str = end_dt.strftime('%Y-%m-%dT%H:%M:%S.000000000Z')
			endpoint = 'instruments/{}/candles?price=BA' \
						'&from={}&to={}&granularity={}&alignmentTimezone=Europe/London'.format(
							product, start_str, end_str, period
						)
		print(endpoint)
		res = requests.get(
			self.url + endpoint,
			headers=self.headers
		)

		if res.status_code == 200:
			if 'bids' not in result: result['bids'] = {}
			if 'asks' not in result: result['asks'] = {}

			data = res.json()
			candles = data['candles']

			for i in candles:
				time = datetime.datetime.strptime(i['time'], '%Y-%m-%dT%H:%M:%S.000000000Z')
				ts = self.utils.convertUTCTimeToTimestamp(time)

				result['bids'][ts] = [float(j) for j in i['bid'].values()]
				result['asks'][ts] = [float(j) for j in i['ask'].values()]

			if count:
				if not self.isLastCandleFound(period, start_dt, end_dt, count):
					last_dt = datetime.datetime.strptime(candles[-1]['time'], '%Y-%m-%dT%H:%M:%S.000000000Z')
					return self.getPrices(product, period, start_dt=last_dt, end_dt=end_dt, count=5000, result=result)

			return result
		if res.status_code == 400:
			print('({}) Bad Request: {}'.format(res.status_code, res.json()['errorMessage']))
			if 'Maximum' in res.json()['errorMessage'] or 'future' in res.json()['errorMessage']:
				return self.getPrices(product, period, start_dt=start_dt, end_dt=end_dt, count=5000, result={})
			else:
				return result
		else:
			print('Error:\n{0}'.format(res.json()))
			return None

	def isLastCandleFound(self, period, start_dt, end_dt, count):
		if period == Constants.ONE_MINUTE:
			return start_dt + datetime.timedelta(minutes=count) >= end_dt
		elif period == Constants.ONE_HOUR:
			return start_dt + datetime.timedelta(hours=count) >= end_dt
		elif period == Constants.FOUR_HOURS:
			return start_dt + datetime.timedelta(hours=count*4) >= end_dt

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