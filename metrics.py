from matplotlib.patches import Rectangle
from core import A_COLOR, B_COLOR, TARGET, TEXT, MUTED, GRID, money, pct


TITLE = "My College Shortlist"
SUBTITLE = "Compare colleges you’re considering and rank them by your priorities."
ROW_KEYS = {"st", "major", "sat", "act", "use_sat", "use_act", "budget", "pref_size", "weights", "selected"}

def _best_value_score(r):
    if r.tuition <= 0:
        return r.s['earn']
    return r.s['earn'] / r.tuition

def _best_value_subline(r):
    residency = 'in_state' if r.resident else 'out-of-state'
    if r.tuition <= 0:
        return f"Your tuition: $0 ({residency}) — Note: tuition is $0 or not found"
    return f"Your tuition: {money(r.tuition)} ({residency})"

CARDS = [
    ("Best Value", A_COLOR, _best_value_score, _best_value_subline),
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
        self._card_artists = []

    def build(self, fig, spec):
        subgrid = spec.subgridspec(2, 1, height_ratios=[.5, .95], hspace=.12)
        self.head = fig.add_subplot(subgrid[0, 0])
        self.head.axis("off")
        cards = subgrid[1, 0].subgridspec(1, len(CARDS), wspace=.08)
        self.axes = []
        self._card_artists = []

        for k, (label, color, _, _) in enumerate(CARDS):
            ax = fig.add_subplot(cards[0, k])
            ax.axis("off")
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.add_patch(Rectangle((.003, .01), .994, .98, facecolor='white', edgecolor=GRID, linewidth=1, clip_on=False))
            ax.add_patch(Rectangle((.003, .95), .994, .04, facecolor=color, edgecolor='none', clip_on=False))
            ax.text(.06, .8, label, fontsize=8, fontweight='bold', color=color, ha='left', va='center')

            main_txt = ax.text(.06, .46, "—", fontsize=15, fontweight="bold", color=MUTED, ha="left", va="center")
            sub_txt = ax.text(.06, .16, "", fontsize=7.5, color=MUTED, ha="left", va="center")
            self.axes.append(ax)
            self._card_artists.append((main_txt, sub_txt))
            
    def render(self, rows, state, changed=None):
        if changed is not None and not (changed & ROW_KEYS):
            return
        
        winners = pick_winners(rows)
        for (_, _, _, subline), row, (main_txt, sub_txt) in zip(CARDS, winners, self._card_artists):
            if row is None:
                main_txt.set_text('-')
                main_txt.set_fontsize(15)
                main_txt.set_color(MUTED)
                sub_txt.set_text('No schools selected')
                continue

            name = row.s['ab']
            main_txt.set_text(name)
            main_txt.set_fontsize(15 if len(name) <= 18 else 11.5)
            main_txt.set_color(TEXT)
            sub_txt.set_text(subline(row))
