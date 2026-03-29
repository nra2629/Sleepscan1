"""
utils/clustering.py
Matches patient to one of 5 clusters based on age, gender, sleep onset.
"""

import numpy as np

CLUSTER_CENTROIDS = {
    0: {'age': 40,  'onset_min': 1397, 'gender': 'female'},
    1: {'age': 38,  'onset_min': 1435, 'gender': 'male'},
    2: {'age': 63,  'onset_min': 1456, 'gender': 'female'},
    3: {'age': 83,  'onset_min': 1338, 'gender': 'female'},
    4: {'age': 75,  'onset_min': 1388, 'gender': 'male'},
}

CLUSTER_PROFILES = {
    0: {
        'name':  'Mid-age Late-sleeping Female',
        'label': 'Late-onset sleep pattern',
        'desc':  (
            'This person tends to fall asleep later in the evening, which is common among middle-aged adults. '
            'Their sleep architecture shows a pattern of delayed onset with moderate fragmentation. '
            'People in this group often experience lighter transitions between sleep stages and may benefit from consistent sleep timing.'
        ),
    },
    1: {
        'name':  'Late-sleeping Male',
        'label': 'Evening-type sleep pattern',
        'desc':  (
            'This person has a naturally late sleep timing, falling asleep closer to midnight. '
            'This is a well-known pattern in younger to middle-aged males and reflects a delayed internal body clock. '
            'Sleep quality in this group is often good once sleep begins, but total sleep time may be shortened by morning obligations.'
        ),
    },
    2: {
        'name':  'Older Late-sleeping Female',
        'label': 'Stable late-onset pattern',
        'desc':  (
            'Despite a late sleep onset, this person shows remarkably stable and consistent sleep once asleep. '
            'This is an unusual but documented pattern in older females where the body clock shifts later rather than earlier with age. '
            'Sleep depth is generally well preserved and signal activity is highly regular throughout the night.'
        ),
    },
    3: {
        'name':  'Elderly Early-sleeping Female',
        'label': 'Early-onset sleep pattern',
        'desc':  (
            'This person falls asleep early in the evening, which is a well-understood change that comes with age. '
            'As we get older, the internal body clock naturally shifts earlier. '
            'Sleep in this group tends to be lighter overall, with more frequent transitions between stages and earlier morning waking.'
        ),
    },
    4: {
        'name':  'Older Early-sleeping Male',
        'label': 'Balanced early-onset pattern',
        'desc':  (
            'This person goes to sleep at a moderately early time and shows well-organised sleep cycles through the night. '
            'This is one of the more efficient sleep patterns observed in the dataset. '
            'Brain and body signals work in a coordinated way, and the overall sleep architecture is relatively stable and healthy.'
        ),
    },
}

VAR_INSIGHTS = {
    0: {
        'insight': (
            'During this person\'s sleep, eye movements appear to trigger small responses in muscle activity. '
            'This means the body is subtly reacting to what the eyes do during sleep a pattern often seen in people who have more active or restless sleep. '
            'The brain itself, however, runs independently and is not strongly driven by eye or muscle signals. '
            'EMG muscle tone remains fairly consistent across the night, while eye activity is more variable, particularly during dream-rich periods.'
        ),
        'emg_persistence':  0.68,
        'eeg_persistence':  0.55,
        'eog_persistence':  0.48,
    },
    1: {
        'insight': (
            'In this person\'s sleep, the brain is clearly in charge. Brain activity directly influences both eye movements and muscle tone throughout the night. '
            'This top-down pattern means the brain is actively coordinating the body\'s behaviour during sleep rather than responding to it. '
            'Muscle tone is very stable and persistent, suggesting deep and continuous physical relaxation. '
            'This is a sign of well-regulated sleep where the brain governs the sleep process efficiently.'
        ),
        'emg_persistence':  0.81,
        'eeg_persistence':  0.72,
        'eog_persistence':  0.38,
    },
    2: {
        'insight': (
            'This person\'s sleep signals are highly self-contained. The brain, eyes, and muscles each follow their own independent rhythms with very little cross-influence between them. '
            'This kind of signal independence is associated with deep, undisturbed sleep where each physiological system is doing its job without interference. '
            'All three signals show strong predictability from one moment to the next, meaning sleep is smooth, consistent, and well-structured throughout the night.'
        ),
        'emg_persistence':  0.74,
        'eeg_persistence':  0.69,
        'eog_persistence':  0.61,
    },
    3: {
        'insight': (
            'This person shows a highly connected pattern where brain activity and eye movements continuously influence each other during sleep. '
            'This bidirectional relationship means the sleep process is more dynamic and interactive than average. '
            'Muscle activity shows some unusual behaviour, occasionally responding in ways that go against the expected direction. '
            'This level of signal interaction is often seen in lighter or more fragmented sleep where the brain remains more actively engaged throughout the night.'
        ),
        'emg_persistence':  0.52,
        'eeg_persistence':  0.61,
        'eog_persistence':  0.58,
    },
    4: {
        'insight': (
            'This person\'s sleep shows a well-balanced pattern where signals are mostly self-sustaining, with the brain playing a gentle coordinating role. '
            'Each signal brain waves, eye movements, and muscle tone is highly predictable from moment to moment, indicating smooth and efficient sleep. '
            'There is some cross-signal communication originating from the brain, but it is mild rather than dominant. '
            'Overall this pattern reflects well-organised, efficient sleep with good physiological coordination throughout the night.'
        ),
        'emg_persistence':  0.77,
        'eeg_persistence':  0.66,
        'eog_persistence':  0.54,
    },
}


def parse_onset(sleep_onset_str):
    try:
        h, m = map(int, sleep_onset_str.split(':'))
        total = h * 60 + m
        if total < 720:
            total += 1440
        return total
    except Exception:
        return 1380


def match_cluster(age, gender, sleep_onset_str):
    onset_min  = parse_onset(sleep_onset_str)
    gender_str = str(gender).lower()
    best_id    = 0
    best_dist  = float('inf')

    for cid, centroid in CLUSTER_CENTROIDS.items():
        age_dist    = abs(age - centroid['age']) / 50.0
        onset_dist  = abs(onset_min - centroid['onset_min']) / 120.0
        gender_dist = 0.0 if gender_str == centroid['gender'] else 0.5
        dist        = age_dist + onset_dist + gender_dist
        if dist < best_dist:
            best_dist = dist
            best_id   = cid

    profile = CLUSTER_PROFILES[best_id]
    return best_id, profile['name']
