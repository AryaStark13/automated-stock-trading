import pandas as pd
import numpy as np
import os
import datetime as dt
from tqdm import tqdm

STOCK_LIST = os.listdir('./Data/1MinDataset/')
LOT_SIZES_DF = pd.read_csv('./Data/LotSizes/LotSizes.csv')
LOT_SIZES_DF['stock'] = [x.split(' ')[0] for x in list(LOT_SIZES_DF['stock'])]

stock_counter = 1
df_compare_stocks = pd.DataFrame(columns=['stock', 'buy_threshold', 'sell_threshold', 'lookback_period', 'total_transactions', 'adjusted_P&L'])


for STOCK in tqdm(STOCK_LIST):
    try:

        df = pd.read_csv(f'./Data/1MinDataset/{STOCK}')
        STOCK_NAME = STOCK.split('.')[0]
        LOT_SIZE = int(LOT_SIZES_DF[LOT_SIZES_DF['stock'] == STOCK_NAME].iloc[:, 1])

        SLOPE_THRESHOLD_BUY_LIST = [0.4, 0.5, 0.6]
        SLOPE_THRESHOLD_SELL_LIST = [-0.4, -0.5, -0.6]
        LOOKBACK_PERIOD_LIST = list(range(5, 15))
        # SLOPE_THRESHOLD_BUY_LIST = [0.7]
        # SLOPE_THRESHOLD_SELL_LIST = [-0.2]
        # LOOKBACK_PERIOD_LIST = [6]
        COST_PER_TRANSACTION = 210
        COMBINATIONS = len(SLOPE_THRESHOLD_BUY_LIST) * len(SLOPE_THRESHOLD_SELL_LIST) * len(LOOKBACK_PERIOD_LIST)
        COLUMNS=['buy_threshold', 'sell_threshold', 'lookback_period', 'total_transactions', 'total_transaction_cost', 'adjusted_P&L', 'day_1', 'day_2', 'day_3', 'day_4', 'day_5', 'day_6', 'day_7', 'day_8', 'day_9', 'day_10', 'day_11', 'day_12', 'day_13', 'day_14', 'day_15', 'day_16', 'day_17', 'day_18', 'day_19']

        df['Date'] = pd.to_datetime(df['Date'])
        dates_arr = np.array([x.date() for x in df['Date']])

        # if len(np.unique(dates_arr)) != 21:
        #     print(f'Missing Data for {STOCK}')
        #     print('Moving to next stock')
        #     continue

        arr_close = np.array(df.loc[:, 'Close'].copy())
        df_track_arr = np.empty([COMBINATIONS, len(COLUMNS)])

        row_count = 0

        print(f'\n{stock_counter}/{len(STOCK_LIST)} \t {STOCK_NAME} \t {LOT_SIZE}')
        stock_counter += 1

        for SLOPE_THRESHOLD_BUY in SLOPE_THRESHOLD_BUY_LIST:

            for SLOPE_THRESHOLD_SELL in SLOPE_THRESHOLD_SELL_LIST:
            
                for LOOKBACK_PERIOD in LOOKBACK_PERIOD_LIST:
                    
                    position = 0
                    buy_price = sell_price = np.nan

                    profit_loss = 0
                    profit_loss_daily = []

                    daily_trades = 0
                    daily_trades_count = []


                    for i in range(LOOKBACK_PERIOD, len(arr_close)):

                        x = np.array(list(range(0, LOOKBACK_PERIOD)))
                        price_list = arr_close[i - LOOKBACK_PERIOD : i]
                        N = len(x)
                        slope = (N * np.sum(x * price_list) - np.sum(x) * np.sum(price_list)) / ((N * np.sum(x ** 2)) - (np.sum(x) ** 2))
                        date_i = df['Date'][i]

                        # First Transaction of the day
                        if position == 0 and date_i.time() < dt.time(15, 0):

                            if slope > SLOPE_THRESHOLD_BUY:
                                position = 1
                                daily_trades += 0.5
                                buy_price = price_list[-1]
                                action = f'DateTime: {date_i} \t Position: 0 --> 1 \t Buy Price: {buy_price} \t Slope: {slope}'

                            elif slope < SLOPE_THRESHOLD_SELL:
                                position = -1
                                daily_trades += 0.5
                                sell_price = price_list[-1]
                                action = f'DateTime: {date_i} \t Position: 0 --> -1 \t Sell Price: {sell_price} \t Slope: {slope}'


                        elif position == 1:

                            if date_i.time() < dt.time(15, 15):

                                if slope < SLOPE_THRESHOLD_SELL:
                                    position = -1
                                    daily_trades += 1
                                    sell_price = price_list[-1]
                                    action = f'DateTime: {date_i} \t Position: 1 --> -1 \t Sell Price: {sell_price} \t Slope: {slope}'

                                    # Calculating P&L
                                    profit_loss += sell_price - buy_price

                                else:
                                    action = f'DateTime: {date_i} \t Position: 1 --> 1 \t HOLD \t Slope: {slope}'
                                    pass

                            elif date_i.time() < dt.time(15, 28):

                                if slope < 0:
                                    position = 0
                                    daily_trades += 0.5
                                    sell_price = price_list[-1]
                                    action = f'DateTime: {date_i} \t Position: 1 --> 0 \t Sell Price: {sell_price} \t Slope: {slope}'

                                    # Calculating P&L
                                    profit_loss += sell_price - buy_price

                                else:
                                    action = f'DateTime: {date_i} \t Position: 1 --> 1 \t HOLD \t Slope: {slope}'
                                    pass

                            
                        elif position == -1:

                            if date_i.time() < dt.time(15, 15):

                                if slope > SLOPE_THRESHOLD_BUY:
                                    position = 1
                                    daily_trades += 1
                                    buy_price = price_list[-1]
                                    action = f'DateTime: {date_i} \t Position: -1 --> 1 \t  Buy Price: {buy_price} \t Slope'

                                    # Calculating P&L
                                    profit_loss += sell_price - buy_price

                                else:
                                    action = f'DateTime: {date_i} \t Position: -1 --> -1 \t HOLD \t Slope: {slope}'
                                    pass

                            if date_i.time() < dt.time(15, 28):
                                if slope > 0:
                                    position = 0
                                    daily_trades += 0.5
                                    buy_price = price_list[-1]
                                    action = f'DateTime: {date_i} \t Posiion: -1 --> 0 \t Buy Price: {buy_price} \t Slope: {slope}'

                                    # Calculating P&L
                                    profit_loss += sell_price - buy_price

                                else:
                                    action = f'DateTime: {date_i} \t Position: -1 --> -1 \t HOLD \t Slope: {slope}'
                                    pass


                        if date_i.time() == dt.time(15, 28):

                            if position == 1:
                                position = 0
                                daily_trades += 0.5
                                sell_price = price_list[-1]
                                action = f'DateTime: {date_i} \t Position: 1 --> 0 \t Square-Off \t Slope: {slope}'

                                # Calculating P&L
                                profit_loss += sell_price - buy_price

                            elif position == -1:
                                position = 0
                                daily_trades += 0.5
                                buy_price = price_list[-1]
                                action = f'DateTime: {date_i} \t Position: -1 --> 0 \t Square-Off \t Slope: {slope}'

                                # Calculating P&L
                                profit_loss += sell_price - buy_price

                            profit_loss_daily.append(profit_loss)
                            daily_trades_count.append(daily_trades)
                            profit_loss = 0
                            daily_trades = 0


                    total_transaction_cost = sum(daily_trades_count) * COST_PER_TRANSACTION
                    adjusted_profit_loss = (sum(profit_loss_daily) * LOT_SIZE) - total_transaction_cost
                    adjusted_profit_loss_daily = [x * LOT_SIZE - y * COST_PER_TRANSACTION for x, y in zip(profit_loss_daily, daily_trades_count)]

                    df_track_arr[row_count, 0] = SLOPE_THRESHOLD_BUY
                    df_track_arr[row_count, 1] = SLOPE_THRESHOLD_SELL
                    df_track_arr[row_count, 2] = LOOKBACK_PERIOD
                    df_track_arr[row_count, 3] = sum(daily_trades_count)
                    df_track_arr[row_count, 4] = total_transaction_cost
                    df_track_arr[row_count, 5] = adjusted_profit_loss
                    df_track_arr[row_count, 6:] = adjusted_profit_loss_daily

                    row_count += 1
                
    # Uncomment while running for 1 stock
                    # print(f'------------------------------------------------------------------------------')
                    # print(f'Combination: {row_count}')
                    # print(f'Threshold High: {SLOPE_THRESHOLD_BUY}, Threshold Low: {SLOPE_THRESHOLD_SELL}, Lookback Period: {LOOKBACK_PERIOD}')
                    # print(f'Total trades = {sum(profit_loss_daily)}')
                    # print(f'Total cost of trades = {total_transaction_cost}')
                    # print(f'Adjusted P&L for {STOCK} having {LOT_SIZE} LOT Size = {adjusted_profit_loss:.2f}')
        
        df_track = pd.DataFrame(df_track_arr, columns=COLUMNS)

        df_track_partial = df_track[(df_track['adjusted_P&L'] > 0) & (df_track['total_transactions'] <= 126)].copy().sort_values(by=['adjusted_P&L'], ascending=False).reset_index(drop=True)
        df_track.sort_values(by='adjusted_P&L', ascending=False, inplace=True)


        if df_track_partial.shape[0]:
            df_compare_stocks.loc[len(df_compare_stocks), 'stock'] = STOCK_NAME
            df_compare_stocks.iloc[len(df_compare_stocks) - 1, 1:4] = df_track_partial.iloc[0:1, 0:3]
            df_compare_stocks.loc[len(df_compare_stocks) - 1, 'total_transactions'] = df_track_partial.loc[0, 'total_transactions']
            df_compare_stocks.loc[len(df_compare_stocks) - 1, 'adjusted_P&L'] = df_track_partial.loc[0, 'adjusted_P&L']

        df_track_partial.to_csv(f'./BacktestingResults/Strategy1ResultsPartial/{STOCK_NAME}_Partial.csv', index=False)
        df_track.to_csv(f'./BacktestingResults/Strategy1ResultsComplete/{STOCK_NAME}_Complete.csv', index=False)
    
    except Exception as e:
        print(f'Error in {STOCK_NAME}')
        print(e)
        pass

df_compare_stocks.sort_values(by='adjusted_P&L', ascending=False, inplace=True)
df_compare_stocks.to_csv('./BacktestingResults/ComparingBestStocks/AllStocks.csv', index=False)