import pandas as pd
import numpy as np
import os

downloaded_data_list = os.listdir('Data/1MinDataset/')

count = 0
for stock in downloaded_data_list:
    df = pd.read_csv(f'Data/1MinDataset/{stock}')
    df['Date'] = pd.to_datetime(df['Date'])
    dates_arr = np.array([x.date() for x in df['Date']])
    if len(np.unique(dates_arr)) != 19:
        print(f'Missing Data for {stock}')
        print(f'Dates: {len(np.unique(dates_arr))}')
        print(f'Removing {stock} from list')
        downloaded_data_list.remove(stock)
        os.remove(f'Data/1MinDataset/{stock}')
        count += 1
        print(f'count: {count}')
        continue

print(f'Total Missing Data: {count}/{len(downloaded_data_list)} \n')