  
import sys
import basic

if __name__ == '__main__':
    strategy = basic.TechnicalFilters(
        config_file_name='sample',  # =sys.argv[1]
        broker_type='IB',  # =sys.argv[2]
        api_key='127.0.0.1',  # =sys.argv[3]
        token='7497:67',  # =sys.argv[4]
        kafka_bootstrap_servers='127.0.0.1:9092',  # =sys.argv[5]
        management_topic='managementTopic',  # =sys.argv[6]
        broadcast_topic='broadcastTopic',  # =sys.argv[7]
        # paper=sys.argv[8],
        # sub_broker_config=sys.argv[9],
        # datasource_type=sys.argv[8],
        # datasource_user=sys.argv[9],
        # datasource_password=sys.argv[10],
        # paper_flag=sys.argv[11],
        # sub_broker_config=sys.argv[12]
    )
    # try:
    #     strategy.influx_strategy = sys.argv[13]
    # except (KeyError, IndexError):
    #     strategy.influx_strategy = 'basic'
    # try:
    #     strategy.strategy_version = sys.argv[14]
    # except (KeyError, IndexError):
    #     strategy.strategy_version = '1'
    strategy.start()