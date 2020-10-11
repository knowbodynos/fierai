import os
import subprocess as sp
import pandas as pd
from pathlib import Path
from typing import Union
from sklearn.model_selection import train_test_split

from . audio import Audio
from . subtitles import Subtitles
from . utils import IncrementalNPZ


def run_scrape(playlist_url: str) -> None:
    cmd = "youtube-dl -i --id --write-auto-sub --sub-format vtt --sub-lang en -x --audio-format wav"
    cmd += f' {playlist_url}'
    proc = sp.Popen(cmd.split(' '))
    proc.wait()


def run_chunk(audio_file: Union[str, Path],
              subtitles_file: Union[str, Path],
              chunk_duration: float = 10.) -> None:
    audio_prefix, *_ = os.path.abspath(audio_file).split(os.extsep, 1)
    subtitles_prefix, *_ = os.path.abspath(subtitles_file).split(os.extsep, 1)
    id = os.path.basename(audio_prefix)

    audio_out = Path(audio_prefix + '.npz')
    subtitles_out = Path(subtitles_prefix + '.txt')

    with IncrementalNPZ(audio_out) as audio_fh, \
            open(subtitles_out, 'w') as subtitles_fh:
        audio = Audio.load(audio_file)
        audio_fh.savez(sample_rate=audio.sample_rate)
        progbar_kws = dict(total=audio.duration, desc=id, unit_scale=True)
        parser = Subtitles.parse(subtitles_file, chunk_duration, progbar_kws)
        for chunk in parser:
            audio_chunk = audio.interval(chunk.start, chunk.end)
            # audio_chunk.filter_background()
            data = dict(start=chunk.start, end=chunk.end, waveform=audio_chunk.waveform)
            payload = {f'{id}_{chunk.index}': data}
            audio_fh.savez(**payload)
            print(chunk.index, chunk.start, chunk.end, chunk.text, sep='\t', file=subtitles_fh)


def run_corpus(subtitles_dir: Union[str, Path] = '.',
               train_frac: float = 0.7,
               valid_frac: float = 0.15) -> None:
    subtitles_dir = Path(subtitles_dir)
    data = pd.DataFrame()
    for file in subtitles_dir.glob('*.txt'):
        frame = pd.read_csv(
            file,
            sep='\t',
            names=['chunk', 'start', 'stop', 'text'],
            header=None
        ).dropna()
        frame['id'] = file.stem
        data = pd.concat([data, frame], axis=0)
    splits = {}
    splits['train'], remainder = train_test_split(data.text, train_size=train_frac)
    splits['valid'], splits['test'] = train_test_split(remainder, train_size=valid_frac/(1.-train_frac))
    for k, v in splits.items():
        with open(subtitles_dir / f"corpus.{k}.txt", 'w') as fh:
            for line in v:
                print(line, end=' ', file=fh)
