from .chapterScraper import chapterScraper
import re
import pandas as pd
import traceback
import json
from ..tools import exceptions


class legislationScraper(chapterScraper):
    def __init__(self):
        chapterScraper.__init__(self)
        # self.codeRegex = "\([0-9]+\/[0-9]+-[0-9]+\)|\([0-9]+\/[0-9]+\)"
        self.codeRegex = "\(([0-9]+.*?)\)"

    def getDocumentCode(self, text: str) -> str:
        return text[0 : text.find("/")]

    def isProposal(self, element) -> bool:
        regex = bool(re.search(self.codeRegex, self.getInnerText(element)))
        return regex and self.isTitle(element)

    def findStartArticleDiscussion(self, elements: list) -> int:
        for i in range(0, len(elements)):
            if (
                self.isTitle(elements[i])
                and bool(
                    re.search(
                        "Discussion des articles|Bespreking van de artikelen|artikel|article",
                        self.getInnerText(elements[i]),
                        flags=re.IGNORECASE,
                    )
                )
            ) or bool(
                re.search(
                    "^Discussion des articles|^Bespreking van de artikelen",
                    self.getInnerText(elements[i]),
                    flags=re.IGNORECASE,
                )
            ):
                return i + 1
        return len(elements)

    def findStartGeneralDiscussion(self, elements: list) -> int:
        for i in range(0, len(elements)):
            if self.isTitle(elements[i]) and bool(
                re.search(
                    "Discussion générale|Algemene bespreking|Algemene|générale",
                    self.getInnerText(elements[i]),
                    flags=re.IGNORECASE,
                )
            ):
                return i + 1
        return 0

    def getTopicCode(self, text: str) -> str:
        return re.search(self.codeRegex, text).group()[1:-1]

    def getTopics(self, elements) -> pd.DataFrame:
        topics = []
        for i in range(0, len(elements)):
            if self.isProposal(elements[i]):
                text = self.getInnerText(elements[i])
                topics.append(
                    {
                        "index": i,
                        "content": text,
                        "code": self.getTopicCode(text),
                        "language": self.getLanguageFromElement(elements[i]),
                    }
                )
        return pd.DataFrame(topics)

    def getProposalCode(self, text: str) -> str:
        if text.find("/") == -1:
            return text
        return text[0 : text.find("/")]

    def parse(self, elements: list) -> None:
        self.status = {}
        self.debates = pd.DataFrame()
        self.proposals = pd.DataFrame()
        try:
            self.proposals = self.getTopics(elements)
            self.proposals = self.identifyBlocks(self.proposals, blockIdName="blockid")
            startStopIndexes = self.startEndPointOfBlock(
                self.proposals, blockIdName="blockid"
            )

            for blockid in startStopIndexes:
                start, stop = startStopIndexes[blockid][0], startStopIndexes[blockid][1]
                if stop == None:
                    stop = len(elements)

                start = start + self.findStartGeneralDiscussion(elements[start:stop])
                stop = start + self.findStartArticleDiscussion(elements[start:stop]) - 1

                debate = self.scrapeDebate(elements[start:stop])
                debate["blockid"] = blockid
                self.debates = pd.concat([self.debates,debate])
                #self.debates = self.debates.append(debate)

            # if len(self.debates) == 0: #dont check this for law proposals since there can be no debate about a bill
            #    raise exceptions.EmptyDebateDataFrame()
            if len(self.debates) > 0:
                self.debates["party"] = self.debates["speaker"].apply(
                    self.getPolitcalParty
                )
                self.debates["speaker"] = self.debates["speaker"].apply(
                    self.getSpeakerName
                )
                self.debates = self.debates.astype(
                    {"speechIndex": "int", "segmentIndex": "int"}
                )

            if len(self.proposals) == 0:
                raise exceptions.EmptyTopicsDataFrame()
            self.proposals.rename(columns={"code": "fullCode"}, inplace=True)
            self.proposals["code"] = self.proposals["fullCode"].apply(
                self.getDocumentCode
            )  # remove the individual articles
            self.mergedTopics = self.mergeTopics(
                self.proposals,
                singleColumns=["blockid", "fullCode"],
                dropColumns=["index"],
                matchColumn="code",
                langColumn="language",
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
            self.mergedTopics.to_csv(path + "/topics.csv", index=False)
            self.debates.to_csv(path + "/debates.csv", index=False)
        with open(path + "/log.json", "w") as fp:
            fp.write(json.dumps(self.status, indent=4))

    def getBlockIndices(self):
        out = self.mergeTopics(
            self.proposals,
            singleColumns=["blockid", "index"],
            dropColumns=["fullCode"],
            matchColumn="code",
            langColumn="language",
        )
        out = out[["blockid", "index"]].values.tolist()
        temp = []
        blockid = -1
        for item in out:
            if item[0] > blockid:
                blockid = item[0]
                temp.append(item)
        return temp
