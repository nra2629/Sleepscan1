"""
utils/edf_reader.py
Reads EDF files using pyedflib (lightweight — no MNE needed).
Much lower memory footprint — suitable for Render free tier.
"""

import pyedflib
import numpy as np
import pandas as pd

CHANNEL_ALIASES = {
    'EEG Fpz-Cz': ['EEG Fpz-Cz', 'EEG FpzCz', 'Fpz-Cz', 'EEG1', 'eeg fpz-cz', 'fpzcz'],
    'EOG horizontal': ['EOG horizontal', 'EOG Horizontal', 'EOG horiz', 'EOG', 'eog'],
    'EMG submental':  ['EMG submental', 'EMG Submental', 'EMG', 'emg submental'],
}

STAGE_MAP = {
    'Sleep stage W':   'W',
    'Sleep stage 1':   'N1',
    'Sleep stage 2':   'N2',
    'Sleep stage 3':   'N3',
    'Sleep stage 4':   'N3',
    'Sleep stage R':   'REM',
    'Sleep stage ?':   'W',
    'W':   'W', 'N1': 'N1', 'N2': 'N2',
    'N3':  'N3', 'R':  'REM', 'REM': 'REM',
}

EPOCH_SEC = 30


def find_channel(available, aliases):
    available_lower = {c.lower().strip(): c for c in available}
    for alias in aliases:
        if alias.lower() in available_lower:
            return available_lower[alias.lower()]
    return None


def read_edf(edf_path):
    """
    Read raw EDF using pyedflib.
    Returns signals dict, sfreq, channel_names list.
    """
    f = pyedflib.EdfReader(edf_path)
    n_channels = f.signals_in_file
    ch_names   = f.getSignalLabels()
    sfreq      = f.getSampleFrequency(0)

    signals = {}
    found   = []

    for label, aliases in CHANNEL_ALIASES.items():
        ch = find_channel(ch_names, aliases)
        if ch is not None:
            idx  = list(ch_names).index(ch)
            data = f.readSignal(idx).astype(np.float32)
            signals[label] = data
            found.append(label)
            print(f"✓ Channel: {label} ({ch})")
        else:
            print(f"⚠ Not found: {label}")

    f.close()

    if not signals:
        raise ValueError(f"No matching channels. Available: {ch_names}")

    return signals, float(sfreq), found


def read_annotations(ann_path):
    """
    Read sleep stage annotations from annotation EDF.
    Returns stages list and epoch_times list (in minutes from start).
    """
    stages      = []
    epoch_times = []

    try:
        f   = pyedflib.EdfReader(ann_path)
        ann = f.readAnnotations()
        f.close()

        # ann = (onsets, durations, descriptions)
        onsets       = ann[0]
        durations    = ann[1]
        descriptions = ann[2]

        for onset, duration, desc in zip(onsets, durations, descriptions):
            desc  = desc.strip()
            stage = STAGE_MAP.get(desc, None)

            if stage is None:
                for key, val in STAGE_MAP.items():
                    if key.lower() in desc.lower():
                        stage = val
                        break

            if stage is not None:
                dur_sec  = float(duration) if float(duration) > 0 else EPOCH_SEC
                n_epochs = max(1, int(round(dur_sec / EPOCH_SEC)))
                for j in range(n_epochs):
                    stages.append(stage)
                    epoch_times.append(round((float(onset) + j * EPOCH_SEC) / 60.0, 2))

    except Exception as e:
        print(f"Annotation read error: {e}")
        raise

    print(f"✓ {len(stages)} epochs — {dict(zip(*np.unique(stages, return_counts=True)))}")
    return stages, epoch_times


def extract_epoch_features(signals, sfreq, stages, epoch_times):
    """
    Extract RMS features per epoch for each channel.
    """
    samples_per_epoch = int(sfreq * EPOCH_SEC)
    n_epochs = len(stages)
    rows = []

    for i in range(n_epochs):
        row   = {'epoch': i, 'time_min': epoch_times[i], 'stage': stages[i]}
        start = i * samples_per_epoch
        end   = start + samples_per_epoch

        for ch, signal in signals.items():
            seg = signal[start:end] if end <= len(signal) else signal[start:]
            if len(seg) > 0:
                row[f'{ch}_rms']  = float(np.sqrt(np.mean(seg**2)))
                row[f'{ch}_mean'] = float(np.mean(seg))
                row[f'{ch}_std']  = float(np.std(seg))
            else:
                row[f'{ch}_rms']  = 0.0
                row[f'{ch}_mean'] = 0.0
                row[f'{ch}_std']  = 0.0

        rows.append(row)

    return pd.DataFrame(rows)
