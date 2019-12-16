'''
Products
'''
GBPUSD = 'CS.D.GBPUSD.MINI.IP'

'''
Periods
'''
ONE_MINUTE = 0
PRICE_LIVE_ONE_MINUTE = '1MINUTE'
PRICE_ONE_MINUTE = 'MINUTE'

ONE_HOUR = 1
PRICE_ONE_HOUR = 'HOUR'

FOUR_HOURS = 4
PRICE_FOUR_HOURS = 'HOUR_4'
FOUR_HOURS_BARS = list(range(0,24,4))

DAILY = 24
PRICE_DAILY = 'DAY'
DAILY_BARS = [0]

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
import datetime
DT_START_DATE = datetime.datetime(year=2014, month=1, day=1)
MT_DT_START_DATE = datetime.datetime(year=1970, month=1, day=1)

'''
Backtester
'''
DAILY_PERC_RET = 'd_perc'
DAILY_PIP_RET = 'd_pip'
DAILY_PERC_DD = 'd_dd'
DAILY_WINS = 'd_wins'
DAILY_LOSSES = 'd_losses'

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

