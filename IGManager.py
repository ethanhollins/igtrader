from lightstreamer_client import LightstreamerClient as LSClient
from lightstreamer_client import LightstreamerSubscription as Subscription
from Chart import Chart
from Utilities import Utilities

import requests
import json
import traceback
import time

class IGManager(object):

	def __init__(self, root):
		self.root = root
		self.utils = Utilities()
		self.charts = []

		self.current_account = None
		self.ls_endpoint = None

		if root.is_demo:
			self.url = 'https://demo-api.ig.com/gateway/deal/'
		else:
			self.url = 'https://api.ig.com/gateway/deal/'

		self.headers = {
			'Content-Type': 'application/json; charset=UTF-8',
			'Accept': 'application/json; charset=UTF-8',
			'X-IG-API-KEY': self.root.key, 
			'Version': '2',
			'X-SECURITY-TOKEN': '',
			'CST': ''
		}

		self.getSavedTokens()

		self.creds = {
			'identifier': self.root.username,
			'password': self.root.password,
			'encryptedPassword': None
		}

		self.attempts = 0;

	def getRootDict(self):
		root_path = 'Accounts/{0}.json'.format(self.root.root_name)
		with open(root_path, 'r') as f:
			root_dict = json.load(f)
		return root_dict

	def getSavedTokens(self):
		info = self.getRootDict()
		self.headers['X-SECURITY-TOKEN'] = info['tokens']['X-SECURITY-TOKEN']
		self.headers['CST'] = info['tokens']['CST']

	def saveTokens(self):
		info = self.getRootDict()
		info['tokens']['X-SECURITY-TOKEN'] = self.headers['X-SECURITY-TOKEN']
		info['tokens']['CST'] = self.headers['CST']
		root_path = 'Accounts/{0}.json'.format(self.root.root_name)
		with open(root_path, 'w') as f:
			f.write(json.dumps(info, indent=4))

	'''
	Chart helper functions
	'''
	def subscribeChart(self, plan, product, period):
		for chart in self.charts:
			if chart.isChart(product, period):
				if not account in chart.subscribed_accounts:
					chart.subscribed_plans.append(plan)
					return chart
		return None

	def unsubscribeChart(self, plan, product, period):
		for chart in self.charts:
			if chart.isChart(product, period):
				if account in chart.subscribed_accounts:
					del chart.subscribed_accounts[
						chart.subscribed_plans.index(plan)
					]
					return chart
		return None

	def getChart(self, plan, product, period):
		for chart in self.charts:
			if chart.isChart(product, period):
				chart.subscribed_plans.append(plan)
				return chart
		
		chart = self.createChart(product, period)
		chart.subscribed_plans.append(plan)
		return chart

	def getChartFromChart(self, plan, chart):
		chart = Chart(self.root, chart=chart)
		self.charts.append(chart)
		chart.subscribed_plans.append(plan)
		return chart

	def createChart(self, product, period):
		chart = Chart(self.root, product=product, period=period)
		self.charts.append(chart)
		return chart

	def getPricesByDate(self, product, period, start_dt, end_dt, page_number, result):
		if not self.getTokens():
			return None

		endpoint = 'prices/{0}?resolution={1}&from={2}&to={3}&pageSize=500&pageNumber={4}'.format(
			product, period,
			start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
			end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
			page_number
		)

		self.headers['Version'] = '3'
		res = requests.get(
			self.url + endpoint, 
			headers=self.headers
		)

		if res.status_code == 200:
			data = res.json()
			if not 'bids' in result:
				result['bids'] = {}
			if not 'asks' in result:
				result['asks'] = {}

			for price in data['prices']:
				ts = self.utils.convertUTCSnapshotToTimestamp(price['snapshotTimeUTC'])
				result['bids'][ts] = [
					float(price['openPrice']['bid']),
					float(price['highPrice']['bid']),
					float(price['lowPrice']['bid']),
					float(price['closePrice']['bid'])
				]

				result['asks'][ts] = [
					float(price['openPrice']['ask']),
					float(price['highPrice']['ask']),
					float(price['lowPrice']['ask']),
					float(price['closePrice']['ask'])
				]

			page_number = data['metadata']['pageData']['pageNumber']
			total_pages = data['metadata']['pageData']['totalPages']

			if page_number < total_pages:
				return self.getPricesByDate(product, period, start_dt, end_dt, page_number+1, result)
			else:
				return result

		else:
			print('Error getting tokens:\n{0}'.format(res.json()))
			return None

	'''
	REST API helper functions
	'''

	def checkTokens(self):
		if self.headers['X-SECURITY-TOKEN'] and self.headers['CST']:
			endpoint = 'session'
			self.headers['Version'] = '2'
			res = requests.post(
				self.url + endpoint, 
				data=json.dumps(self.creds),
				headers=self.headers
			)

			if res.status_code == 200:
				self.ls_endpoint = res.json()['lightstreamerEndpoint']
				# self.current_account = res.json().get('currentAccountId')
				return True
			elif res.status_code == 401:
				self.headers['X-SECURITY-TOKEN'] = ''
				self.headers['CST'] = ''
				return False
			else:
				print('Error checking tokens ({0}):\n{1}'.format(res.status_code, res.json()))
				self.headers['X-SECURITY-TOKEN'] = ''
				self.headers['CST'] = ''
				return False
		else:
			self.headers['X-SECURITY-TOKEN'] = ''
			self.headers['CST'] = ''
			return False

	def getTokens(self, accountid=None):
		if self.checkTokens():
			if accountid:
				if self.switchAccount(accountid):
					return True
				else:
					return False
			return True

		endpoint = 'session'
		self.headers['Version'] = '2'
		self.headers['X-SECURITY-TOKEN'] = ''
		self.headers['CST'] = ''
		res = requests.post(
			self.url + endpoint, 
			data=json.dumps(self.creds),
			headers=self.headers
		)

		if res.status_code == 200:
			print('Tokens retrieved ({0})'.format(res.status_code))

			self.headers['X-SECURITY-TOKEN'] = res.headers.get('X-SECURITY-TOKEN')
			self.headers['CST'] = res.headers.get('CST')
			self.saveTokens()
			self.ls_endpoint = res.json().get('lightstreamerEndpoint')
			self.current_account = res.json().get('currentAccountId')
			self.attempts = 0

			if accountid:
				if self.switchAccount(accountid):
					return True
				else:
					return False

			return True
		else:
			print('Error getting tokens ({0}):\n{1}'.format(res.status_code, res.json()))
			if self.attempts >= 5:
				self.attempts = 0
				return False
			else:
				self.headers['X-SECURITY-TOKEN'] = ''
				self.headers['CST'] = ''
				self.attempts += 1
				print('Reattempting token retrieval ({1})'.format(self.attempts))
				return self.getTokens(accountid)

	def switchAccount(self, accountid):
		if self.current_account == accountid:
			print('[{0}] Is already currrent.'.format(accountid))
			return True

		endpoint = 'session'
		self.headers['Version'] = '1'
		payload = {
			"accountId": accountid,
			"defaultAccount": None
		}
		res = requests.put(
			self.url + endpoint,
			data=json.dumps(payload),
			headers=self.headers
		)

		if res.status_code == 200 or res.status_code == 412:
			print('[{0}] Account switched ({1})'.format(accountid, res.status_code))
			self.current_account = accountid
			if res.headers.get('X-SECURITY-TOKEN'):
				self.headers['X-SECURITY-TOKEN'] = res.headers.get('X-SECURITY-TOKEN')
			self.saveTokens()
			self.attempts = 0
			return True
		else:
			print('Error switching account ({0}):\n{1}'.format(res.status_code, res.json()))
			if self.attempts >= 5:
				self.attempts = 0
				return False
			else:
				self.attempts += 1
				print('[{0}] Reattempting account switch ({1})'.format(accountid, self.attempts))
				return self.switchAccount(accountid)

	def accountInfo(self, accountid):
		if not self.getTokens():
			return None

		endpoint = 'accounts'
		self.headers['Version'] = '1'
		res = requests.get(
			self.url + endpoint, 
			headers=self.headers
		)

		if res.status_code == 200:
			for account in res.json()['accounts']:
				if account['accountId'] == accountid:
					return account

			print('Couldn\'t find account:\n{0}'.format(res.json()))
		else:
			print('Error getting account info ({0}):\n{1}'.format(res.status_code, res.json()))
			return False

	def getPositions(self, accountid):
		if not self.getTokens(accountid):
			return None

		endpoint = 'positions'
		self.headers['Version'] = '2'
		res = requests.get(
			self.url + endpoint,
			headers=self.headers
		)

		if res.status_code == 200:
			return res.json()
		else:
			print('Error:\n{0}'.format(res.json()))
			return None

	def getPosition(self, accountid, orderid):
		if not self.getTokens(accountid):
			return None

		endpoint = 'positions/{0}'.format(orderid)
		self.headers['Version'] = '2'
		res = requests.get(
			self.url + endpoint,
			headers=self.headers
		)

		if res.status_code == 200:
			return res.json()
		else:
			print('Error:\n{0}'.format(res.json()))
			return None

	def getReferenceDetails(self, accountid, ref):
		if not self.getTokens(accountid):
			return None

		endpoint = 'confirms/{0}'.format(ref)
		self.headers['Version'] = '1'
		res = requests.get(
			self.url + endpoint,
			headers=self.headers
		)

		if res.status_code == 200:
			return res.json()
		else:
			print('Error:\n{0}'.format(res.json()))
			return None

	def createPosition(self,
		accountid,
		product, direction, lotsize, 
		orderType = 'MARKET', 
		slPrice = None, slRange = None,
		tpPrice = None, tpRange = None,
		is_gslo = False
	):
		if not self.getTokens(accountid):
			return None

		endpoint = 'positions/otc'
		payload = {
			"epic": product,
			"expiry": "-",
			"direction": direction,
			"size": lotsize,
			"orderType": orderType,
			"timeInForce": "FILL_OR_KILL",
			"level": None,
			"guaranteedStop": str(is_gslo).lower(),
			"stopLevel": slPrice,
			"stopDistance": slRange,
			"trailingStop": "false",
			"trailingStopIncrement": None,
			"forceOpen": "true",
			"limitLevel": tpPrice,
			"limitDistance": tpRange,
			"quoteId": None,
			"currencyCode": "USD"
		}

		self.headers['Version'] = '2'
		res = requests.post(
			self.url + endpoint, 
			data=json.dumps(payload),
			headers=self.headers
		)

		if res.status_code == 200:
			return self.getReferenceDetails(accountid, res.json()['dealReference'])
		else:
			print('Error creating position ({0}):\n{1}'.format(res.status_code, res.json()))
			return None

	def modifyPosition(self, accountid, orderid, slPrice=None, tpPrice=None):
		if not self.getTokens(accountid):
			return None

		endpoint = 'positions/otc/{0}'.format(orderid)
		payload = {
			"stopLevel": slPrice,
			"limitLevel": tpPrice,
			"trailingStop": "false",
			"trailingStopDistance": None,
			"trailingStopIncrement": None
		}

		self.headers['Version'] = '2'
		res = requests.put(
			self.url + endpoint, 
			data=json.dumps(payload),
			headers=self.headers
		)

		if res.status_code == 200:
			return self.getReferenceDetails(accountid, res.json()['dealReference'])
		else:
			print('Error:\n{0}'.format(res.json()))
			return None

	def closePosition(self, accountid, pos):
		if not self.getTokens(accountid):
			return None

		endpoint = 'positions/otc'
		payload = {
			"dealId": pos.orderid,
			"epic": None,
			"expiry": None,
			"size": pos.lotsize,
			"level": None,
			"orderType": "MARKET",
			"timeInForce": None,
			"quoteId": None
		}

		if pos.direction == 'BUY':
			payload['direction'] = 'SELL'
		else:
			payload['direction'] = 'BUY'

		self.headers['Version'] = '1'
		self.headers['_method'] = 'DELETE'
		res = requests.post(
			self.url + endpoint, 
			data=json.dumps(payload),
			headers=self.headers
		)
		self.headers.pop('_method', None)

		if res.status_code == 200:
			return self.getReferenceDetails(accountid, res.json()['dealReference'])
		else:
			print('Error closing position ({0}):\n{1}'.format(res.status_code, res.json()))
			return None

	'''
	Lightstreamer helper functions
	'''

	def connectLS(self):
		count = 1
		while True:
			if not self.getTokens():
				return None

			ls_client = LSClient(
				self.root.root_name,
				"CST-{0}|XST-{1}".format(
					self.headers['CST'], 
					self.headers['X-SECURITY-TOKEN']
				),
				self.ls_endpoint
			)

			print("Attempting to connect ({0})...".format(count))
			try:
				ls_client.connect()
				return ls_client
			except Exception as e:
				count += 1
				time.sleep(1)
				pass

	def reconnectLS(self, ls_client):
		subscriptions = ls_client._subscriptions

		count = 1
		while True:
			if not self.getTokens():
				return None
			
			new_ls_client = LSClient(
				self.root.root_name,
				"CST-{0}|XST-{1}".format(
					self.headers['CST'], 
					self.headers['X-SECURITY-TOKEN']
				),
				self.ls_endpoint
			)

			print("Attempting to reconnect ({0})...".format(count))
			try:
				new_ls_client.connect()
				break
			except Exception as e:
				count += 1
				time.sleep(1)
				pass
				
		for i in subscriptions:
			self.subscribe(
				new_ls_client, 
				subscriptions[i].mode, 
				subscriptions[i].item_names, 
				subscriptions[i].field_names,
				subscriptions[i]._listeners[0]
			)
			
		ls_client.disconnect()

		return new_ls_client

	def subscribe(self, ls_client, mode, items, fields, listener):
		subscription = Subscription(
			mode=mode, 
			items= items,
			fields= fields
		)

		subscription.addlistener(listener)
		ls_client.subscribe(subscription)
		return subscription