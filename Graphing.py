import matplotlib.pyplot as plt
from matplotlib import dates as mpl_dates
import Constants
import os

class Graphing(object):

	def plotBacktestResults(self):
		return

	def plotBatchResults(self, results):
		plt.style.use('seaborn')
		fig1, axs = plt.subplots(1, 2, sharex=True)

		for plan in results:
			batch_data_list = results[plan]

			for batch in batch_data_list:

				""" Daily """

				# Percentage Drawdown
				data = sorted(batch[Constants.DAILY_PERC_DD].items(), key=lambda kv: kv[0])
				dates = [i[0] for i in data]
				y_ax = range(0, len(dates))
				perc_dd = [i[1] for i in data]

				# Percentage Return
				data = sorted(batch[Constants.DAILY_PERC_RET].items(), key=lambda kv: kv[0])
				perc_ret = [i[1] for i in data]

				ax = axs[0]
				ax.plot(dates, perc_ret, alpha=0.8)
				ax.bar(dates, perc_dd, alpha=0.3)

				ax.set_ylabel('Percentage %')
				ax.set_xlabel('Daily')
				ax.xaxis_date()

				""" Position """

				# Percentage Drawdown
				data = sorted(batch[Constants.POS_EQUITY_DD].items(), key=lambda kv: kv[0])
				dates = [i[0] for i in data]
				y_ax = range(0, len(dates))
				perc_dd = [i[1] for i in data]

				# Percentage Return
				data = sorted(batch[Constants.POS_EQUITY_RET].items(), key=lambda kv: kv[0])
				perc_ret = [i[1] for i in data]

				ax = axs[1]
				ax.plot(dates, perc_ret, alpha=0.8)
				ax.bar(dates, perc_dd, alpha=0.3)
				ax.set_xlabel('Position')
				ax.xaxis_date()

				print('\n--------------\n{0}:\n'.format(plan))
				print(' Trading DAYS: {}'.format(
					batch[Constants.DAILY_WINS] + batch[Constants.DAILY_LOSSES]
				))
				print('% Ret        : {0}\t| % DD        : {1}'.format(
					batch[Constants.POS_PERC_RET],
					batch[Constants.POS_PERC_DD]
				))
				print('CMP % Ret    : {0}\t| CMP % DD    : {1}'.format(
					batch[Constants.POS_COMPOUND_RET],
					batch[Constants.POS_COMPOUND_DD]
				))
				print('(D) CMP % Ret: {0}\t| (D) CMP % DD: {1}'.format(
					batch[Constants.DAY_COMPOUND_RET],
					batch[Constants.DAY_COMPOUND_DD]
				))
				print('PIP Ret      : {0}\t|'.format(
					batch[Constants.POS_PIP_RET]
				))
				print('Wins         : {0}\t| Losses      : {1}'.format(
					batch[Constants.WINS],
					batch[Constants.LOSSES]
				))
				print('Daily Wins   : {0}\t| Daily Losses: {1}'.format(
					batch[Constants.DAILY_WINS],
					batch[Constants.DAILY_LOSSES]
				))
				print('Win %        : {0}\t| Loss %      : {1}'.format(
					batch[Constants.WIN_PERC],
					batch[Constants.LOSS_PERC]
				))
				print('Gain         : {0}\t| Loss        : {1}'.format(
					batch[Constants.GAIN],
					batch[Constants.LOSS]
				))
				print('GPR          : {0}\t|'.format(batch[Constants.GPR]))

		date_format = mpl_dates.DateFormatter('%b %d \'%y')
		axs[0].xaxis.set_major_formatter(date_format)
		axs[1].xaxis.set_major_formatter(date_format)
		axs[0].legend(results.keys())
		axs[1].legend(results.keys())

		plt.gcf().autofmt_xdate()
		plt.tight_layout()
		plt.show()
