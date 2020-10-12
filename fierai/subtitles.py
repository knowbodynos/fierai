import re
import webvtt
from pathlib import Path
from webvtt.webvtt import WebVTT


class Subtitles(object):
    def __init__(self, parser: WebVTT):
        self.parser = parser
        self.id = Path(parser.file)
        while self.id.suffixes:
            self.id = Path(self.id.stem)
        self.id = self.id.stem
        self.duration = self.parser.total_length
        self.index = 0
        self.i = 0
        self.text = ""
        self.start = 0
        self.end = 0

    @classmethod
    def parse(cls, file: str):
        parser = webvtt.read(file)
        return cls(parser)

    def split_on_pauses(self, split_time: float = 3.):
        index = 0
        start = 0
        end = 0
        text = ""
        for i, caption in enumerate(self.parser):
            if i % 2 == 1:
                if caption.start_in_seconds - end > split_time:
                    yield dict(index=index, start=start, end=end, text=text)
                    index += 1
                    start = caption.start_in_seconds
                    text = ""
                line = re.sub('\[.*\]', '', caption.text)
                line = re.sub('\s+', ' ', line)
                text += line
                end = caption.end_in_seconds
            i += 1
        yield dict(index=index, start=start, end=end, text=text)
