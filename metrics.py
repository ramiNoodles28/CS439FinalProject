from matplotlib.patches import Rectangle
from core import A_COLOR, B_COLOR, TARGET, TEXT, MUTED, GRID, money, pct


TITLE = "My College Shortlist"
SUBTITLE = "Compare colleges you’re considering and rank them by your priorities."


CARDS = [
    ("Best Value", A_COLOR, lambda r: r.s['earn'] / r.tuition,
     lambda r: f"Your tuition: {money(r.tuition)} ({'in-state' if r.resident else 'out-of-state'})"),
    ("Top Earnings", TARGET, lambda r: r.s['earn'],
     lambda r: f"Median earnings, 10 yrs: {money(r.s['earn'])}{'*' if r.s['imp'] else ''}"),
    ("Highest Graduation Rate", B_COLOR, lambda r: r.s['gr'],
     lambda r: f"Graduation rate: {pct(r.s['gr'])}"),
    ("Best Match", A_COLOR, lambda r: -r.rank, lambda r: f"Fit score: {r.fit} / 100"),
]

def pick_winners(rows):
    return [max(rows, key=score) if rows else None for _, _, score, _ in CARDS]

class MetricCards:
    def __init__(self, store, schools):
        self.store = store
        self.schools = schools

    def build(self, fig, spec):
        subgrid = spec.subgridspec(2, 1, height_ratios=[.5, .95], hspace=.12)
        self.head = fig.add_subplot(subgrid[0, 0])
        self.head.axis("off")
        self.head.text(0, .95, TITLE, fontsize=19, fontweight="bold", color=TEXT, ha="left", va="top", transform=self.head.transAxes)
        self.head.text(0, .2, SUBTITLE, fontsize=9, color=MUTED, ha="left", va="center", transform=self.head.transAxes)
        cards = subgrid[1, 0].subgridspec(1, len(CARDS), wspace=.08)
        self.axes = []
        for k in range(len(CARDS)):
            ax = fig.add_subplot(cards[0, k])
            ax.axis("off")
            self.axes.append(ax)
            
    def render(self, rows, state):
        winners = pick_winners(rows)
        for ax, (label, color, _, subline), row in zip(self.axes, CARDS, winners):
            ax.clear()
            ax.axis("off")
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.add_patch(Rectangle((.003, .01), .994, .98, facecolor="white", edgecolor=GRID, linewidth=1, clip_on=False))
            ax.add_patch(Rectangle((.003, .01), .012, .98, facecolor=color, edgecolor="none"))
            ax.text(.06, .8, label, fontsize=8, fontweight="bold", color=color, ha="left", va="center")
            if row is None:
                ax.text(.06, .45, "—", fontsize=15, fontweight="bold", color=MUTED, ha="left", va="center")
                ax.text(.06, .16, "No schools selected", fontsize=7.5, color=MUTED, ha="left", va="center")
                continue
            name = row.s['ab']
            ax.text(.06, .48, name, fontsize=15 if len(name) <= 18 else 11.5, fontweight="bold", color=TEXT, ha="left", va="center")
            ax.text(.06, .16, subline(row), fontsize=7.5, color=MUTED, ha="left", va="center")