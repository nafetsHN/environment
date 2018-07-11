import sys
sys.path.append('../')

import logging

try:
    import Queue as queue
except ImportError:
    import queue
    
import time

from settings import CSV_DATA_DIR


class Backtest(object):
    """
    Event driven back-test.
    """
    
    def __init__ (self, pairs, data_handler, strategy, strategy_params,
                  portfolio, execution, equity=100000.0, heartbeat=0.0,
                  max_iters = 100000):
        self.pairs = pairs
        self.events = queue.Queue()
        self.csv_dir = CSV_DATA_DIR
        self.ticker = data_handler(self.pairs, self.events, self.csv_dir)
        self.strategy_params = strategy_params
        self.strategy = strategy(
                self.pairs, self.events, **self.strategy_params)
        self.equity = equity
        self.heartbeat = heartbeat
        self.max_iters = max_iters
        self.portfolio = portfolio(self.ticker, self.events, equity=self.equity, 
                                  backtest=True)
        self.execution = execution()
        self.logger = logging.getLogger(__name__)
        
    def _run_backtest(self):
        """
        Caries out an infinite loop that pool the events queue and directs each
        event to either the strategy component or the execution handler. The 
        loop will then pause for 'heartbeat' seconds and continue until the 
        maximum number of iterations is exceeded.
        """
        self.logger.info("Running Backtest...")
        iters = 0
        while iters < self.max_iters and self.ticker.continue_backtest:
            try:
                event = self.events.get(False)
            except queue.Empty:
                self.ticker.stream_next_tick()
            else:
                if event is not None:
                    if event.type == 'TICK':
                        self.strategy.calculate_signals(event)
                        #print("Event sent to strategy: %s" % event)
                        self.portfolio.update_portfolio(event) # BUG: this doesn't work, check definition
                        #print("Portfolio update")
                    elif event.type == 'SIGNAL':
                        self.portfolio.execute_signal(event)
                        #print("Portfolio execute signal: %s" % event)
                    elif event.type == 'ORDER':
                        self.execution.execute_order(event)
                        #print("Execute order: %s" % event)
                        
            time.sleep(self.heartbeat)
            iters += 1
        
    
    def _output_performance(self):
        """
        Output the strategy performance from the backtest.
        """
        self.logger.info("Calculating Performance Metrics...")
        self.portfolio.output_results()
    
    def simualte_trading(self):
        """
        Simulates the backtest and outputs portfolio performance.
        """
        self._run_backtest()
        self._output_performance()
        self.logger.info("Backtest complete.")