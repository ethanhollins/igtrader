import Constants
import numpy as np
import datetime

VARIABLES = {
	'PRODUCT': Constants.GBPUSD
}

def init(utilities):
	''' Initialize utilities and indicators '''
	global utils, h4_chart, d_chart, sma_20, sma_50, isLong, rsi
	utils = utilities

	# d_chart = utils.getChart(VARIABLES['PRODUCT'], Constants.DAILY)
	d_chart = utils.getChart(VARIABLES['PRODUCT'], Constants.ONE_MINUTE)
	# h4_chart = utils.getChart(VARIABLES['PRODUCT'], Constants.FOUR_HOURS)
	rsi = utils.RSI(10)
	sma_20 = utils.SMA(20)
	sma_50 = utils.SMA(50)
	isLong = None


	global info
	info = {}
	for i in range(0,24,4): 
		info[i] = {}
		info[i]['isLong'] = False
		info[i]['close'] = 0
		info[i]['open'] = 0
		# for j in range(0,24,4):
		# 	if i != j:
		# 		info[i][j] = {}

	global all_times, last_time
	all_times = []
	last_time = None

def setup(utilities):
	return

def onNewBar(chart):
	global last_time, isLong

	# if chart.period == Constants.DAILY:
	# 	time = utils.convertTimestampToDatetime(utils.getLatestTimestamp())
	# 	london_time = utils.convertTimezone(time, 'Europe/London')
	# 	ohlc = d_chart.getCurrentBidOHLC(utils)
	# 	print('d: {} - {}'.format(ohlc, london_time.strftime('%Y-%m-%d %H:%M:%S')))

	if chart.period == Constants.FOUR_HOURS:
		time = utils.convertTimestampToDatetime(utils.getLatestTimestamp())
		london_time = utils.convertTimezone(time, 'Europe/London')
		_open, high, low, close = h4_chart.getCurrentBidOHLC(utils)
		sma_20_val = sma_20.getCurrent(utils, d_chart)
		sma_50_val = sma_50.getCurrent(utils, d_chart)
		rsi_val = rsi.getCurrent(utils, d_chart)

		# ohlc_h4 = h4_chart.getCurrentBidOHLC(utils)
		# ohlc_d = d_chart.getCurrentBidOHLC(utils)
		# print('d: {} - h4 ({}): {} - {}'.format(ohlc_d, london_time.hour, ohlc_h4, london_time.strftime('%Y-%m-%d %H:%M:%S')))
		# if last_time and london_time != last_time + datetime.timedelta(hours=4):
		# 	for i in info:
		# 		info[i]['close'] = 0

		pl = calculatePivotLines()
		hour = london_time.hour

		time_str = london_time.strftime('%Y-%m-%d %H:%M:%S')

		if rsi_val >= 70:
			isLong = True
		if rsi_val <= 30:
			isLong = False

		info[hour]['isLong'] = isLong
		info[hour]['open'] = _open
		info[hour]['close'] = close
		info[hour]['time'] = time_str
		
		info[hour][time_str] = {}

		all_times.append(time_str)

		for i in range(0,24,4):
			if i != hour:
				if info[i]['close'] != 0 and isLong:
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

					long_max = -999
					for x in info[i][info[i]['time']]:
						dist = info[i][info[i]['time']][x][3]
						long_max = max(long_max, dist)

					long_max = max(long_max, utils.convertToPips(high - info[i]['close']))

					short_max = -999
					for x in info[i][info[i]['time']]:
						dist = info[i][info[i]['time']][x][4]
						short_max = max(short_max, dist)

					short_max = max(short_max, utils.convertToPips(info[i]['close'] - low))


					if info[i]['isLong']:
						pos_result = pip_result
					else:
						pos_result = pip_result * -1

					info[i][info[i]['time']][hour] = (
						pos_result, max_dist, max_dd, 
						utils.convertToPips(high - info[i]['close']),
						utils.convertToPips(info[i]['close'] - low),
						long_max, short_max, info[i]['isLong']
					)

		last_time = london_time

def onLoop():
	''' Function called on every program iteration '''
	return

def onEnd():
	print('{}\n'.format(VARIABLES['PRODUCT']))
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
				long_list = [x[5] for x in processed[i][j]]
				short_list = [x[6] for x in processed[i][j]]
				dir_list = [x[7] for x in processed[i][j]]

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
					long_result = long_list[x]
					short_result = short_list[x]
					dir_result = dir_list[x]

					if dir_result:
						if long_result > result[i][j]['dd_median']:
							result[i][j]['estimate'] -= result[i][j]['dd_median']
						elif short_result > result[i][j]['max_median']:
							result[i][j]['estimate'] += result[i][j]['max_median']		
						else:
							result[i][j]['estimate'] += close_result*-1
					else:
						if short_result > result[i][j]['dd_median']:
							result[i][j]['estimate'] -= result[i][j]['dd_median']
						elif long_result > result[i][j]['max_median']:
							result[i][j]['estimate'] += result[i][j]['max_median']	
						else:
							result[i][j]['estimate'] += close_result*-1

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