from Position import Position
from Plan import Plan
import Constants
import json
import time

class Account(object):
	
	def __init__(self, 
		root, manager, ls_client,
		accountid, plans
	):
		self.root = root
		self.manager = manager
		self.ls_client = ls_client

		self.accountid = accountid
		self.position_queue = []
 
		self.manager.subscribe(
			self.ls_client, 
			'DISTINCT', 
			['TRADE:{0}'.format(self.accountid)], 
			['OPU'], 
			self.onItemUpdate
		)

		self.plans = [Plan(
			self, i,
			plans[i]['variables'],
			plans[i]['storage']
		) for i in plans]

	def getRootDict(self):
		root_path = 'Accounts/{0}.json'.format(self.root.root_name)
		with open(root_path, 'r') as f:
			root_dict = json.load(f)
		return root_dict

	def onItemUpdate(self, item):
		if 'OPU' in item['values'] and item['values']['OPU']:
			opu = item['values']['OPU']

			if opu['dealStatus'] == 'ACCEPTED':

				if opu['status'] == 'OPEN':
					pos = Position(
						self, opu['dealId'],
						opu['epic'], opu['direction']
					)
					pos.lotsize = float(opu['size'])
					pos.entryprice = float(opu['level'])
					pos.opentime = self.manager.utils.convertUTCSnapshotToTimestamp(opu['timestamp'])
					pos.sl = float(opu['stopLevel'])
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

								if float(opu['level']) == float(opu['stopLevel']):
									plan.onStopLoss(pos)
								elif float(opu['level']) == float(opu['limitLevel']):
									plan.onTakeProfit(pos)
								else:
									low_chart = plan.getLowestPeriodChart()
									if low_chart:
										if opu['direction'] == Constants.BUY:
											if low_chart.c_bid[2] <= float(opu['stopLevel']):
												plan.onStopLoss(pos)
											elif low_chart.c_bid[1] >= float(opu['limitLevel']):
												plan.onTakeProfit(pos)
											else:
												plan.onClose(pos)

										else:
											if low_chart.c_ask[1] >= float(opu['stopLevel']):
												plan.onStopLoss(pos)
											elif low_chart.c_ask[2] <= float(opu['limitLevel']):
												plan.onTakeProfit(pos)
											else:
												plan.onClose(pos)

								plan.savePositions()
								
				elif opu['status'] == 'UPDATED':

					for pos in self.position_queue:
						if pos.orderid == opu['dealId']:
							pos.sl = float(opu['stopLevel'])
							pos.tp = float(opu['limitLevel'])

					for plan in self.plans:
						for pos in plan.positions:
							if pos.orderid == opu['dealId']:
								pos.sl = float(opu['stopLevel'])
								pos.tp = float(opu['limitLevel'])

								plan.onModified(pos)
								plan.savePositions()

			elif opu['dealStatus'] == 'REJECTED':
				for plan in self.plans:
					for pos in plan.positions:
						if pos.orderid == opu['dealId']:
							plan.onRejected(pos)

