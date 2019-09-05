from IGManager import IGManager
from Account import Account
from Plan import PlanState
from Utilities import Utilities
from Backtester import Backtester
from matplotlib import pyplot as plt
from matplotlib import dates as mpl_dates
from matplotlib import gridspec as gridspec
import Constants
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
								print('PlanError ({0}):\n{1}'.format(acc.accountid, traceback.format_exc()))
								plan.plan_state = PlanState.STOPPED
			
			if time.time() - check_time > ONE_HOUR:
				self.manager.getTokens()
				check_time = time.time()
			time.sleep(0.1)

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
					plans.append(Backtester(i['name'], i['variables'], info['source']))

		results = {}
		for i in range(len(plans)):
			plan = plans[i]
			_, data = plan.backtest(start=start, end=end, method=method)
			results[plan.name + ' ({0})'.format(i)] = data

		if method == 'compare':
			self.showGraphs(results)

	def showGraphs(self, results):
		plt.style.use('seaborn')
		# fig = plt.figure()
		# gridspec.GridSpec((4,2))
		# fig, (ax1, ax2) = plt.subplots(1, 2)

		ax1 = plt.subplot2grid((1,8), (0,0), colspan=3)
		ax2 = plt.subplot2grid((1,8), (0,3), colspan=3)
		ax3 = plt.subplot2grid((1,8), (0,6), colspan=1)
		ax3.grid(False)
		ax3.patch.set_facecolor('white')
		ax3.set_xticks([])
		ax3.set_yticks([])

		colors = ['b', 'g', 'r', 'c', 'm', 'y']

		count = 0
		for plan in results:
			color = colors[count]

			# Percentage Drawdown
			data = sorted(results[plan][Constants.DAILY_PERC_DD].items(), key=lambda kv: kv[0])
			dates = [i[0] for i in data]
			perc_dd = [i[1] for i in data]

			ax1.bar(dates, perc_dd, color=color, alpha=0.5)
			ax1.xaxis_date()

			# Percentage Return
			data = sorted(results[plan][Constants.DAILY_PERC_RET].items(), key=lambda kv: kv[0])
			dates = [i[0] for i in data]
			perc_ret = [i[1] for i in data]

			ax1.plot(dates, perc_ret, color=color, alpha=0.8)
			ax1.xaxis_date()

			# Position Equity Drawdown
			data = sorted(results[plan][Constants.POS_EQUITY_DD].items(), key=lambda kv: kv[0])
			dates = [i[0] for i in data]
			pos_equity_dd = [i[1] for i in data]
			ax2.bar(dates, pos_equity_dd, color=color, alpha=0.5)
			ax2.xaxis_date()

			# Position Equity Return
			data = sorted(results[plan][Constants.POS_EQUITY_RET].items(), key=lambda kv: kv[0])
			dates = [i[0] for i in data]
			pos_equity_ret = [i[1] for i in data]

			ax2.plot(dates, pos_equity_ret, color=color, alpha=0.8)
			ax2.xaxis_date()

			ax3.text(
				0,len(results)*8-count*8-7, 
				'{0}:'.format(plan), 
				fontsize=11, horizontalalignment='left',
				fontweight='bold'
			)
			ax3.text(
				0, len(results)*8-count*8-6, 
				'% Ret: {0}'.format(
					results[plan][Constants.POS_PERC_RET]
				), 
				fontsize=10, horizontalalignment='left'
			)
			ax3.text(
				0, len(results)*8-count*8-5, 
				'PIP Ret: {0}'.format(
					results[plan][Constants.POS_PIP_RET]
				), 
				fontsize=10, horizontalalignment='left'
			)
			ax3.text(
				0, len(results)*8-count*8-4, 
				'% DD: {0}'.format(
					results[plan][Constants.POS_PERC_DD]
				), 
				fontsize=10, horizontalalignment='left'
			)
			ax3.text(
				0, len(results)*8-count*8-3, 
				'Wins: {0} | Losses: {1}'.format(
					results[plan][Constants.WINS],
					results[plan][Constants.LOSSES]
				), 
				fontsize=10, horizontalalignment='left'
			)
			ax3.text(
				0, len(results)*8-count*8-2, 
				'Win %: {0} | Loss %: {1}'.format(
					results[plan][Constants.WIN_PERC],
					results[plan][Constants.LOSS_PERC]
				), 
				fontsize=10, horizontalalignment='left'
			)
			ax3.text(
				0, len(results)*8-count*8-1, 
				'Gain: {0} | Loss: {1}'.format(
					results[plan][Constants.GAIN],
					results[plan][Constants.LOSS]
				), 
				fontsize=10, horizontalalignment='left'
			)
			ax3.text(
				0, len(results)*8-count*8, 
				'GPR: {0}'.format(results[plan][Constants.GPR]), 
				fontsize=10, horizontalalignment='left'
			)

			count += 1

		date_format = mpl_dates.DateFormatter('%b %d \'%y')

		ax1.set_title('Daily Equity')
		ax1.set_xlabel('Date')
		ax1.set_ylabel('Percentage')
		ax1.legend(results.keys())
		ax1.xaxis.set_major_formatter(date_format)

		ax2.set_title('Position Return')
		ax2.set_xlabel('Date')
		ax2.set_ylabel('Percentage')
		ax2.legend(results.keys())
		ax2.xaxis.set_major_formatter(date_format)

		ax3.set_ylim(max((count)*8, 2*8),0)

		plt.gcf().autofmt_xdate()
		plt.tight_layout()
		plt.show()

	def findAccount(self, accountid):
		for acc in self.accounts:
			if acc.accountid == accountid:
				return accountid
		return None
		