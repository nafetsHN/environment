"""

Defines classes for all event types that will be sent to queue and used to
activate different scripts and functions.

Event types:
    Tick:   event between two queue requests with no signal or order
    Signal: event created by trading strategy # check?
    Order:  event to place a order to Oanda 
    
"""
import sys
sys.path.append('../')

class Event(object):
    pass

class TickEvent(Event):
    def __init__(self, instrument, time, bid, ask):
        self.type = 'TICK'
        self.instrument = instrument
        self.time = time
        self.bid = bid
        self.ask = ask
        
    def __str__(self):
        return ("Type: {}, Instrument: {}, Time: {}, Bid: {}, Ask: {}".format(
                str(self.type), str(self.instrument), str(self.time),
                str(self.bid), str(self.ask)))
        
    def __repr__(self):
        return str(self)
    
class SignalEvent(Event):
    def __init__(self, instrument, order_type, side, time):
        self.type = 'SIGNAL'
        self.instrument = instrument
        self.order_type = order_type
        self.side = side
        self.time = time # Time of the last tick that generated the signal
        
    def __str__(self):
        return ("Type: {}, Instrument: {}, Order Type: {}, Side: {}, Time: {}".format(
                str(self.type), str(self.instrument), str(self.order_type),
                str(self.side), str(self.time)))
    
    def __repr__(self):
        return str(self)
    
class OrderEvent(Event):
    def __init__(self, instrument, units, order_type, side):
        self.type = 'ORDER'
        self.instrument = instrument
        self.units = units
        self.order_type = order_type
        self.side = side
        
    def __str__(self):
        return ("Type: {}, Instrument: {}, Units: {}, Order Type: {}, Side: {}".format(
                str(self.type), str(self.instrument), str(self.units),
                str(self.order_type), str(self.side)))
        
    def __repr__(self):
        return str(self)