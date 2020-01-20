from Chart import Chart

import Constants
import json
import fxcmpy
import datetime

ONE_HOUR = 60*60

class FXCMManager(object):

	def __init__(self, root):
		self.root = root
		self.utils = self.root.utils
		
		print('Connecting...')
		self.con = fxcmpy.fxcmpy(
			access_token=self.root.key, 
			log_level='error',
			log_file='./Logs/FXCM',
			server='demo'
		)
		print('Connected.')

		self.getPrices('GBP/USD', 'H4', count=100)

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
			if chart.isChart(product, period):
				if not account in chart.subscribed_accounts:
					chart.subscribed_plans.append(plan)
					return chart
		return None

	def unsubscribeChart(self, plan, product, period):
		for chart in self.root.controller.charts:
			if chart.isChart(product, period):
				if account in chart.subscribed_accounts:
					del chart.subscribed_accounts[
						chart.subscribed_plans.index(plan)
					]
					return chart
		return None

	def getChart(self, plan, product, period):
		for chart in self.root.controller.charts:
			if chart.isChart(product, period):
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

	def getPrices(self, product, period, start_dt=None, end_dt=None, count=None):
		req_period = self.getReqPeriod(period)

		if start_dt and end_dt:
			data = self.con.get_candles(
				product, period=req_period,
				start=start, to=end_dt
			)
		elif count:
			data = self.con.get_candles(
				product, period=req_period,
				number=count
			)

		result = {'bids': {}, 'asks': {}}
		keys = ['bidopen', 'bidhigh', 'bidlow', 'bidclose', 
				'askopen', 'askhigh', 'asklow', 'askclose']

		timestamps = data['bidopen'].keys()
		vals = data[keys].values

		for i in range(vals.shape[0]):
			ts = timestamps[i].to_pydatetime()
			bids = vals[i][:4]
			result['bids'][ts] = bids

			asks = vals[i][4:]
			result['asks'][ts] = asks

		if period == 'H4':
			result['bids'] = self.stitchH4(result['bids'])
			result['asks'] = self.stitchH4(result['asks'])

		print(result)
	
	def getReqPeriod(self, period):
		if period.startswith('m'):
			return 'm1'
		elif period.startswith('H'):
			return 'H1'
		elif period.startswith('D'):
			return 'D1'
		elif period.startswith('W'):
			return 'W1'

	def stitchH4(self, vals):
		c_ohlc = []
		c_dt = None
		result = {}
		for dt, ohlc in vals.items():
			l_dt = self.utils.convertToLondonTimezone(dt)
			if l_dt.hour in Constants.FOUR_HOURS_BARS:
				if len(c_ohlc) > 0:
					ts = self.utils.convertUTCTimeToTimestamp(c_dt)
					result[ts] = c_ohlc

				c_ohlc = ohlc
				c_dt = dt
			elif len(c_ohlc) > 0:
				c_ohlc[1] = ohlc[1] if ohlc[1] > c_ohlc[1] else c_ohlc[1]
				c_ohlc[2] = ohlc[2] if ohlc[2] < c_ohlc[2] else c_ohlc[2]
				c_ohlc[3] = ohlc[3]
		return result

	'''
	REST API helper functions
	'''

	# def accountInfo(self, accountid):
		

	# def getPositions(self, accountid):
		

	# def getPosition(self, accountid, orderid):
		

	# def getReferenceDetails(self, accountid, ref):
		

	# def createPosition(self,
	# 	accountid,
	# 	product, direction, lotsize, 
	# 	orderType = 'MARKET', 
	# 	slPrice = None, slRange = None,
	# 	tpPrice = None, tpRange = None,
	# 	is_gslo = False
	# ):
		

	# def modifyPosition(self, accountid, orderid, slPrice=None, tpPrice=None):
		

	# def closePosition(self, accountid, pos):
		

	