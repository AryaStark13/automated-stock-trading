# Runs all codes one after the other

# 1. Update 21 days data - Take downloading script from Sankalp

# 2. Data Validation - Check if all stocks have N unique dates

# 3. Run Backtesting code - ./Regression Codes/regression-strategy-1.ipynb

# 4. Top 50 Stocks to PKL and Update sample.yaml - ./Stocks to PKL/Top 50/top_50.ipynb

# 5. Paper Trading Code - C:\Users\ariha\Desktop\regression-algorithm-nts\regression-algorithm\TechnicalFilters.py

# 6. Verify Paper Trading Results

import os
import shutil
import sys
import colorama
from colorama import Fore

colorama.init(autoreset=True)

sep = f"\n{'-'*120}\n\n"
# TODO Implement first step of the above steps

# Step 2: Data Validation
if __name__ == '__main__':

    print('Performing Data Validation...')

    try:
        with open('./Data/DataDownloadingSetup/DataValidation.py') as data_validation_file:
            exec(data_validation_file.read())
    except FileNotFoundError:
        print(f'{Fore.RED} Data Validation File Not Found')
        print('Stopping execution...')
        sys.exit()
    except Exception as e:
        print(e)
        print(f'{Fore.RED} Error in Data Validation File')
        print('Stopping execution...')
        sys.exit()
    else:
        print(f'{Fore.GREEN} Data Validation File Executed Successfully')
        print('Moving to Step - 3: Regression Strategy', end=sep)


    # Step 3: Regression Strategy

    try:
        with open('./RegressionCodes/RegressionStrategy1.py') as strategy_file:
            exec(strategy_file.read())
    except FileNotFoundError:
        print(f'{Fore.RED} Regression Strategy File Not Found')
        print('Stopping execution...')
        sys.exit()
    except Exception as e:
        print(e)
        print(f'{Fore.RED} Error in Regression Strategy File')
        print('Stopping execution...')
        sys.exit()
    else:
        print(f'{Fore.GREEN} Regression Strategy File Executed Successfully')
        print('Moving to Step - 4: Update Sample YAML', end=sep)

    # Step 4: Converting stocks to PKL and updating sample.yaml

    try:
        with open('./StocksToPKL/Top50/Top50.py') as top_50_file:
            exec(top_50_file.read())
    except FileNotFoundError:
        print(f'{Fore.RED} Top 50 Stocks File Not Found')
        print('Stopping execution...')
        sys.exit()
    except Exception as e:
        print(e)
        print(f'{Fore.RED} Error in Top 50 Stocks File')
        print('Stopping execution...')
        sys.exit()
    else:
        print(f'{Fore.GREEN} Top 50 Stocks parameters generated and sample.yaml updated successfully')
        print('Copying sample.yaml and top_50.pkl to paper trading folder', end=sep)

    # Copy sample.yaml and top_50.pkl to paper trading folder

    try:
        config_folder = os.listdir('./Config/')
        for file in config_folder:
                shutil.copy(f'./Config/{file}', r'C:\Users\ariha\Desktop\regression-algorithm-nts\regression-algorithm\Config')
    except Exception as e:
        print(e)
        print(f'{Fore.RED} Error in copying sample.yaml and top_50.pkl to paper trading folder')
        print('Stopping execution...')
        sys.exit()
    else:
        print(f'{Fore.GREEN} sample.yaml and top_50.pkl copied to paper trading folder')
        print('Move to Step - 5: Manually execute Paper Trading Code', end=sep)
        print(f'{Fore.GREEN} DONE !!!')