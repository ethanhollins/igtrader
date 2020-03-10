from Position import Position
from Plan import Plan
from IGManager import IGManager
import Constants
import json
import time

class Account(object):
	
	def __init__(self, 
		root, accountid, plans
	):
		self.root = root
		self.manager = root.manager

		self.accountid = accountid
		self.position_queue = []
		self.rejected_queue = []

		self.audusd_bid = None
		self.getLiveData()

		self.funds = 0
		self.equity = 0

		self.last_save = time.time()

		self.plans = [Plan(
			self, i,
			plans[i]['name'],
			plans[i]['variables'],
			plans[i]['storage']
		) for i in range(len(plans))]

	def checkSave(self):
		if time.time() - self.last_save > 60:
			for plan in self.plans:
				if plan.needs_save:
					print('Saving Positions ({})...'.format(plan.idx))
					plan.savePositions()
					plan.needs_save = False
			self.last_save = time.time()


	def getRootDict(self, name=''):
		root_path = 'Accounts/{0}.json'.format(self.root.root_name)
		return self.root.getJsonFromFile(root_path, name=name)

	def getLiveData(self):
		if self.root.broker == 'ig':
			self.manager.subscribe(
				self.root.controller.ls_clients[self.root.username], 
				'DISTINCT', 
				['TRADE:{0}'.format(self.accountid)], 
				['OPU'], 
				self.onOpuItemUpdate
			)
			self.root.controller.subscriptions[self.root.username].append((
				'DISTINCT',
				['TRADE:{0}'.format(self.accountid)], 
				['OPU'], 
				self.onOpuItemUpdate
			))

			self.manager.subscribe(
				self.root.controller.ls_clients[self.root.username], 
				'DISTINCT', 
				['CHART:CS.D.AUDUSD.CFD.IP:TICK'], 
				['BID'],
				self.onAUDItemUpdate
			)
			self.root.controller.subscriptions[self.root.username].append((
				'DISTINCT',
				['CHART:CS.D.AUDUSD.CFD.IP:TICK'], 
				['BID'], 
				self.onAUDItemUpdate
			))

			self.manager.subscribe(
				self.root.controller.ls_clients[self.root.username], 
				'DISTINCT', 
				['CHART:CS.D.AUDUSD.CFD.IP:TICK'], 
				['BID'],
				self.onAUDItemUpdate
			)
			self.root.controller.subscriptions[self.root.username].append((
				'DISTINCT',
				['CHART:CS.D.AUDUSD.CFD.IP:TICK'], 
				['BID'], 
				self.onAUDItemUpdate
			))

			self.manager.subscribe(
				self.root.controller.ls_clients[self.root.username], 
				'MERGE', 
				['ACCOUNT:{}'.format(self.accountid)], 
				['FUNDS', 'EQUITY'],
				self.onAccountUpdate
			)
			self.root.controller.subscriptions[self.root.username].append((
				'MERGE',
				['ACCOUNT:{}'.format(self.accountid)], 
				['FUNDS', 'EQUITY'],
				self.onAccountUpdate
			))

		# elif self.root.broker == 'fxcm':
		# 	# TODO

	def onOpuItemUpdate(self, item):
		if 'OPU' in item['values'] and item['values']['OPU']:
			opu = json.loads(item['values']['OPU'])
			if opu['dealStatus'] == 'ACCEPTED':
				if opu['status'] == 'OPEN':
					pos = Position(
						self, opu['dealId'],
						opu['epic'], opu['direction']
					)
					pos.ref = opu['dealReference']
					pos.lotsize = float(opu['size'])
					pos.entryprice = float(opu['level'])
					pos.opentime = self.manager.utils.convertUTCSnapshotToTimestamp(opu['timestamp'])
					if opu['stopLevel']:
						pos.sl = float(opu['stopLevel'])
					if opu['limitLevel']:
						pos.tp = float(opu['limitLevel'])

					self.position_queue.append(pos)

				elif opu['status'] == 'DELETED':

					for pos in self.position_queue:
						if pos.orderid == opu['dealId']:
							pos.closeprice = float(opu['level'])
							pos.closetime = self.manager.utils.convertUTCSnapshotToTimestamp(opu['timestamp'])

					for plan in self.plans:
						for pos in plan.positions:
							if pos.orderid == opu['dealId']:
								pos.closeprice = float(opu['level'])
								pos.closetime = self.manager.utils.convertUTCSnapshotToTimestamp(opu['timestamp'])

								del plan.positions[plan.positions.index(pos)]
								plan.closed_positions.append(pos)

								if opu['stopLevel'] and float(opu['level']) == float(opu['stopLevel']):
									plan.onStopLoss(pos)
								elif opu['limitLevel'] and float(opu['level']) == float(opu['limitLevel']):
									plan.onTakeProfit(pos)
								else:
									low_chart = plan.getLowestPeriodChart()
									if low_chart:
										if opu['direction'] == Constants.BUY:
											if opu['stopLevel'] and low_chart.c_bid[2] <= float(opu['stopLevel']):
												plan.onStopLoss(pos)
											elif opu['limitLevel'] and low_chart.c_bid[1] >= float(opu['limitLevel']):
												plan.onTakeProfit(pos)
											else:
												plan.onClose(pos)

										else:
											if opu['stopLevel'] and low_chart.c_ask[1] >= float(opu['stopLevel']):
												plan.onStopLoss(pos)
											elif opu['limitLevel'] and low_chart.c_ask[2] <= float(opu['limitLevel']):
												plan.onTakeProfit(pos)
											else:
												plan.onClose(pos)

								plan.needs_save = True
								
				elif opu['status'] == 'UPDATED':

					for pos in self.position_queue:
						if pos.orderid == opu['dealId']:
							if opu['stopLevel']:
								pos.sl = float(opu['stopLevel'])
							if opu['limitLevel']:
								pos.tp = float(opu['limitLevel'])

					for plan in self.plans:
						for pos in plan.positions:
							if pos.orderid == opu['dealId']:
								if opu['stopLevel']:
									pos.sl = float(opu['stopLevel'])
								else:
									pos.sl = None
								if opu['limitLevel']:
									pos.tp = float(opu['limitLevel'])
								else:
									pos.tp = None

								plan.onModified(pos)

			elif opu['dealStatus'] == 'REJECTED':
				for plan in self.plans:
					for pos in plan.positions:
						if pos.orderid == opu['dealId']:
							plan.onRejected(pos)
							return
				self.rejected_queue.append(opu['dealReference'])

	def onAUDItemUpdate(self, item):
		if item['values'] and item['values']['BID']:
			self.audusd_bid = float(item['values']['BID'])

	def onAccountUpdate(self, item):
		if 'values' in item:
			self.funds = float(item['values']['FUNDS'])
			self.equity = float(item['values']['EQUITY'])

	def refreshTokens(self):
		self.manager.refreshTokens()