import sys
sys.path.append('../')

from backtest.backtest import Backtest
from execution.execution import SimulatedExecution
from portfolio.portfolio import Portfolio
from settings import EQUITY
from strategy.strategy import TestStrategy, MovingAverageCrossStrategy
from data.price import HistoricCSVPriceHandler

if __name__ == '__main__':
    # Trade on GBPUSD
    pairs = ["GBPUSD"] # or ["GBPUSD","EURUSD"]
    # Specify straregy to use
    strategy = 'test'
    
    if strategy =='test':
        strategy = TestStrategy
        # Create the strategy parameters for the TestStrategy
        strategy_params = {}
    elif strategy =='ma':  
        strategy = MovingAverageCrossStrategy
        # Create the strategy parameters for the MovingAverageCrossStrategy
        strategy_params = {
            "short_window": 500,
            "long_window": 2000
            }
    
    # Create and execute the backtest
    backtest = Backtest(
            pairs, HistoricCSVPriceHandler,
            strategy, strategy_params,
            Portfolio, SimulatedExecution,
            equity = EQUITY,
            heartbeat= 0.0,
            max_iters = 100000)
    
    
    backtest.simualte_trading()