from pyNTS.App.lot_map import lot_map
from pyNTS.App.common import Order, Contract

from threading import Thread
# from kafka import KafkaConsumer, KafkaProducer
from influxdb import InfluxDBClient

import json
import yaml
import collections
import os
import time
import statistics


from colorama import init, Style, Fore, Back
init()

import requests
import urllib.request

import numpy as np
import statistics as st

from datetime import datetime
from dateutil.relativedelta import relativedelta


class TechnicalFilters(Thread):
    def __init__(self, config_file_name, broker_type, api_key, token, management_topic, broadcast_topic, kafka_bootstrap_servers, monitor_stocks_class=None, execute_trades_class=None):
        Thread.__init__(self)
        self.status = 'Starting up...'
        self.influx_strategy = ''
        self.strategy_version = ''
        self.write_to_influx = False
        self.basic_sleep_time = 5e-5
        if broker_type == 'IB':
            from pyNTS.App.IB_app import App
            self.app = App(ip_address=api_key, port_id=int(token.split(':')[0]), client_id=int(token.split(':')[1]))
        else:
            print()
        if monitor_stocks_class is None:
            self.monitor_class = Monitor
        else:
            self.monitor_class = monitor_stocks_class
        if execute_trades_class is None:
            self.execute_trades_class = ExecuteTrades
        else:
            self.execute_trades_class = execute_trades_class
        self.strat_config = yaml.safe_load(open(f"{config_file_name}.yaml"))

        defaults = self.strat_config['default']
        self.portfolio_settings = self.strat_config['portfolio']
        del self.strat_config['portfolio']
        del self.strat_config['default']
        self.threads = min(1, len(self.strat_config))
        print(f'Threads = {self.threads}')

        def update(d, u):
            for k, v in u.items():
                if isinstance(v, collections.Mapping):
                    d[k] = update(d.get(k, {}), v)
                else:
                    d[k] = v
            return d

        for stk in self.strat_config.keys():
            temp_dict = defaults.copy()
            temp_dict = update(temp_dict, self.strat_config[stk])
            self.strat_config[stk] = temp_dict

        self.nts_contracts = {}
        self.broker_contracts = {}
        self.open_positions = {}
        self.open_lots = {}
        self.average_cost = {}
        assign_mkt_id_1 = 201
        self.test_key = next(iter(self.strat_config))
        mkt_open_hour = int(self.strat_config[self.test_key]['contract']['mkt_open'].split(':')[0])
        mkt_open_min = int(self.strat_config[self.test_key]['contract']['mkt_open'].split(':')[1])
        mkt_close_hour = int(self.strat_config[self.test_key]['contract']['mkt_close'].split(':')[0])
        mkt_close_min = int(self.strat_config[self.test_key]['contract']['mkt_close'].split(':')[1])
        tz_offset_hour = 0
        tz_offset_min = 0
        self.mkt_open = datetime.now().replace(hour=mkt_open_hour, minute=mkt_open_min, second=0, microsecond=0) + relativedelta(hours=tz_offset_hour, minutes=tz_offset_min)
        self.mkt_close = datetime.now().replace(hour=mkt_close_hour, minute=mkt_close_min, second=0, microsecond=0) + relativedelta(hours=tz_offset_hour, minutes=tz_offset_min)

        new_lot_map = {}
        for lot_key in lot_map:
            if len(lot_key) > 9:
                new_lot_map[lot_key[:9]] = lot_map[lot_key]
            if '&' in lot_key:
                new_key = lot_key.replace('&', '')
                new_lot_map[new_key] = lot_map[lot_key]
        lot_map.update(new_lot_map)

        for stk in self.strat_config.keys():
            self.strat_config[stk]['mkt_id'] = (assign_mkt_id_1, )
            new_contract = Contract(self.strat_config[stk]['symbol'], self.strat_config[stk]['contract']['security_type'])
            if new_contract.sec_type == 'FUT' or new_contract.sec_type == 'OPT':
                self.strat_config[stk]['quantum_type'] = 'lot'
                self.expiry = self.app.get_next_expiry()
                new_contract.expiry = self.expiry
            if new_contract.sec_type == 'STK':
                self.strat_config[stk]['quantum_type'] = 'exposure'
            self.nts_contracts[stk] = new_contract
            print(f'Trying to create new contract for- {Style.BRIGHT} {Fore.GREEN} {new_contract} .. {Style.RESET_ALL}')
            self.broker_contracts[stk] = self.app.resolve_contract(new_contract)
            print("this stk is of type ", self.broker_contracts[stk])
            assign_mkt_id_1 = assign_mkt_id_1 + 1
            print(f'New contract created- {self.broker_contracts[stk]}')
            self.open_positions[stk] = 0
            self.open_lots[stk] = 0
            self.average_cost[stk] = 0

        self.data_threads = []
        self.updating_portfolio = False
        self.monitor_threads = []
        print(f'End of __init__')
    
    def run(self):
        splits = self.split_stocks(self.threads, self.strat_config)
        self.update_portfolio()
        self.download_all_historic(splits)
        print(f"FIRST UPDATE PORTFOLIO \n{self.app.positions_handler.positions}")
        for stk in self.strat_config.keys():
            if self.strat_config[stk]['quantum_type'] == 'exposure':
                self.normalize_exposure(stk)
        print("FIRING UP THE THREADS...")
        for ind, stk_group in enumerate(splits):
            print(f'STK_GROUPS - {stk_group}')
            new_thread = self.monitor_class(stk_group, self)
            self.monitor_threads.append(new_thread)
            new_thread.start()

    @staticmethod
    def split_stocks(how_many, strat_config):
        split_op = []
        for i in range(how_many):
            split_op.append([])
        for ind, stk in enumerate(strat_config):
            split_op[ind % how_many].append(stk)
        print(f'Split into {how_many} groups...')
        for group_no, group in enumerate(split_op):
            print(f'Group {group_no} has {len(group)} elements...')
        return split_op

    def normalize_exposure(self, stk):
        lot_map[self.strat_config[stk]['symbol']] = self.strat_config[stk]['quantum']  # round(self.strat_config[stk]['quantum'] / self.app.closes[self.strat_config[stk]['mkt_id'][0]][-1])
        # self.strat_config[stk]['quantum'] = 1
        print("checking quantum ", lot_map[self.strat_config[stk]['symbol']])

    def download_all_historic(self, splits):
        for group in splits:
            t = Thread(target=self.download_group_hist_data, args=(group, ))
            self.data_threads.append(t)
            t.start()
            time.sleep(1)
        for t in self.data_threads:
            t.join()
        print("Downloaded all hist data groups")

    def download_group_hist_data(self, group):
        for stk in group:
            print(f'Starting historic data download for {stk}')
            self.app.hist_data_mkt_update(
                self.broker_contracts[stk],
                ticker_id=self.strat_config[stk]['mkt_id'][0],
                bar_size=self.strat_config[stk]['candle_size'],
                duration="5 D",
                timeout_limit=60
            )
            time.sleep(1)
        print(f'Downloaded hist data for {group}')

    def update_portfolio(self, forced_data=None):
        while self.updating_portfolio:  # Ensuring thread safety
            time.sleep(1)
        self.updating_portfolio = True
        self.app.get_open_positions()
        temp = self.app.get_open_positions()
        print("Printing out open position from interactive brokers \n ",temp)
        time.sleep(1)
        for stk in self.strat_config:
            try:
                pos = self.app.positions_handler.positions
                #print("this is pos ", pos, "having length ", len(pos['con_id']))
                con = self.broker_contracts[stk]
                stk_pos = pos[pos['con_id'] == con.conId].to_dict(orient='records')[0]
                # stk_pos = pos[True].to_dict(orient='records')[0]
                self.open_positions[stk] = stk_pos['position']
                print(f"OPEN Positions of {stk} = {self.open_positions[stk]}")
                self.open_lots[stk] = stk_pos['position'] / lot_map[self.strat_config[stk]['symbol']]
                print(f'''$$$$$$
                   =============
                    OPEN LOTS OF {stk} = {self.open_lots[stk]}
                    =============
                    $$$$$$''')
                self.average_cost[stk] = stk_pos['avg_cost']
                print(f"AVERAGE cost {stk} = {self.average_cost[stk]}")
            except (KeyError, IndexError):
                print("went inside exception ")
                print("\n\n")
                self.open_positions[stk] = 0
                self.open_lots[stk] = 0
                self.average_cost[stk] = 0
                print(f"AVERAGE cost {stk} = {self.average_cost[stk]} EXCEPTION")
        if forced_data is not None:
            for stk in forced_data:
                self.open_positions[stk] = forced_data[stk]['position']
                self.open_lots[stk] = forced_data[stk]['position'] / lot_map[self.strat_config[stk]['symbol']]
                self.average_cost[stk] = forced_data[stk]['avg_cost']
                print(f'''Forced_data inside For loop {stk}
                Open positions = {self.open_positions[stk]}
                Open Lots = {self.open_lots[stk]}
                Average cost = {self.average_cost[stk]}''')
        self.updating_portfolio = False
        time.sleep(2)


class Monitor(Thread):

    def __init__(self, stocks_list, main_strat_obj: TechnicalFilters):
        super().__init__()
        self.stocks_list = stocks_list
        self.stocks_list_copy = self.stocks_list
        self.forced_sleep_time = 1/len(stocks_list)
        self.main_strat = main_strat_obj
        self.strat_config = main_strat_obj.strat_config
        self.app = main_strat_obj.app
        self.stock_functions = {}
        self.stocks_on_hold = {}
        self.highest_pnl_perc = {}
        self.highest_pnl = {}
        self.last_traded_stk_price = {}
        running_state_files = os.listdir('running_state')
        self.stock_state = {}
        self.prev_price = {}
        self.full_state_details = {}

        self.stop_loss = {}
        self.stop_flag = False
        self.terminate_flag = False
        self.candle_mins = {}
        self.peak_price = {}
        self.print_at = {}
        self.last_entered_time = {}
        self.position_type = {}
        self.candle_count = {}
        for stk in self.stocks_list:
            self.last_entered_time[stk] = ''
            self.position_type[stk] = ''
            self.print_at[stk] = 0
            #self.stop_loss[stk] = self.strat_config[stk]['Stop Loss']
            if self.main_strat.slug + '-' + stk + '.yaml' in running_state_files:
                run_state = yaml.safe_load(open('running_state' + self.main_strat.slug + '-' + stk + '.yaml'))
                self.highest_pnl_perc[stk] = run_state['highest_pnl_perc']
                self.highest_pnl[stk] = run_state['highest_pnl']
                self.full_state_details[stk] = run_state['current_state']
                self.stock_state[stk] = run_state['current_state']['state']
            else:
                self.highest_pnl_perc[stk] = 0.0
                self.highest_pnl[stk] = 0.0
                self.stock_state[stk] = self.get_stock_state(stk)
                # yaml.safe_dump({'highest_pnl_perc': 0, 'highest_pnl': 0, 'current_state': {'state': self.stock_state[stk]}}, open('running_state' + self.main_strat.slug + '-' + stk + '.yaml', 'wt'), default_flow_style=False)
            mkt_id = self.strat_config[stk]['mkt_id'][0]
            
        self.state_map = {
            'waiting to enter': self.check_signal,
            'entered': self.check_signal,
        }
        self.whisper_state_map = {
            'Entered': 'entered',
            'Exited': 'waiting to enter'
        }

    def get_stock_state(self, stk):  # ONLY USED AS REDUNDANCY IF FILE IS NOT FOUND... Should be called very rarely...
        if self.main_strat.open_positions[stk] == 0:
            return 'waiting to enter'
        else:
            return 'entered'


    def run(self): #TODO
        #MAKE CHANGES ACCORDING TO YOUR CHECK SIGNAL AND STRATEGY
        while datetime.now() < self.main_strat.mkt_open:
            print(f"Waiting for the market to open...")
            time.sleep((self.main_strat.mkt_open - datetime.now()).seconds)
        print(f"BEFORE START PORTFOLIO\n{self.app.positions_handler.positions}")
        print("stocks are : ", self.stocks_list)
        while self.main_strat.mkt_open <= datetime.now() < self.main_strat.mkt_close:
            for stk_ind, stk in enumerate(self.stocks_list):
                signal, order_desc, price_at_trigger, stp_limit, exec_type = self.state_map[self.stock_state[stk]](self.strat_config[stk]['mkt_id'][0], stk)
                if (signal == 1) or (signal == -1):

                    self.last_entered_time[stk] = datetime.now().strftime('%H:%M:%S')
                    if 'ENTRY' in order_desc:
                        self.position_type[stk] = "E"
                    if 'SL' in order_desc:
                        self.position_type[stk] = "SL"
                    if 'REVERSAL' in order_desc:
                        self.position_type[stk] = "R"
                    new_execute_thread = self.main_strat.execute_trades_class(stk, signal * lot_map[self.strat_config[stk]['symbol']], self, order_desc, stp_limit, signal, exec_type=exec_type)
                    new_execute_thread.start()
                    self.stocks_on_hold[stk] = stk
                    time.sleep(1)
                    print("stocks list before DEL", self.stocks_list)

                    del self.stocks_list[stk_ind]
                    print("stocks list ", self.stocks_list)


        print('Markets have closed...')
 
    def trade_callback(self, stk, filled_order_id, whisper):
        old_state = self.stock_state[stk]
        new_state = self.whisper_state_map[whisper]
        print(f'|||| {stk} going from {old_state} to {new_state}')
        self.stock_state[stk] = self.whisper_state_map[whisper]
        print(f"Trade callback whispered - {whisper}")
        # remaining = self.trading_app.orders[filled_order_id].remaining
        # avg_filled_price = self.trading_app.orders[filled_order_id].avg_fill_price
        # avg_total_price = self.trading_app.orders[filled_order_id].avg_total_price
        # print(f'{stk} || Order filled with ID- {filled_order_id} \n'
        #       f'{stk} || with average fill price- {avg_filled_price} \n'
        #       f'{stk} || and average total price- {avg_total_price} \n'
        #       f'{stk} || and {remaining} remaining')
        # yaml.safe_dump({'highest_pnl_perc': 0, 'highest_pnl': 0, 'current_state': {'state': self.stock_state[stk]}}, open('running_state' + self.main_strat.slug + '-' + stk + '.yaml', 'wt'), default_flow_style=False)
        self.highest_pnl_perc[stk] = self.highest_pnl[stk] = 0.0
        self.stocks_list.append(self.stocks_on_hold[stk])

    def check_signal(self, req_id, stk):
        price = self.app.closes[req_id][-1]
        time.sleep(self.main_strat.basic_sleep_time)
        time.sleep(self.forced_sleep_time)
        # self.candle_count[stk] = len(self.app.closes[req_id])
        try:
            pnl_perc = ((price / self.main_strat.average_cost[stk]) - 1) * np.sign(self.main_strat.open_positions[stk])
            pnl = (price - self.main_strat.average_cost[stk]) * self.main_strat.open_positions[stk]  # * lot_map[self.strat_config[stk]['symbol']]
        except (ZeroDivisionError, KeyError):
            pnl_perc = 0.0
            pnl = 0.0
     
        #TODO WRITE YOUR STRATEGY LOGIC HERE

            
        return 0, 'NOTHING', price, price, 'MKT'

    # def stop(self):
    #     self.stop_flag = True


class ExecuteTrades(Thread):

    def __init__(self, stk, position, monitor_parent: Monitor, order_desc, price_at_trigger, signal, exec_type='MKT', 
                 addn_data=None):
        super().__init__()
#order_type='MARKET' can be used instead exec_type='MKT'

        self.stk = stk
        self.order_ids = {}
        self.monitor_parent = monitor_parent            #monitor
        self.trade_app = monitor_parent.app             
        self.position = position
        #print('position ', self.position)
        self.influx_strategy = monitor_parent.main_strat.influx_strategy
        self.strategy_version = monitor_parent.main_strat.strategy_version
        self.order_desc = order_desc
        self.exec_type = exec_type
        self.price_at_trigger = price_at_trigger
        self.signal = signal
        self.addn_data = addn_data
        self.trade_function_map = {
            self.exec_type: self.place_market_order,
        }
        self.desc_whisper_map = {
            'ENTRY': 'Entered',
            'REVERSAL': 'Entered',
            'LONG': 'Entered',
            'SHORT': 'Entered',
            'TP': 'Exited',
            'SL': 'Exited',
        }
        self.trade_influx = InfluxDBClient(host='127.0.0.1', port=8086, database='trades')

    def calc_trade_needed(self):
        #trade_to_make = self.position - self.monitor_parent.main_strat.open_positions[self.stk]
        trade_to_make = self.position
        print(f"{self.stk} || CURRENT STATE {self.monitor_parent.main_strat.open_positions[self.stk]} \n"
              f"{self.stk} || NEEDED STATE {self.position} \n"
              f"{self.stk} || TRADE TO MAKE {trade_to_make} \n"
              f"{self.stk} || LOT SIZE IS {lot_map[self.monitor_parent.strat_config[self.stk]['symbol']]}")
        if self.signal == 1:
            return abs(trade_to_make), 'BUY'
        else:
            return abs(trade_to_make), 'SELL'
        # if trade_to_make < 0:
        #     return abs(trade_to_make), 'SELL'
        # else:
        #     return abs(trade_to_make), 'BUY'

    def run(self):
        self.trade_function_map[self.exec_type]()

    def place_market_order(self):
        trade_quantity, trade_signal = self.calc_trade_needed()
        
        change_order = Order(trade_signal, self.exec_type, trade_quantity)   #where action is trade_signal, order_type is 'MKT' and quantity is trade_quantity
        change_order.lmt_price = self.price_at_trigger
        order_time = datetime.now()
        print(f"{Style.BRIGHT}{Back.WHITE}{Fore.RED} Placing order at {order_time.strftime('%Y-%m-%d %H:%M:%S.%f')} .. {Style.RESET_ALL}")

        
        self.order_ids['ENTRY_MKT'] = self.trade_app.place_new_order(
            contract=self.monitor_parent.main_strat.broker_contracts[self.stk], 
            order=change_order)
        print(f"Placed order {self.order_ids['ENTRY_MKT']}")
        time.sleep(15)
        order_details = self.monitor_parent.app.orders[self.order_ids['ENTRY_MKT']]
        
        print(f"Order details ==== {order_details}")
        if order_details.status == 'rejected':
            print('rejected')
            f_data = {self.stk: {
                'position': self.position,
                'avg_ cost': self.price_at_trigger,
            }}
            self.monitor_parent.main_strat.update_portfolio(forced_data=f_data)
        else:
            #print("Inside else loop")
            #self.trade_app.order_data_handler(order=change_order, order_id = self.order_ids['ENTRY_MKT'])
            #while self.trade_app.orders[self.order_ids['ENTRY_MKT']].remaining != 0:
            #   time.sleep(1)
            self.monitor_parent.main_strat.update_portfolio()

        # if self.monitor_parent.main_strat.write_to_influx:
        #     self.write_trade_to_influx(
        #         contract_traded=self.monitor_parent.main_strat.broker_contracts[self.stk],
        #         order_executed=change_order,
        #         order_id=self.order_ids['ENTRY_MKT'],
        #         order_time=order_time,
        #     )
        self.monitor_parent.trade_callback(self.stk, {'ENTRY_MKT': self.order_ids['ENTRY_MKT']},
                                           whisper=self.desc_whisper_map[self.order_desc])


    def write_trade_to_influx(self, contract_traded, order_executed, order_id, order_time):
        if self.trade_app.orders[self.order_ids['MKT']].cumulative_quantity == order_executed.totalQuantity:
            print('Fully executed... Everything matched...')
        else:
            print('Something not tallied up...')
        influx_trade_data = [
            {
                'measurement': self.influx_strategy,
                'tags': {
                    'symbol': contract_traded.symbol,
                    'action': order_executed.action,
                    'order_type': order_executed.orderType,
                    'order_desc': self.order_desc,
                    'sec_type': contract_traded.secType,
                    'exchange': contract_traded.exchange,
                    'currency': contract_traded.currency,
                    # 'account_no': str(self.monitor_parent.main_strat.trade_port),
                    'account_no': 'main account',
                    'strategy_version': self.monitor_parent.main_strat.strategy_version
                },
                'time': order_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'fields': {
                    'total_quantity': int(order_executed.totalQuantity),
                    'total_lots': int(
                        order_executed.totalQuantity / lot_map[self.monitor_parent.strat_config[self.stk]['symbol']]),
                    'price_at_trigger': float(self.price_at_trigger),
                    'commission': float(self.trade_app.orders[order_id].commissions),
                    'realized_pnl': float(self.trade_app.orders[order_id].realized_pnl),
                    'avg_trade_price': float(self.trade_app.orders[order_id].avg_total_price),
                    'avg_fill_price': float(self.trade_app.orders[order_id].avg_fill_price)
                }
            }
        ]
        self.trade_influx.write_points(influx_trade_data)
        self.trade_influx.close()
        # del trade_influx