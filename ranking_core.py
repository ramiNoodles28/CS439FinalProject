from core import load_schools, chance

schools = load_schools()

NAME = "ab"
STATE = "st"
TUITION_IN = "tin"
TUITION_OUT = "tout"
SAT = "sat"
ADM = "adm"      # admission rate, percent
GR = "gr"        # 4yr completion rate, percent
EARN = "earn"    # 10-yr median earnings


def _max(col: str) -> float:
    return schools[col].max()


def create_school_metrics(index: int, is_in_state: bool = False):
    s = schools.iloc[index]

    if is_in_state:
        tuition = s[TUITION_IN]
        tuition_pct = 1 - (tuition / _max(TUITION_IN))
    else:
        tuition = s[TUITION_OUT]
        tuition_pct = 1 - (tuition / _max(TUITION_OUT))
    tuition_label = tuition

    earning = s[EARN]
    earning_pct = earning / _max(EARN)
    earning_label = earning

    sat_pct = s[SAT] / _max(SAT)
    sat_label = s[SAT]

    grad_pct = s[GR] / _max(GR)
    grad_label = round(s[GR], 2)

    admit_label = round(s[ADM], 2)

    return {
        "tuition": (tuition_pct, tuition_label),
        "grad": (grad_pct, grad_label),
        "earning": (earning_pct, earning_label),
        "admit": (s[ADM] / 100, admit_label),
        "sat": (sat_pct, sat_label),
    }


def create_school_profile(index: int, selector_stats: dict, state_of_residency: str, active: bool = False):
    """
    state_of_residency: valid 2 letter state abbreviation
    """
    s = schools.iloc[index]

    is_in_state = state_of_residency == s[STATE]
    residency = "In-state" if is_in_state else "Out-of-state"

    metrics = create_school_metrics(index, is_in_state)

    p, feasibility = chance(s, selector_stats['sat'])

    # TODO: create methods for
    #       2. Fit score

    return {
        "name": s[NAME],
        "residency": residency,
        "metrics": metrics,
        "category": feasibility,
        "fit_score": 50,
        "active": active,
    }


def generate_ranking_list(indices: list[int], state_of_residency: str, active: bool = False, selector_stats: dict = None):
    """indices: list of row indices into the core schools frame"""
    if selector_stats is None:
        selector_stats = {"sat": 1420}  # core default SAT
    # active is on/off for all, TODO: figure out how we want it to work
    return [create_school_profile(index, selector_stats, state_of_residency, active) for index in indices]
