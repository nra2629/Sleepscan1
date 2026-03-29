"""
utils/plotter.py
Sleep architecture — clean stacked timeline like Apple Health / Fitbit style.
One horizontal bar showing the full night, colour coded by stage.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import base64
import io

STAGE_COLORS = {
    'W':   '#dcd8f0',
    'N1':  '#98c8f0',
    'N2':  '#4a8ed0',
    'N3':  '#1a3a8a',
    'REM': '#b060d0',
}
STAGE_LABEL = {
    'W': 'Wake', 'N1': 'Light N1',
    'N2': 'Light N2', 'N3': 'Deep N3', 'REM': 'REM'
}


def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return b64


def get_runs(stages):
    if not stages:
        return []
    runs = []
    cur, start = stages[0], 0
    for i in range(1, len(stages)):
        if stages[i] != cur:
            runs.append((cur, start, i - 1))
            cur, start = stages[i], i
    runs.append((cur, start, len(stages) - 1))
    return runs


def plot_hypnogram(stages, epoch_times):
    """
    Two-part chart:
    TOP — single thick horizontal bar showing the full night colour coded
    BOTTOM — clean bar chart showing minutes spent in each stage
    """
    if not stages:
        return None

    # Trim leading wake
    sleep_start = 0
    for i, s in enumerate(stages):
        if s != 'W':
            sleep_start = max(0, i - 2)
            break

    stages_trim = stages[sleep_start:]
    n = len(stages_trim)
    epoch_min = 0.5  # 30 sec = 0.5 min
    total_min = n * epoch_min
    total_h   = total_min / 60.0

    runs = get_runs(stages_trim)

    fig = plt.figure(figsize=(13, 4.8))
    fig.patch.set_facecolor('white')

    # Two rows: top = timeline bar, bottom = duration bars
    gs = fig.add_gridspec(2, 1, height_ratios=[1.2, 2.8], hspace=0.55)
    ax_top = fig.add_subplot(gs[0])
    ax_bot = fig.add_subplot(gs[1])

    # ── TOP: full night timeline bar ─────────────────
    epoch_h = epoch_min / 60.0
    bar_h   = 0.6
    for s, start_i, end_i in runs:
        x = start_i * epoch_h
        w = (end_i - start_i + 1) * epoch_h
        rect = FancyBboxPatch(
            (x, -bar_h/2), w, bar_h,
            boxstyle='square,pad=0',
            facecolor=STAGE_COLORS.get(s, '#ccc'),
            edgecolor='none', linewidth=0, zorder=3
        )
        ax_top.add_patch(rect)

    # Round the ends
    for x0, col in [(0, STAGE_COLORS.get(stages_trim[0], '#ccc')),
                    (total_h, STAGE_COLORS.get(stages_trim[-1], '#ccc'))]:
        pass

    ax_top.set_xlim(0, total_h)
    ax_top.set_ylim(-0.8, 1.4)

    # Hour tick marks
    for h in range(0, int(total_h) + 1):
        ax_top.axvline(h, color='white', linewidth=1.2, zorder=4)
        ax_top.text(h, 0.7, f'{h}h', ha='center', va='bottom',
                    fontsize=9, color='#888880')

    ax_top.axis('off')
    ax_top.set_title('Sleep timeline', fontsize=11,
                     color='#3a3530', loc='left', pad=8, fontweight='normal')

    # Legend inside top
    patches = [mpatches.Patch(color=STAGE_COLORS[s], label=STAGE_LABEL[s])
               for s in ['W', 'N1', 'N2', 'N3', 'REM']]
    ax_top.legend(handles=patches, loc='lower right', fontsize=8.5,
                  ncol=5, framealpha=0, edgecolor='none',
                  bbox_to_anchor=(1.0, -0.5))

    # ── BOTTOM: duration bar chart ────────────────────
    from collections import Counter
    counts = Counter(stages_trim)
    stage_order = ['W', 'REM', 'N1', 'N2', 'N3']
    stage_names = ['Wake', 'REM', 'Light N1', 'Light N2', 'Deep N3']
    durations   = [counts.get(s, 0) * epoch_min for s in stage_order]
    colors      = [STAGE_COLORS[s] for s in stage_order]

    bars = ax_bot.barh(
        stage_names, durations,
        color=colors, height=0.52,
        edgecolor='white', linewidth=1.0
    )

    # Value labels
    for bar, val in zip(bars, durations):
        if val > 3:
            h_val = val / 60.0
            label = f'{int(val)}m' if val < 60 else f'{h_val:.1f}h'
            ax_bot.text(
                bar.get_width() + total_min * 0.008,
                bar.get_y() + bar.get_height() / 2,
                label, va='center', fontsize=9.5,
                color='#4a4a4a', fontweight='500'
            )

    ax_bot.set_xlabel('Duration (minutes)', fontsize=10,
                      color='#3a3530', labelpad=6)
    ax_bot.set_xlim(0, max(durations) * 1.18 if durations else 60)
    ax_bot.set_title('Time spent in each stage', fontsize=11,
                     color='#3a3530', loc='left', pad=8, fontweight='normal')

    ax_bot.spines['top'].set_visible(False)
    ax_bot.spines['right'].set_visible(False)
    ax_bot.spines['left'].set_visible(False)
    ax_bot.tick_params(left=False)
    ax_bot.tick_params(axis='y', labelsize=10, colors='#3a3530')
    ax_bot.tick_params(axis='x', labelsize=9, colors='#888880')
    ax_bot.grid(True, axis='x', alpha=0.15,
                linestyle='--', color='#aaaaaa')

    plt.tight_layout(pad=1.4)
    return fig_to_base64(fig)


def plot_signals(signals, sfreq, channel_names, epoch_times):
    return None
