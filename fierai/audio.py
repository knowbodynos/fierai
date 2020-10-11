import librosa
import numpy as np
import soundfile as sf
from librosa.feature import mfcc, chroma_stft, melspectrogram, spectral_contrast, tonnetz


class Audio(object):
    def __init__(self, waveform: np.ndarray, sample_rate: float = None):
        self.waveform = waveform
        self.sample_rate = sample_rate

    def __len__(self):
        return len(self.waveform)

    def __getitem__(self, key):
        return self.waveform[key]

    @classmethod
    def load(cls, file: str, sample_rate: float = None):
        waveform, sample_rate = librosa.load(file, sr=sample_rate)
        return cls(waveform, sample_rate)

    @property
    def duration(self):
        idx = len(self.waveform)
        return self.idx_to_sec(idx)

    def idx_to_sec(self, idx):
        if idx is None:
            return None
        return idx / self.sample_rate

    def sec_to_idx(self, sec):
        if sec is None:
            return None
        return int(sec * self.sample_rate)

    def interval(self, start: float = None, stop: float = None):
        start, stop = map(self.sec_to_idx, (start, stop))
        chunk = self.waveform[start:stop]
        return Audio(chunk, self.sample_rate)

    def filter_background(self, margin_v: int = 5, power: int = 2):
        stft = librosa.stft(self.waveform)
        S_full, phase = librosa.magphase(stft)
        S_filter = librosa.decompose.nn_filter(
            S_full,
            aggregate=np.median,
            metric='cosine',
            width=int(librosa.time_to_frames(2, sr=self.sample_rate))
        )
        S_filter = np.minimum(S_full, S_filter)
        mask_v = librosa.util.softmask(
            S_full - S_filter,
            margin_v * S_filter,
            power=power
        )
        S_foreground = mask_v * S_full
        y_foreground = librosa.istft(S_foreground * phase)
        self.waveform = y_foreground
        return self

    def extract_features(self):
        # Generates a Short-time Fourier transform (STFT) to use in the chroma_stft
        stft = np.abs(librosa.stft(self.waveform))
        # Generate Mel-frequency cepstral coefficients (MFCCs) from a time series
        mfccs = mfcc(y=self.waveform, sr=self.sample_rate, n_mfcc=40).mean(axis=1)
        # Computes a chromagram from a waveform or power spectrogram.
        chroma = chroma_stft(S=stft, sr=self.sample_rate ).mean(axis=1)
        # Computes a mel-scaled spectrogram.
        mel = melspectrogram(self.waveform, sr=self.sample_rate).mean(axis=1)
        # Computes spectral contrast
        contrast = spectral_contrast(S=stft, sr=self.sample_rate).mean(axis=1)
        # Computes the tonal centroid features (tonnetz)
        harmonic = librosa.effects.harmonic(self.waveform)
        tonn = tonnetz(y=harmonic, sr=self.sample_rate).mean(axis=1)
        return np.concatenate([mfccs, chroma, mel, contrast, tonn], axis=0)

    def write(self, file):
        sf.write(file, self.waveform, self.sample_rate)
