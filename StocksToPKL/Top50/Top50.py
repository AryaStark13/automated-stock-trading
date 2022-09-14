import pandas as pd
import numpy as np
import yaml

all_stocks = pd.read_csv('./BacktestingResults/ComparingBestStocks/AllStocks.csv')

top_50 = all_stocks.iloc[:50, :4].copy()
top_50.to_pickle('./Config/Top50.pkl')

top_50_dict = {value: { 'symbol': value } for value in top_50['stock']}

with open('./Config/Sample.yaml', 'r') as yaml_file:
    new_yaml = yaml.load(yaml_file, Loader=yaml.SafeLoader)
    new_yaml.update(top_50_dict)
    
with open('./Config/Sample.yaml', 'w') as yaml_file:
    yaml.safe_dump(new_yaml, yaml_file, sort_keys=False)