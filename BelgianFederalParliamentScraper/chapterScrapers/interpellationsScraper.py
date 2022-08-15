import re
import pandas as pd
from .questionScraper import questionScraper
import traceback

class interpellationScraper(questionScraper):
    def __init__(self):
        questionScraper.__init__(self)
        #when looking at the regex below you notice it also includes entries for normal questions
        #on rare occasion parliament mixes in questions in the interpellation section.
        self.codeRegex = "\([0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]I\)|[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]I|[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]P"
        


    
