import Constants
import datetime, pytz

class Utilities(object):

	def convertTimezone(self, dt, tz):
		return dt.astimezone(pytz.timezone(tz))

	def convertToMelbourneTimezone(self, dt):
		dst_start = datetime.datetime(year=dt.year, month=10, day=5, hour=16)
		dst_end = datetime.datetime(year=dt.year, month=4, day=6, hour=16)
		if dst_end <= dt < dst_start:
			return dt + datetime.timedelta(hours=10)
		else:
			return dt + datetime.timedelta(hours=11)

	def setTimezone(self, dt, tz):
		return pytz.timezone(tz).localize(dt)

	def convertSnapshotToTimestamp(self, snapshot):
		s_dt = datetime.datetime.strptime(snapshot, '%Y/%m/%d %H:%M:%S')
		return int((s_dt - Constants.DT_START_DATE).total_seconds())

	def convertSnapshotToDatetime(self, snapshot):
		return datetime.datetime.strptime(snapshot, '%Y/%m/%d %H:%M:%S')

	def convertUTCSnapshotToTimestamp(self, snapshot):
		s_dt = datetime.datetime.strptime(snapshot.split('.')[0], '%Y-%m-%dT%H:%M:%S')
		s_dt = self.convertToMelbourneTimezone(s_dt)
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