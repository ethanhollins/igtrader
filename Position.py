import Constants

class Position(object):

	def __init__(self, account, orderid, product, direction):
		self.account = account
		self.utils = self.account.root.manager.utils
		self.orderid = orderid
		self.product = product
		self.direction = direction

		self.plan = None

		self.opentime = None
		self.closetime = None

		self.lotsize = 0

		self.entryprice = 0
		self.closeprice = 0
		self.sl = 0
		self.tp = 0

		self.risk = 0

		self.is_dummy = False

		self.data = {}

	def __iter__(self):
		for key in self.__dict__:
			if key != 'account' or key != 'utils':
				yield (key, self.__dict__[key])

	def copy(self):
		pos = Position(
			self.account, 
			self.orderid, self.product, 
			self.direction, self.ordertype
		)
		for key in dict(self):
			pos.__dict__[key] = dict(self)[key]
		return pos

	def setDict(self, pos):
		for key in pos:
			self.__dict__[key] = pos[key]

	def stopAndReverse(self, 
		lotsize, 
		slPrice=None, slRange=None, 
		tpPrice=None, tpRange=None
	):
		self.close()

		if self.direction == Constants.BUY:
			pos = self.plan.sell(
				self.product, lotsize, 
				slPrice=slPrice, slRange=slRange,
				tpPrice=tpPrice, tpRange=tpRange
			)
		else:
			pos = self.plan.buy(
				self.product, lotsize, 
				slPrice=slPrice, slRange=slRange,
				tpPrice=tpPrice, tpRange=tpRange
			)

		return pos

	def modify(self, sl=None, tp=None):
		if self.is_dummy:
			self.sl = sl
			self.tp = tp
			return True

		result = self.account.root.manager.modifyPosition(self.account.accountid, self.orderid, sl, tp)
		return result != None

	def modifySL(self, sl):
		if self.is_dummy:
			self.sl = sl
			return True

		result = self.account.root.manager.modifyPosition(self.account.accountid, self.orderid, sl, self.tp)
		return result != None

	def removeSL(self):
		if self.is_dummy:
			self.sl = 0
			return True

		result = self.account.root.manager.modifyPosition(self.account.accountid, self.orderid, None, self.tp)
		return result != None

	def modifyTP(self, tp):
		if self.is_dummy:
			self.tp = tp
			return True

		result = self.account.root.manager.modifyPosition(self.account.accountid, self.orderid, self.sl, tp)
		return result != None

	def removeTP(self):
		if self.is_dummy:
			self.tp = 0
			return True

		result = self.account.root.manager.modifyPosition(self.account.accountid, self.orderid, self.sl, None)
		return result != None

	def breakeven(self):
		min_price = 0.00040
		if self.direction == Constants.BUY:
			if self.plan.getBid(self.product) > self.entryprice + min_price:
				if self.is_dummy:
					self.sl = self.entryprice
					return True
				else:
					result = self.account.root.manager.modifyPosition(self.account.accountid, self.orderid, self.entryprice, self.tp)
					return result != None
			elif self.plan.getBid(self.product) < self.entryprice - min_price:
				if self.is_dummy:
					self.tp = self.entryprice
					return True
				else:
					result = self.account.root.manager.modifyPosition(self.account.accountid, self.orderid, self.sl, self.entryprice)
					return result != None
			else:
				print('Error: Breakeven must be atleast 4 pips from entry.')
				return False

		else:
			if self.plan.getAsk(self.product) < self.entryprice - min_price:
				if self.is_dummy:
					self.sl = self.entryprice
					return True
				else:
					result = self.account.root.manager.modifyPosition(self.account.accountid, self.orderid, self.entryprice, self.tp)
					return result != None
			elif self.plan.getAsk(self.product) > self.entryprice + min_price:
				if self.is_dummy:
					self.tp = self.entryprice
					return True
				else:
					result = self.account.root.manager.modifyPosition(self.account.accountid, self.orderid, self.sl, self.entryprice)
					return result != None
			else:
				print('Error: Breakeven must be atleast 4 pips from entry.')
				return False

	def close(self):
		if self.is_dummy:
			del self.plan.positions[self.plan.positions.index(self)]
			self.plan.savePositions()
			return True
		else:
			result = self.account.root.manager.closePosition(self.account.accountid, self)
			return result != None

	def isBreakeven(self):
		return self.sl == self.entryprice or self.tp == self.entryprice

	def calculateSLPoints(self, price):
		if self.is_dummy and not self.entryprice:
			return 0

		if self.direction == Constants.BUY:
			points = self.entryprice - price
		else:
			points = price - self.entryprice
		
		return self.utils.convertToPips(points)

	def calculateSLPrice(self, points):
		if self.is_dummy and not self.entryprice:
			return 0

		price = self.utils.convertToPrice(points)
		if self.direction == Constants.BUY:
			return round(self.entryprice - price, 5)
		else:
			return round(self.entryprice + price, 5)

	def isSLPoints(self, points):
		if self.is_dummy and not self.entryprice:
			return 0

		sl_price = self.utils.convertToPrice(points)

		if self.direction == Constants.BUY:
			check_sl = round(self.entryprice - sl_price, 5)
		else:
			check_sl = round(self.entryprice + sl_price, 5)
			
		return self.sl == check_sl

	def isSLPrice(self, price):
		return self.sl == price

	def calculateTPPoints(self, price):
		if self.is_dummy and not self.entryprice:
			return 0

		if self.direction == Constants.BUY:
			points = round(price - self.entryprice, 5)
		else:
			points = round(self.entryprice - price, 5)
		
		return self.utils.convertToPips(points)

	def calculateTPPrice(self, points):
		if self.is_dummy and not self.entryprice:
			return 0

		price = self.utils.convertToPrice(points)
		if self.direction == Constants.BUY:
			return round(self.entryprice + price, 5)
		else:
			return round(self.entryprice - price, 5)

	def isTPPoints(self, points):
		if self.is_dummy and not self.entryprice:
			return True

		tp_price = self.utils.convertToPrice(points)

		if self.direction == Constants.BUY:
			check_tp = round(self.entryprice + tp_price, 5)
		else:
			check_tp = round(self.entryprice - tp_price, 5)
			
		return self.tp == check_tp

	def isTPPrice(self, price):
		return self.tp == price

	def getPipProfit(self):
		if self.is_dummy:
			return 0

		if not self.closeprice:
			if self.direction == Constants.BUY:
				profit = self.plan.getBid(self.product) - self.entryprice
			else:
				profit = self.entryprice - self.plan.getAsk(self.product)
		else:
			if self.direction == Constants.BUY:
				profit = self.closeprice - self.entryprice
			else:
				profit = self.entryprice - self.closeprice
		
		return self.utils.convertToPips(profit)

	def getPercentageProfit(self):
		if self.is_dummy:
			return 0

		if not self.closeprice:
			if self.direction == Constants.BUY:
				profit = self.plan.getBid(self.product) - self.entryprice
			else:
				profit = self.entryprice - self.plan.getAsk(self.product)
		else:
			if self.direction == Constants.BUY:
				profit = self.closeprice - self.entryprice
			else:
				profit = self.entryprice - self.closeprice
			
		profit = self.utils.convertToPips(profit)

		variables = self.plan.module.VARIABLES
		risk = variables['risk'] if 'risk' in variables else None
		stoprange = variables['stoprange'] if 'stoprange' in variables else None
		
		if stoprange and risk:
			profit = profit / stoprange * risk
		else:
			profit = 0

		return round(profit, 2)
