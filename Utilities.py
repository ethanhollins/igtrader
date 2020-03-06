import Constants
import datetime, pytz

class Utilities(object):

	def convertTimezone(self, dt, tz):
		return dt.astimezone(pytz.timezone(tz))

	def convertToMelbourneTimezone(self, dt):
		dst_start = self.findFirstWeekday(
			datetime.datetime(year=dt.year, month=10, day=1, hour=16),
			6
		)
		dst_end = self.findFirstWeekday(
			datetime.datetime(year=dt.year, month=4, day=1, hour=16),
			6
		)
		if dst_end <= dt < dst_start:
			return dt + datetime.timedelta(hours=10)
		else:
			return dt + datetime.timedelta(hours=11)

	def convertToLondonTimezone(self, dt):
		dst_start = self.findFirstWeekday(
			datetime.datetime(year=dt.year, month=3, day=31, hour=1),
			6,
			reverse=True
		)
		dst_end = self.findFirstWeekday(
			datetime.datetime(year=dt.year, month=10, day=31, hour=1),
			6,
			reverse=True
		)
		if dst_start <= dt < dst_end:
			return dt + datetime.timedelta(hours=1)
		else:
			return dt

	def findFirstWeekday(self, dt, weekday, reverse=False):
		while dt.weekday() != weekday:
			if reverse:
				dt -= datetime.timedelta(days=1)
			else:
				dt += datetime.timedelta(days=1)
		return dt

	def setTimezone(self, dt, tz):
		return pytz.timezone(tz).localize(dt)

	def convertSnapshotToTimestamp(self, snapshot):
		s_dt = datetime.datetime.strptime(snapshot, '%Y/%m/%d %H:%M:%S')
		return int((s_dt - Constants.DT_START_DATE).total_seconds())

	def convertSnapshotToDatetime(self, snapshot):
		return datetime.datetime.strptime(snapshot, '%Y/%m/%d %H:%M:%S')

	def convertUTCSnapshotToTimestamp(self, snapshot):
		time = datetime.datetime.strptime(snapshot.split('.')[0], '%Y-%m-%dT%H:%M:%S')
		time = self.setTimezone(time, 'UTC')
		time = self.convertTimezone(time, 'Australia/Melbourne').replace(tzinfo=None)
		# s_dt = self.convertToMelbourneTimezone(s_dt)
		return int((time - Constants.DT_START_DATE).total_seconds())

	def convertUTCTimeToTimestamp(self, time):
		time = self.setTimezone(time, 'UTC')
		time = self.convertTimezone(time, 'Australia/Melbourne').replace(tzinfo=None)
		# time = self.convertToMelbourneTimezone(time)
		return int((time - Constants.DT_START_DATE).total_seconds())

	def convertLondonTimeToTimestamp(self, time):
		time = self.setTimezone(time, 'Europe/London')
		time = self.convertTimezone(time, 'Australia/Melbourne').replace(tzinfo=None)
		return int((time - Constants.DT_START_DATE).total_seconds())

	def convertTimestampToDatetime(self, ts):
		return Constants.DT_START_DATE + datetime.timedelta(seconds=int(ts))
		
	def convertDatetimeToTimestamp(self, dt):
		return int((dt - Constants.DT_START_DATE).total_seconds())

	def convertToPips(self, price):
		return round(price * 10000, 1)

	def convertToPrice(self, pips):
		return round(pips / 10000, 5)