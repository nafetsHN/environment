"""

Streaming using OANDA REST V20.

"""
import sys
sys.path.append('../')

from decimal import Decimal, getcontext, ROUND_HALF_DOWN
import logging
import json

import requests
from requests.exceptions import ConnectionError

from event.event import TickEvent
from data.price import PriceHandler

import oandapyV20
from oandapyV20 import API
from oandapyV20.exceptions import V20Error, StreamTerminated
from oandapyV20.endpoints.pricing import PricingStream



class StreamingForexPrices(PriceHandler):
    def __init__(self, domain, access_token, account_id, pairs, events_queue):
        self.domain = domain
        self.access_token = access_token
        self.account_id = account_id
        self.pairs = pairs
        self.events_queue = events_queue
        self.prices = self._set_up_prices_dict() # inherited from PriceHandler
        self.logger = logging.getLogger(__name__)
        
    def invert_prices(self, pair, bid, ask):
        """
        Simply inverts the prices for a particular currency pair.
        This will turn the bid/ask of "GBPUSD" into bid/ask for
        "USDGBP" and palce them in the prices dictionary.
        """
        getcontext().rounding = ROUND_HALF_DOWN
        inv_pair = "%s%s" % (pair[3:], pair[:3])
        inv_bid = (Decimal("1.0")/bid).quantize(Decimal("0.00001"))
        inv_ask = (Decimal("1.0")/ask).quantize(Decimal("0.00001"))
        return inv_pair, inv_bid, inv_ask
    
    def connect_to_stream(self):
        """
        Converts CCY pair to OANDA style pair.
        Creates OADAN V20 API.
        Raises PricingStream request
        
        Output: 
            client.request(request)
        """
        pairs_oanda = ["%s_%s" % (p[:3], p[3:]) for p in self.pairs]
        pairs_list = ','.join(pairs_oanda)
        params = {"instruments": pairs_list}
        client = API(access_token=self.access_token, environment=self.domain)
        request = PricingStream(accountID=self.account_id, params=params)
        return client.request(request)
    
    def stream_to_queue(self):
        """
        Receives responce from OANDA request. Checks if 'instrument' or 'tick'
        are in msg. If true, collect instrument, time, bid and ask price for 
        pair and for inverted pair (e.g. for EUR_USD and USD_EUR).
        
        Also, logg any msg and any error that might occure when connecting to
        the stream.
        """
        response = self.connect_to_stream()
        # TODO: figure out how to get request.status_code and check if = 200
        #if response.status_code != 200:
        #    print("Status_code: {}".format(response.status_code))
        #   return
        try:
            for msg in response:
                if 'instrument' in msg or 'tick' in msg:
                    print(msg)
                    self.logger.debug(msg)
                    getcontext().rounding = ROUND_HALF_DOWN
                    instrument = msg['instrument'].replace("_","")
                    time = msg['time']
                    bid = Decimal(str(msg['bids'][0]['price'])).quantize(
                            Decimal("0.00001"))
                    ask = Decimal(str(msg['asks'][0]['price'])).quantize(
                            Decimal("0.00001"))
                    print("Bid: %s, Ask: %s" % (bid, ask))
                    self.prices[instrument]['bid'] = bid
                    self.prices[instrument]['ask'] = ask
                    # Invert the prices (GBP_USD -> USD_GBP)
                    inv_pair, inv_bid, inv_ask = self.invert_prices(instrument, bid, ask)
                    self.prices[inv_pair]['bid'] = inv_bid
                    self.prices[inv_pair]['ask'] = inv_ask
                    self.prices[inv_pair]['time'] = time
                    
                    tick_event = TickEvent(instrument, time, bid, ask)
                    self.events_queue.put(tick_event)
                else:
                    print(msg['type'])
                                    
        except V20Error as e:
            # catch API related errors that may occur
            self.logger.error(str(e))
        except ConnectionError as e:
            self.logger.error(str(e))
        except StreamTerminated as e:
            self.logger.error(str(e))
        except Exception as e:
            self.logger.error('Unidentified connection error: '.format(str(e))) 
            
