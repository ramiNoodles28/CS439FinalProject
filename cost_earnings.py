import math
import numpy as np
from matplotlib.widgets import Button
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.colors import to_rgb
from matplotlib.transforms import Bbox
from matplotlib.offsetbox import TextArea, VPacker, AnnotationBbox
import core
from core import CHANCE_COLOR, A_COLOR, B_COLOR, OVER_BUDGET, TEXT, MUTED, GRID, money, money_k

# ---- look & feel (core.py can override FONT by defining the same name) ----
FONT = getattr(core, "FONT", dict(title=12, sub=7.5, label=8, tick=7.5, annot=7.5, tip=8))   # point sizes
DARKEN = .6                                   # compared-school outlines: 1 = same as A_COLOR/B_COLOR, lower = darker
RING_A = tuple(v * DARKEN for v in to_rgb(A_COLOR))
RING_B = tuple(v * DARKEN for v in to_rgb(B_COLOR))
RING_W = 2.6                                  # outline thickness (points)
DOT, DOT_PAIR = 38, 95                        # dot sizes (area in pt^2): normal / compared schools
HIT_PT = 9                                    # hover radius in POINTS (so it works the same at any screen dpi)
BLIT = True                                   # fast tooltip; set False if a backend ever fails to show it

MODES = [("auto", "My residency"), ("in", "All in-state"), ("out", "All out-of-state")]
XLABEL = {"auto": "Your annual tuition", "in": "In-state tuition", "out": "Out-of-state tuition"}


def _inter(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


class CostEarnings:
    def __init__(self, store, schools):
        self.store, self.schools = store, schools
        self._key = self._lim = self._styled = self._region = self._bg = self._hit = None
        self._pts, self._disp, self._labels = [], np.empty((0, 2)), []

    # ------------------------------------------------------------------ build: runs ONCE (all artists created here)
    def build(self, fig, spec):
        self.fig = fig
        gs = spec.subgridspec(2, 1, height_ratios=[2.3, 9], hspace=.1)
        top = fig.add_subplot(gs[0]); top.axis("off")
        top.text(0, .95, "Cost vs Earnings", fontsize=FONT["title"], fontweight="bold", va="top", transform=top.transAxes)
        top.text(0, .68, "Annual tuition vs median earnings 10 years after entry", fontsize=FONT["sub"], color=MUTED,
                 va="top", transform=top.transAxes)
        self.buttons = {}
        for k, (mode, label) in enumerate(MODES):                                      # toggle buttons
            b = Button(top.inset_axes([k * .33, -.08, .31, .36]), label); b.label.set_fontsize(FONT["label"] - .5)
            b.on_clicked(lambda _e, m=mode: self.store.update(scatter_mode=m))         # m=mode binds THIS loop value
            self.buttons[mode] = b

        ax = self.ax = fig.add_subplot(gs[1])                                          # chart
        ax.set_axisbelow(True); ax.grid(color=GRID, lw=.6)
        for sp in ("top", "right"): ax.spines[sp].set_visible(False)
        ax.tick_params(labelsize=FONT["tick"], colors=MUTED, length=0)
        ax.xaxis.set_major_formatter(money_k); ax.yaxis.set_major_formatter(money_k)
        ax.set_xlabel("", fontsize=FONT["label"], color=MUTED)
        ax.set_ylabel("Median Earnings (10 years)", fontsize=FONT["label"], color=MUTED)
        xt = ax.get_xaxis_transform()                                                   # x = data, y = axes fraction
        self.band = ax.add_patch(Rectangle((0, 0), 1, 1, transform=xt, fc=OVER_BUDGET, alpha=.08, lw=0, zorder=1))
        self.bline = ax.axvline(0, color=OVER_BUDGET, ls="--", lw=1, zorder=2)
        self.btxt = ax.text(0, .97, "", transform=xt, color=OVER_BUDGET, fontsize=FONT["annot"], va="top", zorder=5)
        self.sc = ax.scatter([], [], zorder=3)
        self.empty = ax.text(.5, .5, "No schools selected", ha="center", va="center", color=MUTED,
                             transform=ax.transAxes, visible=False)
        self.foot = ax.text(1, -.3, "* 6-yr earnings used (10-yr missing)", transform=ax.transAxes, ha="right",
                            fontsize=FONT["annot"] - 1, color=MUTED, visible=False)
        self.hid = ax.text(0, -.3, "", transform=ax.transAxes, ha="left", fontsize=FONT["annot"] - 1, color=MUTED, visible=False)
        h = [Line2D([], [], marker="o", ls="", color=CHANCE_COLOR[n], label=n, markersize=6) for n in ("Reach", "Target", "Likely")]
        h += [Line2D([], [], marker="o", ls="", mfc="none", mec=c, mew=RING_W, markersize=8, label=n)
              for n, c in (("A", RING_A), ("B", RING_B))]
        ax.legend(handles=h, loc="upper center", bbox_to_anchor=(.5, -.2), ncol=5, frameon=False,
                  fontsize=FONT["annot"], handletextpad=.2, columnspacing=1.0)

        # tooltip: BOLD school name stacked on a details box. animated => skipped in normal draws, blitted on hover
        self._name = TextArea("", textprops=dict(fontsize=FONT["tip"], fontweight="bold", parse_math=False))
        self._info = TextArea("", textprops=dict(fontsize=FONT["tip"], parse_math=False))
        self.tip = AnnotationBbox(VPacker(children=[self._name, self._info], align="left", pad=0, sep=2), (0, 0),
                                  xybox=(12, 12), boxcoords="offset points", box_alignment=(0, 0), annotation_clip=False,
                                  bboxprops=dict(boxstyle="round", fc="white", ec=GRID), zorder=10)
        self.tip.set_visible(False); self.tip.set_animated(BLIT); self.tip.set_clip_on(False)
        ax.add_artist(self.tip)
        c = fig.canvas
        c.mpl_connect("motion_notify_event", self._hover)
        c.mpl_connect("draw_event", self._on_draw)
        c.mpl_connect("figure_leave_event", lambda e: self._set_hit(None))

    # ------------------------------------------------------------------ render: runs after EVERY state change
    def render(self, rows, state, changed=None):
        mode = state.scatter_mode
        a_id, b_id = (list(state.pair) + [None, None])[:2]
        xs = [self._x(r, mode) for r in rows]
        # Skip all work if nothing THIS chart shows has changed (rank/fit/weights don't matter here)
        key = (mode, state.budget, a_id, b_id, tuple(sorted((r.idx, x, r.chance) for r, x in zip(rows, xs))))
        if key == self._key: return
        self._key = key
        self._style_buttons(mode)
        self.ax.xaxis.label.set_text(XLABEL[mode])
        self._pts, self._hit = [], None
        self.tip.set_visible(False)
        n = len(rows)
        self.empty.set_visible(n == 0)
        self.foot.set_visible(any(r.s["imp"] for r in rows))
        if n == 0:
            for t in (self.band, self.bline, self.btxt, self.hid): t.set_visible(False)
            self.sc.set_offsets(np.empty((0, 2))); self._disp = np.empty((0, 2))
            for a in self._labels: a.set_visible(False)
            return

        xs = np.array(xs, float); ys = np.array([r.s["earn"] for r in rows], float)
        xmax = max(60000, np.ceil(xs.max() / 10000) * 10000)                              # axis ranges (RULES section 4)
        y0 = np.floor((ys.min() - 4000) / 5000) * 5000; y1 = np.ceil((ys.max() + 4000) / 5000) * 5000
        if self._lim != (xmax, y0, y1):                                                   # ticks are slow: only when range changes
            ax = self.ax; self._lim = (xmax, y0, y1)
            ax.set_xlim(0, xmax); ax.set_ylim(y0, y1)
            ystep = 5000 * math.ceil((y1 - y0) / 5000 / 9)                                # $5K lines, wider only if >9 would show
            ax.set_xticks(np.arange(0, xmax + 1, 10000)); ax.set_yticks(np.arange(y0, y1 + 1, ystep))

        pair = np.array([r.idx in (a_id, b_id) for r in rows])                            # dots: ONE collection, updated in place
        self.sc.set_offsets(np.column_stack([xs, ys]))
        self.sc.set_sizes(np.where(pair, DOT_PAIR, DOT))
        self.sc.set_facecolor([CHANCE_COLOR[r.chance] for r in rows])
        self.sc.set_edgecolor([RING_A if r.idx == a_id else RING_B if r.idx == b_id else "none" for r in rows])
        self.sc.set_linewidths(np.where(pair, RING_W, 0))

        bud, show = state.budget, state.budget < xmax                                     # over-budget band + label
        self.band.set_x(bud); self.band.set_width(xmax - bud); self.band.set_visible(show)
        self.bline.set_xdata([bud, bud]); self.bline.set_visible(show); self.btxt.set_visible(show)
        pos = self.ax.get_position()
        Wp, Hp = pos.width * self.fig.get_figwidth() * 72, pos.height * self.fig.get_figheight() * 72   # chart size in points
        bx = bud / xmax * Wp if show else None
        obstacles = []
        if show:
            txt = f"over budget ({money(bud)})"; tw = len(txt) * FONT["annot"] * .56
            flip = bx + 4 + tw > Wp and bx - 4 - tw > 0                                   # no room on the right -> left of the line
            self.btxt.set_text(txt); self.btxt.set_ha("right" if flip else "left")
            self.btxt.set_position((bud - xmax * .008 if flip else bud + xmax * .008, .97))
            top = .97 * Hp; lx = bx - 4 - tw if flip else bx + 4
            obstacles.append((lx, top - FONT["annot"] * 1.3, lx + tw, top))
        hidden = self._place_labels(rows, xs, ys, pair, xmax, y0, y1, Wp, Hp, bx, obstacles)
        self.hid.set_visible(hidden > 0)
        self._pts = list(zip(xs, ys, rows))
        self._disp = self.ax.transData.transform(np.column_stack([xs, ys]))               # for fast hover hit-testing

    # ------------------------------------------------------------------ label placement (points space, no renderer)
    def _place_labels(self, rows, xs, ys, pair, xmax, y0, y1, Wp, Hp, bx, obstacles):
        n, fs = len(rows), FONT["annot"]
        px, py = xs / xmax * Wp, (ys - y0) / (y1 - y0) * Hp
        rad = np.sqrt(np.where(pair, DOT_PAIR, DOT)) / 2 + 1
        dots = [(px[i] - rad[i], py[i] - rad[i], px[i] + rad[i], py[i] + rad[i]) for i in range(n)]
        placed, hidden = list(obstacles), 0
        while len(self._labels) < n:
            self._labels.append(self.ax.annotate("", xy=(0, 0), xytext=(0, 0), textcoords="offset points",
                                                 fontsize=fs, color=TEXT, zorder=4, annotation_clip=False))
        for i in range(n):                        # compared schools get first pick
            a = self._labels[i]
            if not pair[i]:
                a.set_visible(False)
                hidden += 1
                continue

            s = rows[i].s
            text = s["ab"] + ("*" if s["imp"] else "")
            w, h = len(text) * fs * .66, fs * 1.3
            r, d = rad[i] + 3, (rad[i] + 3) * .7
            cands = [(r, 0, "left", "center"), (-r, 0, "right", "center"), (0, r, "center", "bottom"),
                     (0, -r, "center", "top"), (d, d, "left", "bottom"), (-d, d, "right", "bottom"),
                     (d, -d, "left", "top"), (-d, -d, "right", "top")]
            best = None
            for ci, (dx, dy, ha, va) in enumerate(cands):
                ax_, ay_ = px[i] + dx, py[i] + dy
                x0 = ax_ - (0 if ha == "left" else w if ha == "right" else w / 2)
                yb = ay_ - (0 if va == "bottom" else h if va == "top" else h / 2)
                box = (x0, yb, x0 + w, yb + h)
                clash = sum(_inter(box, o) for o in placed) + 1.5 * sum(_inter(box, dots[j]) for j in range(n) if j != i)
                cost = ci * .5 + 4 * clash + 8 * (w * h - _inter(box, (0, 0, Wp, Hp)))
                if bx is not None and box[0] < bx < box[2]:
                    cost += 400
                if best is None or cost < best[0]:
                    best = (cost, dx, dy, ha, va, box)
            _, dx, dy, ha, va, box = best
            placed.append(box)
            a.set_text(text)
            a.xy = (xs[i], ys[i])
            a.xyann = (dx, dy)
            a.set_ha(ha)
            a.set_va(va)
            a.set_fontweight("bold")
            a.set_visible(True)

        for a in self._labels[n:]:
            a.set_visible(False)
        return hidden

    # ------------------------------------------------------------------ helpers
    def _x(self, r, mode):          # x value: toggle affects THIS chart only; ranking/fit always use real residency
        return r.s["tin"] if mode == "in" else r.s["tout"] if mode == "out" else r.tuition

    def _style_buttons(self, mode):
        if self._styled == mode: return
        self._styled = mode
        for m, b in self.buttons.items():
            on = m == mode
            b.color = b.hovercolor = A_COLOR if on else "#eef1f6"
            b.ax.set_facecolor(b.color); b.label.set_color("white" if on else MUTED)

    # ------------------------------------------------------------------ hover tooltip
    def _on_draw(self, _ev):
        if len(self._pts):
            self._disp = self.ax.transData.transform(np.column_stack([[p[0] for p in self._pts], [p[1] for p in self._pts]]))
        if BLIT:
            bb, pad = self.ax.bbox, 1.5 * self.fig.dpi                                   # chart + room for the tooltip box
            reg = Bbox.intersection(Bbox.from_extents(bb.x0 - pad, bb.y0 - pad, bb.x1 + pad, bb.y1 + pad), self.fig.bbox)
            self._region = reg if reg is not None else self.fig.bbox
            self._bg = self.fig.canvas.copy_from_bbox(self._region)                      # clean copy (tooltip is animated)

    def _hover(self, ev):
        hit = None
        if ev.inaxes is self.ax and len(self._disp):
            d = np.hypot(self._disp[:, 0] - ev.x, self._disp[:, 1] - ev.y)
            i = int(d.argmin())
            if d[i] < HIT_PT * self.fig.dpi / 72: hit = i                                # radius in points, not pixels
        self._set_hit(hit)

    def _set_hit(self, hit):
        if hit == self._hit:
            return
        self._hit = hit
        if hit is None or hit >= len(self._pts):
            self.tip.set_visible(False)
        else:
            x, y, r = self._pts[hit]
            xmax, y0, y1 = self._lim if self._lim is not None else (60000, 0, 100000)
            left = x > .65 * xmax
            down = y > y0 + .72 * (y1 - y0)
            dx = -12 if left else 12
            dy = -12 if down else 12
            ax_align = 1 if left else 0
            ay_align = 1 if down else 0
            self.tip.xy = (x, y)
            self.tip.xybox = (dx, dy)
            self.tip.box_alignment = (ax_align, ay_align)
            self._name.set_text(r.s["ab"])
            self._info.set_text(f"Tuition {money(x)}\nEarnings {money(y)}{'*' if r.s['imp'] else ''}\n"
                                f"{r.chance} ({r.p:.0%})")
            self.tip.set_visible(True)
        c = self.fig.canvas
        if not BLIT or self._bg is None or not getattr(c, "supports_blit", False):
            c.draw_idle()
            return
        try:
            c.restore_region(self._bg)
            if self.tip.get_visible():
                self.ax.draw_artist(self.tip)
            c.blit(self._region)
        except Exception:
            c.draw_idle()



        
