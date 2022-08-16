from .chapterScraper import chapterScraper
import re
import pandas as pd
import traceback
import json
import scrapy
from ..tools import exceptions


class questionScraper(chapterScraper):
    def __init__(self):
        chapterScraper.__init__(self)
        self.codeRegex = "\([0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]P\)|[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]P"
        self.codeRegexPre55 = "\(n° P[0-9]+\)|\(nr. P[0-9]+\)|\(nr. [0-9]+\)|\(n° [0-9]+\)|\(nr(.*?)[0-9]+\)|\(n°(.*?)[0-9]+\)"
        self.cleanupRegex = (
            "[0-9][0-9]|-|Question de|Vraag van|mevrouw |de heer |Mme |M. "
        )

    def changeOldCode(self, text: str):
        # assumes old code is present
        newcode = re.search(self.codeRegexPre55, text).group()[1:-1]
        newcode = (
            str(self.legislature) + re.search("[0-9]+", newcode).group().zfill(6) + "P"
        )
        return newcode

    def isQuestion(self, element: scrapy.selector.unified.Selector) -> bool:
        # determines if element is a question
        # in: element
        # out: boolean
        isTitle = bool(
            re.search("titre|titel", self.getClass(element), flags=re.IGNORECASE)
        )
        codeBased = bool(re.search(self.codeRegex, self.getInnerText(element)))
        return codeBased and isTitle

    def findEndOfBlock(self, elements) -> int:
        for i in range(0, len(elements)):
            if self.isTitle(self.getClass(elements[i])):
                return i
        return len(elements)

    def getCode(self, text: str) -> str:  # assumes code exsists
        out = re.search(self.codeRegex, text)
        if out == None:
            return None
        return re.sub("\(|\)", "", out.group())

    def extractQuestionAsker(self, row) -> str:
        text = re.sub(self.cleanupRegex, "", row["content"])
        if row["language"] == "nl":
            text = text.split("aan")[0].strip()
            return text
        elif row["language"] == "fr":
            if "à" in text:
                text = text.split("à")[0].strip()
            else:
                text = text.split("au")[0].strip()
            return text

    def extractInterviewee(self, row) -> str:
        text = re.sub(self.cleanupRegex, "", row["content"])
        if row["language"].lower() == "nl":
            if text.find("aan") != -1:
                text = text.split("aan")[1]
            elif text.find("tot") != -1:
                text = text.split("tot")[1]
            else:
                raise exceptions.couldNotFindInterviewee(text)
            text = text.split("over")[0]
            return text.split("(")[0].strip()
        elif row["language"].lower() == "fr":

            if "à" in text:
                text = text.split("à")[1]
            else:
                text = text.split("au")[1]
            text = text.split("sur")[0]
            return text.split("(")[0].strip()

    def getTopics(self, elements: list) -> pd.DataFrame:
        # collects all questions in section
        # in: start and stopindex of section
        # out: pandas dataframe where every row is question , row contains: index,content and language
        questions = pd.DataFrame(columns=["index", "content", "language", "code"])
        for i in range(0, len(elements)):
            element = elements[i]
            if self.isQuestion(element):
                questions = questions.append(
                    {
                        "index": i,
                        "content": self.getInnerText(element),
                        "language": self.getLanguageFromElement(element),
                        "code": self.getCode(self.getInnerText(element)),
                    },
                    ignore_index=True,
                )
        return questions

    def parse(self, elements) -> None:
        self.status = {}
        self.questions = pd.DataFrame()
        self.answers = pd.DataFrame()
        try:
            self.questions = self.getTopics(elements)
            self.questions = self.identifyBlocks(self.questions)
            startStopIndexes = self.startEndPointOfBlock(self.questions)

            for blockid in startStopIndexes:
                if startStopIndexes[blockid][1] == None:
                    startStopIndexes[blockid] = (
                        startStopIndexes[blockid][0],
                        len(elements),
                    )

                stopIndex = startStopIndexes[blockid][0] + self.findEndOfBlock(
                    elements[
                        startStopIndexes[blockid][0] : startStopIndexes[blockid][1]
                    ]
                )

                debate = self.scrapeDebate(
                    elements[startStopIndexes[blockid][0] : stopIndex]
                )
                debate["blockid"] = blockid
                self.answers = self.answers.append(debate)

            # clean up raw text and extract data
            if len(self.answers) == 0:
                raise exceptions.EmptyDebateDataFrame()
            self.answers["party"] = self.answers["speaker"].apply(self.getPolitcalParty)
            self.answers["speaker"] = self.answers["speaker"].apply(self.getSpeakerName)

            if len(self.questions) == 0:
                raise exceptions.EmptyTopicsDataFrame()

            self.questions["asker"] = self.questions.apply(
                self.extractQuestionAsker, axis=1
            )
            self.questions["interviewee"] = self.questions.apply(
                self.extractInterviewee, axis=1
            )
            self.mergedQuestions = self.mergeTopics(
                self.questions,
                ["asker", "interviewee", "blockid"],
                ["index"],
                "code",
                "language",
            )
            self.status["error"] = False
        except Exception as e:
            trace = traceback.format_exc()
            print(trace)
            self.status["error"] = True
            self.status["message"] = trace
            if "blockid" in locals():
                self.status["blockid"] = blockid
            else:
                self.status["blockid"] = None

    def save(self, path: str) -> None:
        if not self.failed():
            self.mergedQuestions.to_csv(path + "/topics.csv", index=False)
            self.answers.to_csv(path + "/debates.csv", index=False)
        with open(path + "/log.json", "w") as fp:
            fp.write(json.dumps(self.status, indent=4))

    def getBlockIndices(self):
        out = self.mergeTopics(
            self.questions,
            ["asker", "interviewee", "blockid", "index"],
            [],
            "code",
            "language",
        )
        out = out[["blockid", "index"]].values.tolist()
        temp = []
        blockid = -1
        for item in out:
            if item[0] > blockid:
                blockid = item[0]
                temp.append(item)
        return temp
