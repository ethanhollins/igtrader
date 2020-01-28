import Constants
import numpy as np
import datetime

VARIABLES = {
	
}

def init(utilities):
	''' Initialize utilities and indicators '''
	global utils, h4_chart, d_chart
	utils = utilities

	d_chart = utils.getChart(Constants.GBPUSD, Constants.DAILY)
	h4_chart = utils.getChart(Constants.GBPUSD, Constants.FOUR_HOURS)

	global info
	info = {}
	for i in range(0,24,4): 
		info[i] = {}
		info[i]['isLong'] = False
		info[i]['close'] = 0
		# for j in range(0,24,4):
		# 	if i != j:
		# 		info[i][j] = {}

	global all_times, last_time
	all_times = []
	last_time = None

def setup(utilities):
	return

def onNewBar(chart):
	global last_time
	# if chart.period == Constants.DAILY:
	# 	time = utils.convertTimestampToDatetime(utils.getLatestTimestamp())
	# 	ohlc = d_chart.getCurrentBidOHLC(utils)
	# 	print('d: {}'.format(ohlc))

	if chart.period == Constants.FOUR_HOURS:
		time = utils.convertTimestampToDatetime(utils.getLatestTimestamp())
		london_time = utils.convertTimezone(time, 'Europe/London')
		_open, high, low, close = h4_chart.getCurrentBidOHLC(utils)

		# if last_time and london_time != last_time + datetime.timedelta(hours=4):
		# 	for i in info:
		# 		info[i]['close'] = 0

		pl = calculatePivotLines()
		hour = london_time.hour

		time_str = london_time.strftime('%Y-%m-%d %H:%M:%S')
		info[hour]['isLong'] = close > pl[0]
		info[hour]['close'] = close
		info[hour]['time'] = time_str
		
		info[hour][time_str] = {}

		all_times.append(time_str)

		for i in range(0,24,4):
			if i != hour:
				if info[i]['close'] != 0:
					# if (london_time.replace(tzinfo=None) - datetime.datetime.strptime(info[i]['time'], '%Y-%m-%d %H:%M:%S')) <= datetime.timedelta(hours=24):

					pip_result = utils.convertToPips(close - info[i]['close'])

					max_dist = -999
					if pip_result < 0:
						for x in info[i][info[i]['time']]:
							dist = info[i][info[i]['time']][x][4]
							max_dist = max(max_dist, dist)

						max_dist = max(max_dist, utils.convertToPips(info[i]['close'] - low))
					else:
						for x in info[i][info[i]['time']]:
							dist = info[i][info[i]['time']][x][3]
							max_dist = max(max_dist, dist)

						max_dist = max(max_dist, utils.convertToPips(high - info[i]['close']))

					max_dd = -999
					if pip_result < 0:
						for x in info[i][info[i]['time']]:
							dist = info[i][info[i]['time']][x][3]
							max_dd = max(max_dd, dist)

						max_dd = max(max_dd, utils.convertToPips(high - info[i]['close']))
					else:
						for x in info[i][info[i]['time']]:
							dist = info[i][info[i]['time']][x][4]
							max_dd = max(max_dd, dist)

						max_dd = max(max_dd, utils.convertToPips(info[i]['close'] - low))

					if not info[i]['isLong']:
						pip_result *= -1

					info[i][info[i]['time']][hour] = (
						pip_result, max_dist, max_dd, 
						utils.convertToPips(high - info[i]['close']),
						utils.convertToPips(info[i]['close'] - low)
					)

		last_time = london_time

def onLoop():
	''' Function called on every program iteration '''
	return

def onEnd():
	# print(all_times)
	# print('end.')
	processed = {}
	for i in range(0,24,4):
		processed[i] = {}
		for x in range(0,24,4):
			if i != x: processed[i][x] = []

		for t in all_times:
			if t in info[i]:
				for j in range(0,24,4):
					if i != j:
						if j in info[i][t]:
							processed[i][j].append(info[i][t][j])

	result = {}
	for i in range(0,24,4):
		result[i] = {}
		for j in range(0,24,4):
			if i != j:
				result[i][j] = {}

				close_list = [x[0] for x in processed[i][j]]
				max_list = [x[1] for x in processed[i][j]]
				dd_list = [x[2] for x in processed[i][j]]

				result[i][j]['mean'] = round(sum(close_list) / len(close_list), 2)
				mp = int(len(close_list)/2)
				s_info = sorted(close_list)
				result[i][j]['median'] = round((
					(s_info[mp-1] + s_info[mp])/2
					if len(s_info) % 2 == 0 else
					s_info[mp]
				), 2)

				result[i][j]['max_mean'] = round(sum(max_list) / len(max_list), 2)
				mp = int(len(max_list)/2)
				s_info = sorted(max_list)
				result[i][j]['max_median'] = round((
					(s_info[mp-1] + s_info[mp])/2
					if len(s_info) % 2 == 0 else
					s_info[mp]
				), 2)

				result[i][j]['dd_mean'] = round(sum(dd_list) / len(dd_list), 2)
				mp = int(len(dd_list)/2)
				s_info = sorted(dd_list)
				result[i][j]['dd_median'] = round((
					(s_info[mp-1] + s_info[mp])/2
					if len(s_info) % 2 == 0 else
					s_info[mp]
				), 2)

				result[i][j]['pos'] = len([x for x in close_list if x >= 0])
				result[i][j]['neg'] = len([x for x in close_list if x < 0])

				result[i][j]['estimate'] = 0
				for x in range(len(close_list)):
					close_result = close_list[x]
					dd_result = dd_list[x]
					if dd_result > result[i][j]['dd_median']*2:
						result[i][j]['estimate'] -= result[i][j]['dd_median']*2
					elif close_result*-1 > result[i][j]['max_median']:
						result[i][j]['estimate'] += result[i][j]['max_median']
	
	for i in result:
		print('{}:'.format(i))
		for j in result[i]:
			print(
				'\t{}:\n\tMean: {}\n\tMedian: {}' \
				'\n\tMax Mean: {}\n\tMax Median: {}' \
				'\n\tDD Mean: {}\n\tDD Median: {}' \
				'\n\tPos: {}\n\tNeg: {}\n\tEstimate: {:.2f}\n'
				.format(
					j, result[i][j]['mean'], result[i][j]['median'],
					result[i][j]['max_mean'], result[i][j]['max_median'],
					result[i][j]['dd_mean'], result[i][j]['dd_median'],
					result[i][j]['pos'], result[i][j]['neg'],
					result[i][j]['estimate']
				)
			)



def calculatePivotLines():
	_open, high, low, close = d_chart.getCurrentBidOHLC(utils)

	cp = round((high + low + close) / 3, 5)
	r1 = round(cp*2 - low, 5)
	s1 = round(cp*2 - high, 5)
	r2 = round(cp + (high - low), 5)
	s2 = round(cp - (high - low), 5)
	r3 = round(high + 2*(cp-low), 5)
	s3 = round(low - 2*(high-cp), 5)

	return cp, r1, r2, r3, s1, s2, s3