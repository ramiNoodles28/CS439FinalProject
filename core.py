import math, os
from dataclasses import dataclass, field
import pandas as pd

#Colors/Formatting
LIKELY, TARGET, REACH = "#2f9e5a", "#3b6fd4", "#d93636"
CHANCE_COLOR = {"Likely": LIKELY, "Target": TARGET, "Reach": REACH}
A_COLOR, B_COLOR = "#0f8f7a", "#4f46e5"            #school compare colros
OVER_BUDGET, TEXT, MUTED, GRID = REACH, "#1b2333", "#6b7487", "#e3e7ef"
def money(v): return f"${v:,.0f}"
def money_k(v, _=None): return f"${v/1000:.0f}K"
def pct(v): return f"{v:.0f}%"

#DATA RULES
MAJORS = {"c11": "Computer Science", "c14": "Engineering", "c52": "Business"}
SIZE_LABELS, SIZE_CUTS = ["Small", "Medium", "Large", "Very large"], [3000, 9000, 30000] #preset
_SHORT = {"Purdue University-Main": "Purdue", "Indiana University-Bloomington": "Indiana University",
          "Urbana-Champaign": "UIUC", "Ann Arbor": "Michigan", "Michigan State": "Michigan State",
          "Wisconsin-Madison": "Wisconsin", "Ohio State University-Main": "Ohio State",
          "Pennsylvania State University-Main": "Penn State", "Minnesota-Twin": "Minnesota",
          "Illinois State": "Illinois State"}
_DEFAULTS = list(_SHORT)  
DEFAULT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "college_scorecard_fully_cleaned.csv")

def load_schools(path=DEFAULT_CSV):
    L = "latest."
    df = pd.read_csv(path)
    need = [L+"admissions.sat_scores.average.overall", L+"admissions.act_scores.25th_percentile.cumulative",
            L+"admissions.act_scores.75th_percentile.cumulative", "admit_rate_pct", L+"cost.tuition.in_state",
            L+"cost.tuition.out_of_state", "earn10_filled", L+"completion.completion_rate_4yr_150nt",
            L+"student.retention_rate.four_year.full_time", L+"student.size",
            L+"student.demographics.student_faculty_ratio", L+"school.state"]

    d = df.dropna(subset=need)
    d = d[d[L+"school.institutional_characteristics.level"] == 1]  # only 4-year schools
    s = pd.DataFrame({
        "n": d["label"], "raw": d["school.name"], "st": d[L+"school.state"],
        "tin": d[need[4]].round(), "tout": d[need[5]].round(), "sat": d[need[0]].round(),
        "a25": d[need[1]], "a75": d[need[2]], "adm": d["admit_rate_pct"].round(1),
        "gr": (d[need[7]]*100).round(1), "ret": (d[need[8]]*100).round(1), "sz": d[need[9]].round(),
        "sfr": d[need[10]].round(1), "earn": d["earn10_filled"].round(), "imp": d["earn10_is_fallback"].astype(bool),
        "c11": (d[L+"academics.cip_2_digit.cip_11"] > 0).astype(int),
        "c14": (d[L+"academics.cip_2_digit.cip_14"] > 0).astype(int),
        "c52": (d[L+"academics.cip_2_digit.cip_52"] > 0).astype(int)}).reset_index(drop=True)

    def short(raw, n):
        for k, v in _SHORT.items():
            if k in raw and not (k == "Purdue University-Main" and "Main" not in raw): return v
        return n if len(n) <= 24 else n[:23] + "..."

    s['ab'] = [short(r, n) for r, n in zip(s['raw'], s['n'])]
    return s.drop(columns="raw")

def default_selection(schools):
    names = schools['ab'].tolist()
    return [names.index(_SHORT[k]) for k in _DEFAULTS]

#Beginning State (Changeable)
@dataclass
class State:
    st: str = "IN"                    # in/out of state
    major: str = "c11"                # default to cs, "any" = no major preference
    sat: int = 1420                   # default SAT score
    act: int = 32                     # default ACT score (about the same as a 1420 SAT)
    use_sat: bool = True              # SAT box checked in the profile menu
    use_act: bool = False             # ACT box checked in the profile menu
    budget: int = 35000               # default tuition bidget
    pref_size: int = 3                # 0 Small 1 medium, 2 large3 Very large, None = any size
    weights: dict = field(default_factory=lambda: {"aff": 50, "earn": 50, "grad": 50, "adm": 50, "size": 50})  # each 0-100
    selected: list = field(default_factory=list)   # selected schools short list
    pair: list = field(default_factory=list)       # 2 selected schools comparison
    pair_target: int = 1              # which head-to-head side the next click replaces, 0 = A (blue), 1 = B (orange)
    scatter_mode: str = "auto"        # cost earnings chart

class Store:
    def __init__(self, state):
        self.state = state
        self.listeners = []

    def update(self, **kw):
        changed = set()
        for k, v in kw.items():
            if not hasattr(self.state, k):
                raise AttributeError(f"State has no field '{k}'")
            if getattr(self.state, k) != v:
                setattr(self.state, k, v)
                changed.add(k)
        if not changed:
            return
        for fn in self.listeners:
            try:
                fn(self.state, changed)
            except TypeError:
                fn(self.state)

    def commit_pair(self, pair=None, ranked_indices=None):
        pool = list(ranked_indices) if ranked_indices is not None else list(self.state.selected)
        chosen = []
        for idx in (pair or []):
            if idx in pool and idx not in chosen:
                chosen.append(idx)
            if len(chosen) == 2:
                break

        if len(chosen) == 2:
            final_pair = chosen
        elif len(chosen) == 1:
            first = chosen[0]
            second = next((idx for idx in pool if idx != first), None)
            final_pair = [first, second] if second is not None else [first]
        else:
            final_pair = pool[:2]

        self.update(pair=final_pair, pair_target=1)

    def pick_school(self, idx):
        p = list(self.state.pair)
        if idx in p:
            return
        if len(p) < 2:
            p.append(idx)
        else:
            p[self.state.pair_target] = idx
        self.update(pair=p, pair_target=1)

#SAT/ACT CONVERSION TABLE
_CT = [(770,16),(830,17),(880,18),(920,19),(960,20),(1000,21),(1040,22),(1080,23),(1120,24),(1160,25),(1200,26),
       (1240,27),(1280,28),(1320,29),(1350,30),(1390,31),(1420,32),(1460,33),(1500,34),(1540,35),(1590,36)]

@dataclass
class Row:
    idx: int; s: object; tuition: float; resident: bool; p: float; chance: str
    fit: int; missing_major: bool; size_idx: int; rank: int = 0

def sat_to_act(sat): 
    if sat <=_CT[0][0]: return 16
    for (a, b), (c, d) in zip(_CT, _CT[1:]):
        if sat <= c: return b + (d - b) * (sat - a) / (c - a)
    return 36

def act_to_sat(act):
    if act <= _CT[0][1]:
        return _CT[0][0]
    for (a, b), (c, d) in zip(_CT, _CT[1:]):
        if act <= d:
            return a + (c - a) * (act - b) / (d - b)
    return 1600

def test_sat(state):
    scores = []
    if state.use_sat:
        scores.append(state.sat)
    if state.use_act:
        scores.append(act_to_sat(state.act))
    if len(scores) == 0:
        return None
    return max(scores)

def size_index(sz): return sum(sz >= c for c in SIZE_CUTS)
def _clamp01(x): return max(0.0, min(1.0, x))
def tuition_for(s, st): return s['tin'] if st == s['st'] else s['tout']

def chance(s, sat):
    a = min(.98, max(.02, s['adm'] / 100))
    score_part = 0 if sat is None else (sat - s['sat']) / 70
    p = 1 / (1 + math.exp(-(score_part + .8 * math.log(a / (1 - a)))))
    return p, ('Likely' if p >= .75 else 'Target' if p >= .3 else 'Reach')

def compute(schools, state):
    rows = []
    sat_score = test_sat(state)
    budget = state.budget or 1
    for i in state.selected:
        s = schools.iloc[i]
        t = tuition_for(s, state.st)
        p, lab = chance(s, sat_score)
        c = {"aff": 100 - 30 * t / budget if t <= budget else max(0, 70 * (1 - (t - budget) / budget)),
             "earn": 100 * _clamp01((s["earn"] - 35000) / 65000), "grad": 100 * _clamp01((s["gr"] - 40) / 58),
             "adm": p * 100}

        if state.pref_size is not None:
            c["size"] = 100 - 35 * abs(size_index(s["sz"]) - state.pref_size)

        miss = False if state.major == "any" else not s[state.major]

        total_w = sum(state.weights[k] for k in c)
        if total_w > 0:
            fit = sum(state.weights[k] * c[k] for k in c) / total_w
        else:
            fit = sum(c.values()) / len(c)
        fit = fit * (0.92 if miss else 1)
        rows.append(Row(i, s, t, state.st == s['st'], p, lab, int(math.floor(fit +.5)), miss, size_index(s["sz"])))
    rows.sort(key=lambda r: (-r.fit, -r.s['earn'] / r.tuition, r.s['ab'].lower()))
    for k, r in enumerate(rows): r.rank = k + 1
    return rows

def fix_pair(rows, pair):
    ids = [r.idx for r in rows]
    slots = [p if p in ids else None for p in (list(pair) + [None, None])[:2]]
    if slots[0] is not None and slots[0] == slots[1]:
        slots[1] = None
    free = [i for i in ids if i not in slots]
    slots = [s if s is not None else (free.pop(0) if free else None) for s in slots]
    return [s for s in slots if s is not None]

def rebalance_weights(w, key, v):
    v = max(0, min(100, round(v)))
    w = dict(w)
    w[key] = v

    others = [k for k in w if k != key]
    cur = sum(w[k] for k in others)
    rest = 100 - v

    for k in others:
        if cur > 0:
            w[k] = round(w[k] * rest / cur)
        else:
            w[k] = round(rest / len(others))

    total = sum(w.values())
    if total != 100:
        big = max(others, key=lambda k: w[k])
        w[big] = max(0, w[big] + 100 - total)
    return w

