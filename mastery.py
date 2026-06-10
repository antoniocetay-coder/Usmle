from enum import Enum
import math


class MasteryLevel(Enum):
    DRONE        = "drone"
    NEW          = "new"
    LEARNING     = "learning"
    CONSOLIDATED = "consolidated"
    CONSOLIDATED_VERIFIED = "consolidated_verified"
    MASTERED     = "mastered"
    MASTERED_VERIFIED   = "mastered_verified"


P_L0 = 0.15

P_GUESS_BASE = 0.20
P_SLIP_BASE  = 0.15
P_T_BASE     = 0.10

DIFFICULTY_RANK = {"Easy": 0, "Medium": 1, "Hard": 2, "Insane": 3}

COGNITIVE_RANK = {
    "1st Order (Direct Recall / Diagnosis)": 0,
    "2nd Order (Pathophysiology / Next Step)": 1,
    "3rd Order (Integrated Reasoning / Complications)": 2,
}

RANK_TO_DIFFICULTY = {0: "Easy", 1: "Medium", 2: "Hard", 3: "Insane"}
RANK_TO_COGNITIVE = {
    0: "1st Order (Direct Recall / Diagnosis)",
    1: "2nd Order (Pathophysiology / Next Step)",
    2: "3rd Order (Integrated Reasoning / Complications)",
}

DELTA_DIFF = {
    "Easy":   {"p_guess": +0.20, "p_slip": -0.05, "p_t": -0.05},
    "Medium": {"p_guess":  0.00, "p_slip":  0.00, "p_t":  0.00},
    "Hard":   {"p_guess": -0.10, "p_slip": +0.05, "p_t": +0.08},
    "Insane": {"p_guess": -0.15, "p_slip": +0.10, "p_t": +0.15},
}

CEILINGS = {
    ("Easy",   0): 0.40,
    ("Easy",   1): 0.50,
    ("Medium", 0): 0.55,
    ("Medium", 1): 0.70,
    ("Hard",   1): 0.85,
    ("Hard",   2): 0.92,
    ("Insane", 1): 0.93,
    ("Insane", 2): 0.99,
}


def update_bkt(current_prob, is_correct, confidence, dificuldade="Medium", total_attempts=0):
    if current_prob is None:
        current_prob = P_L0

    mod = DELTA_DIFF.get(dificuldade, DELTA_DIFF["Medium"])

    if confidence == "Chute Cego":
        p_guess = 0.80
        p_slip  = 0.10
    elif confidence == "Certeza Absoluta":
        p_guess = 0.05
        p_slip  = 0.05
    else:
        p_guess = max(0.01, min(0.90, P_GUESS_BASE + mod["p_guess"]))
        p_slip  = max(0.01, min(0.50, P_SLIP_BASE  + mod["p_slip"]))

    if is_correct:
        prob_obs = (current_prob * (1 - p_slip)) / (
            (current_prob * (1 - p_slip)) + ((1 - current_prob) * p_guess)
        )
    else:
        prob_obs = (current_prob * p_slip) / (
            (current_prob * p_slip) + ((1 - current_prob) * (1 - p_guess))
        )

    p_t_mod = P_T_BASE + mod["p_t"]
    decay = 1 / (1 + 0.1 * math.sqrt(total_attempts))
    p_t_effective = p_t_mod * decay

    new_prob = prob_obs + (1 - prob_obs) * p_t_effective

    return max(0.01, min(0.99, new_prob))


def get_ceiling(dificuldade, cognitive_order):
    cog_rank = COGNITIVE_RANK.get(cognitive_order, 0)
    return CEILINGS.get((dificuldade, cog_rank), 0.40)


def real_knowledge(bkt_prob, max_difficulty="Easy", max_cognitive_order="1st Order (Direct Recall / Diagnosis)"):
    if bkt_prob is None:
        return P_L0

    ceiling = get_ceiling(max_difficulty, max_cognitive_order)

    if bkt_prob <= ceiling:
        return bkt_prob

    excess = bkt_prob - ceiling
    return ceiling + excess * 0.2


def get_next_level(real_know):
    if real_know < 0.30:
        return ("Easy",   "1st Order (Direct Recall / Diagnosis)")
    if real_know < 0.55:
        return ("Medium", "1st Order (Direct Recall / Diagnosis)")
    if real_know < 0.70:
        return ("Medium", "2nd Order (Pathophysiology / Next Step)")
    if real_know < 0.85:
        return ("Hard",   "2nd Order (Pathophysiology / Next Step)")
    if real_know < 0.93:
        return ("Hard",   "3rd Order (Integrated Reasoning / Complications)")
    return ("Insane", "3rd Order (Integrated Reasoning / Complications)")


def is_eligible_for_proof(real_know):
    return real_know >= 0.70


def classify_tag_bkt(prob, is_verified=False):
    if prob is None:
        return MasteryLevel.NEW
    if is_verified and prob >= 0.90:
        return MasteryLevel.MASTERED_VERIFIED
    if is_verified and prob >= 0.65:
        return MasteryLevel.CONSOLIDATED_VERIFIED
    if prob < 0.30:
        return MasteryLevel.NEW
    elif prob < 0.65:
        return MasteryLevel.LEARNING
    elif prob < 0.90:
        return MasteryLevel.CONSOLIDATED
    else:
        return MasteryLevel.MASTERED


def classify_tag(correct, total, threshold=3):
    if total == 0:
        return MasteryLevel.DRONE
    if total < threshold:
        return MasteryLevel.NEW
    accuracy = correct / total
    if accuracy < 0.50:
        return MasteryLevel.LEARNING
    elif accuracy < 0.80:
        return MasteryLevel.CONSOLIDATED
    else:
        return MasteryLevel.MASTERED
