import sys
sys.path.append('../')

from decimal import Decimal, getcontext, ROUND_HALF_DOWN


class Position(object):
    
    def __init__(self, home_currency, position_type, currency_pair, units, ticker):
        # Currency of our deposit at OADNA brockerage
        self.home_currency = home_currency
        self.position_type = position_type
        self.currency_pair = currency_pair
        self.units = units
        self.ticker = ticker
        self.profit_base = self.calculate_profit_base()
        self.profit_perc = self.calculate_profit_perc()
        
        
    def set_up_currencies(self): #BUG: this function is not called and thus self.cur_price is not initialized!!!
        print("Yes. we call f: set_up_currencies")
        # The currenci that is use as the reference is called the quite currecy
        # and the currency that is quoted in relation is called the base currency
        # For example:
        # EUR/USD = 1.2500 means that 1 euro is exchanged for 1.2500 dollars
        # Here, EUR is the base currency and USD is the quote currencty
        self.base_currency = self.currency_pair[:3]
        self.quote_currency = self.currency_pair[3:]
        
        # For EUR/USD with account denominated in GBP, this is USD/GBP
        # because EUR/USD * USD/GBP = EUR/GBP
        self.quote_home_currency_pair = "%s%s" % (self.quote_currency, 
                                                  self.home_currency)
        
        ticker_cur = self.ticker.prices[self.currency_pair] # ticker.prices?
        
        # In FX quote EUR/USD 1.2500/05 the Bid is 1.2500 and the Ask is 1.2505.
        # Bid and Ask as terms are defined from perspective of a FX broker.
        # If you want to buy EUR/USD you will pay the aks price (the broker
        # asking price) of 1.2505.
        # If you want to sell EUR.USD you will get the bid price (you accept
        # brokers bid)) of 1.2500.
        # Ask > Bid

        if self.position_type == 'long' :
            self.avg_price = Decimal(str(ticker_cur['ask'])) # price you pay when buying
            self.cur_price = Decimal(str(ticker_cur['bid'])) # current price
        else:
            self.avg_price = Decimal(str(ticker_cur['bid'])) # price you receive when selling
            self.cur_price = Decimal(str(ticker_cur['ask'])) # current price

    
    def calculate_pips(self):
        """
        Calculates pips as a difference between current and average price.
        """
        getcontext().rounding = ROUND_HALF_DOWN

        if self.position_type == 'long':
            # If i'm buying the pips are calc as Ask - Bid so the mult is positive
            mult = Decimal("1")
        elif self.position_type == 'short':
            # If i'm selling the pips are calc as Bid - Ask so the mult is negative  
            mult = Decimal("-1")
        print("cur_price: ", self.cur_price)
        pips = (mult * (self.cur_price - self.avg_price).quantize(
                Decimal("0.00001")))
        return pips
    
    def calculate_profit_base(self):
        """
        Calculate absolute amount of trade (?) profit.
        """
        getcontext().rounding = ROUND_HALF_DOWN
        
        pips = self.calculate_pips()
        ticker_qh = self.ticker.prices[self.quote_home_currency_pair]
        if self.position_type == 'long':
            qh_close = ticker_qh['bid']
        else:
            qh_close = ticker_qh['ask']
        
        profit = pips * qh_close * self.units
        return profit.quantize(Decimal("0.00001"))
    
    def calculate_profit_perc(self):
        """
        Calculate trade (?) profit in relative terms. The denominator is 
        numbner of traded units * 100.
        """
        return (self.profit_base / self.units * Decimal("100.00")).quantize(
                Decimal("0.00001"), ROUND_HALF_DOWN)
    
    def update_position_price(self):
        """
        Update current price of traded CCY pair depending on taken position.
        """
        ticker_cur = self.ticker.prices[self.currency_pair]
        
        if self.position_type == 'long':
            self.cur_price = Decimal(str(ticker_cur['bid']))
        else:
            self.cur_price = Decimal(str(ticker_cur['ask']))
        
        self.profit_base = self.calcualte_profit_base()
        self.profit_perc = self.calculate_profit_perc()
    
    def add_units(self, units):
        """
        Add units to existing trade. First update current prices
        and then calculate new total cost.
        """
        dec_units = Decimal(str(units))
        cp = self.ticker.prices[self.currency_pair]
        # get current CCY quote
        if self.position_type == 'long':
            add_price = cp['ask'] # price for buying additional units
        elif self.position_type == 'short':
            add_price = cp['bid']
            
        new_total_units = self.units + dec_units
        # New total cost is equal to:
        # previously paid price (self.avg_price * self.units) plus
        # new cost of bying additional units add_price * units
        new_total_cost = self.avg_price * self.units + add_price * units
        self.avg_price = new_total_cost / new_total_units
        self.units = new_total_units
        self.update_position_price()
        
    
    def remove_units(self, units):
        """
        ????
        Dont udnerstand why getting remove_price and then not using it.
        Check if pnl is calcualted correctly.
        """
        getcontext().rounding = ROUND_HALF_DOWN
        
        dec_units = Decimal(str(units))
        #ticker_cp = self.ticker.prices[self.currency_pair]
        ticker_qh = self.ticker.prices[self.quote_home_currency_pair]
        
        if self.position_type == 'long':
            #remove_price = ticker_cp['bid']
            qh_close = ticker_qh['ask']
        elif self.position_type == 'short':
            #remove_price = ticker_cp['ask']
            qh_close = ticker_qh['bid']
            
        self.units -= dec_units
        self.update_position_price()
        # Calculate pnl
        pnl = self.calculate_pips() * qh_close * dec_units
        return pnl.quantize(Decimal("0.01"))
    
    def close_position(self):
        """
        ???
        Check this
        """
        getcontext().rounding = ROUND_HALF_DOWN
        
        #ticker_cp = self.ticker.prices[self.currency_pair]
        ticker_qh = self.ticker.prices[self.quote_home_currency_pair]
        if self.position_type == 'long':
            qh_close = ticker_qh['ask'] # If we are long, why is closing price ask?!
        elif self.position_type == 'short':
            qh_close = ticker_qh['bid'] # If we are short, wht is closing price bid?!
        self.update_position_price()
        # Calculate pnl
        pnl = self.calcualte_pips() * qh_close * self.units
        return pnl.quantize(Decimal("0.01"))
        