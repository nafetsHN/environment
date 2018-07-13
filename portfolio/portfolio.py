import sys
sys.path.append('../')

import os
import pandas as pd
import logging
from copy import deepcopy
from decimal import Decimal

from settings import BASE_CURRENCY, EQUITY, OUTPUT_RESULT_DIR
from portfolio.position import Position
from performance.performance import create_drawdowns
from event.event import OrderEvent

# TODO:
#   1. Currently leverage is not used. Implement it
class Portfolio(object):
    def __init__(self, ticker, events, equity= EQUITY, 
                 risk_per_trade=Decimal("0.02"), home_currency=BASE_CURRENCY, 
                 leverage=20, backtest=True):
        self.ticker = ticker
        self.events = events
        self.equity = equity
        self.balance = deepcopy(self.equity)
        self.risk_per_trade = risk_per_trade
        self.home_currency = home_currency
        self.leverage = leverage
        self.positions = {}
        self.trade_units = self.calc_risk_position_size()
        self.backtest = backtest
        if self.backtest:
            self.backtest_file = self.create_equity_file()
        self.logger = logging.getLogger(__name__)
        
    def calc_risk_position_size(self):
        # TODO: check if we need to round it down to integer
        return int(self.equity * self.risk_per_trade)
    
    def add_new_position(self, position_type, currency_pair, units, ticker):
        ps = Position(self.home_currency, position_type, 
                      currency_pair, units, ticker)
        self.positions[currency_pair] = ps
    
    def add_position_units(self, currency_pair, units):
        if currency_pair not in self.positions:
            return False
        else:
            ps = self.positions[currency_pair]
            ps.add_units(units)
            return True
    
    def remove_position_units(self, currency_pair, units):
        if currency_pair not in self.positions:
            return False
        else:
            ps = self.positions[currency_pair]
            pnl = ps.remove_units(units)
            self.balance += pnl
            return True
    
    def close_position(self, currency_pair):
        if currency_pair not in self.positions:
            return False
        else:
            ps = self.positions[currency_pair]
            pnl = ps.close_position()
            self.balance += pnl
            del[self.positions[currency_pair]]
            return True
    
    #TODO: 
    #   1. check if created files are overitten when performing multiple backtests 
    #   2. maybe add numbering to file name or keep the last 5 files or so?
    def create_equity_file(self):
        """
        Create output file: backtest.csv
        
        """
        filename = 'backtest.csv'
        out_file = open(os.path.join(OUTPUT_RESULT_DIR, filename), 'w')
        header = "Timestamp,Balance"
        for pair in self.ticker.pairs:
            header += ",%s,%s,%s" % (pair,
                                     pair + "_PositionType", 
                                     pair + "_Units")
        header += "\n"
        out_file.write(header)
        if self.backtest:
            print(header)
        return out_file
    
    def output_results(self):
        # Closes off the Backteste.csv file so it can be read via Pandas 
        # without the problems
        self.backtest_file.close()
        
        in_filename = 'backtest.csv'
        out_filename = 'equity.csv'
        in_file = os.path.join(OUTPUT_RESULT_DIR, in_filename)
        out_file = os.path.join(OUTPUT_RESULT_DIR, out_filename)
        
        # Create equity curve dataframe
        df = pd.read_csv(in_file, index_col=0)
        df.dropna(inplace=True)
        df["Total"] = df.sum(axis=1) # what value are we summing from backtest.csv?
        df["Returns"] = df["Total"].pct_change()
        df["Equity"] = (1.0 + df["Returns"]).cumprod()
        
        # Create drawdown statistics
        drawdown, max_dd, dd_duration = create_drawdowns(df["Equity"]) # input needs to be pnl
        df['Drawdown'] = drawdown
        df.to_csv(out_file, index=True)
        
        print("Simulation compelte and results exported to %s" % out_filename)
    
    def update_portfolio(self, tick_event):
        """
        This updates all positions ensuring an up to date unrealised profit
        and loss (PnL)
        """
        currency_pair = tick_event.instrument
        if currency_pair in self.positions:
            #print("self.positions: %s" % self.positions)
            ps = self.positions[currency_pair]
            # perform the price update
            ps.update_position_price()
        if self.backtest:
            #print("self.positions: %s" % self.positions)
            out_line = "%s,%s" % (tick_event.time, self.balance)
            for pair in self.ticker.pairs:
                if pair in self.positions:
                    
                    out_line += ",%s, %s, %s" % (self.positions[pair].profit_base,
                                                 self.positions[pair].position_type,
                                                 self.positions[pair].units)
                    print(out_line)
                else:
                    out_line += ",0.00, 0.00, 0.00"
            out_line += "\n"
            self.backtest_file.write(out_line)
                
            
    # TODO:
    # 1. Fix placing orders to OADNA - comments below
    def _execute_signal(self, signal_event):
        print(signal_event)
        # Check that the price ticker contians all necessary currency pairs
        # prior to executing an order
        execute = True
        tp = self.ticker.prices
        #print("Ticker.prices: ", self.ticker.prices)
        for pair in tp:
            if tp[pair]['ask'] is None or tp[pair]['bid'] is None:
                execute = False
                print("ERROR: Pair[ask] and pair[bid] are equal to None so execute = False. \
                      Check ask and bid prices!!!")
            
        # All necessary pricing data is available so we can execute
        if execute:
            side = signal_event.side
            currency_pair = signal_event.instrument
            # number of units for a new trade
            units = int(self.trade_units)
            #time = signal_event.time # not used
            
            # If there is no position, create one
            if currency_pair not in self.positions:
                if side == "buy":
                    position_type = "long"
                elif side == "sell":
                    position_type = "short"
                self.add_new_position(
                        position_type, currency_pair,
                        units, self.ticker)
                
            # If a position exists add or remove units
            else:
                ps = self.positions[currency_pair]
                # side = whether to by or sell; position_type = existing units 
                # e.g. next line means that we are going long x units 
                # while up to this point we were already long
                if side == 'buy' and ps.position_type == 'long':
                    self.add_position_units(currency_pair, units)
                    # Order: long units
                    order = OrderEvent(currency_pair, units, "market", side)
                    self.events.put(order)
                
                elif side == 'buy' and ps.position_type == 'short':
                    if units == ps.units:
                        self.close_position(currency_pair)
                        # Order: since we are short, and untis = existing units
                        # "close the tarde" by go long for units
                        order = OrderEvent(currency_pair, units, "market", side)
                        self.events.put(order)
                        # correct way is to use TradeClose that request tradeID
                        # of the trade we are trying to close, this might be hard
                        # to track
                        # https://oanda-api-v20.readthedocs.io/en/latest/contrib/orders/tradecloserequest.html
                    elif units < ps.units:
                        self.close_position(currency_pair)
                        # Order: since we are short and units < existing units,
                        # buy long units 
                        self.add_new_position('long', currency_pair,
                                              units - ps.units, self.ticker)
                        order = OrderEvent(currency_pair, units, "market", side)
                        self.events.put(order)
                    elif units > ps.untis:
                        self.remove_position_units(currency_pair, units)
                        # Order: we are short and units > existing units
                        # "close short positions" by buyng unit long positions
                        order = OrderEvent(currency_pair, units, "market", side)
                        self.events.put(order)
                        # Again this is not correct, ideally we would close the
                        # existing short trade using TradeClose and then open
                
                # we are selling units while we are already long ps.units
                elif side == 'sell' and ps.position_type == 'long':
                    print("Sell/Long")
                    if units == ps.units:
                        self.close_position(currency_pair)
                        # Order: sell units
                        order = OrderEvent(currency_pair, -units, "market", side)
                        self.events.put(order)
                        # Not correct, should use TradeClose
                    elif units < ps.units:
                        self.remove_position_units(currency_pair, units)
                        # Order: sell some of the existing long units
                        order = OrderEvent(currency_pair, -units, "market", side)
                        self.events.put(order)
                        # Correct implementation:
                        # Reduce the number of units in existing trade? 
                    elif units > ps.units:
                        self.close_position(currency_pair)
                        self.add_new_position('short', currency_pair, 
                                              units - ps.units, self.ticker)
                        # Order: sell units
                        order = OrderEvent(currency_pair, -units, "market", side)
                        self.events.put(order)
                        # COrrect: TradeClose + open new trade for units - ps.units
                
                elif side =='sell' and ps.position_type == 'short':
                    print("Sell/Short")
                    self.add_position_units(currency_pair, units)
                    order = OrderEvent(currency_pair, -units, "market", side)
                    self.events.put(order)
            
            # Create market order event
            #order = OrderEvent(currency_pair, units, "market", side)
            # BUG - if we define order here there is no diff between buy 
            # and sell orders. FIX: generate OrderEvent above in each step
            #self.events.put(order) 
            
            
            
            self.logger.info("Portfolio Balance: %s" % self.balance)
        else:
            self.logger.info("Unable to execute order as price data was insufficient")
            
    # temporary function until you fix the _execute_signal function
    def execute_signal(self, signal_event):
        print(signal_event)

        execute = True
        tp = self.ticker.prices
        for pair in tp:
            if tp[pair]['ask'] is None or tp[pair]['bid'] is None:
                execute = False
                print("ERROR: Pair[ask] and pair[bid] are equal to None so execute = False. \
                      Check ask and bid prices!!!")
            
        if execute:
            side = signal_event.side
            currency_pair = signal_event.instrument
            units = int(self.trade_units)

            if currency_pair not in self.positions:
                if side == "buy":
                    position_type = "long"
                elif side == "sell":
                    position_type = "short"
                self.add_new_position(
                        position_type, currency_pair,
                        units, self.ticker)
                
            else:
                ps = self.positions[currency_pair]

                if side == 'buy' and ps.position_type == 'long':
                    self.add_position_units(currency_pair, units)
                    # Create market order event
                
                elif side == "sell" and ps.position_type == "long":
                    if units == ps.units:
                        self.close_position(currency_pair)
                    elif units < ps.units:
                        pass
                    elif units > ps.units:
                        pass
                
                elif side =="buy" and ps.position_type == "short":
                    if units == ps.units:
                        self.close_position(currency_pair)
                    elif units < ps.units:
                        pass
                    elif units > ps.units:
                        pass
                
                elif side == "sell" and ps.position_type == "short":
                    self.add_position_units(currency_pair, units)
            
            if side == "sell":
                units = -units
            
            order = OrderEvent(currency_pair, units, "market", side)
            self.events.put(order)
                

            self.logger.info("Portfolio Balance: %s" % self.balance)
        else:
            self.logger.info("Unable to execute order as price data was insufficient")
    