#!/usr/bin/python
"""simple kdj strategy"""
import common.bill as bl
import utils.indicator as ic
from strategy.strategy import Strategy


class KDJStrategy(Strategy):
    """ simple KDJ stragegy"""

    def __init__(self, strategy_config, engine):
        super().__init__(strategy_config, engine)
        self.kline = strategy_config["kline"]
        self.offset = strategy_config["kdj_offset"]


    def check(self, symbol):
        """ kdj指标，金叉全买入，下降趋势部分卖出，死叉全卖出 """
        klines = self.engine.md.get_klines(
            symbol, self.kline["interval"], self.kline["size"]
        )
        self.cur_price = float(klines[-1][self.closeindex])

        kdj_arr = ic.py_kdj(klines, self.highindex, self.lowindex, self.closeindex)

        cur_k = kdj_arr[-1][1]
        cur_d = kdj_arr[-1][2]
        cur_j = kdj_arr[-1][3]

        signal_info = (
            "(%6.2f, %6.2f) j(%6.2f) k(%6.2f) d(%6.2f)"
            % (
                cur_j - cur_k,
                cur_k - cur_d,
                cur_j,
                cur_k,
                cur_d,
            )
        )

        offset = self.offset[0]
        if cur_j - offset > cur_k > cur_d + offset:
            # 金叉
            return bl.open_long_bill(1, "买：", signal_info)

        elif cur_j + offset < cur_k < cur_d - offset:
            # 死叉
            return bl.close_long_bill(0, "卖：", signal_info)


        return None


    def on_tick(self):
        """ tick处理接口 """
        symbol = self.config["symbol"]
        # 之前的挂单全撤掉
        self.engine.cancle_orders(symbol)

        check_signals = []
        signal = self.check(symbol)
        if signal:
            check_signals.append(signal)
        position_info = self.engine.get_position(symbol, self.cur_price)
        self.engine.handle_order(symbol, position_info, self.cur_price, check_signals)
