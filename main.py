import yfinance as yf
import pandas as pd
from apscheduler.schedulers.blocking import BlockingScheduler
from oandapyV20 import API
import oandapyV20.endpoints.orders as orders
from oandapyV20.contrib.requests import MarketOrderRequest
from oanda_candles import Pair, Gran, CandleClient
from oandapyV20.contrib.requests import TakeProfitDetails, StopLossDetails

dataF = yf.download("EURUSD=X", start="2023-05-26", end="2023-07-23", interval='15m')
dataF.iloc[:,:]
#dataF.Open.iloc

def signal_generator(df, short_window=20, long_window=50):
    # Calculate Bollinger Bands
    df['SMA'] = df['Close'].rolling(window=20).mean()
    df['StdDev'] = df['Close'].rolling(window=20).std()
    df['UpperBand'] = df['SMA'] + 2 * df['StdDev']
    df['LowerBand'] = df['SMA'] - 2 * df['StdDev']

    # Calculate short-term and long-term moving averages
    df['ShortMA'] = df['Close'].rolling(window=short_window).mean()
    df['LongMA'] = df['Close'].rolling(window=long_window).mean()

    # Get the current prices and Bollinger Bands values
    current_close = df['Close'].iloc[-1]
    current_upper_band = df['UpperBand'].iloc[-1]
    current_lower_band = df['LowerBand'].iloc[-1]
    current_short_ma = df['ShortMA'].iloc[-1]
    current_long_ma = df['LongMA'].iloc[-1]

    # Mean Reversion Strategy (1: Buy, 2: Sell, 0: No clear pattern)
    if current_close < current_lower_band:
        return 1
    elif current_close > current_upper_band:
        return 2

    # Moving Average Crossover Strategy (1: Buy, 2: Sell, 0: No clear pattern)
    elif current_short_ma > current_long_ma and df['ShortMA'].iloc[-2] <= df['LongMA'].iloc[-2]:
        return 1
    elif current_short_ma < current_long_ma and df['ShortMA'].iloc[-2] >= df['LongMA'].iloc[-2]:
        return 2

    # No clear pattern
    else:
        return 0

# Assuming you have already loaded dataF with historical price data
# ...

# Create a new column 'Signal' in dataF to store the buy/sell signals (0, 1, or 2)
dataF['Signal'] = 0

# Define short_window and long_window values
short_window = 20
long_window = 50

# Calculate signals using the combined strategy
for i in range(1, len(dataF)):
    df = dataF[i - 1:i + 1]
    dataF.loc[i, 'Signal'] = signal_generator(df, short_window=short_window, long_window=long_window)

# Print the signals generated
#print(dataF['Signal'])

#signal = []
#signal.append(0)
#for i in range(1,len(dataF)):
#    df = dataF[i-1:i+1]
#    signal.append(signal_generator(df))

#signal_generator(data)
#dataF["signal"] = signal

#from config import access_token, accountID
access_token='2e80861c12a53f429677938073cb19b5-53d628037832ebefa27173c8cd5706cb'
accountID = '101-001-26421691-001'
def get_candles(n):
    client = CandleClient(access_token, real=False)
    collector = client.get_collector(Pair.EUR_USD, Gran.M15)
    candles = collector.grab(n)
    return candles

candles = get_candles(3)
for candle in candles:
    print(float(str(candle.bid.o))>1)

def trading_job():
    candles = get_candles(3)
    dfstream = pd.DataFrame(columns=['Open','Close','High','Low'])
    
    i=0
    for candle in candles:
        dfstream.loc[i, ['Open']] = float(str(candle.bid.o))
        dfstream.loc[i, ['Close']] = float(str(candle.bid.c))
        dfstream.loc[i, ['High']] = float(str(candle.bid.h))
        dfstream.loc[i, ['Low']] = float(str(candle.bid.l))
        i=i+1

    dfstream['Open'] = dfstream['Open'].astype(float)
    dfstream['Close'] = dfstream['Close'].astype(float)
    dfstream['High'] = dfstream['High'].astype(float)
    dfstream['Low'] = dfstream['Low'].astype(float)

    signal = signal_generator(dfstream.iloc[:-1,:])#
    
    # EXECUTING ORDERS
    #accountID = "XXXXXXX" #your account ID here
    client = API(access_token)
         
    SLTPRatio = 2.
    previous_candleR = abs(dfstream['High'].iloc[-2]-dfstream['Low'].iloc[-2])
    
    SLBuy = float(str(candle.bid.o))-previous_candleR
    SLSell = float(str(candle.bid.o))+previous_candleR

    TPBuy = float(str(candle.bid.o))+previous_candleR*SLTPRatio
    TPSell = float(str(candle.bid.o))-previous_candleR*SLTPRatio
    
    print(dfstream.iloc[:-1,:])
    print(TPBuy, "  ", SLBuy, "  ", TPSell, "  ", SLSell)
    signal = 2
    #Sell
    if signal == 1:
        mo = MarketOrderRequest(instrument="EUR_USD", units=-1000, takeProfitOnFill=TakeProfitDetails(price=TPSell).data, stopLossOnFill=StopLossDetails(price=SLSell).data)
        r = orders.OrderCreate(accountID, data=mo.data)
        rv = client.request(r)
        print(rv)
    #Buy
    elif signal == 2:
        mo = MarketOrderRequest(instrument="EUR_USD", units=1000, takeProfitOnFill=TakeProfitDetails(price=TPBuy).data, stopLossOnFill=StopLossDetails(price=SLBuy).data)
        r = orders.OrderCreate(accountID, data=mo.data)
        rv = client.request(r)
        print(rv)

trading_job()

#scheduler = BlockingScheduler()
#scheduler.add_job(trading_job, 'cron', day_of_week='mon-fri', hour='00-23', minute='1,16,31,46', start_date='2022-01-12 12:00:00', timezone='America/Chicago')
#scheduler.start()