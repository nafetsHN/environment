import sys
sys.path.append('../')

from abc import ABCMeta, abstractmethod
# https://www.python-course.eu/python3_abstract_classes.php
import logging

import oandapyV20
from oandapyV20 import API
import oandapyV20.endpoints.orders as orders
from oandapyV20.contrib.requests import MarketOrderRequest


class ExecutionHandler(object):
    """
    Provides an abstract base class to handle all execution in the backtesting
    and live trading system.
    """
    
    __metaclass__ = ABCMeta
    
    @abstractmethod
    def execute_order(self):
        """
        Send the order to the brokerage
        """
        raise NotImplementedError("Should implement execute_order()")
        
class SimulatedExecution(object):
    """
    Provides a simulated execution handling environment. This class actually
    does nothing - it simply receives and order to execute.
    
    Instead, the Portfolio object actually provides fill handling. This will 
    be modified in later versions.
    """
    
    def execute_order(self, event):
        pass
    
class OANDAExecutionHandler(ExecutionHandler):
    
    def __init__(self, domain, access_token, account_id):
        self.domain = domain
        self.access_token = access_token
        self.account_id = account_id
        self.client = self.create_OADAN_client()
        self.logger = logging.getLogger(__name__)
        
        
    def create_OADAN_client(self):
        return API(self.access_token)
        
    
    def execute_order(self, event):
        instrument = "%s_%s" % (event.instrument[:3], event.instrument[3:])
        units = event.units
        
        client = self.client()
        #Market order
        mo = MarketOrderRequest(instrument=instrument, units=units)
        # Create order request
        request = orders.OrderCreate(self.account_id, data=mo.data)
        # perform the request
        rv = client.request(request)
        self.logger.debug(rv)
        