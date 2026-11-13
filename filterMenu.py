from matplotlib.widgets import TextBox, RadioButtons, CheckButtons, Slider
from core import MAJORS, SIZE_LABELS, A_COLOR, TEXT, MUTED, GRID, REACH, money, rebalance_weights

# created list of all 50 states + DC so any student can enter their home state (not just states in the data)
US_STATES = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL", "IN",
             "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
             "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT",
             "VT", "VA", "WA", "WV", "WI", "WY"]

# created dict for the slider labels of each weight key
WEIGHT_LABELS = {"aff": "Cost", "earn": "Earnings", "grad": "Grad rate", "adm": "Admit odds", "size": "Size"}

# created limit for how many schools fit in the shortlist checkboxes
MAX_SCHOOLS = 12

FONT = 8


class ProfileMenu:
    def __init__(self, store, schools):
        self.store = store
        self.schools = schools

        # created list of schools shown as checkboxes (starts as the default shortlist)
        self.candidates = list(store.state.selected)

    # ---------------------------------------------------------------- build
    def build(self, fig, spec):
        self.fig = fig

        # created variables for the slot's position in figure coordinates
        box = spec.get_position(fig)
        self.x0 = box.x0
        self.w = box.width
        self.y = box.y1

        # created column where widgets start, leaving room for labels on the left
        self.wx = self.x0 + self.w * 0.42
        self.ww = self.w * 0.58

        # drew light panel behind the whole menu
        bg = fig.add_axes([box.x0, box.y0, box.width, box.height])
        self.bg = bg
        bg.set_facecolor("#f6f8fb")
        bg.set_xticks([])
        bg.set_yticks([])
        for sp in bg.spines.values():
            sp.set_color(GRID)
        bg.set_zorder(-1)

        state = self.store.state
        self._header("My Profile", 0.035, big=True)
        self._build_text_boxes(state)
        self._build_radios(state)
        self._build_sliders(state)
        self._build_schools(state)

        # created status line at the bottom for confirmations and input errors
        self.status = fig.text(self.x0 + self.w * 0.04, box.y0 + 0.008, "", fontsize=7,
                               color=MUTED, va="bottom", wrap=True)

    def _take(self, h, gap=0.006):
        # moved down the panel and returned the rectangle for the next widget
        self.y = self.y - h - gap
        return self.y

    def _header(self, text, h, big=False):
        y = self._take(h)
        size = 12 if big else 9
        self.fig.text(self.x0 + self.w * 0.04, y + h * 0.3, text, fontsize=size,
                      fontweight="bold", color=TEXT)

    def _label(self, text, y, h):
        # drew left-side label for a widget row
        self.fig.text(self.x0 + self.w * 0.04, y + h / 2, text, fontsize=FONT,
                      color=MUTED, va="center")

    def _build_text_boxes(self, state):
        h = 0.03

        y = self._take(h)
        self._label("Home state", y, h)
        self.state_box = TextBox(self.fig.add_axes([self.wx, y, self.ww * 0.45, h]), "",
                                 initial=state.st)
        self.state_box.on_submit(self._on_state)

        y = self._take(h)
        self._label("SAT score", y, h)
        self.sat_box = TextBox(self.fig.add_axes([self.wx, y, self.ww * 0.45, h]), "",
                               initial=str(state.sat))
        self.sat_box.on_submit(self._on_sat)

        y = self._take(h)
        self._label("Budget / yr", y, h)
        self.budget_box = TextBox(self.fig.add_axes([self.wx, y, self.ww * 0.9, h]), "",
                                  initial=money(state.budget))
        self.budget_box.on_submit(self._on_budget)

        # made the typed text match the rest of the dashboard
        for box in (self.state_box, self.sat_box, self.budget_box):
            box.text_disp.set_fontsize(FONT)

    def _build_radios(self, state):
        # created list of major keys so a radio index maps back to 'c11' / 'c14' / 'c52'
        self.major_keys = list(MAJORS)

        self._header("Intended major", 0.022)
        h = 0.065
        y = self._take(h, gap=0)
        ax = self.fig.add_axes([self.x0 + self.w * 0.04, y, self.w * 0.9, h], frameon=False)
        self.major_radio = RadioButtons(ax, list(MAJORS.values()),
                                        active=self.major_keys.index(state.major),
                                        radio_props={"facecolor": A_COLOR})
        self.major_radio.on_clicked(self._on_major)

        self._header("Campus size", 0.022)
        h = 0.08
        y = self._take(h, gap=0)
        ax = self.fig.add_axes([self.x0 + self.w * 0.04, y, self.w * 0.9, h], frameon=False)
        self.size_radio = RadioButtons(ax, SIZE_LABELS, active=state.pref_size,
                                       radio_props={"facecolor": A_COLOR})
        self.size_radio.on_clicked(self._on_size)

        for radio in (self.major_radio, self.size_radio):
            for t in radio.labels:
                t.set_fontsize(FONT)

    def _build_sliders(self, state):
        self._header("Priorities (sum 100)", 0.022)

        # created dict of sliders by weight key so I can sync them after a rebalance
        self.sliders = {}
        h = 0.022
        for key, label in WEIGHT_LABELS.items():
            y = self._take(h, gap=0.008)
            self._label(label, y, h)
            ax = self.fig.add_axes([self.wx, y, self.ww * 0.72, h])
            s = Slider(ax, "", 0, 100, valinit=state.weights[key], valstep=1,
                       valfmt="%d", color=A_COLOR, track_color=GRID)
            s.valtext.set_fontsize(FONT)

            # hid the red starting-value marker since the value moves when other sliders change
            s.vline.set_visible(False)
            s.on_changed(lambda val, k=key: self._on_weight(k, val))
            self.sliders[key] = s

    def _build_schools(self, state):
        self._header("My schools", 0.022)

        # created search box for adding schools beyond the default list
        h = 0.03
        y = self._take(h)
        self._label("Add school", y, h)
        self.search_box = TextBox(self.fig.add_axes([self.wx, y, self.ww * 0.9, h]), "",
                                  initial="")
        self.search_box.text_disp.set_fontsize(FONT)
        self.search_box.on_submit(self._on_search)

        # created axes for the checkboxes, filling the rest of the panel above the status line
        bottom = self.bg.get_position().y0 + 0.03
        top = self.y - 0.006
        self.check_ax = self.fig.add_axes([self.x0 + self.w * 0.04, bottom, self.w * 0.9,
                                           top - bottom], frameon=False)
        self.school_checks = None

        # created variable for what the checkboxes currently show, so I only rebuild when it changes
        self.shown = None
        self._make_checks(state)

    def _make_checks(self, state):
        # disconnected the old checkboxes so clicks don't fire twice after a rebuild
        if self.school_checks is not None:
            self.school_checks.disconnect_events()
        self.check_ax.clear()
        self.check_ax.set_axis_off()

        labels = [self.schools.iloc[i]["ab"] for i in self.candidates]
        actives = [i in state.selected for i in self.candidates]
        self.shown = (list(self.candidates), actives)

        # padded the list with blank rows so every row keeps the same height
        pad = MAX_SCHOOLS - len(labels)
        self.check_ax.set_ylim(0, 1)
        sub = self.check_ax.inset_axes([0, pad / MAX_SCHOOLS, 1, len(labels) / MAX_SCHOOLS])
        sub.set_axis_off()
        self.school_checks = CheckButtons(sub, labels, actives,
                                          check_props={"facecolor": A_COLOR})
        for t in self.school_checks.labels:
            t.set_fontsize(FONT)
        self.school_checks.on_clicked(self._on_check)

    # ---------------------------------------------------------------- callbacks
    def _on_state(self, text):
        code = text.strip().upper()
        if code not in US_STATES:
            self._error(f"'{text}' is not a state code (ex. IN)")
            self._set_box(self.state_box, self.store.state.st)
            return
        self._ok(f"home state set to {code}")
        self.store.update(st=code)

    def _on_sat(self, text):
        # checked the SAT is a whole number between 400 and 1600
        try:
            sat = int(text.strip())
        except ValueError:
            sat = None
        if sat is None or sat < 400 or sat > 1600:
            self._error("SAT must be a number from 400 to 1600")
            self._set_box(self.sat_box, str(self.store.state.sat))
            return
        self._ok(f"SAT set to {sat}")
        self.store.update(sat=sat)

    def _on_budget(self, text):
        budget = parse_money(text)
        if budget is None or budget <= 0:
            self._error("budget must be a dollar amount (ex. 35000 or 35k)")
            self._set_box(self.budget_box, money(self.store.state.budget))
            return
        self._ok(f"budget set to {money(budget)}")
        self.store.update(budget=budget)

    def _on_major(self, label):
        index = list(MAJORS.values()).index(label)
        self.store.update(major=self.major_keys[index])

    def _on_size(self, label):
        self.store.update(pref_size=SIZE_LABELS.index(label))

    def _on_weight(self, key, val):
        new = rebalance_weights(self.store.state.weights, key, val)
        self._sync_sliders(new, skip=key)
        self.store.update(weights=new)

    def _on_check(self, _label):
        # rebuilt the selected list in shortlist order from the checkbox status
        status = self.school_checks.get_status()
        selected = []
        for i, on in zip(self.candidates, status):
            if on:
                selected.append(i)
        self.store.update(selected=selected)

    def _on_search(self, text):
        query = text.strip()
        if query == "":
            return

        idx = find_school(self.schools, query)
        if idx is None:
            self._error(f"no school matches '{query}'")
            return

        name = self.schools.iloc[idx]["ab"]
        selected = list(self.store.state.selected)

        if idx not in self.candidates:
            if len(self.candidates) >= MAX_SCHOOLS:
                # removed the oldest unchecked school to make room, if there is one
                unchecked = [i for i in self.candidates if i not in selected]
                if not unchecked:
                    self._error(f"list is full ({MAX_SCHOOLS}); uncheck a school first")
                    return
                self.candidates.remove(unchecked[0])
            self.candidates.append(idx)

        if idx not in selected:
            selected.append(idx)

        self._ok(f"added {name}")
        self._set_box(self.search_box, "")
        self.store.update(selected=selected)

    # ---------------------------------------------------------------- render
    def render(self, rows, state):
        # synced every widget to the state without firing callbacks (other sections can change state too)
        self._set_box(self.state_box, state.st)
        self._set_box(self.sat_box, str(state.sat))
        self._set_box(self.budget_box, money(state.budget))

        self._set_radio(self.major_radio, self.major_keys.index(state.major))
        self._set_radio(self.size_radio, state.pref_size)

        self._sync_sliders(state.weights)

        # added any selected school that isn't in the checkbox list yet, then rebuilt the checkboxes
        for i in state.selected:
            if i not in self.candidates:
                self.candidates.append(i)
        actives = [i in state.selected for i in self.candidates]
        if self.shown != (self.candidates, actives):
            self._make_checks(state)

    def _sync_sliders(self, weights, skip=None):
        for key, s in self.sliders.items():
            if key == skip:
                continue
            if s.val != weights[key]:
                s.eventson = False
                s.set_val(weights[key])
                s.eventson = True

    def _set_box(self, box, text):
        # only replaced the text when it changed, so I don't wipe what the user is typing
        if box.text != text:
            box.eventson = False
            box.set_val(text)
            box.eventson = True

    def _set_radio(self, radio, index):
        if radio.index_selected != index:
            radio.eventson = False
            radio.set_active(index)
            radio.eventson = True

    def _ok(self, msg):
        self.status.set_text(msg)
        self.status.set_color(MUTED)

    def _error(self, msg):
        self.status.set_text(msg)
        self.status.set_color(REACH)
        self.fig.canvas.draw_idle()


def parse_money(text):
    # cleaned typed money like "$35,000" or "35k" into an int, or None if it can't be read
    t = text.strip().lower().replace("$", "").replace(",", "")
    mult = 1
    if t.endswith("k"):
        mult = 1000
        t = t[:-1]
    try:
        return int(float(t) * mult)
    except ValueError:
        return None


def find_school(schools, query):
    # found the best match for the typed name: exact short name, then starts-with, then shortest contains
    q = query.lower()
    short = schools["ab"].str.lower()
    full = schools["n"].str.lower()

    exact = schools.index[(short == q) | (full == q)]
    if len(exact) > 0:
        return int(exact[0])

    starts = schools.index[short.str.startswith(q) | full.str.startswith(q)]
    if len(starts) > 0:
        return int(min(starts, key=lambda i: len(schools.at[i, "n"])))

    contains = schools.index[short.str.contains(q, regex=False) | full.str.contains(q, regex=False)]
    if len(contains) > 0:
        return int(min(contains, key=lambda i: len(schools.at[i, "n"])))

    return None
