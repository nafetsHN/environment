"""

Define basic settings:
    ACCOUNT_ID:         needed to connect to OANDA REST V20
    ACCESS_TOKEN:       needed to connect to OANDA REST V20
    DOMAIN:             trading domain: 'practice' or 'live'
    CSV_DATA_DIR:       dir to save data csv files
    OUTPUTI_RESULT_DIR: dir to save outputs
    BASE_CURRENCY:      OANDA account base CCY
    EQUITY:             starting amount of funds in base CCY
    
"""
import sys
sys.path.append('../')

import os
import configparser
from decimal import Decimal

os.chdir(r'C:\Users\2019765\Desktop\Naf\ML\trading\OANDA\tradingLayer')
WORKING_DIR = r'C:\Users\2019765\Desktop\Naf\ML\trading\OANDA\tradingLayer'

config = configparser.ConfigParser()
config.read('config/config_v20.ini')

DOMAIN = 'practice' # or: 'live'

ACCOUNT_ID = config['oanda']['account_id']
ACCESS_TOKEN = config['oanda']['access_token']

CSV_DATA_DIR = r'C:\Users\2019765\Desktop\Naf\ML\trading\OANDA\tradingLayer\dump\Data'
OUTPUT_RESULT_DIR = r'C:\Users\2019765\Desktop\Naf\ML\trading\OANDA\tradingLayer\dump\Results'

BASE_CURRENCY = 'GBP'
EQUITY = Decimal('100000.00')
