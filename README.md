# fierai
Come on down to Flavortown!

*"It's da bomb.com!"*, says some Guy on the internet

## Table of Contents
1. [Install](#install)
2. [Usage](#usage)
    - [Scrape](#scrape)
    - [Chunk](#chunk)
    - [Corpus](#corpus)


## Install
```
git clone https://github.com/knowbodynos/fierai.git
cd fierai
pip install --user .
```

or 

```
pip install --user git+https://github.com/knowbodynos/fierai.git
```

## Usage
```
usage: fierai [-h] {scrape,chunk,corpus} ...

Come on down to Flavortown.

positional arguments:
  {scrape,chunk,corpus}

optional arguments:
  -h, --help            show this help message and exit
```

### Scrape
```
usage: fierai scrape [-h] playlist_url

Scrape a YouTube playlist.

positional arguments:
  playlist_url  YouTube playlist URL to scrape.

optional arguments:
  -h, --help    show this help message and exit
```

### Chunk
```
usage: fierai chunk [-h] [--chunk-duration CHUNK_DURATION]
                    audio_file subtitles_file

Chunk audio and subtitle files.

positional arguments:
  audio_file            Path to audio file
  subtitles_file        Path to subtitles file

optional arguments:
  -h, --help            show this help message and exit
  --chunk-duration CHUNK_DURATION, -c CHUNK_DURATION
                        Max duration of chunks in seconds. [Default: 10]
```

### Corpus
```
usage: fierai corpus [-h] [--subs-dir SUBTITLES_DIR] [--train-frac TRAIN_FRAC]
                     [--valid-frac VALID_FRAC]

Create corpus from subtitles.

optional arguments:
  -h, --help            show this help message and exit
  --subs-dir SUBTITLES_DIR, -s SUBTITLES_DIR
                        Directory of parsed subtitles. [Default: '.']
  --train-frac TRAIN_FRAC, -t TRAIN_FRAC
                        Fraction of data to use for training. [Default: 0.7]
  --valid-frac VALID_FRAC, -v VALID_FRAC
                        Fraction of data to use for validation. [Default:
                        0.15]
```
