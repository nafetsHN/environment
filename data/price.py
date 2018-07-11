import sys
sys.path.append('../')

import os
import re
import pandas as pd
from decimal import Decimal, getcontext, ROUND_HALF_DOWN

import settings
from event.event import TickEvent

class PriceHandler(object):
    """
    PriceHandler is an abstract base class providing an interface for 
    all subsequent (inherited) data handlers (both live and historic).
    
    The goal of a (derived) PriceHandler object is to output a set of
    bid/ask/timestamp 'ticks' for each curreny pair and palce them into
    an event queue.
    
    This will replicate how a live strategy would function as current
    tick data would be streamed via brokerage. Thus a historic and live
    system will be treated identically by the rest of the backtesting 
    suite.
    """
    
    def _set_up_prices_dict(self):
        """
        Due to the way that the Position  object handles P&L
        calculation, it is necessary to include values for not
        only base/quote currencies but also their reciprocals.
        This means that this class will contain kets for, e.g.
        "GBP_USD" and "USD_GBP"
        
        At this stage they are calculated in an ad-hoc manner,
        but a future TODO is to modify the following code to 
        be more robust and straightforward to follow.
        """
        # example:
        # self.prices[instrument]['bid'] = bid
        # self.prices['EUR_USD]['bid'] = 1.12
        prices_dict = dict(
                (pair, values) for pair, values in [
                        (p, {'bid':None,'ask':None,'time':None}) 
                        for p in self.pairs]
                )
        inv_prices_dict = dict(
                (pair, values) for pair, values in[
                        ("%s%s" % (p[3:], p[:3]), {"bid":None, "ask":None, "time":None})
                        for p in self.pairs]
                )
        
        prices_dict.update(inv_prices_dict) # ???? why?
        return prices_dict
        
    def invert_prices(self, pair, bid, ask):
        """
        Invert the prices for a particular currency pair. This will turn
        bid/ask of 'GBPUSD' into bid/ask for 'USDGBP' and place them in
        the prices dicrionary.
        """
        getcontext().rounding = ROUND_HALF_DOWN
        # inv_pair = "%s_%s" % (pair[3:], pair[:3]) - original code with '_' - CONFIRM THAT THIS IS WRONG!!!
        inv_pair = "%s%s" % (pair[3:], pair[:3])
        inv_bid = (Decimal('1.0')/bid).quantize(Decimal('0.00001'))
        inv_ask = (Decimal('1.0')/ask).quantize(Decimal('0.00001'))
        
        return inv_pair, inv_bid, inv_ask
    
class HistoricCSVPriceHandler(PriceHandler):
    """
    HistoricCSVPriceHandler is designed to read CSV files of tick data for
    each requested currency pair and stream those to the provided events 
    queue.
    """
    
    def __init__(self, pairs, events_queue, csv_dir):
        """
        Initialises the historic data handelr by requesting the location of
        the CSV files and a list of symbols.
        
        It's assumed that all files are of the form 'pair_YYYYMMDD.csv', 
        whenre 'pair' is the currency pair. For GBPUSD the file name is 
        GBPUSD_20180706.csv
        
        Args:
            pairs: the list of currency pairs to obtain
            events_queue: the events queue to send the ticks to
            csv_dir: absolute directory path to the CSV files
        """
        self.pairs = pairs
        self.csv_dir = csv_dir
        # prices structure -> self.prices[instrument]['bid']
        self.prices = self._set_up_prices_dict()
        self.pair_frames = {}
        # date container for all available CSV files
        self.file_dates = self._list_all_file_dates()
        # index of CSV date that is currently used
        self.cur_date_idx = 0
        # data container that combines data of all CCY pairs on current date
        self.cur_date_pairs = self._open_convert_csv_files_for_day(
                self.file_dates[self.cur_date_idx])
        # Flag that signals backtesting function to stop. It's set to True when
        # we run out of historical data.
        self.continue_backtest = True
        self.events_queue = events_queue
      
    def _list_all_csv_files(self):
        files = os.listdir(settings.CSV_DATA_DIR)
        # pattert to recognize files named as: EURUSD_20180706.csv
        pattern = re.compile("[A-Z]{6}_\d{8}.csv")
        matching_files = [f for f in files if pattern.search(f)]
        matching_files.sort()
        return matching_files
    
    def _list_all_file_dates(self):
        """
        Removes the pair, underscore and '.csv' from the dates and eliminates
        duplicates. Returns a list of date strings of the form YYYYMMDD
        """
        csv_files = self._list_all_csv_files()
        de_dup_csv = list(set(d[7:-4] for d in csv_files))
        de_dup_csv.sort()
        return de_dup_csv
    
    def _open_convert_csv_files_for_day(self, date_str):
        """
        Opens the CSV files from the data directory, converting them into
        pandas DataFrame within a pairs dictionary.
        
        The function then concatenates all of the seperate pairs for a single
        day into a single data frame that is time orderd, allowing tick data
        events to be added to the queie in a chronological fashion.
        """
        for p in self.pairs:
            pairs_path = os.path.join(self.csv_dir, "%s_%s.csv" % (p, date_str))
            self.pair_frames[p] = pd.read_csv(
                    pairs_path, header=None, index_col=0, parse_dates=True,
                    dayfirst=True,
                    names=("Time", "Bid", "Ask", "BidVolume", "AskVolume")) # BIdVolume and AskVolume?!
            # since first column is Time and index_col is set to 0
            # index column will be Time  
            self.pair_frames[p]['Pair'] = p
            #print(self.pair_frames)
            #tmp = pd.concat(self.pair_frames.values())
            #print(tmp)
        return pd.concat(self.pair_frames.values()).sort_index().iterrows() 
    # original code was:
    # pd.concat(self.pair_frames.values()).sort_index().iterrows()
    # the sort() was depreciated for DataFrame in favor of sort_value() and 
    # sort_index()
    # I've assumed the sorting needs to be done on Time level so i've used
    # sort_index() - CONFIRM THIS!
    
    def _update_csv_for_day(self):
        """
        Function that adds CCY pairs data to data container for next date.
        If date is not available returns False. 
        """
        try:
            # go to the next date in a list of CVS file dates
            next_date = self.file_dates[self.cur_date_idx+1]
        except IndexError: 
            # There is no CSV file with next date
            return False
        # execute if try clause does not raise an exception
        else:
            self.cur_date_pairs = self._open_convert_csv_files_for_day(next_date)
            self.cur_date_idx += 1
            return True
        
    def stream_next_tick(self):
        """
        The Backtester is run on single thread in order to fully reproduce
        results on each run. This means that the stream_to_queue method is
        replaced by stream_next_tick.
        
        This method is called by the ebacktesting function outside of this
        class and places a single tick onto the queue, as well as updating 
        the current bid/ask and inverse bid/ask.
        """
        try:
            # index = Time, we have rows since we used .iterrows() to create 
            # the container
            index, row = next(self.cur_date_pairs)
        except StopIteration:
            # End of the current days date
            if self._update_csv_for_day():
                index, row = next(self.cur_date_pairs)
            else: # End of the data
                self.continue_backtest = False
                print("Continue Backtest: False. End of available historical data")
                return
            
        getcontext().rounding = ROUND_HALF_DOWN
        # TODO:
        # how to set this for whole class so i dont have to re-specified it 
        # in every function? - is it simpel as doing:
        # getcontext().rounding = ROUND_HALF_DOWN in def __init__() ?
        
        pair = row['Pair']
        bid = Decimal(str(row['Bid'])).quantize(
                Decimal("0.00001"))
        ask = Decimal(str(row['Ask'])).quantize(
                Decimal("0.00001"))

        # Create decimalised prices for traded pair
        # self.prices[instrument]['bid'] = bid
        self.prices[pair]['bid'] = bid
        self.prices[pair]['ask'] = ask
        self.prices[pair]['time'] = index # index = Time of a data row
        
        # Create decimalised prices for inverted pair
        inv_pair, inv_bid, inv_ask = self.invert_prices(pair, bid, ask)
        #print("Pair: %s, Bid: %s, Ask: %s" %(pair, bid, ask))
        #print("Inv_pair: %s, Inv_bid: %s, Inv_ask: %s" %(inv_pair, inv_bid, inv_ask))
        self.prices[inv_pair]['bid'] = inv_bid
        self.prices[inv_pair]['ask'] = inv_ask
        self.prices[inv_pair]['time'] = index # index = TIme of a data row
        
        #print("self.prices: ", self.prices)
        # Create the tick event for the queue
        tick_event = TickEvent(pair, index, bid, ask)
        self.events_queue.put(tick_event)
        
        
        
                    