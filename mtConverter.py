import os
import json
import datetime
import pytz

MT_PATH = 'C:\\Users\\Ethan\\AppData\\Roaming\\MetaQuotes\\Terminal\\D0E8209F77C8CF37AD8BF550E51FF075\\MQL5\\Files\\ohlc\\'
DATA_PATH = 'Data/'
START_DT = datetime.datetime(year=1970, month=1, day=1)

LONDON_FOUR_BARS = [0, 4, 8, 12, 16, 20]

'''
Periods
'''
MT_ONE_HOUR = 16385

FOUR_HOURS = 4

'''
Products
'''
MT_GBPUSD = "GBPUSD"

GBPUSD = "CS.D.GBPUSD.MINI.IP"

def convertTimezone(dt, tz):
	return dt.astimezone(pytz.timezone(tz))

def setTimezone(dt, tz):
	return pytz.timezone(tz).localize(dt)

def convertTimestampToDatetime(ts):
	return START_DT + datetime.timedelta(seconds=int(ts))
	
def convertDatetimeToTimestamp(dt):
	return int((dt - START_DT).total_seconds())

def getMTDatetime(ts):
	dt = START_DT + datetime.timedelta(seconds=int(ts))
	if pytz.timezone('America/New_York').dst(dt).seconds:
		return dt.replace(tzinfo=datetime.timezone(datetime.timedelta(seconds=2*60*60)))
	else:
		return dt.replace(tzinfo=datetime.timezone(datetime.timedelta(seconds=1*60*60)))

def stitchData(product, period, data):
	print('Stitching data...')
	new_data = {}
	stitch = []
	aus_ts = None
	if period == FOUR_HOURS:
		ts_l = [i[0] for i in sorted(data.items(), key=lambda kv: kv[0])]
		for ts in ts_l:
			mt_dt = getMTDatetime(int(ts))
			aus_dt = convertTimezone(mt_dt, 'Australia/Melbourne')
			lon_dt = convertTimezone(aus_dt, 'Europe/London')
			aus_dt = aus_dt.replace(tzinfo=None)

			if lon_dt.hour in LONDON_FOUR_BARS:
				if aus_ts:
					stitch.append(data[ts])
					new_ohlc = [0,0,0,0]
					for i in range(len(stitch)):
						ohlc = stitch[i]
						if i == 0:
							new_ohlc[0] = ohlc[0]
							new_ohlc[1] = ohlc[1]
							new_ohlc[2] = ohlc[2]
							new_ohlc[3] = ohlc[3]
						else:
							if ohlc[1] > new_ohlc[1]:
								new_ohlc[1] = ohlc[1]

							if ohlc[2] < new_ohlc[2]:
								new_ohlc[2] = ohlc[2]

							new_ohlc[3] = ohlc[3]

					new_data[aus_ts] = new_ohlc
				
				aus_ts = convertDatetimeToTimestamp(aus_dt)
				stitch = []
			else:
				if aus_ts:
					stitch.append(data[ts])

		if product == MT_GBPUSD:
			product = GBPUSD

	return new_data

def reformatData(f_name, product, period):
	mt_path = '{0}{1}.json'.format(MT_PATH, f_name)
	if os.path.exists(mt_path):
		with open(mt_path, 'r') as f:
			s = f.read()
			for i in range(len(s)):
				if s[i] == '{':
					s = s[i:]
					break

			s = s.replace(chr(0), '')
			data = json.loads(s)
			data = stitchData(product, period, data)

			with open('{0}MT_{1}_{2}.json'.format(DATA_PATH, GBPUSD, FOUR_HOURS), 'w') as f:
				f.write(json.dumps(data, indent=4))
			print("DONE.")
	else:
		print('{0} does not exist.'.format(f_name))


if __name__ == '__main__':
	product = input('Product: ')
	period = int(input('Period: '))

	if period == FOUR_HOURS:
		f_name = '{0}_{1}'.format(product, MT_ONE_HOUR)
		

	reformatData(f_name, product, period)
