import re
from langdetect import detect_langs
class parentClass:
    def __init__(self):
        pass
    def getInnerText(self,element) -> str:
        return self.removeWeirdCharacters(str("".join(element.css("::text").extract()).strip()))
    def getClass(self,element) -> str:
        return str("".join(element.xpath("@class").extract()).lower().strip())
    def getLanguageFromElement(self,element) -> str: 
        #works most of the time, sometimes no lang info is present see https://www.dekamer.be/doc/PCRI/html/55/ip111x.html as example where no lang info is present on whole document
        out = self.getClass(element)[-2:]
        if out in ['nl','fr']:
            return out
        try:
            langs = detect_langs(self.getInnerText(element)) # fall back to language detection if no lang is specified
            if len(langs)>0:
                if langs[0].lang in ["nl","fr"] and langs[0].prob >= 0.5:
                    #print(f"detected lang {langs[0].lang}  with prob: {langs[0].prob} for text: {self.getInnerText(element)}")
                    return langs[0].lang 
        except:
            pass

        return None
    def removeWeirdCharacters(self,text:str)->str:
        #parliament uses weird charactesr like carriage returns and non breaking spaces this functions removes those from a string
        text = re.sub("\u000d","",text)
        text = re.sub("\u00A0|\u000a"," ",text)
        return text