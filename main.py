import argparse
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from core import (State, Store, load_schools, default_selection, compute, fix_pair, DEFAULT_CSV, money)
from cost_earnings import CostEarnings
from filterMenu import ProfileMenu
from collegeComparison import CollegeComparison


# ---- ADD SECTIONS HERE (one import + one line each). Slots: profile, metrics, ranking, cost_earnings, head_to_head, score_lands
# Ex. (CostEarnings, 'cost_earnings')
SECTIONS = [(ProfileMenu, 'profile'), (CollegeComparison, 'head_to_head'), (CostEarnings, 'cost_earnings')]

def make_slots(fig):
    outer = GridSpec(1, 2, figure=fig, width_ratios=[1,5], wspace=.08, left=.02, right=.99, top=.96, bottom=.11)
    main = outer[1].subgridspec(3, 1, height_ratios=[.6, 2.3, 2.9], hspace=.35)
    bottom = main[2].subgridspec(1, 3, width_ratios=[1.1, 1.1, .9], wspace=.28)
    return {"profile": outer[0], "metrics": main[0], "ranking": main[1], "cost_earnings": bottom[0], "head_to_head": bottom[1], "score_lands": bottom[2]}

def build_app(csv=DEFAULT_CSV, **overrides):
    schools = load_schools(csv)
    sel = default_selection(schools)
    state = State(selected=sel, pair=[sel[0], sel[3]], **overrides)      # default pair: 
    store = Store(state)
    fig = plt.figure(figsize=(17, 9.5)); slots = make_slots(fig)
    sections = []
    for cls, slot in SECTIONS:
        s = cls(store, schools); s.build(fig, slots[slot]); sections.append(s)
    def refresh(st):
        rows = compute(schools, st)                  # computed ONCE per change, shared by all sections
        st.pair = fix_pair(rows, st.pair)
        for s in sections: s.render(rows, st)
        fig.canvas.draw_idle()
    store.listeners.append(refresh); refresh(state)
    return fig, store, schools
 
def print_check(csv, overrides):
    schools = load_schools(csv); sel = default_selection(schools)
    st = State(selected=sel, pair=[sel[0], sel[3]], **overrides)
    print(f"{len(schools)} schools loaded | state={st.st} SAT={st.sat} budget={money(st.budget)} weights={st.weights}")
    for r in compute(schools, st):
        print(f"{r.rank:>2}. {r.s['ab']:<20} fit {r.fit:>3}  {r.chance:<6} ({r.p:.0%})  tuition {money(r.tuition):>8}"
              f"{'  [no major]' if r.missing_major else ''}{'  [*est earnings]' if r.s['imp'] else ''}")
 
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=DEFAULT_CSV); ap.add_argument("--check", action="store_true")
    ap.add_argument("--state", dest="st"); ap.add_argument("--sat", type=int); ap.add_argument("--budget", type=int)
    a = ap.parse_args(); ov = {k: v for k, v in vars(a).items() if k in ("st", "sat", "budget") and v is not None}
    if a.check: print_check(a.csv, ov)
    else: build_app(a.csv, **ov); plt.show()