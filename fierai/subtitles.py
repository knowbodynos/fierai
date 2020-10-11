import webvtt
from tqdm import tqdm
from typing import Optional, Dict


class SubtitlesChunk(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)


class Subtitles(object):
    def __init__(self, parser, chunk_duration: float = 10, progbar_kws: Optional[Dict] = None):
        self.parser = parser
        self.chunk_duration = chunk_duration
        self.progbar_kws = progbar_kws

    def __iter__(self):
        text = ""
        index = 0
        start = 0
        prev_line = None
        progbar = tqdm(**self.progbar_kws) if self.progbar_kws is not None else None
        for caption in self.parser:
            for line in caption.text.strip().split('\n'):
                if (prev_line is None) or (prev_line != line):
                    text += ' ' + line if text else line
                    prev_line = line
            end = caption.end_in_seconds
            if end - start > self.chunk_duration:
                yield SubtitlesChunk(
                    index=index,
                    text=text,
                    start=start,
                    end=end
                )
                index += 1
                text = ""
                start = caption.start_in_seconds
            if progbar is not None:
                progbar.update(caption.end_in_seconds - progbar.n)
        if progbar is not None:
            progbar.update(progbar.total - progbar.n)

    @classmethod
    def parse(cls, file: str, chunk_duration: float = 10, progbar_kws: Optional[Dict] = None):
        parser = webvtt.read(file)
        return cls(parser, chunk_duration, progbar_kws)
