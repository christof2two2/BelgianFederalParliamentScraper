from .chapterScraper import chapterScraper
import pandas as pd
from ..tools import exceptions
import traceback
import json


class govDeclarationScraper(chapterScraper):
    def __init__(self):
        chapterScraper.__init__(self)

    def findEndOfSection(self, elements: list) -> int:
        for i in range(0, len(elements)):
            if self.isTitle(self.getClass(elements[i])):
                return i + 1
        return len(elements)

    def parse(self, elements: list) -> None:
        self.status = {}
        self.debates = pd.DataFrame()
        try:

            self.debates = self.scrapeDebate(
                elements[0 : self.findEndOfSection(elements)]
            )

            if len(self.debates) == 0:
                raise exceptions.EmptyDebateDataFrame()
            self.debates["party"] = self.debates["speaker"].apply(self.getPolitcalParty)
            self.debates["speaker"] = self.debates["speaker"].apply(self.getSpeakerName)

            self.status["error"] = False
        except Exception as e:
            trace = traceback.format_exc()
            print(trace)
            self.status["error"] = True
            self.status["message"] = trace

    def save(self, path: str) -> None:
        if not self.failed():
            self.debates.to_csv(path + "/debates.csv", index=False)
        with open(path + "/log.json", "w") as fp:
            fp.write(json.dumps(self.status, indent=4))

    def getBlockIndices(self):
        return [[0, 0]]
