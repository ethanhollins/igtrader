import Constants
import datetime, pytz

class Utilities(object):

	def convertTimezone(self, dt, tz):
		return dt.astimezone(pytz.timezone(tz))

	def setTimezone(self, dt, tz):
		return pytz.timezone(tz).localize(dt)

	def convertSnapshotToTimestamp(self, snapshot):
		s_dt = datetime.datetime.strptime(snapshot, '%Y/%m/%d %H:%M:%S')
		return int((s_dt - Constants.DT_START_DATE).total_seconds())

	def convertSnapshotToDatetime(self, snapshot):
		return datetime.datetime.strptime(snapshot, '%Y/%m/%d %H:%M:%S')

	def convertUTCSnapshotToTimestamp(self, snapshot):
		print('1')
		s_dt = datetime.datetime.strptime(snapshot.split('.')[0], '%Y-%m-%dT%H:%M:%S')
		print('2')
		s_dt = pytz.utc.localize(s_dt)
		print('3')
		s_dt = self.convertTimezone(s_dt, 'Australia/Melbourne')
		print('4')
		s_dt = s_dt.replace(tzinfo=None)
		print('5')
		return int((s_dt - Constants.DT_START_DATE).total_seconds())

	def convertTimestampToDatetime(self, ts):
		return Constants.DT_START_DATE + datetime.timedelta(seconds=int(ts))
		
	def convertDatetimeToTimestamp(self, dt):
		return int((dt - Constants.DT_START_DATE).total_seconds())

	def convertMTDatetimeToTimestamp(self, dt):
		return int((dt - Constants.MT_DT_START_DATE).total_seconds())

	def convertToPips(self, price):
		return round(price * 10000, 1)

	def convertToPrice(self, pips):
		return round(pips / 10000, 5)