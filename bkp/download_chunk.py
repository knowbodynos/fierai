import os
import argparse
import shutil
import string
import time
import json
import tqdm
import inflect
import re
import webvtt as wv
import subprocess as sp
import librosa
import numpy as np
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
                    new_word = new_word.replace(" and", "")
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

def filter_background(y, sample_rate=None):
    S_full, phase = librosa.magphase(librosa.stft(y))

    S_filter = librosa.decompose.nn_filter(
        S_full,
        aggregate=np.median,
        metric='cosine',
        width=int(librosa.time_to_frames(2, sr=sample_rate))
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

def extract_features(y, sample_rate=None):
    # Generates a Short-time Fourier transform (STFT) to use in the chroma_stft
    stft = np.abs(librosa.stft(y))
    # Generate Mel-frequency cepstral coefficients (MFCCs) from a time series 
    mfccs = librosa.feature.mfcc(y=y, sr=sample_rate, n_mfcc=40).mean(axis=1)
    # Computes a chromagram from a waveform or power spectrogram.
    chroma = librosa.feature.chroma_stft(S=stft, sr=sample_rate).mean(axis=1)
    # Computes a mel-scaled spectrogram.
    mel = librosa.feature.melspectrogram(y, sr=sample_rate).mean(axis=1)
    # Computes spectral contrast
    contrast = librosa.feature.spectral_contrast(S=stft, sr=sample_rate).mean(axis=1)
    # Computes the tonal centroid features (tonnetz)
    tonnetz = librosa.feature.tonnetz(y=librosa.effects.harmonic(y), sr=sample_rate).mean(axis=1)
    return np.concatenate([mfccs, chroma, mel, contrast, tonnetz], axis=0)

def download_content(url, playlist_start=1, cwd='.'):
    # prefixes = list()
    cmd = f"youtube-dl -i --print-json --write-auto-sub --sub-format vtt --sub-lang en -x --audio-format wav --playlist-start {playlist_start} {url}"
    p = sp.Popen(cmd.split(), stdout=sp.PIPE, stderr=sp.PIPE, cwd=cwd)
    vid_num = playlist_start
    for line in iter(p.stdout.readline, b''):
        if line == b'':
            break
        try:
            info = json.loads(line)
        except:
            pass
        else:
            prefix = os.path.splitext(info['_filename'])[0]
            prefix = os.path.join(cwd, prefix)
            has_captions = False
            if 'en' in info['automatic_captions']:
                for fmt in info['automatic_captions']['en']:
                    if fmt['ext'] == 'vtt':
                        has_captions = True
            if has_captions:
                wav_file = prefix+".wav"
                sub_file = prefix+".en.vtt"
                start = time.time()
                while not all(map(os.path.exists, [wav_file, sub_file])):
                    if p.poll() is not None:
                        raise Exception("Connection broken")
                    if time.time()-start > 120:
                        break
                    time.sleep(0.1)
                sz = 0
                while os.stat(wav_file).st_size > sz:
                    sz = os.stat(wav_file).st_size
                    time.sleep(0.1)
                yt_id = info['id']
                # new_path_prefix = os.path.join(cwd, new_prefix, new_prefix)
                # os.makedirs(
                #     os.path.dirname(new_path_prefix),
                #     exist_ok=True
                # )
                # os.rename(old_path_prefix+".wav", new_path_prefix+".wav")
                # os.rename(old_path_prefix+".en.vtt", new_path_prefix+".en.vtt")
                # prefixes.append(new_prefix)
                # print(i, yt_id, os.path.basename(prefix))
                yield (vid_num, yt_id, prefix)
            else:
                wav_file = prefix+".wav"
                start = time.time()
                while not os.path.exists(wav_file):
                    if p.poll() is not None:
                        raise Exception("Connection broken")
                    if time.time()-start > 120:
                        break
                    time.sleep(0.1)
                os.remove(wav_file)
        vid_num += 1

def chunk_content(vid_num, yt_id, prefix, chunk_length=10, sample_rate=None):
    # chunk_dir = os.path.join(cwd, prefix, "chunks")
    # if os.path.exists(chunk_dir):
    #     shutil.rmtree(chunk_dir)
    # os.makedirs(chunk_dir, exist_ok=True)
    # wav = AudioSegment.from_wav(os.path.join(cwd, prefix, prefix)+'.wav')
    y, sample_rate = librosa.load(prefix+".wav", sr=sample_rate)
    total = len(y) / sample_rate
    text = ""
    # delta = 0
    chunk = 0
    prev_line = None
    with tqdm.tqdm(total=total, unit_scale=True, desc=f"{vid_num} {yt_id}") as pbar:
        for cap in wv.read(prefix+".en.vtt"):
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
                            # chunk_prefix = os.path.join(chunk_dir, f"chunk_{chunk}")
                            # start_ms = round(start*1e3)
                            # end_ms = round(end*1e3)
                            # wav_chunk = wav[start_ms:end_ms]
                            # wav_chunk.export(chunk_prefix+".wav", format="wav")
                            pos_start = round(start*sample_rate)
                            pos_end = round(end*sample_rate)
                            y_chunk = y[pos_start:pos_end]
                            try:
                                y_chunk = filter_background(y_chunk, sample_rate=sample_rate)
                                features = extract_features(y_chunk, sample_rate=sample_rate)
                            except Exception as e:
                                print(repr(e))
                            # librosa.output.write_wav(chunk_prefix+".wav", y_chunk, sample_rate)
                            yield (chunk, text, y_chunk, sample_rate, features)
                            chunk += 1
                            text = ""
                        prev_line = line
            pbar.update(cap.end_in_seconds-pbar.n)
        pbar.update(total-pbar.n)
    os.remove(prefix+".wav")
    os.remove(prefix+".en.vtt")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download and chunk audio and text from youtube video.')
    parser.add_argument('url', help='youtube video url')
    parser.add_argument('--out-dir', '-o', dest='out_dir', default='.', help='output directory (default is current working directory')
    parser.add_argument('--chunk-length', '-c', dest='chunk_length', type=int, default=10, help='max length of chunks in seconds (default is 10')
    parser.add_argument('--sample-rate', '-s', dest='sample_rate', type=int, default=None, help='sample rate')
    parser.add_argument('--playlist-start', '-p', dest='playlist_start', type=int, default=1, help='playlist video to start at (default is 1)')
    args = parser.parse_args()

    audio_dir = os.path.join(args.out_dir, "audio")
    features_dir = os.path.join(args.out_dir, "features")
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(features_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "corpus.tsv"), 'w') as corpus_fh:
        for vid_num, yt_id, prefix in download_content(args.url, playlist_start=args.playlist_start, cwd=args.out_dir):
            chunks = chunk_content(vid_num, yt_id, prefix, chunk_length=args.chunk_length, sample_rate=args.sample_rate)
            for chunk, raw_text, audio, sample_rate, features in chunks:
                text = tokenize(raw_text)
                label = f"{yt_id}_{chunk}"
                print(label, raw_text, text, sep='\t', file=corpus_fh, flush=True)
                wav_fn = os.path.join(audio_dir, label+".wav")
                librosa.output.write_wav(wav_fn, audio, sample_rate)
                np.save(os.path.join(features_dir, label), features)
