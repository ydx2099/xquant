#!/usr/bin/python3
import sys
sys.path.append('../')
import argparse
from datetime import datetime
import uuid
import pprint
import utils.tools as ts
import common.xquant as xq
import common.log as log
from engine.backtest import BackTest
from common.overlap_studies import *
from db.mongodb import get_mongodb

BACKTEST_INSTANCES_COLLECTION_NAME = 'bt_instances'

bt_db = get_mongodb('backtest')

def run(args):
    if not (args.m and args.sc and args.r):
        exit(1)

    instance_id = datetime.now().strftime("%Y%m%d-%H%M%S_") + str(uuid.uuid1())  # 每次回测都是一个独立的实例
    print('instance_id: %s' % instance_id)

    config = xq.get_strategy_config(args.sc)

    module_name = config["module_name"].replace("/", ".")
    class_name = config["class_name"]

    symbol = config['symbol']
    time_range = args.r
    start_time, end_time = ts.parse_date_range(time_range)

    if args.log:
        logfilename = class_name + "_"+ symbol + "_" + time_range + "_" + instance_id + ".log"
        print(logfilename)
        log.init("backtest", logfilename)
        log.info("strategy name: %s;  config: %s" % (class_name, config))


    engine = BackTest(instance_id, args.m, config)
    strategy = ts.createInstance(module_name, class_name, config, engine)
    engine.run(strategy, start_time, end_time)
    engine.analyze(symbol, engine.orders)
    _id = bt_db.insert_one(
        BACKTEST_INSTANCES_COLLECTION_NAME,
        {
            "instance_id": instance_id,
            "start_time": start_time,
            "end_time": end_time,
            "orders": engine.orders,
            "mds": args.m,
            "sc": args.sc,
        },
    )

    if args.chart:
        engine.chart(symbol, start_time, end_time, args)


def get_instance(instance_id):
    if not (instance_id):
        exit(1)

    instances = bt_db.find(
        BACKTEST_INSTANCES_COLLECTION_NAME,
        {"instance_id": instance_id}
    )
    #print("instances: %s" % instances)
    if len(instances) <= 0:
        exit(1)
    instance = instances[0]
    return instance


def view(args):
    instance_id = args.sii
    instance = get_instance(instance_id)

    config = xq.get_strategy_config(instance['sc'])

    engine = BackTest(instance_id, instance['mds'], config)
    engine.view(config['symbol'], instance['orders'])


def analyze(args):
    instance_id = args.sii
    instance = get_instance(instance_id)
    print('marketing data src: %s  strategy config path: %s  ' % (instance['mds'], instance['sc']))

    config = xq.get_strategy_config(instance['sc'])
    pprint.pprint(config, indent=4)

    engine = BackTest(instance_id, instance['mds'], config)
    engine.analyze(config['symbol'], instance['orders'], args.rmk)


def chart(args):
    instance_id = args.sii
    instance = get_instance(instance_id)

    config = xq.get_strategy_config(instance['sc'])

    engine = BackTest(instance_id, instance['mds'], config)
    engine.md.tick_time = instance['end_time']
    engine.orders = instance['orders']
    engine.chart(config['symbol'], instance['start_time'], instance['end_time'], args)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='backtest')

    subparsers = parser.add_subparsers(help='sub-command help')

    """
    parser_run = subparsers.add_parser('run', help='run help')
    parser_run.add_argument('-m', help='market data source')
    parser_run.add_argument('-sc', help='strategy config')
    parser_run.add_argument('-r', help='time range (2018-7-1T8' + xq.time_range_split + '2018-8-1T8)')
    parser_run.add_argument('--cs', help='chart show', action="store_true")
    parser_run.add_argument('--log', help='log', action="store_true")
    add_argument_overlap_studies(parser_run)
    parser_run.set_defaults(func=run)
    """
    parser.add_argument('-m', help='market data source')
    parser.add_argument('-sc', help='strategy config')
    parser.add_argument('-r', help='time range (2018-7-1T8' + xq.time_range_split + '2018-8-1T8)')
    parser.add_argument('--chart', help='chart', action="store_true")
    parser.add_argument('--log', help='log', action="store_true")
    add_argument_overlap_studies(parser)

    parser_view = subparsers.add_parser('view', help='view help')
    parser_view.add_argument('-sii', help='strategy instance id')
    parser_view.set_defaults(func=view)

    parser_analyze = subparsers.add_parser('analyze', help='analyze help')
    parser_analyze.add_argument('-sii', help='strategy instance id')
    parser_analyze.add_argument('--rmk', help='remark', action="store_true")
    parser_analyze.set_defaults(func=analyze)

    parser_chart = subparsers.add_parser('chart', help='chart help')
    parser_chart.add_argument('-sii', help='strategy instance id')
    add_argument_overlap_studies(parser_chart)
    parser_chart.set_defaults(func=chart)

    args = parser.parse_args()
    # print(args)
    if hasattr(args, 'func'):
        args.func(args)
    else:
        #parser.print_help()
        run(args)
