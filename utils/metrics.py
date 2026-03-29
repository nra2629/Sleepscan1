"""
utils/metrics.py
Computes sleep metrics from stage sequence.
"""

from collections import Counter
import numpy as np


def compute_sleep_metrics(stages):
    n = len(stages)
    counts = Counter(stages)
    sleep_stages = {'N1', 'N2', 'N3', 'REM'}
    n_sleep = sum(counts.get(s, 0) for s in sleep_stages)

    pct = {s: round(counts.get(s, 0) / n * 100, 1) for s in ['W','N1','N2','N3','REM']}
    transitions = sum(1 for i in range(1, n) if stages[i] != stages[i-1])
    awakenings  = sum(1 for i in range(1, n) if stages[i] == 'W' and stages[i-1] in sleep_stages)
    efficiency  = round(n_sleep / n * 100, 1) if n > 0 else 0.0
    tst_hours   = round(n_sleep * 30 / 3600, 2)
    tib_hours   = round(n * 30 / 3600, 2)

    return {
        'n_epochs':    n,
        'tst_hours':   tst_hours,
        'tib_hours':   tib_hours,
        'efficiency':  efficiency,
        'transitions': transitions,
        'awakenings':  awakenings,
        'stage_pct':   pct,
        'n3_pct':      pct.get('N3', 0),
        'rem_pct':     pct.get('REM', 0),
        'wake_pct':    pct.get('W', 0),
    }
