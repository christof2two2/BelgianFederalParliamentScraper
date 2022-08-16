class endOfFile(Exception):
    def __init__(self, message="index reached end of file"):
        self.message = message
        super().__init__(self.message)


class EmptyTopicsDataFrame(Exception):
    """No topics were detected in this section"""


class EmptyDebateDataFrame(Exception):
    """Debate dataframe returend empty"""


class couldNotFindNewSpeaker(Exception):
    """Could not get new speaker"""

    def __init__(self, message, text) -> None:
        super().__init__(f"{message} with raw text: {text}")


class couldNotFindInterviewee(Exception):
    """Could not get new speaker"""

    def __init__(self, message) -> None:
        super().__init__(f"could not find interviewee in text: {message}")


class tooFewElements(Exception):
    """Could not get new speaker"""

    def __init__(self, elementCount, url) -> None:
        super().__init__(
            f"too few html elements extracted from url {url}, extratced {elementCount} elements"
        )


class NoTopicsDetected(Exception):
    """Could not get new speaker"""

    def __init__(self) -> None:
        super().__init__(f"No topics were detected")


class couldNotFind(Exception):
    def __init__(self, message) -> None:
        super().__init__(message)
