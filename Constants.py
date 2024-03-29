'''
Products
'''
GBPUSD = 'GBP_USD'
EURUSD = 'EUR_USD'
EURJPY = 'EUR_JPY'
AUDUSD = 'AUD_USD'

'''
Periods
'''
ONE_MINUTE = 'M1'
TWO_MINUTES = 'M2'
THREE_MINUTES = 'M3'
FIVE_MINUTES = 'M5'
TEN_MINUTES = 'M10'
FIFTEEN_MINUTES= 'M15'
THIRTY_MINUTES = 'M30'
ONE_HOUR = 'H1'
TWO_HOURS = 'H2'
THREE_HOURS = 'H3'
FOUR_HOURS = 'H4'
DAILY = 'D'
WEEKLY = 'W'
MONTHLY = 'M'

'''
BAR RANGES
'''
FOUR_HOURS_BARS = list(range(0,24,4))
DAILY_BARS = [0]

'''
IG PERIODS
'''
IG_LIVE_ONE_MINUTE = '1MINUTE'

IG_ONE_MINUTE = 'MINUTE'
IG_TEN_MINUTES = 'MINUTE_10'
IG_ONE_HOUR = 'HOUR'
IG_FOUR_HOURS = 'HOUR_4'
IG_DAILY = 'DAY'

'''
IG PRODUCTS
'''
IG_GBPUSD = 'CS.D.GBPUSD.CFD.IP'
IG_GBPUSD_MINI = 'CS.D.GBPUSD.MINI.IP'

'''
IG ITEM CALLBACK NAMES
'''
IG_OPEN = 'OPEN'
IG_DELETED = 'DELETED'
IG_UPDATED = 'UPDATED'
IG_REJECTED = 'REJECTED'

'''
Positions
'''
BUY = 'BUY'
SELL = 'SELL'
MARKET = 'MARKET'

'''
Position Status
'''
ACCEPTED = 'ACCEPTED'
REJECTED = 'REJECTED'

'''
Timestamps
'''
import datetime as dt
import pytz
TS_START_DATE = dt.datetime(year=2000, month=1, day=1)
DT_START_DATE = pytz.timezone('UTC').localize(dt.datetime(year=1970, month=1, day=1))

'''
Backtester
'''
DAILY_PERC_RET = 'd_perc'
DAILY_PIP_RET = 'd_pip'
DAILY_PERC_DD = 'd_dd'
DAILY_WINS = 'd_wins'
DAILY_LOSSES = 'd_losses'

DAY_COMPOUND_RET = 'd_compound_ret'
DAY_COMPOUND_DD = 'd_compound_dd'

POS_EQUITY_RET = 'pos_equity_ret'
POS_EQUITY_DD = 'pos_equity_dd'

POS_COMPOUND_RET = 'pos_compound_ret'
POS_COMPOUND_DD = 'pos_compound_dd'

POS_PERC_RET = 'pos_perc'
POS_PIP_RET = 'pos_pip'
POS_PERC_DD = 'pos_dd'

WINS = 'wins'
LOSSES = 'losses'
WIN_PERC = 'w_perc'
LOSS_PERC = 'l_perc'
GAIN = 'gain'
LOSS = 'loss'
GPR = 'GPR'

