import re
import pandas as pd
from ..parentClass import parentClass
from ..tools import exceptions

class chapterScraper(parentClass):
    def __init__(self):
        pass
    def newSpeaker(self,element) -> bool:
        #determines if element is  the first line of a new speaker
        #in: text
        #out: boolean
        text = self.getInnerText(element)
        if bool(re.match("^[0-9]{1,2}\.[0-9]{1,2} ", text)):
            return True
        if len(element.css(".oraspr")) > 0:
            return True
        if ":" in text[0:40] and bool(re.search("voorzitter|president|président|voorzitster",text[0:40],flags=re.IGNORECASE)):
            return True
        return False

    def identifyBlocks(self,elements:pd.DataFrame,blockIdName = "blockid")-> pd.DataFrame:
        #divides the chapters into their blocks and gives id to each block
        #in: -Pandas dataframe with at leas an index column
        #    -(Optional) name for block ids
        #out: pandas dataframe with qblockid column added

        #TODO replace for loop with pandas function
        if len(elements)==0:
            raise exceptions.NoTopicsDetected()

        elements[blockIdName] = pd.NaT
        blockid = 0
        elements.at[0,blockIdName] = blockid
        for i in range(1,len(elements)):  
            if elements.iloc[i]["index"] - elements.iloc[i-1]["index"] > 2:
                blockid += 1
            elements.at[i,blockIdName] = blockid
        return elements
    def startEndPointOfBlock(self,blocks:pd.DataFrame,blockIdName:str = "blockid")-> dict:
        #determine the start and end point for every block
        #in: pandas dataframe with at least Index and blockIdName column
        #out: dictionary where keys represent blockIdName's and values are (start,end)
        out = dict()
        id = 0
        for i in range(0,len(blocks)):
            if blocks.iloc[i][blockIdName] != id:
                out[id] = (blocks.iloc[i-1]["index"]+1,blocks.iloc[i]["index"])
                id = blocks.iloc[i][blockIdName]
        out[id] = (blocks.iloc[-1]["index"]+1,None)
        return out
    def getPolitcalParty(self,text:str) -> str:
        regex ="\((.*?)\)"
        if  re.search(regex,text) != None:
            return re.search(regex,text).group()[1:-1]
        return None

    def getSpeakerName(self,text:str)->str:
        text = re.sub("\((.*?)\)|\.|\d", '', text)
        text = re.sub("eerste minister|premier|ministre|minister|,|secrétaire d'État|staatssecretaris|première|rapporteur","",text,flags=re.IGNORECASE)
        return text.strip()

    def isTitle(self,className:str)->bool:
        return bool(re.search("titel|titre",className))

    def isSpeakerPresident(self,text:str)->bool:
        return bool(re.search("voorzitter|président|présidente|voorzitster",flags=re.IGNORECASE))
    def scrapeDebate(self,elements:list)->pd.DataFrame:
        begin = 0
        debate =[]
        speechIndex = -1
        while begin < len(elements):
            if self.newSpeaker(elements[begin]):
                break
            begin += 1

        speechIndex = -1
        currentLang = ""
        content = ""
        for i in range(begin,len(elements)):
            element = elements[i]
            text = self.getInnerText(element)
            if self.newSpeaker(element):
                #add segment to list
                if len(content) >0:
                    row = self.makeDebateSegmentRow(content,currentSpeaker,currentLang,segmentIndex,speechIndex)
                    debate.append(row) 
                j = text.find(":")
                if j == -1:
                    raise exceptions.couldNotFindNewSpeaker("could not located : to split new speaker and spoken text",text)
                segmentIndex = 0
                speechIndex += 1
                currentSpeaker = text[0:j]
                currentLang = self.getLanguageFromElement(element)
                content = text[j+1:].strip()
            elif bool(re.match("^((\*)+( |	|\n|\u00A0|\u000a|\u000d)+)+\*$",text)): 
                #check if we have run into a sequence like *  *  * * 
                # this signals the end of text and start of info about amendments
                #yes they use char code 160 a non breaking space, normal spaces, tabs, a line feed character and a carriage return
                #no i am not making this up and no i dont know why they use all of them
                break
            else:
                spokenWords=text.strip()
                lang = self.getLanguageFromElement(element)
                if lang != currentLang:
                    if len(content) >0:
                        row = self.makeDebateSegmentRow(content,currentSpeaker,currentLang,segmentIndex,speechIndex)
                        debate.append(row) 
                        
                    segmentIndex+= 1
                    content = spokenWords
                    currentLang = lang
                else:
                    content += spokenWords

        if len(content) >0:
            row = self.makeDebateSegmentRow(content,currentSpeaker,currentLang,segmentIndex,speechIndex)
            debate.append(row) 
        debate = pd.DataFrame(debate)
        if len(debate)>0: #there can be no discussion about a topic, see 20% of law proposals
            debate = debate.astype({"speechIndex":"int","segmentIndex":"int"})
        return debate


    def makeDebateSegmentRow(self,text:str,speaker:str,lang:str,segmentIndex:int,speechIndex:int)->dict:
        return {"speechIndex":speechIndex,"segmentIndex":segmentIndex,"speaker":speaker,"language":lang,"content":text}

    def mergeTopics(self,topics:pd.DataFrame,singleColumns:list,dropColumns:list,matchColumn:str,langColumn:str)->pd.DataFrame:
        mergedTopics = []
        cols = [x for x in topics.columns if ((x not in singleColumns) and (x != langColumn) and (x != matchColumn) and (x not in dropColumns))]
        topics[langColumn] = topics[langColumn].str.lower()
        codes= topics[matchColumn].unique()
        for code in codes:
            nl = topics.loc[(topics[langColumn]=="nl") & (topics[matchColumn]==code)]
            fr = topics.loc[(topics[langColumn]=="fr") & (topics[matchColumn]==code)]
            #print("nl:",nl)
            #print("fr:",fr)
            row = {matchColumn:code}
            for col in singleColumns:
                if len(nl) >0:
                    row[col] = nl[col].values[0]
                else:
                    row[col] = fr[col].values[0]

            for col in cols:
                if len(nl)>0:
                    row[col+"nl"]=nl[col].values[0]
                else:
                    row[col+"nl"]=None
                if len(fr)>0:
                    row[col+"fr"]=fr[col].values[0]
                else:
                    row[col+"fr"]=None
            mergedTopics.append(row)

        mergedTopics=pd.DataFrame(mergedTopics)
        mergedTopics["blockid"] = mergedTopics["blockid"].astype(int)
        return mergedTopics
    
    def failed(self)->bool:
        return self.status["error"]

    def getBlockIndices(self):
        return []

    def addToStatus(self,key,value):
        self.status[key]=value