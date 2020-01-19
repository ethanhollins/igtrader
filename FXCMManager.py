from Chart import Chart

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
		# print(self.con.get_instruments())
		# data = self.con.get_candles('EUR/USD', period='m1', number=250)
		# print(data.head())

		# start = datetime.datetime(2017, 7, 12)
		# stop = datetime.datetime(2017, 7, 12, 1)
		# data = self.con.get_candles(
		# 	'GBP/USD', period='m1',
		# 	start=start, number=10
		# )
		# print(data)

	def getRootDict(self):
		root_path = 'Accounts/{0}.json'.format(self.root.root_name)
		with open(root_path, 'r') as f:
			root_dict = json.load(f)
		return root_dict

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

	# def getPricesByDate(self, product, period, start_dt, end_dt, page_number, result):
		

	'''
	REST API helper functions
	'''

	# def checkTokens(self):
		

	# def refreshTokens(self):
		

	# def getTokens(self, accountid=None, attempts=0):
		

	# def switchAccount(self, accountid, attempts=0):
		

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
		

	