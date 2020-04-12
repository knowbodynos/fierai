import os
import argparse
import shutil
import string
import json
import webvtt as wv
import subprocess as sp
from pydub import AudioSegment

def download_content(url, cwd="."):
    cmd = f"youtube-dl --print-json --write-auto-sub -x --audio-format wav {url}"
    p = sp.Popen(cmd.split(), stdout=sp.PIPE, stderr=sp.PIPE, cwd=cwd)
    out, err = p.communicate()
    out = json.loads(out)
    title = out['title'].split()
    season = title[title.index("Season")+1]
    episode = title[title.index("Episode")+1]
    old_prefix = os.path.splitext(out['_filename'])[0]
    old_prefix = os.path.join(cwd, old_prefix)
    new_prefix = f"s{season}e{episode}"
    data_dir = os.path.join(cwd, new_prefix)
    os.makedirs(data_dir, exist_ok=True)
    new_prefix = os.path.join(data_dir, new_prefix)
    os.rename(old_prefix+".wav", new_prefix+".wav")
    os.rename(old_prefix+".en.vtt", new_prefix+".en.vtt")
    return new_prefix

def chunk_content(prefix, chunk_length=10):
    data_dir = os.path.dirname(prefix)
    chunk_dir = os.path.join(data_dir, "chunks")
    if os.path.exists(chunk_dir):
        shutil.rmtree(chunk_dir)
    os.makedirs(chunk_dir, exist_ok=True)
    punc_table = str.maketrans('', '', string.punctuation)
    wav = AudioSegment.from_wav(prefix+'.wav')
    text = ""
    delta = 0
    i = 0
    for cap in wv.read(prefix+".en.vtt"):
        if len(text) == 0:
            start = cap.start_in_seconds
        next_text = cap.text.split('\n')[1]
        next_text = next_text.translate(punc_table)
        next_text = next_text.lower()
        text += next_text
        end = cap.end_in_seconds
        if end-start > chunk_length:
            isalpha = True
            for sent in text.split('\n'):
                for word in text.split():
                    isalpha = isalpha and word.isalpha()
            if isalpha:
                chunk_prefix = os.path.join(chunk_dir, f"chunk_{i}")
                wav[start*1e3:end*1e3].export(chunk_prefix+".wav", format="wav")
                with open(chunk_prefix+".txt", 'w') as fh:
                    fh.write(text.strip())
                i += 1
            text = ""

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download and chunk audio and text from youtube video.')
    parser.add_argument('url', help='youtube video url')
    parser.add_argument('--out-dir', '-o', dest='out_dir', default='.', help='output directory')
    parser.add_argument('--chunk-length', '-c', dest='chunk_length', type=int, default=10, help='max length of chunks in seconds')
    args = parser.parse_args()

    prefix = download_content(args.url, cwd=args.out_dir)
    chunk_content(prefix, chunk_length=args.chunk_length)
