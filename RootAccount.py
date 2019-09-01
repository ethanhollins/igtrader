from IGManager import IGManager
from Account import Account
from Plan import PlanState
from Utilities import Utilities
from Backtester import Backtester
import os
import sys
import json
import time
import traceback
import datetime

ONE_HOUR = 60 * 60

class RootAccount(object):
	
	def __init__(self, root_name, running_accounts):
		self.root_name = root_name
		if self.root_name == 'backtester':
			self.run_backtester(root_name)
		else:
			try:
				self.set_credentials(root_name, running_accounts)
				self.runloop()
			except:
				print(traceback.format_exc())
				if self.ls_client:
					self.ls_client.disconnect()
				sys.exit()

	def set_credentials(self, root_name, running_accounts):
		f_path = 'Accounts/{0}.json'.format(root_name)
		if os.path.exists(f_path):
			with open(f_path, 'r') as f:
				info = json.load(f)
				self.username = info['username']
				self.password = info['password']
				self.key = info['key']
				self.is_demo = info['isDemo']

				self.ls_client = None
				self.manager = IGManager(self)
				self.ls_client = self.manager.connectLS()
				
				self.accounts = []

				for name in info['accounts']:
					if name in running_accounts:
						new_acc = Account(
							self,
							self.manager,
							self.ls_client,
							name,
							info['accounts'][name]
						)

						if not self.manager:
							self.manager = new_acc.manager
							self.ls_client = new_acc.ls_client

						self.accounts.append(new_acc)

		else:
			print('Account name {0} does not exist'.format(root_name))

	def run_backtester(self, root_name):
		f_path = 'Accounts/{0}.json'.format(root_name)
		utils = Utilities()
		plans = []
		if os.path.exists(f_path):
			with open(f_path, 'r') as f:
				info = json.load(f)
				method = info['method']

				if info['start']:
					start = utils.convertDatetimeToTimestamp(
						datetime.datetime.strptime(info['start'], '%d/%m/%y %H:%M')
					)
				else:
					start = None

				if info['end']:
					end = utils.convertDatetimeToTimestamp(
						datetime.datetime.strptime(info['end'], '%d/%m/%y %H:%M')
					)
				else:
					end = None

				plans_info = info['plans']

				for i in plans_info:
					plans.append(Backtester(i['name'], i['variables']))

		results = {}
		for i in range(len(plans)):
			plan = plans[i]
			_, data = plan.backtest(start=start, end=end, method=method)
			results[plan.name + ' ({0})'.format(i)] = data

		# print(results)

	def runloop(self):
		check_time = time.time()
		while True:

			for acc in self.accounts:
				for plan in acc.plans:
					if plan.plan_state == PlanState.STARTED:
						try:
							plan.module.onLoop()
						except Exception as e:
							if not 'onLoop' in str(e):
								print('PlanError {0}:\n{1}'.format(acc.accountid, str(e)))
								plan.plan_state = PlanState.STOPPED
			
			if time.time() - check_time > ONE_HOUR:
				self.manager.getTokens()
				check_time = time.time()
			time.sleep(0.1)

	def findAccount(self, accountid):
		for acc in self.accounts:
			if acc.accountid == accountid:
				return accountid
		return None
		