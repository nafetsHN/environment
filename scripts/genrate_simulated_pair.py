import sys
sys.path.append('../')

import calendar
from copy import deepcopy
import datetime
import os, os.path

import numpy as np

from settings import CSV_DATA_DIR

def month_weekdays(year_int, month_int):
    """
    Produce a list of datetime.date objects representing the weekdays in a
    particular month, given a year.
    """    
    cal = calendar.Calendar()
    return [d for d in cal.itermonthdates(year_int, month_int) 
            if d.weekday() < 5 and d.month == month_int and d.year == year_int]
    
if __name__ == '__main__':
    # unnecessary try/except sintax - use it if you want to run the script from
    # cmd line and ask for pair input
    try:
        pair = "GBPUSD"
    except IndexError:
        print("Enter a currency pair e.g. GBPUSD")
    else:
        np.random.seed(42)
        
        s0 = 1.5000
        spread = 0.002
        mu_dt = 1400 # milliseconds
        sigma_dt = 100 # milliseconds
        ask = deepcopy(s0) + spread / 2.0
        bid = deepcopy(s0) - spread / 2.0
        days = month_weekdays(2018, 7) # July 2018
        current_time = datetime.datetime(days[0].year, 
                                         days[0].month, days[0].day, 0, 0, 0)
        
        # Loop over eavery day in the month and crate a CSV file for each day
        # e.g. "GBPUSD_20180801
        for d in days:
            print(d.day)
            current_time = current_time.replace(day=d.day)
            outfile = open(
                    os.path.join(CSV_DATA_DIR,"%s_%s.csv" % (
                            pair,d.strftime("%Y%m%d"))), 'w')
            
            # Create the random walk for the bod/ask prices with fixed spread
            while True:
                dt = abs(np.random.normal(mu_dt, sigma_dt))
                current_time += datetime.timedelta(0,0,0, dt)
                if current_time.day != d.day:
                    outfile.close()
                    break
                else:
                    W = np.random.standard_normal() * dt / 1000.0 / 86400.0
                    ask += W
                    bid += W
                    ask_volume = 1.0 + np.random.uniform(0.0, 2.0)
                    bid_volume = 1.0 + np.random.uniform(0.0, 2.0)
                    line = "%s,%s,%s,%s,%s\n" % (
                        current_time.strftime("%d.%m.%Y %H:%M:%S.%f")[:-3], 
                        "%0.5f" % ask, "%0.5f" % bid,
                        "%0.2f00" % ask_volume, "%0.2f00" % bid_volume
                    )
                    outfile.write(line)
            