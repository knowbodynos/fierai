import os
import argparse
import shutil
import string
import time
import json
import inflect
import re
import webvtt as wv
import subprocess as sp
import librosa
from pydub import AudioSegment

punc_table = str.maketrans('', '', string.punctuation)
inflect_eng = inflect.engine()

def tokenize(text):
    text = text.strip()
    new_text = ""
    for i, sent in enumerate(text.split('\n')):
        sent = re.sub("[\(\[].*?[\)\]]", "", sent) # Remove bracketed text
        new_sent = ""
        for j, word in enumerate(sent.split()):
            new_word = ""
            for sub_word in re.findall(r"[^\W\d_]+|[\d,]+", word): # Convert numbers to words
                if sub_word.replace(',', '').isnumeric():
                    new_word += inflect_eng.number_to_words(sub_word)
                    new_word = new_word.replace(" and ", "")
                    new_word = new_word.replace("-", " ")
                else:
                    new_word += sub_word
            new_word = new_word.translate(punc_table) # Remove punctuation
            new_word = new_word.lower() # Convert to lowercase
            if j > 0:
                new_sent += ' '
            new_sent += new_word
        if i > 0:
            new_text += '\n'
        new_text += new_sent
    return new_text

def filter_background(y, sr=None):
    S_full, phase = librosa.magphase(librosa.stft(y))

    S_filter = librosa.decompose.nn_filter(
        S_full,
        aggregate=np.median,
        metric='cosine',
        width=int(librosa.time_to_frames(2, sr=sr))
    )
    S_filter = np.minimum(S_full, S_filter)
    margin_v = 5
    power = 2
    mask_v = librosa.util.softmask(
        S_full - S_filter,
        margin_v * S_filter,
        power=power
    )
    S_foreground = mask_v * S_full
    y_foreground = librosa.istft(S_foreground*phase)
    return y_foreground

def download_content(url, cwd='.'):
    # prefixes = list()
    cmd = f"youtube-dl -i --print-json --write-auto-sub --sub-format vtt --sub-lang en -x --audio-format wav {url}"
    p = sp.Popen(cmd.split(), stdout=sp.PIPE, stderr=sp.PIPE, cwd=cwd)
    i = 0
    for line in iter(p.stdout.readline, ''):
        if line == '':
            break
        try:
            info = json.loads(line)
        except:
            pass
        else:
            old_prefix = os.path.splitext(info['_filename'])[0]
            old_path_prefix = os.path.join(cwd, old_prefix)
            has_captions = False
            if 'en' in info['automatic_captions']:
                for fmt in info['automatic_captions']['en']:
                    if fmt['ext'] == 'vtt':
                        has_captions = True
            if has_captions:
                wav_file = old_path_prefix+".wav"
                sub_file = old_path_prefix+".en.vtt"
                while not all(map(os.path.exists, [wav_file, sub_file])):
                    if p.poll() is not None:
                        raise Exception("Connection broken")
                    time.sleep(0.1)
                sz = 0
                while os.stat(wav_file).st_size > sz:
                    sz = os.stat(wav_file).st_size
                    time.sleep(0.1)
                new_prefix = info['id']
                new_path_prefix = os.path.join(cwd, new_prefix, new_prefix)
                os.makedirs(
                    os.path.dirname(new_path_prefix),
                    exist_ok=True
                )
                os.rename(old_path_prefix+".wav", new_path_prefix+".wav")
                os.rename(old_path_prefix+".en.vtt", new_path_prefix+".en.vtt")
                # prefixes.append(new_prefix)
                print(i, new_prefix)
                yield new_prefix
            else:
                wav_file = old_path_prefix+".wav"
                while not os.path.exists(wav_file):
                    if p.poll() is not None:
                        raise Exception("Connection broken")
                    time.sleep(0.1)
                os.remove(old_path_prefix+".wav")
        i += 1

def chunk_content(prefix, cwd='.', chunk_length=10, write_corpus=True):
    chunk_dir = os.path.join(cwd, prefix, "chunks")
    if os.path.exists(chunk_dir):
        shutil.rmtree(chunk_dir)
    os.makedirs(chunk_dir, exist_ok=True)
    # wav = AudioSegment.from_wav(os.path.join(cwd, prefix, prefix)+'.wav')
    y, sr = librosa.load(os.path.join(cwd, prefix, prefix)+'.wav', sr=44100)
    text = ""
    delta = 0
    i = 0
    prev_line = None
    for cap in wv.read(os.path.join(cwd, prefix, prefix)+".en.vtt"):
        for line in cap.text.split('\n'):
            if (prev_line is None) or (prev_line not in line):
                if line.strip() != '':
                    if text == '':
                        start = cap.start_in_seconds
                    else:
                        text += ' '
                    end = cap.end_in_seconds
                    text += line
                    if end-start > chunk_length:
                        chunk_prefix = os.path.join(chunk_dir, f"chunk_{i}")
                        with open(chunk_prefix+".raw", 'w') as fh:
                            fh.write(text)
                        text = tokenize(text)
                        with open(chunk_prefix+".txt", 'w') as fh:
                            fh.write(text)
                        if write_corpus:
                            yield text
                        # start_ms = round(start*1e3)
                        # end_ms = round(end*1e3)
                        # wav_chunk = wav[start_ms:end_ms]
                        # wav_chunk.export(chunk_prefix+".wav", format="wav")
                        y_chunk = y[start*sr:end*sr]
                        y_chunk = filter_background(y_chunk, sr=sr)
                        librosa.output.write_wav(chunk_prefix+".wav", y_chunk, sr)
                        i += 1
                        text = ""
                    prev_line = line

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download and chunk audio and text from youtube video.')
    parser.add_argument('url', help='youtube video url')
    parser.add_argument('--out-dir', '-o', dest='out_dir', default='.', help='output directory')
    parser.add_argument('--chunk-length', '-c', dest='chunk_length', type=int, default=10, help='max length of chunks in seconds')
    parser.add_argument('--write-corpus', '-w', dest='write_corpus', action='store_true', help='write text to corpus')
    args = parser.parse_args()

    with open(os.path.join(args.out_dir, "corpus.txt"), 'w') as corpus_fh:
        for prefix in download_content(args.url, cwd=args.out_dir):
            for line in chunk_content(prefix, cwd=args.out_dir, chunk_length=args.chunk_length, write_corpus=args.write_corpus):
                corpus_fh.write(line+'\n')
