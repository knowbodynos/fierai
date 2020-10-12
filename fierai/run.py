import os
import subprocess as sp
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from youtube_api import YouTubeDataAPI
from typing import Union, Optional, Any

from . audio import Audio
from . subtitles import Subtitles
from . utils import IncrementalNPZ


def run_download(playlist_url: str,
                 audio: bool = False,
                 subtitles: bool = False) -> None:
    assert audio or subtitles, "Must specify audio and/or subtitles to download."
    cmd = "youtube-dl -i --id"
    if subtitles:
        cmd += " --write-auto-sub --sub-format vtt --sub-lang en"
    if audio:
        cmd += " -x --audio-format wav"
    else:
        cmd += " --skip-download"
    cmd += f' {playlist_url}'
    proc = sp.Popen(cmd.split(' '))
    proc.wait()


def run_scrape(query: str,
               max_results: int = 100,
               audio: bool = False,
               subtitles: bool = False) -> None:
    assert audio or subtitles, "Must specify audio and/or subtitles to scrape."

    try:
        YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", None)
        yt = YouTubeDataAPI(YOUTUBE_API_KEY)
    except:
        raise Exception("Please set YOUTUBE_API_KEY environment variable")

    def parser(x):
        url = "https://www.youtube.com/playlist?list="
        return url + x['id']['playlistId']

    results = yt.search(
        part=['id'],
        parser=parser,
        q=query,
        max_results=max_results,
        search_type='playlist'
    )
    for url in results:
        run_download(url, audio, subtitles)


def run_chunk(audio_file: Union[str, Path],
              subtitles_file: Union[str, Path],
              split_time: float = 3.) -> None:
    audio_prefix, *_ = os.path.abspath(audio_file).split(os.extsep, 1)
    subtitles_prefix, *_ = os.path.abspath(subtitles_file).split(os.extsep, 1)
    id = os.path.basename(audio_prefix)

    audio_out = Path(audio_prefix + '.npz')
    subtitles_out = Path(subtitles_prefix + '.txt')

    with IncrementalNPZ(audio_out) as audio_fh, \
            open(subtitles_out, 'w') as subtitles_fh:
        audio = Audio.load(audio_file)
        audio_fh.savez(sample_rate=audio.sample_rate)
        parser = Subtitles.parse(subtitles_file).split_on_pauses(split_time)
        with tqdm(total=audio.duration, desc=id, unit_scale=True) as pbar:
            for chunk in parser:
                audio_chunk = audio.interval(chunk['start'], chunk['end'])
                # audio_chunk.filter_background()
                data = dict(start=chunk['start'], end=chunk['end'], waveform=audio_chunk.waveform)
                payload = {f"{id}_{chunk['index']}": data}
                audio_fh.savez(**payload)
                print(chunk['index'], chunk['start'], chunk['end'], chunk['text'], sep='\t', file=subtitles_fh)


def run_corpus(subtitles_dir: Union[str, Path] = '.',
               train_frac: float = 0.9,
               valid_frac: Optional[float] = None,
               random_seed: Optional[Any] = None,
               split_time: float = 3.) -> None:
    valid_frac = 1. - train_frac if valid_frac is None else valid_frac
    subtitles_dir = Path(subtitles_dir)
    records = []
    print("Preparing...")
    for file in subtitles_dir.glob('*.en.vtt'):
        subtitles = Subtitles.parse(file)
        records.append({'file': file.name, 'duration': subtitles.duration})
    videos = pd.DataFrame.from_records(records)
    videos = videos.sample(frac=1, random_state=random_seed)
    durations = videos.duration.cumsum() / videos.duration.sum()
    splits = {
        'train': videos.file[durations < train_frac],
        'valid': videos.file[(train_frac <= durations) & (durations < train_frac + valid_frac)],
        'test': videos.file[train_frac + valid_frac < durations]
    }
    with tqdm(total=len(videos), unit_scale=True) as pbar:
        for mode, files in splits.items():
            with open(subtitles_dir / f"corpus.{mode}.txt", 'w') as fh:
                for file in files:
                    pbar.set_description(file)
                    for chunk in Subtitles.parse(file).split_on_pauses(split_time):
                        print(chunk['text'], file=fh)
                    pbar.update()
