from core import LIKELY, TARGET, REACH, A_COLOR, B_COLOR, TEXT, MUTED, GRID
from core import act_to_sat, test_sat

# Status shown on the right of each school, (label, color)
ABOVE = ("Above range", LIKELY)
INSIDE = ("In range", TARGET)
BELOW = ("Below range", REACH)

class ScorePercentile:
    # store holds the current state (SAT/ACT, selected schools), schools is the dataframe from load_schools
    def __init__(self, store, schools):
        self.store = store
        self.schools = schools

    # Called once by main.py, spec is the slot for this section
    # Left axis draws the 25th-75th percentile bars, right axis holds the status text
    def build(self, fig, spec):
        subgrid = spec.subgridspec(1, 2, width_ratios=[3, 1.15], wspace=.02)
        self.ax = fig.add_subplot(subgrid[0, 0])
        self.txt = fig.add_subplot(subgrid[0, 1])
        self.txt.axis("off")

    # Decide which scale to draw on and what score to draw the line at
    # ACT scale only when ACT is the only test checked, otherwise SAT
    # Both checked -> better of the two (same rule the chance calculation uses)
    def score_setup(self, state):
        if state.use_act and not state.use_sat:
            return "ACT", state.act
        score = test_sat(state)
        return "SAT", score

    # The 25th-75th range for a school in the chosen scale
    # The scorecard data only has ACT percentiles, so for SAT they are converted with the table in core
    def school_range(self, school, scale):
        lo, hi = school['a25'], school['a75']
        if scale == "SAT":
            return act_to_sat(lo), act_to_sat(hi)
        return lo, hi

    # Compare the score to a school's range
    def status(self, score, lo, hi):
        if score < lo:
            return BELOW, score - lo
        if score > hi:
            return ABOVE, score - hi
        return INSIDE, 0

    # Called by main.py every time the state changes
    def render(self, rows, state):
        ax, txt = self.ax, self.txt
        ax.clear()
        txt.clear()
        txt.axis("off")
        ax.set_title("Where Your Score Lands", loc="left", fontsize=10, fontweight="bold", color=TEXT)

        scale, score = self.score_setup(state)

        # Nothing to draw if no schools or no score
        if not rows or score is None:
            ax.axis("off")
            msg = "No schools selected" if not rows else "Check SAT or ACT to see where you land"
            ax.text(.5, .5, msg, ha="center", va="center", color=MUTED, fontsize=8, transform=ax.transAxes)
            return
        ax.axis("on")

        ranges = [self.school_range(r.s, scale) for r in rows]
        n = len(rows)
        fs = 7 if n <= 12 else 6   # smaller text when a lot of schools are selected

        # x limits, include the student's score so the line is always visible
        lows = [lo for lo, _ in ranges] + [score]
        highs = [hi for _, hi in ranges] + [score]
        if scale == "SAT":
            pad, cap_lo, cap_hi = 40, 400, 1600
        else:
            pad, cap_lo, cap_hi = 1, 1, 36
        xmin = max(cap_lo, min(lows) - pad)
        xmax = min(cap_hi, max(highs) + pad)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(n - .5, -.5)   # flipped so rank 1 is on top
        txt.set_xlim(0, 1)
        txt.set_ylim(n - .5, -.5)

        a_id, b_id = (list(state.pair) + [None, None])[:2]
        for i, (r, (lo, hi)) in enumerate(zip(rows, ranges)):
            (label, color), diff = self.status(score, lo, hi)
            fmt = "{:.0f}" if scale == "SAT" else "{:.0f}"

            # 25th-75th percentile bar, colored by where the student lands
            ax.barh(i, hi - lo, left=lo, height=.5, color=color, alpha=.45, zorder=2)
            ax.text(lo - (xmax - xmin) * .01, i, fmt.format(lo), ha="right", va="center", fontsize=fs - 1, color=MUTED)
            ax.text(hi + (xmax - xmin) * .01, i, fmt.format(hi), ha="left", va="center", fontsize=fs - 1, color=MUTED)

            # Status text on the right, with how far outside the range when not in it
            extra = f" ({diff:+.0f})" if diff else ""
            txt.text(0.02, i, label + extra, ha="left", va="center", fontsize=fs, fontweight="bold", color=color)

        # Vertical line for the student's score
        ax.axvline(score, color=TEXT, lw=1.5, ls="--", zorder=4)
        ax.text(score, -.5 - .02 * n, f"You: {score:.0f}", ha="center", va="bottom", fontsize=7,
                fontweight="bold", color=TEXT, clip_on=False)

        # School names on the left, compared schools get their A / B color
        ax.set_yticks(range(n))
        ax.set_yticklabels([r.s['ab'] for r in rows], fontsize=fs)
        for lbl, r in zip(ax.get_yticklabels(), rows):
            if r.idx == a_id:
                lbl.set_color(A_COLOR)
                lbl.set_fontweight("bold")
            elif r.idx == b_id:
                lbl.set_color(B_COLOR)
                lbl.set_fontweight("bold")
            else:
                lbl.set_color(TEXT)

        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.tick_params(axis="x", labelsize=7, colors=MUTED, length=0)
        ax.set_axisbelow(True)
        ax.grid(axis="x", color=GRID, lw=.6)
        if scale == "SAT":
            ax.set_xlabel("SAT (middle 50% of admitted students)", fontsize=7.5, color=MUTED)
        else:
            ax.set_xlabel("ACT (middle 50% of admitted students)", fontsize=7.5, color=MUTED)


# Run this file by itself to see just this chart, using the default shortlist from core.py
#   python scorePercentile.py                  -> default SAT (1420)
#   python scorePercentile.py --sat 1300
#   python scorePercentile.py --act 28         -> ACT scale (turns SAT off)
#   python scorePercentile.py --sat 1350 --act 30   -> both checked, uses the better one
if __name__ == "__main__":
    import argparse
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec
    from core import State, Store, load_schools, default_selection, compute, fix_pair, DEFAULT_CSV

    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=DEFAULT_CSV)
    ap.add_argument("--sat", type=int)
    ap.add_argument("--act", type=int)
    ap.add_argument("--state", dest="st", default="IN")
    a = ap.parse_args()

    schools = load_schools(a.csv)
    sel = default_selection(schools)   # the same default shortlist main.py's --check uses

    # --act alone means ACT only, --sat alone means SAT only, both means both, neither means default SAT
    use_act = a.act is not None
    use_sat = a.sat is not None or not use_act
    state = State(st=a.st, selected=sel, pair=[sel[0], sel[3]], use_sat=use_sat, use_act=use_act)
    if a.sat is not None:
        state.sat = a.sat
    if a.act is not None:
        state.act = a.act

    fig = plt.figure(figsize=(6.5, 5))
    spec = GridSpec(1, 1, figure=fig, left=.2, right=.97, top=.9, bottom=.12)[0]
    chart = ScorePercentile(Store(state), schools)
    chart.build(fig, spec)

    rows = compute(schools, state)
    state.pair = fix_pair(rows, state.pair)
    chart.render(rows, state)
    plt.show()