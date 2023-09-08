import scrapy
import re
import pandas as pd
from .parentClass import parentClass
import os
import shutil
import json
from .tools import exceptions


class parliamentScraper(scrapy.Spider, parentClass):
    def __init__(self, urls: list, chapterScrapers: dict, dataPath: str):
        self.start_urls = urls
        self.chapterScrapers = chapterScrapers
        self.path = dataPath

        self.loadUselessElementRegex()
        self.loadChapterHeaders()

    def loadUselessElementRegex(self):
        path = os.path.join(
            os.path.dirname(__file__), "operatingData", "uselessElements.csv"
        )
        temp = pd.read_csv(path)
        temp = "^" + temp["regex"]
        self.uselessElementRegex = "|".join(temp.tolist())

    def loadChapterHeaders(self):
        path = os.path.join(os.path.dirname(__file__), "operatingData", "headers.csv")
        self.chapterHeaders = pd.read_csv(path)
        self.chapterHeadersRegex = ""
        self.subChapterHeadersRegex = ""
        self.chapterRegexAndName = dict()
        self.subChapterRegexAndName = dict()
        for name in self.chapterHeaders["name"].unique():
            if (
                self.chapterHeaders[self.chapterHeaders["name"] == name].iloc[0]["type"]
                == "header"
            ):
                regexes = self.chapterHeaders[self.chapterHeaders["name"] == name]
                self.chapterRegexAndName[name] = "|".join(
                    regexes["regex"].tolist()
                ).lower()
            elif (
                self.chapterHeaders[self.chapterHeaders["name"] == name].iloc[0]["type"]
                == "subHeader"
            ):
                regexes = self.chapterHeaders[self.chapterHeaders["name"] == name]
                self.subChapterRegexAndName[name] = "|".join(
                    regexes["regex"].tolist()
                ).lower()

        regexes = self.chapterHeaders[self.chapterHeaders["type"] == "header"]
        self.chapterHeadersRegex = ("|".join(regexes["regex"].tolist())).lower()

    def isElementUseless(self, element) -> bool:
        text = self.getInnerText(element)
        return (len(text) == 0) or (
            bool(re.match(self.uselessElementRegex, text, flags=re.IGNORECASE))
        )

    def filterOutUselessElements(self, elementList) -> list:
        out = [None] * len(elementList)
        j = 0
        for i in range(0, len(elementList)):
            if not self.isElementUseless(elementList[i]):
                out[j] = elementList[i]
                j += 1
        (
            self.status["amountOfElements"],
            self.status["removedElements"],
            self.status["originalELements"],
        ) = (len(elementList) - j, j, len(elementList))
        return out[0:j]

    def isChapterHeader(self, element) -> bool:
        if bool(re.search("titre1|titel1", self.getClass(element))):
            return True
        if bool(re.search("titre2|titel2", self.getClass(element))) and bool(
            re.search(
                "\bverklaring van de regering|\bdéclaration du gouvernement",
                self.getInnerText(element),
                flags=re.IGNORECASE,
            )
        ):
            return True
        if self.getTag(element) in ["h1"]:
            return True
        return False

    def getHeaderType(self, element) -> str:
        text = self.getInnerText(element)
        for key, value in self.chapterRegexAndName.items():
            if bool(re.search(value, text, flags=re.IGNORECASE)):
                return key
        return None

    def getChapters(self, elements) -> dict:
        chapters = list()
        for i in range(0, len(elements)):
            if self.isChapterHeader(elements[i]):
                t = self.getHeaderType(elements[i])
                chapters.append((i, t, self.getInnerText(elements[i])))

        if len(chapters) == 0:
            return {"intro": [(0, len(elements))]}

        new = list()
        i = 0
        while i < len(chapters):
            new.append((chapters[i][1], chapters[i][0], chapters[i + 1][0]))
            i += 2

        chapters = new
        new = list()
        for i in range(0, len(chapters)):
            if i < len(chapters) - 1:
                new.append((chapters[i][0], chapters[i][2] + 1, chapters[i + 1][1]))
            else:
                new.append((chapters[i][0], chapters[i][2] + 1, len(elements)))

        chapters = new
        new = dict()
        for i in range(0, len(chapters)):
            if chapters[i][0] in new:
                continue
            new[chapters[i][0]] = []
            new[chapters[i][0]].append((chapters[i][1], chapters[i][2]))
            for j in range(i + 1, len(chapters)):
                if chapters[j][0] == chapters[i][0]:
                    new[chapters[i][0]].append((chapters[j][1], chapters[j][2]))
        min = 100000
        for key, value in new.items():
            for v in value:
                if v[0] < min:
                    min = v[0]
        new["intro"] = [(0, min)]
        return new

    def makeInputForChapterScraper(self, elements, indices):
        out = []
        for item in indices:
            start, stop = item
            out += elements[start:stop]
        return out

    def parse(self, response):
        self.status = {"error": False, "errorChapters": [], "url": response.request.url}
        totalNodes = list()
        allNodes = response.selector.css("body>*")
        for x in allNodes:
            y = x.css("div>*")
            if len(y) > 0:
                totalNodes += y
        self.totalElements = self.filterOutUselessElements(totalNodes)
        if len(self.totalElements) < 15:
            raise exceptions.tooFewElements(
                len(self.totalElements), response.request.url
            )
        self.chapters = self.getChapters(self.totalElements)

        for cs in self.chapterScrapers:
            if cs in self.chapters:
                inp = self.makeInputForChapterScraper(
                    self.totalElements, self.chapters[cs]
                )
  
                self.chapterScrapers[cs].parse(inp)
                if self.chapterScrapers[cs].failed():
                    self.status["error"] = True
                    self.status["errorChapters"].append(cs)

        self.status["chapters"] = self.chapters

        temp = response.request.url.split("/")
        if temp[-1][0:2] == "ic":
            org = "commision"
        else:
            org = "plenary"
        i = temp[-1].find("x")
        documentNumber = temp[-1][2:i].lstrip("0")
        self.status["legis"] = temp[-2]
        self.status["orgName"] = org
        self.status["documentNumber"] = documentNumber

        self.makeBlockIdsGlobal()
        self.save(legislature=temp[-2], orgName=org, documentNumber=documentNumber)

    def save(self, legislature: int, orgName: str, documentNumber: int):
        if not os.path.isdir(self.path):
            os.mkdir(self.path)
        if (not os.path.exists(f"{self.path}/{legislature}")) or (
            not os.path.isdir(f"{self.path}/{legislature}")
        ):
            os.mkdir(f"{self.path}/{legislature}")

        if (not os.path.exists(f"{self.path}/{legislature}/{orgName}")) or (
            not os.path.isdir(f"{self.path}/{legislature}/{orgName}")
        ):
            os.mkdir(f"{self.path}/{legislature}/{orgName}")

        if (
            not os.path.exists(f"{self.path}/{legislature}/{orgName}/{documentNumber}")
        ) or (
            not os.path.isdir(f"{self.path}/{legislature}/{orgName}/{documentNumber}")
        ):
            os.mkdir(f"{self.path}/{legislature}/{orgName}/{documentNumber}")

        folder = f"{self.path}/{legislature}/{orgName}/{documentNumber}"
        # clean folder
        for f in os.listdir(folder):
            if os.path.isfile(f"{folder}/{f}"):
                os.remove(f"{folder}/{f}")
            else:
                shutil.rmtree(f"{folder}/{f}")

        for cs in self.chapterScrapers:
            if cs in self.chapters:
                os.mkdir(f"{folder}/{cs}")
                self.chapterScrapers[cs].save(f"{folder}/{cs}")

        with open(folder + "/log.json", "w") as fp:
            fp.write(json.dumps(self.status, indent=4))

    def localToGlobalIndices(self, localIndices: list, ranges: list) -> list:
        # local indices are [[chapter name,blockid , index],[...]]
        # ranges are[[start,stop],[...]]
        lengths = [x[1] - x[0] for x in ranges]
        globalIndices = []
        for i in range(len(lengths)):
            shift = lengths[i]
            localIndices = [[x[0], x[1], x[2] - shift] for x in localIndices]

            # remaining
            globalIndices += [
                [x[0], x[1], x[2] + shift + ranges[i][0]]
                for x in localIndices
                if x[2] < 0
            ]
            localIndices = [[x[0], x[1], x[2]] for x in localIndices if x[2] >= 0]
        return globalIndices

    def makeBlockIdsGlobal(self):
        topics = []
        for cs in self.chapterScrapers:
            if cs in self.chapters:
                blocks = [
                    [cs, x[0], x[1]] for x in self.chapterScrapers[cs].getBlockIndices()
                ]
                if len(blocks) > 0:
                    topics += self.localToGlobalIndices(blocks, self.chapters[cs])
        # topics [[chapterName,blocid,globalIndex],...]
        topics = sorted(topics, key=lambda tup: tup[2])
        conversionDicts = {}
        for i in range(0, len(topics)):
            if topics[i][0] not in conversionDicts:
                conversionDicts[topics[i][0]] = {}  # add a dict for every chapter
            conversionDicts[topics[i][0]][topics[i][1]] = i
        for key, value in conversionDicts.items():
            self.chapterScrapers[key].addToStatus("localBlockIdToGlobal", value)
