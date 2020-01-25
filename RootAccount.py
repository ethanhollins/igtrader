from IGManager import IGManager
from FXCMManager import FXCMManager
from Account import Account
from Plan import PlanState
from Utilities import Utilities
from Backtester import Backtester
from matplotlib import pyplot as plt
from matplotlib import dates as mpl_dates
from matplotlib import gridspec as gridspec
from mpl_finance import candlestick_ohlc
from threading import Thread
from lightstreamer_client import LightstreamerClient as LSClient
from lightstreamer_client import LightstreamerSubscription as Subscription
import Constants
import os
import sys
import json
import time
import traceback
import datetime
import numpy as np

TWO_MINUTES = 60 * 2
ONE_HOUR = 60*60

class RootAccount(object):
	
	def __init__(self, controller, idx, root_name, running_accounts):
		self.controller = controller
		self.idx = idx
		self.root_name = root_name
		self.cmd_queue = []

		if self.root_name == 'backtester':
			self.run_backtester(root_name)
		else:
			try:
				self.set_credentials(root_name, running_accounts)
			except:
				print(traceback.format_exc())
				if self.broker == 'ig' and self.username in self.controller.ls_clients:
					self.controller.ls_clients[self.username].disconnect()
				sys.exit()

	def set_credentials(self, root_name, running_accounts):
		f_path = 'Accounts/{0}.json'.format(root_name)
		if os.path.exists(f_path):
			with open(f_path, 'r') as f:
				info = json.load(f)
				
				self.key = info['key']
				self.is_demo = info['isDemo']
				self.utils = Utilities()

				self.setBrokerAccounts(info)
		else:
			print('Account name {0} does not exist'.format(root_name))

	def setBrokerAccounts(self, info):
		if info['broker'] == 'ig':
			self.username = info['username']
			self.password = info['password']
			self.broker = info['broker']
			self.manager = IGManager(self)

			self.accounts = []

			for name in info['accounts']:
				if name in running_accounts:
					new_acc = Account(
						self,
						name,
						info['accounts'][name]['plans']
					)

					self.accounts.append(new_acc)

		elif info['broker'] == 'fxcm':
			self.broker = info['broker']
			self.manager = FXCMManager(self)

	def runloop(self):
		self.is_weekend = True
		while True:
			time.sleep(0.1)

			if all([i.is_open == False for i in self.controller.charts]):
				# if not self.is_weekend:
					# self.controller.performScheduledRestart()
				self.is_weekend = True
			else:
				self.is_weekend = False
				for chart in self.controller.charts:
					if not chart.last_update or (datetime.datetime.now() - chart.last_update).total_seconds() > TWO_MINUTES:
						print('isClientReconnect {0}'.format(datetime.datetime.now()))

						chart.last_update = datetime.datetime.now()
						self.controller.ls_clients[self.username] = self.reconnectLS(
							self.controller.ls_clients[self.username],
							self.controller.subscriptions[self.username]
						)
						break
			self.manager.streamCheck()
			
			if self.is_weekend:
				continue
			
			threads = []
			for acc in self.accounts:
				t = Thread(target=self.onLoop, args=(acc,))
				t.start()
				threads.append(t)
			
			for t in threads:
				t.join()
				
			self.manager.refreshTokens()

	def onLoop(self, account):
		for plan in account.plans:
			if plan.plan_state == PlanState.STARTED:
				try:
					plan.module.onLoop()
				except Exception as e:
					if not 'onLoop' in str(e):
						plan.plan_state = PlanState.STOPPED
						print('PlanError ({0}):\n{1}'.format(acc.accountid, traceback.format_exc()))
		account.refreshTokens()

	def run_backtester(self, root_name):
		f_path = 'Accounts/{0}.json'.format(root_name)
		utils = Utilities()
		plans = []
		formatting = {}

		if os.path.exists(f_path):
			with open(f_path, 'r') as f:
				info = json.load(f)
				method = info['method']
				source = info['source']

				if info['start']:
					if source == 'ig':
						start = utils.convertDatetimeToTimestamp(
							datetime.datetime.strptime(info['start'], '%d/%m/%y %H:%M')
						)
					elif source == 'mt':
						start = utils.convertMTDatetimeToTimestamp(
							datetime.datetime.strptime(info['start'], '%d/%m/%y %H:%M')
						)
				else:
					start = None

				if info['end']:
					if source == 'ig':
						end = utils.convertDatetimeToTimestamp(
							datetime.datetime.strptime(info['end'], '%d/%m/%y %H:%M')
						)
					elif source == 'mt':
						end = utils.convertMTDatetimeToTimestamp(
							datetime.datetime.strptime(info['end'], '%d/%m/%y %H:%M')
						)
				else:
					end = None

				plans_info = info['plans']

				for i in range(len(plans_info)):
					plan = plans_info[i]
					plans.append(Backtester(self, plan['name'], plan['variables'], info['source']))

					name = plan['name'] + ' ({0})'.format(i)
					formatting[name] = {}
					if 'colors' in plan:
						formatting[name]['colors'] = plan['colors']
					if 'styles' in plan:
						formatting[name]['styles'] = plan['styles']
					if 'studies' in plan:
						formatting[name]['studies'] = plan['studies']
					if 'pos_data' in plan:
						formatting[name]['pos_data'] = plan['pos_data']

		results = {}
		for i in range(len(plans)):
			plan = plans[i]
			_, data = plan.backtest(start=start, end=end, method=method)
			results[plan.name + ' ({0})'.format(i)] = data

		if method == 'compare':
			self.showGraphs(results)
		elif method == 'show':
			self.showCharts(results, formatting)

	def saveToFile(self, path, data, priority=0, **kwargs):
		if self.controller.saveToFile(self.root_name, path, data, priority=priority, **kwargs):
			return self.controller.wait(self.root_name)
		return False

	def getJsonFromFile(self, path, priority=0, **kwargs):
		self.controller.getJsonFromFile(self.root_name, path, priority=priority, **kwargs)
		return self.controller.wait(self.root_name)

	def showGraphs(self, results):
		plt.style.use('seaborn')

		ax1 = plt.subplot2grid((1,8), (0,0), colspan=3)
		ax2 = plt.subplot2grid((1,8), (0,3), colspan=3)
		ax3 = plt.subplot2grid((1,8), (0,6), colspan=1)
		ax3.grid(False)
		ax3.patch.set_facecolor('white')
		ax3.set_xticks([])
		ax3.set_yticks([])

		colors = ['b', 'g', 'r', 'c', 'm', 'y']

		pos_aggregate = {}

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

			for i in range(len(dates)):
				if i != 0:
					pos_aggregate[dates[i]] = (
						pos_aggregate[dates[i]] + (perc_ret[i] - perc_ret[i-1])/len(results)
						if dates[i] in pos_aggregate else
						(perc_ret[i] - perc_ret[i-1])/len(results)
					)

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

			info_pos = len(results)*11-count*11

			ax3.text(
				0,info_pos-10, 
				'{0}:'.format(plan), 
				fontsize=11, horizontalalignment='left',
				fontweight='bold'
			)
			ax3.text(
				0, info_pos-9, 
				'Trading DAYS: {}'.format(
					results[plan][Constants.DAILY_WINS] + results[plan][Constants.DAILY_LOSSES]
				), 
				fontsize=10, horizontalalignment='left'
			)
			ax3.text(
				0, info_pos-8, 
				'% Ret: {0} | % DD: {1}'.format(
					results[plan][Constants.POS_PERC_RET],
					results[plan][Constants.POS_PERC_DD]
				), 
				fontsize=10, horizontalalignment='left'
			)
			ax3.text(
				0, info_pos-7, 
				'CMP % Ret: {0} | CMP % DD: {1}'.format(
					results[plan][Constants.POS_COMPOUND_RET],
					results[plan][Constants.POS_COMPOUND_DD]
				), 
				fontsize=10, horizontalalignment='left'
			)
			ax3.text(
				0, info_pos-6, 
				'Daily CMP % Ret: {0} | Daily CMP % DD: {1}'.format(
					results[plan][Constants.DAY_COMPOUND_RET],
					results[plan][Constants.DAY_COMPOUND_DD]
				), 
				fontsize=10, horizontalalignment='left'
			)
			ax3.text(
				0, info_pos-5, 
				'PIP Ret: {0}'.format(
					results[plan][Constants.POS_PIP_RET]
				), 
				fontsize=10, horizontalalignment='left'
			)
			ax3.text(
				0, info_pos-4, 
				'Wins: {0} | Losses: {1}'.format(
					results[plan][Constants.WINS],
					results[plan][Constants.LOSSES]
				), 
				fontsize=10, horizontalalignment='left'
			)
			ax3.text(
				0, info_pos-3, 
				'Daily Wins: {0} | Daily Losses: {1}'.format(
					results[plan][Constants.DAILY_WINS],
					results[plan][Constants.DAILY_LOSSES]
				), 
				fontsize=10, horizontalalignment='left'
			)
			ax3.text(
				0, info_pos-2, 
				'Win %: {0} | Loss %: {1}'.format(
					results[plan][Constants.WIN_PERC],
					results[plan][Constants.LOSS_PERC]
				), 
				fontsize=10, horizontalalignment='left'
			)
			ax3.text(
				0, info_pos-1, 
				'Gain: {0} | Loss: {1}'.format(
					results[plan][Constants.GAIN],
					results[plan][Constants.LOSS]
				), 
				fontsize=10, horizontalalignment='left'
			)
			ax3.text(
				0, info_pos, 
				'GPR: {0}'.format(results[plan][Constants.GPR]), 
				fontsize=10, horizontalalignment='left'
			)

			count += 1

		# Daily Equity Return Aggregate
		data = sorted(pos_aggregate.items(), key=lambda kv: kv[0])
		dates = [i[0] for i in data]
		pos_equity_ret = [i[1] for i in data]

		agg_ret = round(sum(pos_equity_ret), 2)
		agg_dd = round(self.getDD(pos_equity_ret), 2)

		c_ret = pos_equity_ret[0]
		ret_plot = [c_ret]
		for i in range(1, len(pos_equity_ret)):
			ret_plot.append(pos_equity_ret[i] + ret_plot[-1])

		color = colors[count+1]
		ax1.plot(dates, ret_plot, color=color, alpha=0.5)
		ax1.xaxis_date()

		info_pos = len(results)*11
		ax3.text(
			0, info_pos+1, 
			'Aggregate Result:', 
			fontsize=11, horizontalalignment='left',
			fontweight='bold'
		)
		ax3.text(
			0, info_pos+2, 
			'% Ret: {0} | % DD: {1}'.format(
				agg_ret,
				agg_dd
			), 
			fontsize=10, horizontalalignment='left'
		)

		date_format = mpl_dates.DateFormatter('%b %d \'%y')

		ax1.set_title('Daily Equity')
		ax1.set_xlabel('Date')
		ax1.set_ylabel('Percentage')
		ax1.legend(list(results.keys())+['Aggregate'])
		ax1.xaxis.set_major_formatter(date_format)

		ax2.set_title('Position Return')
		ax2.set_xlabel('Date')
		ax2.set_ylabel('Percentage')
		ax2.legend(results.keys())
		ax2.xaxis.set_major_formatter(date_format)

		ax3.set_ylim(max((count)*11, 2*11),0)

		plt.gcf().autofmt_xdate()
		plt.tight_layout()
		plt.show()

	def getDD(self, pos_ret):
		perc_ret = 0
		max_ret = 0
		perc_dd = 0

		for perc in pos_ret:
			perc_ret += perc

			if perc_ret > max_ret:
				max_ret = perc_ret
			else:
				dd = max_ret - perc_ret
				perc_dd = dd if dd > perc_dd else perc_dd

		return perc_dd

	def showCharts(self, results, formatting):

		for plan in results:
			ax1 = plt.subplot2grid((4 + len(results[plan]['studies']),1), (0,0), rowspan=4)

			candlestick_ohlc(ax1, 
				results[plan]['quotes'],
				colorup='g',
				colordown='r',
				width=0.1
			)

			dates = [i[0] for i in results[plan]['quotes']]
			date_format = mpl_dates.DateFormatter('%d/%m/%y %H:%M')

			for i in range(len(results[plan]['overlays'])):
				if 'colors' in formatting[plan]:
					colors = formatting[plan]['colors']
				else:
					colors = ['b', 'g', 'r', 'c', 'm', 'y']

				if 'styles' in formatting[plan]:
					styles = formatting[plan]['styles']
				else:
					styles = None

				if 'studies' in formatting[plan]:
					studies = formatting[plan]['studies']
				else:
					studies = None

				if 'pos_data' in formatting[plan]:
					pos_data = formatting[plan]['pos_data']
				else:
					pos_data = None

				overlay = results[plan]['overlays'][i]
				if len(overlay) > 0:
					if type(overlay[0]) == np.ndarray:
						for j in range(overlay[0].size):
							data = []
							for dp in overlay:
								data.append(dp[j])

							style = styles[(i % len(styles))] if styles else None

							ax1.plot(dates, data, linestyle=style, color= colors[(i % len(colors))], alpha=0.7, linewidth=0.75)
					else:
						style = styles[(i % len(styles))] if styles else None
						ax1.plot(dates, overlay, linestyle=style, color= colors[(i % len(colors))], alpha=0.7, linewidth=0.75)

			for i in range(len(results[plan]['studies'])):
				ax = plt.subplot2grid((4 + len(results[plan]['studies']),1), (4 + i,0), sharex=ax1)
				study = results[plan]['studies'][i]

				s_type = None
				if studies:
					s_type = studies[i][0]

				if len(study) > 0:
					if type(study[0]) == np.ndarray:
						for j in range(study[0].size):
							data = []
							for dp in study:
								data.append(dp[j])

							if s_type == 'MACD':
								if j == 2:
									for z in studies[i][1:]:
										y = np.ones(len(dates)) * z
										ax.plot(dates, y, color='black', alpha=0.5, linewidth=0.75)
									ax.bar(dates, data, alpha=0.8, width=0.1)
							else:
								ax.plot(dates, data, alpha=0.8, linewidth=0.75)
					else:
						if s_type == 'RSI':
							for z in studies[i][1:]:
								y = np.ones(len(dates)) * z
								ax.plot(dates, y, color='black', alpha=0.5, linewidth=0.75)
							ax.plot(dates, study, alpha=0.8, linewidth=1)
						else:
							ax.plot(dates, study, alpha=0.8, linewidth=1)
				
				ax.xaxis_date()
				ax.xaxis.set_major_formatter(date_format)
				ax.autoscale(tight=True)

			for i in results[plan]['positions']:
				d = results[plan]['positions'][i][0]
				ep = results[plan]['positions'][i][1]

				if d == Constants.BUY:
					ax1.arrow(i, ep + 0.002, 0, 0.005, color='blue', length_includes_head=True, head_width=0.075, head_length=0.002)
					annotation = []
					if pos_data:
						for j in pos_data:
							annotation.append(str(results[plan]['positions'][i][2][j]))

					ax1.annotate(', '.join(annotation), xy=(i + 0.003, ep + 0.003))

				elif d == Constants.SELL:
					ax1.arrow(i, ep - 0.002, 0, -0.005, color='orange', length_includes_head=True, head_width=0.075, head_length=0.002)
					annotation = []
					if pos_data:
						for j in pos_data:
							annotation.append(str(results[plan]['positions'][i][2][j]))
					
					ax1.annotate(', '.join(annotation), xy=(i + 0.003, ep - 0.003))

			ax1.xaxis_date()
			ax1.xaxis.set_major_formatter(date_format)
			ax1.autoscale(tight=True)

			plt.gcf().autofmt_xdate()
			plt.show()

	def findAccount(self, accountid):
		for acc in self.accounts:
			if acc.accountid == accountid:
				return accountid
		return None
		
	def addToQueue(self, item):
		self.cmd_queue.append(item)
