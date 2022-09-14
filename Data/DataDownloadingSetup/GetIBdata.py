#
#  Created by Mridul Mehta on 2/20/20.
#

import argparse
import datetime as dt
import numpy as np
import pandas as pd
import queue
import os
# import tzlocal 
import pytz
import time
import xmltodict

from threading import Thread
from dateutil import relativedelta as rd
from ibapi.ticktype import TickType,TickTypeEnum
from ibapi.wrapper import EWrapper
from ibapi.client import EClient
from ibapi.order import Order
from ibapi.order_state import OrderState
from ibapi.client import BarData
from ibapi.client import Contract
from ibapi.common import OrderId, TickerId,TagValueList,TickAttribLast,TickAttrib
from ibapi.common import HistoricalTickLast
from ibapi.contract import ContractDetails,ComboLeg
from ibapi.tag_value import TagValue
from tqdm import tqdm
#
# IB Wrapper implementation
#
class IBWrapper(EWrapper):
    pass

#
# IB Client implementation
#
class IBClient(EClient):

    """ Constructor
    """
    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)

#
# This defines the IB interface for interacting with all IB APIs.
#
class IB(IBWrapper, IBClient):

    """ Constructor
    """
    def __init__(self):
        # init base classes
        IBWrapper.__init__(self)
        IBClient.__init__(self, wrapper=self)
        # Init variables
        self.is_error = False
        self.order_id = None
        self.order_state = None
        self.temp = pd.DataFrame()
        self.caller = None
        self.data = pd.DataFrame()
        self.sample = None
        self.contract_id = None
        self.is_complete = False
        # connect
        self.connect("192.168.1.107", 7497, 54)
        thread = Thread(target = self.run)
        thread.start()
        setattr(self, "thread", thread)
        print("Connected")

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.order_id = orderId
    """ Close connection
    """
    def close(self):
        self.disconnect()


    """ Error callback
    """
    def error(self, reqId, errorCode, errorString):
        if errorCode not in [2104, 2106, 2158,2168,2169]:
            self.is_error = True
            print('Error (%d): %s' % (errorCode, errorString))
            if self.caller is not None:
                self.caller.callback(0, None)

    """ Historical data callbacks
    """
    def historicalDataUpdate(self, reqId: int, bar: BarData):
        df = pd.DataFrame({'Date': [bar.date], 'Open': [bar.open], 'High': [bar.high],
            'Low': [bar.low], 'Close': [bar.close], 'Volume': [bar.volume]})
        df.Date = pd.to_datetime(df.Date)
        print("New Data")

    def historicalData(self, reqId:int, bar: BarData):
        # print("update")
        df = pd.DataFrame({'Date': [bar.date], 'Open': [bar.open], 'High': [bar.high],
            'Low': [bar.low], 'Close': [bar.close], 'Volume': [bar.volume]})
        #self.data = self.data.append(df)
        self.data = pd.concat([self.data, df])
        # print(self.data)

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        super().historicalDataEnd(reqId, start, end)

        df = self.data
        # self.data.index = np.array(range(self.data.shape[0])) + 1
        self.data['Date'] = pd.to_datetime(self.data['Date'])
        self.is_complete = True

    def saveFile(self,filename):
        # if self.data.shape[0] != 0:
        #     self.data['Time'] = pd.to_datetime(self.data['Time'],unit='s') + dt.timedelta(hours=5,minutes=30)
        self.data = self.data.drop_duplicates().reset_index(drop=True)
        self.data['Date'] = pd.to_datetime(self.data['Date'])
        self.data.to_csv(f'./Data/02-09-22_ThursdayData/{filename}.csv', index=False)
        self.data = pd.DataFrame()

    def close(self):
        self.disconnect()

stocks = pd.read_csv('./Data/DataDownloadingSetup/stock_list.csv')
existing_stock = os.listdir('./Data/02-09-22_ThursdayData/')
app = IB()
ticker_id = 1000

stock_list = stocks['Symbol'].to_list()
# stock_list = stock_list[:15]

for ind_stock in tqdm(stock_list):
    if ind_stock+'.csv' in existing_stock:
        continue
    print("Downloading Data for",ind_stock)
    time.sleep(5)
    stock = Contract()
    stock.secType = 'CONTFUT'
    # stock.strike = 36500.0
    # stock.right = 'C'
    # stock.lastTradeDateOrContractMonth = '20220428'
    stock.symbol = ind_stock
    stock.currency = "INR"
    stock.exchange = "NSE"
    # stock.multiplier = 2500

    # app.reqMktData(ticker_id,stock,"233",False,False,[])

    duration = '2 D'
    freq = '1 min'

    ticker_id += 1

    app.data = pd.DataFrame()
    app.reqHistoricalData(ticker_id, stock, '', duration, freq, 'TRADES', 1, 1, False, [])
    count = 0
    while count <= 5:
        if app.is_error:
            app.is_error = False
            break
        if app.data.empty:
            count += 1
            # print(count)
            time.sleep(20)
        else:
            break
    
    if not app.data.empty:
        # print("Data is there")
        while not app.is_complete:
            count += 1
        app.saveFile(stock.symbol)
        app.is_complete = False
        
        df = pd.read_csv(f'./Data/02-09-22_ThursdayData/{stock.symbol}.csv')

        df['Date'] = pd.to_datetime(df['Date'])
        dates_arr = np.array([x.date() for x in df['Date']])

        if len(np.unique(dates_arr)) != 19:
            print(f'Missing Data for {stock.symbol}')
            print('Moving to next stock')
        # time.sleep(20)
        # print(count)
    else:
        print("Couldn't Download Data for",stock.symbol)
        # time.sleep(20)

downloaded_stocks = os.listdir('./Data/02-09-22_ThursdayData/')
print(f'{len(downloaded_stocks)} stocks downloaded out of {len(stock_list)}')

print('Moving to next step: Appending new day data and removing first day')
app.close()
