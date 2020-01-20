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
		
		print('Connecting to FXCM...')
		self.con = fxcmpy.fxcmpy(
			access_token=self.root.key, 
			log_level='error',
			log_file='./Logs/FXCM',
			server='demo'
		)
		print('Connected to FXCM.')

		# print(self.getPositions('5633193'))

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
			result['bids'] = self.stitchH(result['bids'], Constants.FOUR_HOURS_BARS)
			result['asks'] = self.stitchH(result['asks'], Constants.FOUR_HOURS_BARS)

		return result
	
	def getReqPeriod(self, period):
		if period.startswith('m'):
			return 'm1'
		elif period.startswith('H'):
			return 'H1'
		elif period.startswith('D'):
			return 'D1'
		elif period.startswith('W'):
			return 'W1'

	def stitchH(self, vals, bars):
		c_ohlc = []
		c_dt = None
		result = {}
		for dt, ohlc in vals.items():
			l_dt = self.utils.convertToLondonTimezone(dt)
			if l_dt.hour in bars:
				if len(c_ohlc) > 0:
					ts = self.utils.convertUTCTimeToTimestamp(c_dt)
					result[ts] = c_ohlc

				c_ohlc = ohlc
				c_dt = dt
			elif len(c_ohlc) > 0:
				c_ohlc[1] = ohlc[1] if ohlc[1] > c_ohlc[1] else c_ohlc[1]
				c_ohlc[2] = ohlc[2] if ohlc[2] < c_ohlc[2] else c_ohlc[2]
				c_ohlc[3] = ohlc[3]

		ts = self.utils.convertUTCTimeToTimestamp(c_dt)
		result[ts] = c_ohlc
		return result

	'''
	REST API helper functions
	'''

	def getEquity(self, accountid):
		result = self.con.get_accounts(kind='list')
		for i in result:
			if i['accountId'] == accountid:
				return i['equity']
		return None
	
	def getBalance(self, accountid):
		result = self.con.get_accounts(kind='list')
		for i in result:
			if i['accountId'] == accountid:
				return i['balance']
		return None	

	def getPositions(self, accountid):
		result = self.con.get_open_positions(kind='list')
		return [i for i in result if i['accountId'] == accountid]
		
	def getPosition(self, orderid):
		result = self.con.get_open_position(orderid)
		return result

	def createPosition(self,
		accountid,
		product, direction, lotsize, 
		orderType = 'MARKET', 
		slPrice = None, slRange = None,
		tpPrice = None, tpRange = None,
		is_gslo = False
	):
		sl = None
		tp = None
		is_in_pips = False

		if slPrice or tpPrice:
			sl = slPrice
			tp = tpPrice
		elif slRange or tpRange:
			sl = slRange
			tp = tpRange
			is_in_pips = True

		order = self.con.open_trade(
			symbol=product,
			is_buy= direction == Constants.BUY,
			amount=str(lotsize),
			time_in_force='GTC',
			order_type='AtMarket',
			is_in_pips=is_in_pips,
			limit=tpRange if is_in_pips else tpPrice,
			stop=slRange if is_in_pips else slPrice,
			accountid=accountid
		)

		return order

	def modifyPosition(self, orderid, slPrice=None, tpPrice=None):
		
		if slPrice:
			self.con.change_trade_stop_limit(
				orderid, is_in_pips=False,
				is_stop=True,
				rate=slPrice
			)
		if tpPrice:
			self.con.change_trade_stop_limit(
				orderid, is_in_pips=False,
				is_stop=False,
				rate=tpPrice
			)

		return

	def closePosition(self, orderid):
		self.con.close_trade(
			trade_id=orderid, amount=0,
		)
		return

	def closeAllPositions(self):
		self.con.close_all()
	