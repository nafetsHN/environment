import sys
sys.path.append('../')

import os
import logging
import logging.config
from decimal import Decimal, getcontext

try:
    import Queue as queue
except ImportError:
    import queue

import threading
import time

from settings import WORKING_DIR, EQUITY, DOMAIN, BASE_CURRENCY, ACCESS_TOKEN, ACCOUNT_ID
from execution.execution import OANDAExecutionHandler
from portfolio.portfolio import Portfolio
from strategy.strategy import TestStrategy
from data.streaming import StreamingForexPrices

def trade(events, strategy, portfolio, execution, heartbeat):
    """
    Carries out an infinite while loop that pools the events queue and directs
    each event to either the strategy component or the execution handler. The
    loop will then pause for "heartbeat" seconds and continue.
    """
    
    while True:
        try:
            event = events.get(False)
        except queue.Empty:
            pass
        else:
            if event is not None and event.type == 'TICK':
                print("TICK")
                logger.info("Received new TICK event: %s" % event)
                strategy.calculate_signals(event)
                portfolio.update_portfolio(event)
            elif event.type == 'SIGNAL':
                print("SIGNAL")
                logger.info("Received new SIGNAL event: %s" % event)
                portfolio.execute_signal(event)
            elif event.type == 'ORDER':
                print("ORDER")
                logger.info("Received new ORDER event: %s" % event)
                execution.execute_order(event)
        time.sleep(heartbeat)
        
if __name__ == '__main__':
    """
    For logger to work restart the python kernel before each run!
    """
    
    # Set up a workgin directory
    os.chdir(WORKING_DIR)

    # Set up logging
    logging.config.fileConfig('logging.conf')
    logger = logging.getLogger('logger_tradingLayer.trading.trading') # check this
    
    # Set the number of decimal palces to 2
    getcontext().prec = 2
    
    heartbeat = 1 # Time in seconds between pooling
    events = queue.Queue()
    equity = EQUITY
    
    # Pairs to include in streaming data set
    pairs = ["GBPUSD"] # ["EURUSD", "GBPUSD"]
    # if EURUSD is used we need to have another stream GBPUSD for 
    # home currency information. Test this after GBPUSD
    
    # Create the OADNA market price streaming class
    # making sure to provide authentication commands
    #print('before streaming prices')
    prices = StreamingForexPrices(domain=DOMAIN, 
                                  access_token=ACCESS_TOKEN,
                                  account_id=ACCOUNT_ID, 
                                  pairs=pairs, 
                                  events_queue=events)
    #print('after streaming prices')
    
    # Crete the strategy/signal generator, passing the instrument and the 
    # event queue
    strategy = TestStrategy(pairs, events)
        
    # Create the portfolio objet that will be used to compare the OANDA
    # positions with the local, to ensure backtesting integirty
    portfolio = Portfolio(ticker=prices, 
                          events=events,
                          equity=equity, 
                          risk_per_trade=Decimal("0.02"),
                          home_currency=BASE_CURRENCY,
                          leverage=20,
                          backtest=False)
    
    # Create the execution handler making sure to provide authentication
    # commands
    execution = OANDAExecutionHandler(domain=DOMAIN, 
                                      access_token=ACCESS_TOKEN,
                                      account_id=ACCOUNT_ID)
    
    # Create two seperate threads: One for the trading loop and another for 
    # the market price streaming class
    trade_thread = threading.Thread(target=trade, args=[events, 
                                                        strategy,
                                                        portfolio,
                                                        execution,
                                                        heartbeat])
    price_thread = threading.Thread(target=prices.stream_to_queue, args=[])
    
    # Start both threads
    logger.info("Starting trading thread")
    trade_thread.start()
    logger.info("Starting price streaming thread")
    price_thread.start()
    
    