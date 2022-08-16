from sys import flags
from .chapterScraper import chapterScraper
from ..tools import exceptions
import traceback
import json
import re


class introScraper(chapterScraper):
    def __init__(self):
        chapterScraper.__init__(self)

    def findTable(self, elements):
        for i in range(0, len(elements)):
            rows = elements[i].xpath(".//tr")
            if len(rows) > 0:
                return i

        return -1

    def cleanStrings(self, text: str) -> str:
        text = re.sub("(_)+", "", text)
        text = re.sub("( )+", " ", text)
        return text.strip()

    def getDayMonthYear(self, text: str):
        if text == None:
            return (None, None, None)
        day = int(text[0 : text.find(" ")])
        monthDict = {
            1: "januari|janvier",
            2: "februari|février",
            3: "maart|mars",
            4: "april|avril",
            5: "mei|may",
            6: "juni|juin",
            7: "juli|juillet",
            8: "augustus|aout",
            9: "september|septembre",
            10: "oktober|octobre",
            11: "november|novembre",
            12: "december|décembre",
        }
        month = None
        for key, value in monthDict.items():
            if bool(re.search(value, text, flags=re.IGNORECASE)):
                month = key
                break
        year = int(re.search("[0-9]{4}", text).group())
        return (day, month, year)

    def getFullDate(self, text: str):
        regex = "[0-9]{1,2} [a-zÀ-ú]+ [0-9]{4}"
        if bool(re.search(regex, text, flags=re.IGNORECASE)):
            return re.search(regex, text, flags=re.IGNORECASE).group()
        return None

    def parse(self, elements):
        self.status = {}
        self.data = {}
        try:
            i = self.findTable(elements)
            if i == -1:
                raise exceptions.couldNotFind(
                    "could not find table with meeting time and organization info"
                )
            rows = elements[i].xpath(".//tr")
            # scrape org name
            names = rows[0].xpath(".//td")
            self.data["orgNamefr"] = self.cleanStrings(self.getInnerText(names[0]))
            self.data["orgNamenl"] = self.cleanStrings(self.getInnerText(names[1]))

            # scrape time of meeting
            times = rows[1].xpath(".//td")
            self.data["meetingTimefr"] = self.cleanStrings(self.getInnerText(times[0]))
            self.data["meetingTimenl"] = self.cleanStrings(self.getInnerText(times[1]))

            self.data["fullDatenl"] = self.getFullDate(self.data["meetingTimenl"])
            self.data["fullDatefr"] = self.getFullDate(self.data["meetingTimefr"])

            (
                self.data["day"],
                self.data["month"],
                self.data["year"],
            ) = self.getDayMonthYear(self.data["fullDatenl"])
            self.status["error"] = False
        except Exception as e:
            trace = traceback.format_exc()
            print(trace)
            self.status["error"] = True
            self.status["message"] = trace

    def save(self, path):
        if not self.failed():
            with open(path + "/data.json", "w") as fp:
                fp.write(json.dumps(self.data, indent=4))
        with open(path + "/log.json", "w") as fp:
            fp.write(json.dumps(self.status, indent=4))
