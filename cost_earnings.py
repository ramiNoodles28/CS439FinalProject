import numpy as np
from matplotlib.widgets import Button
from matplotlib.lines import Line2D
from core import CHANCE_COLOR, A_COLOR, B_COLOR, OVER_BUDGET, TEXT, MUTED, GRID, LIKELY, TARGET, REACH, money, money_k


MODES = [("auto", "My residency"), ("in", "All in-state"), ("out", "All out-of-state")]
XLABEL = {"auto": "Your annual tuition", "in": "In-state tuition", "out": "Out-of-state tuition"}

class CostEarnings:
    def __init__(self, store, schools):
        self.store = store
        self.schools = schools

    def build(self, fig, spec):
        gs = spec.subgridspec(2, 1, height_ratios=[2.3, 9], hspace=.1)
        top = fig.add_subplot(gs[0])
        top.axis("off")
        top.text(0, .95, "Cost vs Earnings", fontsize=12, fontweight="bold", va="top", transform=top.transAxes)
        top.text(0, .68, "Annual tuition vs median earnings 10 years after entry", fontsize=7.5, color=MUTED,
                 va="top", transform=top.transAxes)
        self.buttons = {}
        for k, (mode, label) in enumerate(MODES):
            b = Button(top.inset_axes([k * .33, -.08, .31, .36]), label)
            b.label.set_fontsize(7.5)
            b.on_clicked(lambda _e, m=mode: self.store.update(scatter_mode=m))
            self.buttons[mode] = b
        self.ax = fig.add_subplot(gs[1])
        self.tip, self._pts = None, []
        fig.canvas.mpl_connect("motion_notify_event", self._hover)

    def render(self, rows, state):
        ax = self.ax
        ax.clear()
        self._pts = []
        self._style_buttons(state.scatter_mode)
        for sp in ('top', 'right'):
            ax.spines[sp].set_visible(False)
        self.tip = ax.annotate("", xy=(0, 0), xytext=(12, 12), textcoords="offset points", fontsize=8, zorder=10, bbox=dict(boxstyle='round', fc='white', ec=GRID), visible=False)
        if not rows:
            ax.set_xticks([])
            ax.set_yticks([])
            ax.text(.5, .5, "No schools selected", ha='center', va='center', color=MUTED, transform=ax.transAxes)
            return
        mode = state.scatter_mode
        xs = np.array([self._x(r, mode) for r in rows])
        ys = np.array([r.s['earn'] for r in rows])
        xmax = max(60000, np.ceil(xs.max() / 10000) * 10000)

        y0 = np.floor((ys.min() - 4000) / 5000) * 5000
        y1 = np.ceil((ys.max() + 4000) / 5000) * 5000
        ax.set_xlim(0, xmax)
        ax.set_ylim(y0, y1)
        ax.set_xticks(np.arange(0, xmax + 1, 10000))
        ax.set_yticks(np.arange(y0, y1 + 1, 5000))
        ax.xaxis.set_major_formatter(money_k)
        ax.yaxis.set_major_formatter(money_k)
        ax.tick_params(labelsize=7.5, colors=MUTED, length=0)
        ax.set_axisbelow(True)
        ax.grid(color=GRID, lw=.6)

        if state.budget < xmax:
            ax.axvspan(state.budget, xmax, color=OVER_BUDGET, alpha=.08, lw=0)
            ax.axvline(state.budget, color=OVER_BUDGET, ls='--', lw=1)
            ax.text(state.budget + xmax * .01, y1 - (y1 - y0) * .02, f"over budget ({money(state.budget)})", color=OVER_BUDGET, fontsize=7.5, va='top')

        a_id, b_id = (list(state.pair) + [None, None])[:2]
        ppy = ax.get_window_extent().height * 72 / ax.figure.dpi / (y1 - y0)
        placed = []
        for r, x, y in zip(rows, xs, ys):
            ring = A_COLOR if r.idx == a_id else B_COLOR if r.idx == b_id else 'none'
            pair = ring != 'none'
            ax.scatter([x], [y], s=75 if pair else 28, c=CHANCE_COLOR[r.chance], edgecolors=ring, linewidths=2 if pair else 0, zorder=3)
            right = x > .75 * xmax
            yoff = next((o for o in (-3, 7, -13, 17) if all(abs(x - px) > .2 * xmax or abs((y - py) * ppy + o - po) > 9 for px, py, po in placed)), -3)
            placed.append((x, y, yoff))
            ax.annotate(r.s['ab'] + ('*' if r.s['imp'] else ''), (x, y), xytext=(-8 if right else 8, yoff), textcoords='offset points', ha='right' if right else 'left', fontsize=7.5, fontweight='bold' if pair else 'normal', color=TEXT, zorder=4)
            self._pts.append((x, y, r))

        ax.set_xlabel(XLABEL[mode], fontsize=8, color=MUTED)
        ax.set_ylabel('Median Earnings (10 years)', fontsize=8, color=MUTED)
        h = [Line2D([], [], marker='o', ls='', color=c, label=n, markersize=6)
             for n, c in (("Reach", REACH), ("Target", TARGET), ("Likely", LIKELY))]
        ax.legend(handles=h, loc='upper center', bbox_to_anchor=(.5, -.2), ncol=3, frameon=False, fontsize=7.5)
        if any(r.s['imp'] for r in rows):
            ax.text(1, -.3, '* 6-yr earnings used (10-yr missing)', transform=ax.transAxes, ha='right', fontsize=6.5, color=MUTED)

    def _x(self, r, mode):
        return r.s['tin'] if mode == 'in' else r.s['tout'] if mode == 'out' else r.tuition

    def _style_buttons(self, mode):
        for m, b in self.buttons.items():
            on = m == mode
            b.color = b.hovercolor = A_COLOR if on else "#eef1f6"
            b.ax.set_facecolor(b.color)
            b.label.set_color('white' if on else MUTED)

    def _hover(self, ev):
        if self.tip is None:
            return
        was, hit = self.tip.get_visible(), None
        if ev.inaxes is self.ax and self._pts:
            d = [np.hypot(*(self.ax.transData.transform((x, y)) - (ev.x, ev.y))) for x, y, _ in self._pts]
            if min(d) < 12:
                hit = self._pts[int(np.argmin(d))]
        if hit:
            x, y, r = hit
            self.tip.xy = (x, y)
            self.tip.set_text(f"{r.s['ab']}\nTuition {money(x)}\nEarnings {money(y)}{'*' if r.s['imp'] else ''}\n"
                              f"{r.chance} ({r.p:.0%})")
        self.tip.set_visible(hit is not None)
        if was != self.tip.get_visible():
            ev.canvas.draw_idle()



        
