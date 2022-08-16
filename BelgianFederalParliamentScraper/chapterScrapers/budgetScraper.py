import re
import pandas as pd
from .legislationScraper import legislationScraper
import traceback


class budgetScrapper(legislationScraper):
    def __init__(self):
        legislationScraper.__init__(self)
