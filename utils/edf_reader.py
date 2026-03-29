"""
utils/edf_reader.py
Reads EDF files using MNE.
Extracts EEG Fpz-Cz, EOG horizontal, EMG submental.
Reads sleep stage annotations from annotation EDF.
"""

import mne
import numpy as np
import pandas as pd

# Channels we want — flexible name matching
CHANNEL_ALIASES = {
    'EEG Fpz-Cz': ['EEG Fpz-Cz', 'EEG FpzCz', 'Fpz-Cz', 'EEG1', 'eeg fpz-cz'],
    'EOG horizontal': ['EOG horizontal', 'EOG Horizontal', 'EOG horiz', 'EOG', 'eog'],
    'EMG submental':  ['EMG submental', 'EMG Submental', 'EMG', 'emg submental'],
}

STAGE_MAP = {
    'Sleep stage W':   'W',
    'Sleep stage 1':   'N1',
    'Sleep stage 2':   'N2',
    'Sleep stage 3':   'N3',
    'Sleep stage 4':   'N3',   # N4 → N3 in AASM
    'Sleep stage R':   'REM',
    'Sleep stage ?':   'W',
    'W':   'W',
    'N1':  'N1',
    'N2':  'N2',
    'N3':  'N3',
    'R':   'REM',
    'REM': 'REM',
}

EPOCH_SEC = 30  # standard 30-second epochs


def find_channel(available, target_aliases):
    """Find channel name from list of aliases."""
    available_lower = {c.lower(): c for c in available}
    for alias in target_aliases:
        if alias.lower() in available_lower:
            return available_lower[alias.lower()]
    return None


def read_edf(edf_path):
    """
    Read raw EDF file.
    Returns:
        signals      — dict {channel_name: numpy array of raw signal}
        sfreq        — sampling frequency (Hz)
        channel_names — list of found channel names
    """
    raw = mne.io.read_raw_edf(edf_path, preload=True, verbose=False)
    sfreq = raw.info['sfreq']
    available = raw.ch_names

    signals = {}
    found_names = []

    for label, aliases in CHANNEL_ALIASES.items():
        ch = find_channel(available, aliases)
        if ch is not None:
            data = raw.get_data(picks=[ch])[0]  # shape (n_samples,)
            signals[label] = data
            found_names.append(label)
            print(f"✓ Found channel: {label} ({ch})")
        else:
            print(f"⚠ Channel not found: {label} — tried {aliases}")

    if not signals:
        raise ValueError(f"No matching channels found. Available: {available}")

    return signals, sfreq, found_names


def read_annotations(ann_path):
    """
    Read annotation EDF file (hypnogram).
    Returns:
        stages      — list of stage strings ['W','N1','N2','N3','REM',...]
        epoch_times — list of start times in minutes
    """
    try:
        # Try reading as EDF annotations
        ann = mne.read_annotations(ann_path)
        stages = []
        epoch_times = []

        for desc, onset, duration in zip(ann.description, ann.onset, ann.duration):
            stage = STAGE_MAP.get(desc.strip(), None)
            if stage is None:
                # Try partial match
                for key, val in STAGE_MAP.items():
                    if key.lower() in desc.lower():
                        stage = val
                        break
            if stage is not None:
                n_epochs = max(1, int(round(duration / EPOCH_SEC)))
                for j in range(n_epochs):
                    stages.append(stage)
                    epoch_times.append((onset + j * EPOCH_SEC) / 60.0)  # minutes

    except Exception:
        # Fallback: try reading as raw EDF with annotations
        raw_ann = mne.io.read_raw_edf(ann_path, preload=False, verbose=False)
        ann = raw_ann.annotations
        stages = []
        epoch_times = []

        for desc, onset, duration in zip(ann.description, ann.onset, ann.duration):
            stage = STAGE_MAP.get(desc.strip(), None)
            if stage is None:
                for key, val in STAGE_MAP.items():
                    if key.lower() in desc.lower():
                        stage = val
                        break
            if stage is not None:
                n_epochs = max(1, int(round(duration / EPOCH_SEC)))
                for j in range(n_epochs):
                    stages.append(stage)
                    epoch_times.append((onset + j * EPOCH_SEC) / 60.0)

    print(f"✓ Annotations read: {len(stages)} epochs")
    print(f"  Stage counts: { {s: stages.count(s) for s in set(stages)} }")

    return stages, [round(t, 2) for t in epoch_times]


def extract_epoch_features(signals, sfreq, stages, epoch_times):
    """
    Extract RMS features per 30-second epoch for each channel.
    Returns a DataFrame for VAR analysis.
    """
    samples_per_epoch = int(sfreq * EPOCH_SEC)
    n_epochs = len(stages)
    rows = []

    for i in range(n_epochs):
        row = {'epoch': i, 'time_min': epoch_times[i], 'stage': stages[i]}
        start = i * samples_per_epoch
        end   = start + samples_per_epoch

        for ch_name, signal in signals.items():
            epoch_data = signal[start:end] if end <= len(signal) else signal[start:]
            if len(epoch_data) > 0:
                row[f'{ch_name}_rms']  = float(np.sqrt(np.mean(epoch_data**2)))
                row[f'{ch_name}_mean'] = float(np.mean(epoch_data))
                row[f'{ch_name}_std']  = float(np.std(epoch_data))
            else:
                row[f'{ch_name}_rms']  = 0.0
                row[f'{ch_name}_mean'] = 0.0
                row[f'{ch_name}_std']  = 0.0

        rows.append(row)

    return pd.DataFrame(rows)
