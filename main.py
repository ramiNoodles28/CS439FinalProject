import argparse
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from core import (State, Store, load_schools, default_selection, compute, fix_pair, DEFAULT_CSV, money)
from cost_earnings import CostEarnings 
from filterMenu import ProfileMenu
from collegeComparison import CollegeComparison
from metrics import MetricCards
from ranking_list_bars import RankingBars
from scorePercentile import ScorePercentile

# ---- ADD SECTIONS HERE (one import + one line each). Slots: profile, metrics, ranking, cost_earnings, head_to_head, score_lands
# Ex. (CostEarnings, 'cost_earnings')
SECTIONS = [
    (ProfileMenu, 'profile'),
    (RankingBars, 'ranking'),
    (CollegeComparison, 'head_to_head'),
    (CostEarnings, 'cost_earnings'),
    (MetricCards, 'metrics'),
    (ScorePercentile, 'score_lands'),
]

ROW_KEYS = {"st", "major", "sat", "act", "use_sat", "use_act", "budget", "pref_size", "weights", "selected"}

SECTION_KEYS = {
    "profile": ROW_KEYS | {"pair"},
    "ranking": ROW_KEYS,
    "head_to_head": {"pair", "pair_target", "st", "sat", "use_sat", "act", "use_act", "selected"},
    "cost_earnings": ROW_KEYS | {"pair", "scatter_mode"},
    "metrics": ROW_KEYS,
    "score_lands": ROW_KEYS | {"pair"},
}

def make_slots(fig):
    outer = GridSpec(1, 2, figure=fig, width_ratios=[1,5], wspace=.08, left=.02, right=.99, top=.96, bottom=.11)
    main = outer[1].subgridspec(3, 1, height_ratios=[1.5, 2.8, 3.2], hspace=.08)
    bottom = main[2].subgridspec(1, 3, width_ratios=[.7, .85, 0.5], wspace=.25)
    return {
        "profile": outer[0],
        "metrics": main[0],
        "ranking": main[1],
        "cost_earnings": bottom[0],
        "head_to_head": bottom[1],
        "score_lands": bottom[2],
    }

def build_app(csv=DEFAULT_CSV, shortlist=True, **overrides):
    schools = load_schools(csv)
    sel = default_selection(schools) if shortlist else []
    state = State(selected=sel, pair=[], **overrides)
    store = Store(state)
    store.latest_rows = []
    fig = plt.figure(figsize=(17, 9.5))
    slots = make_slots(fig)
    built = []
    for cls, slot in SECTIONS:
        s = cls(store, schools)
        s.build(fig, slots[slot])
        built.append((slot, s))

    def refresh(st, changed=None):
        rows_dirty = changed is None or bool(changed & ROW_KEYS)
        if rows_dirty:
            rows = compute(schools, st)
            store.latest_rows = rows
        else:
            rows = store.latest_rows

        if changed is not None and "selected" in changed and st.pair:
            fixed = fix_pair(rows, st.pair)
            if fixed != st.pair:
                st.pair = fixed

        any_rendered = False
        for slot, sec in built:
            deps = SECTION_KEYS.get(slot)
            if changed is None or deps is None or (changed & deps) or (rows_dirty and (deps & ROW_KEYS)):
                sec.render(rows, st)
                any_rendered = True

        if any_rendered:
            fig.canvas.draw_idle()

    store.listeners.append(refresh)
    refresh(state, changed=None)
    return fig, store, schools
 
def print_check(csv, overrides):
    schools = load_schools(csv)
    sel = default_selection(schools)
    st = State(selected=sel, pair=[sel[0], sel[3]], **overrides)
    print(f"{len(schools)} schools loaded | state={st.st} SAT={st.sat} budget={money(st.budget)} weights={st.weights}")
    for r in compute(schools, st):
        print(f"{r.rank:>2}. {r.s['ab']:<20} fit {r.fit:>3}  {r.chance:<6} ({r.p:.0%})  tuition {money(r.tuition):>8}"
              f"{'  [no major]' if r.missing_major else ''}{'  [*est earnings]' if r.s['imp'] else ''}")
 
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=DEFAULT_CSV)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--state", dest="st")
    ap.add_argument("--sat", type=int)
    ap.add_argument("--budget", type=int)
    a = ap.parse_args()
    ov = {k: v for k, v in vars(a).items() if k in ("st", "sat", "budget") and v is not None}
    if a.check:
        print_check(a.csv, ov)
    else:
        build_app(a.csv, **ov)
        plt.show()
