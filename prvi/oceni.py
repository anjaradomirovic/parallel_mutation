import math
import json


BLOSUM62 = json.load(open('blosum62.json'))
PARETO_ANCHORS = json.load(open('anchors.json'))
AA = set('ACDEFGHIKLMNPQRSTVWY')


def get_blosum_distance(seq1, seq2):
    score = 0
    max_score1 = 0
    max_score2 = 0
    for a, b in zip(seq1, seq2):
        score += BLOSUM62[a][b]
        max_score1 += BLOSUM62[a][a]
        max_score2 += BLOSUM62[b][b]
    max_self = max(max_score1, max_score2)
    return 1.0 - (max(0, score) / max_self)

def oceni(seq):
    player_seq = seq.upper().strip()

    # Absolute exact match intercept
    for name, data in PARETO_ANCHORS.items():
        if seq == data["seq"]:
            return data["stats"]

    t_sum, s_sum, e_sum = 0.0, 0.0, 0.0
    total_weight = 0.0
    min_distance = 1.0

    for name, data in PARETO_ANCHORS.items():
        dist = get_blosum_distance(seq, data["seq"])
        if dist < min_distance:
            min_distance = dist

        if dist < 0.001: dist = 0.001

        # High power IDW cleanly blends neighboring nodes
        weight = 1.0 / (dist ** 4)
        total_weight += weight

        t_sum += data["stats"][0] * weight
        s_sum += data["stats"][1] * weight
        e_sum += data["stats"][2] * weight

    t = t_sum / total_weight
    s = s_sum / total_weight
    e = e_sum / total_weight

    # THE CORRECTION: Apply an exponential decay multiplier based on distance.
    # Moving away from exact anchor landmarks instantly scales numbers downward.
    # A single mutation away from Wuhan scales the output directly toward zero.
    decay_strictness = 8.0
    viability_decay = math.exp(-decay_strictness * min_distance)

    t *= viability_decay
    s *= viability_decay
    e *= viability_decay

    return min(10.0, round(t, 2)), min(10.0, round(s, 2)), min(10.0, round(e, 2))

# --- CLEAN TESTING EXAMPLES ---
# Exact match works cleanly
print("Pure Delta Profile:", oceni("TEIYQAGSTPCNGVEGFNCYFPLQSYGFQPTN"))

# Chaotic broken sequence naturally drops to zero via the viability decay multiplier
print("Biologically Broken (RWRW...):", oceni("RWRWRWRWRWRWRWRWRWRWRWRWRWRWRWRW"))
