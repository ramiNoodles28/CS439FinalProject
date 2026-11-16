from matplotlib.widgets import TextBox, RadioButtons, CheckButtons, Slider, Button
from matplotlib.patches import Rectangle
from core import MAJORS, SIZE_LABELS, A_COLOR, B_COLOR, TEXT, MUTED, GRID, REACH, money

# created dict of all 50 states + DC so any student can pick their home state (not just states in the data)
STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
    "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"}

# created list of state codes sorted by full name, for the dropdown
STATE_ORDER = sorted(STATE_NAMES, key=lambda code: STATE_NAMES[code])

# created dict for the label of each priority weight
WEIGHT_LABELS = {"aff": "Cost", "earn": "Earnings", "grad": "Grad rate", "adm": "Admit odds", "size": "Size"}

# created variables for the budget slider range (typing allows going past the slider)
BUDGET_MIN = 0
BUDGET_MAX = 100000
BUDGET_STEP = 1000

# created limit for how many schools can be on the list
MAX_SCHOOLS = 10

FONT = 8
PANEL_BG = "#f6f8fb"
ROW_HOVER = "#e6ebf3"


class ProfileMenu:
    def __init__(self, store, schools):
        self.store = store
        self.schools = schools

        # created variable for whether the state dropdown is open
        self.popup_open = False

        # created list of school indices currently shown in the list rows (one per row)
        self.row_idx = []

        # created variable for what the list rows are showing: "list" (my schools) or "suggest" (search matches)
        self.mode = "list"

    # ================================================================ build
    def build(self, fig, spec):
        self.fig = fig

        # created variables for the slot's position in figure coordinates
        box = spec.get_position(fig)
        self.x0 = box.x0
        self.w = box.width
        self.y = box.y1
        self.bottom = box.y0

        # created column where widgets start, leaving room for labels on the left
        self.wx = self.x0 + self.w * 0.40
        self.ww = self.w * 0.56

        # created list of every widget so I can turn them off while the state dropdown is open
        # (I set widget.active instead of set_active(), since radio/check buttons use set_active() to pick an option)
        self.widgets = []

        # drew light panel behind the whole menu
        bg = fig.add_axes([box.x0, box.y0, box.width, box.height])
        bg.set_facecolor(PANEL_BG)
        bg.set_xticks([])
        bg.set_yticks([])
        for sp in bg.spines.values():
            sp.set_color(GRID)
        bg.set_zorder(-1)

        state = self.store.state
        self._header("My Profile", 0.032, big=True)
        self._build_home_state(state)
        self._build_tests(state)
        self._build_budget(state)
        self._build_radios(state)
        self._build_priorities(state)
        self._build_schools(state)

        # created status line at the bottom for confirmations and input errors
        self.status = fig.text(self.x0 + self.w * 0.04, self.bottom + 0.008, "", fontsize=7,
                               color=MUTED, va="bottom")

        # built the dropdown last so it draws on top of everything else
        self._build_state_popup(state)
        fig.canvas.mpl_connect("button_press_event", self._on_press)

    # ---------------------------------------------------------------- layout helpers
    def _take(self, h, gap=0.006):
        # moved down the panel and returned the bottom y of the next row
        self.y = self.y - h - gap
        return self.y

    def _header(self, text, h, big=False):
        y = self._take(h)
        size = 12 if big else 9
        self.fig.text(self.x0 + self.w * 0.04, y + h * 0.3, text, fontsize=size,
                      fontweight="bold", color=TEXT)
        return y

    def _label(self, text, y, h):
        # drew left-side label for a widget row
        return self.fig.text(self.x0 + self.w * 0.04, y + h / 2, text, fontsize=FONT,
                             color=MUTED, va="center")

    def _text_box(self, rect, initial):
        box = TextBox(self.fig.add_axes(rect), "", initial=initial)
        box.text_disp.set_fontsize(FONT)
        self.widgets.append(box)
        return box

    # ---------------------------------------------------------------- home state
    def _build_home_state(self, state):
        h = 0.028
        y = self._take(h)
        self.state_row_y = y
        self._label("Home state", y, h)

        ax = self.fig.add_axes([self.wx, y, self.ww, h])
        self.state_button = Button(ax, self._state_text(state.st), color="white", hovercolor=ROW_HOVER)
        self.state_button.label.set_fontsize(FONT)
        for sp in ax.spines.values():
            sp.set_color(MUTED)
        self.state_button.on_clicked(self._toggle_popup)
        self.widgets.append(self.state_button)

    def _state_text(self, code):
        return f"{STATE_NAMES[code]} ({code}) ▾"

    def _build_state_popup(self, state):
        # created dropdown as one axes with a 2-column grid of state names, hidden until clicked
        self.popup_cols = 2
        self.popup_rows = (len(STATE_ORDER) + 1) // 2
        row_h = 0.0145
        height = self.popup_rows * row_h
        top = self.state_row_y - 0.002

        self.popup_ax = self.fig.add_axes([self.x0 + self.w * 0.03, top - height, self.w * 0.94, height])
        self.popup_ax.set_zorder(50)
        self.popup_ax.set_xlim(0, self.popup_cols)
        self.popup_ax.set_ylim(self.popup_rows, 0)
        self.popup_ax.set_xticks([])
        self.popup_ax.set_yticks([])
        self.popup_ax.set_facecolor("white")
        for sp in self.popup_ax.spines.values():
            sp.set_color(MUTED)

        # created dict of the highlight box behind each state so I can mark the current one
        self.popup_cells = {}
        for k, code in enumerate(STATE_ORDER):
            col = k // self.popup_rows
            row = k % self.popup_rows
            cell = Rectangle((col, row), 1, 1, color=A_COLOR, alpha=0.15, visible=False)
            self.popup_ax.add_patch(cell)
            self.popup_cells[code] = cell
            self.popup_ax.text(col + 0.05, row + 0.5, f"{STATE_NAMES[code]} ({code})",
                               fontsize=6.5, color=TEXT, va="center")

        self.popup_ax.set_visible(False)

    def _toggle_popup(self, _event):
        if self.popup_open:
            self._close_popup()
        else:
            self._open_popup()

    def _open_popup(self):
        # highlighted the current state and turned off the widgets under the dropdown
        for code, cell in self.popup_cells.items():
            cell.set_visible(code == self.store.state.st)
        for widget in self.widgets:
            widget.active = False
        self.popup_open = True
        self.popup_ax.set_visible(True)
        self.fig.canvas.draw_idle()

    def _close_popup(self):
        self.popup_open = False
        self.popup_ax.set_visible(False)
        for widget in self.widgets:
            widget.active = True

        # re-hid any empty school rows and re-locked Size, since I just turned everything back on
        self._refresh_rows()
        self._sync_priorities(self.store.state)
        self.fig.canvas.draw_idle()

    def _on_press(self, event):
        # picked a state if the click is inside the open dropdown, otherwise just closed it
        if not self.popup_open:
            return

        inside = self.popup_ax.contains(event)[0]
        if inside and event.xdata is not None and event.ydata is not None:
            col = int(event.xdata)
            row = int(event.ydata)
            k = col * self.popup_rows + row
            if 0 <= k < len(STATE_ORDER):
                code = STATE_ORDER[k]
                self._close_popup()
                self._ok(f"home state set to {STATE_NAMES[code]}")
                self.store.update(st=code)
                return
        self._close_popup()

    # ---------------------------------------------------------------- SAT / ACT
    def _build_tests(self, state):
        self._header("Test scores", 0.02)
        h = 0.026

        # created one checkbox + one text box per test, so the user can use SAT, ACT, both, or neither
        y = self._take(h)
        self.sat_check = self._test_check("SAT", state.use_sat, y, h)
        self.sat_box = self._text_box([self.wx, y, self.ww * 0.45, h], str(state.sat))
        self.fig.text(self.wx + self.ww * 0.5, y + h / 2, "400-1600", fontsize=6.5, color=MUTED, va="center")
        self.sat_check.on_clicked(self._on_test_check)
        self.sat_box.on_submit(self._on_sat)

        y = self._take(h)
        self.act_check = self._test_check("ACT", state.use_act, y, h)
        self.act_box = self._text_box([self.wx, y, self.ww * 0.45, h], str(state.act))
        self.fig.text(self.wx + self.ww * 0.5, y + h / 2, "1-36", fontsize=6.5, color=MUTED, va="center")
        self.act_check.on_clicked(self._on_test_check)
        self.act_box.on_submit(self._on_act)

    def _test_check(self, name, on, y, h):
        ax = self.fig.add_axes([self.x0 + self.w * 0.02, y, self.w * 0.34, h], frameon=False)
        check = CheckButtons(ax, [name], [on], check_props={"facecolor": A_COLOR})
        check.labels[0].set_fontsize(FONT)
        self.widgets.append(check)
        return check

    # ---------------------------------------------------------------- budget
    def _build_budget(self, state):
        h = 0.026
        y = self._take(h, gap=0.012)
        self._label("Budget / yr", y, h)
        self.budget_box = self._text_box([self.wx, y, self.ww, h], money(state.budget))
        self.budget_box.on_submit(self._on_budget_box)
        self.budget_box.on_text_change(self._keep_dollar_sign)

        # created slider under the text box, both set the same budget
        h = 0.018
        y = self._take(h, gap=0.004)
        ax = self.fig.add_axes([self.wx, y, self.ww, h])
        self.budget_slider = Slider(ax, "", BUDGET_MIN, BUDGET_MAX, valinit=min(state.budget, BUDGET_MAX),
                                    valstep=BUDGET_STEP, color=A_COLOR, track_color=GRID)
        self.budget_slider.valtext.set_visible(False)
        self.budget_slider.vline.set_visible(False)
        self.budget_slider.on_changed(self._on_budget_slider)
        self.widgets.append(self.budget_slider)

    # ---------------------------------------------------------------- major / size
    def _build_radios(self, state):
        # created list of major keys so a radio index maps back to 'any' / 'c11' / 'c14' / 'c52'
        self.major_keys = ["any"] + list(MAJORS)
        major_labels = ["Any"] + list(MAJORS.values())

        self._header("Intended major", 0.02)
        h = 0.064
        y = self._take(h, gap=0)
        ax = self.fig.add_axes([self.x0 + self.w * 0.04, y, self.w * 0.9, h], frameon=False)
        self.major_radio = RadioButtons(ax, major_labels,
                                        active=self.major_keys.index(state.major),
                                        radio_props={"facecolor": A_COLOR})
        self.major_radio.on_clicked(self._on_major)

        # created size options with "Any" first, so radio index 0 = None and index k = size k - 1
        self._header("Campus size", 0.02)
        h = 0.076
        y = self._take(h, gap=0)
        ax = self.fig.add_axes([self.x0 + self.w * 0.04, y, self.w * 0.9, h], frameon=False)
        self.size_radio = RadioButtons(ax, ["Any"] + SIZE_LABELS, active=size_to_radio(state.pref_size),
                                       radio_props={"facecolor": A_COLOR})
        self.size_radio.on_clicked(self._on_size)

        for radio in (self.major_radio, self.size_radio):
            self.widgets.append(radio)
            for t in radio.labels:
                t.set_fontsize(FONT)

    # ---------------------------------------------------------------- priorities
    def _build_priorities(self, state):
        y = self._header("Priorities", 0.02)

        # created total next to the header, each priority is 0-100 so the max is 500
        self.total_text = self.fig.text(self.x0 + self.w * 0.96, y + 0.006, "", fontsize=7,
                                        color=MUTED, ha="right")

        # created dicts of sliders and text boxes by weight key, each priority moves on its own
        self.sliders = {}
        self.weight_boxes = {}
        self.weight_labels = {}
        h = 0.02
        for key, label in WEIGHT_LABELS.items():
            y = self._take(h, gap=0.005)
            self.weight_labels[key] = self._label(label, y, h)

            ax = self.fig.add_axes([self.wx, y, self.ww * 0.64, h])
            s = Slider(ax, "", 0, 100, valinit=state.weights[key], valstep=1, color=A_COLOR, track_color=GRID)
            s.valtext.set_visible(False)
            s.vline.set_visible(False)
            s.on_changed(lambda val, k=key: self._on_weight_slider(k, val))
            self.sliders[key] = s
            self.widgets.append(s)

            box = self._text_box([self.wx + self.ww * 0.70, y, self.ww * 0.30, h], str(state.weights[key]))
            box.on_submit(lambda text, k=key: self._on_weight_box(k, text))
            self.weight_boxes[key] = box

    # ---------------------------------------------------------------- schools
    def _build_schools(self, state):
        y = self._header("My schools", 0.02)
        self.count_text = self.fig.text(self.x0 + self.w * 0.96, y + 0.006, "", fontsize=7,
                                        color=MUTED, ha="right")

        # created search box, typing in it shows matching schools in the rows below
        h = 0.026
        y = self._take(h)
        self._label("Search", y, h)
        self.search_box = self._text_box([self.wx, y, self.ww, h], "")
        self.search_box.on_text_change(self._on_search_change)
        self.search_box.on_submit(self._on_search_submit)

        # created as many rows as fit above the status line (up to MAX_SCHOOLS)
        row_h = 0.019
        list_bottom = self.bottom + 0.026
        n_rows = int((self.y - 0.004 - list_bottom) / row_h)
        n_rows = max(1, min(MAX_SCHOOLS, n_rows))

        # created hint shown when the list is empty
        self.hint = self.fig.text(self.x0 + self.w * 0.5, self.y - 0.04, "", fontsize=7.5,
                                  color=MUTED, ha="center", va="center")

        # created one name button and one remove (x) button per row
        self.name_buttons = []
        self.remove_buttons = []
        for k in range(n_rows):
            y = self._take(row_h, gap=0)
            name_ax = self.fig.add_axes([self.x0 + self.w * 0.03, y, self.w * 0.80, row_h * 0.92])
            name_btn = Button(name_ax, "", color=PANEL_BG, hovercolor=ROW_HOVER)
            name_btn.label.set_fontsize(FONT)
            name_btn.label.set_horizontalalignment("left")
            name_btn.label.set_x(0.03)
            name_btn.on_clicked(lambda _e, row=k: self._on_row_click(row))

            x_ax = self.fig.add_axes([self.x0 + self.w * 0.84, y, self.w * 0.12, row_h * 0.92])
            x_btn = Button(x_ax, "×", color=PANEL_BG, hovercolor="#f7dede")
            x_btn.label.set_fontsize(9)
            x_btn.label.set_color(MUTED)
            x_btn.on_clicked(lambda _e, row=k: self._on_remove_click(row))

            # hid the black borders so the rows look like a list instead of a stack of buttons
            for ax in (name_ax, x_ax):
                for sp in ax.spines.values():
                    sp.set_visible(False)

            self.name_buttons.append(name_btn)
            self.remove_buttons.append(x_btn)
            self.widgets.append(name_btn)
            self.widgets.append(x_btn)

    def _refresh_rows(self):
        # showed search matches while the user is typing, otherwise showed their schools
        query = self.search_box.text.strip()
        if query != "":
            self._show_suggestions(query)
        else:
            self._show_list()

    def _show_list(self):
        self.mode = "list"
        state = self.store.state
        self.row_idx = list(state.selected)

        if len(self.row_idx) == 0:
            self.hint.set_text("Search above to add schools")
        else:
            self.hint.set_text("")

        # created list of the two compared schools so I can color them like the head-to-head chart
        pair = list(state.pair)

        for k in range(len(self.name_buttons)):
            if k < len(self.row_idx):
                idx = self.row_idx[k]
                s = self.schools.iloc[idx]
                color = TEXT
                weight = "normal"
                if len(pair) > 0 and idx == pair[0]:
                    color = A_COLOR
                    weight = "bold"
                elif len(pair) > 1 and idx == pair[1]:
                    color = B_COLOR
                    weight = "bold"
                self._show_row(k, f"{s['ab']} ({s['st']})", color, weight, show_x=True)
            else:
                self._hide_row(k)

    def _show_suggestions(self, query):
        self.mode = "suggest"
        selected = self.store.state.selected
        self.row_idx = search_schools(self.schools, query, len(self.name_buttons))

        if len(self.row_idx) == 0:
            self.hint.set_text(f"No schools match '{query}'")
        else:
            self.hint.set_text("")

        for k in range(len(self.name_buttons)):
            if k < len(self.row_idx):
                s = self.schools.iloc[self.row_idx[k]]
                if self.row_idx[k] in selected:
                    self._show_row(k, f"✓ {s['ab']} ({s['st']})", MUTED, "normal", show_x=False)
                else:
                    self._show_row(k, f"+ {s['ab']} ({s['st']})", TEXT, "normal", show_x=False)
            else:
                self._hide_row(k)

    def _show_row(self, k, text, color, weight, show_x):
        btn = self.name_buttons[k]
        btn.label.set_text(text)
        btn.label.set_color(color)
        btn.label.set_fontweight(weight)
        btn.ax.set_visible(True)
        btn.active = not self.popup_open

        x_btn = self.remove_buttons[k]
        x_btn.ax.set_visible(show_x)
        x_btn.active = show_x and not self.popup_open

    def _hide_row(self, k):
        for btn in (self.name_buttons[k], self.remove_buttons[k]):
            btn.ax.set_visible(False)
            btn.active = False

    # ================================================================ callbacks
    def _on_test_check(self, _label):
        use_sat = self.sat_check.get_status()[0]
        use_act = self.act_check.get_status()[0]
        if not use_sat and not use_act:
            self._ok("no test score: chances use admit rate only")
        elif use_sat and use_act:
            self._ok("using the better of your SAT and ACT")
        else:
            self._ok("")
        self.store.update(use_sat=use_sat, use_act=use_act)

    def _on_sat(self, text):
        # checked the SAT is a whole number between 400 and 1600
        sat = parse_int(text)
        if sat is None or sat < 400 or sat > 1600:
            self._error("SAT must be a number from 400 to 1600")
            self._set_box(self.sat_box, str(self.store.state.sat))
            return
        if sat == self.store.state.sat:
            return

        # checked the SAT box too, since typing a new score means they want to use it
        self._ok(f"SAT set to {sat}")
        self.store.update(sat=sat, use_sat=True)

    def _on_act(self, text):
        act = parse_int(text)
        if act is None or act < 1 or act > 36:
            self._error("ACT must be a number from 1 to 36")
            self._set_box(self.act_box, str(self.store.state.act))
            return
        if act == self.store.state.act:
            return
        self._ok(f"ACT set to {act}")
        self.store.update(act=act, use_act=True)

    def _keep_dollar_sign(self, text):
        # kept the "$" locked at the front while typing: removed any "$" the user typed or moved,
        # put one back at the start, and kept the cursor after it
        box = self.budget_box
        before_cursor = text[:box.cursor_index].replace("$", "")
        rest = text.replace("$", "")
        fixed = "$" + rest
        if fixed == text and box.cursor_index >= 1:
            return

        box.eventson = False
        box.set_val(fixed)
        box.eventson = True

        # moved the cursor to where it was, counting the "$" (TextBox has no public way to do this)
        box.cursor_index = 1 + len(before_cursor)
        box._rendercursor()

    def _on_budget_box(self, text):
        budget = parse_money(text)
        if budget is None or budget <= 0 or budget > BUDGET_MAX:
            self._error(f"budget must be $1 to {money(BUDGET_MAX)} (ex. 35000 or 35k)")
            self._set_box(self.budget_box, money(self.store.state.budget))
            return
        if budget == self.store.state.budget:
            return
        self._ok(f"budget set to {money(budget)}")
        self.store.update(budget=budget)

    def _on_budget_slider(self, val):
        self.store.update(budget=int(val))

    def _on_major(self, _label):
        index = self.major_radio.index_selected
        self.store.update(major=self.major_keys[index])

    def _on_size(self, _label):
        index = self.size_radio.index_selected
        self.store.update(pref_size=radio_to_size(index))

    def _on_weight_slider(self, key, val):
        # copied the weights and changed only this one, the others stay where they are
        new = dict(self.store.state.weights)
        new[key] = int(val)
        self.store.update(weights=new)

    def _on_weight_box(self, key, text):
        value = parse_int(text)
        if value is None or value < 0 or value > 100:
            self._error("priorities must be a number from 0 to 100")
            self._set_box(self.weight_boxes[key], str(self.store.state.weights[key]))
            return
        if value == self.store.state.weights[key]:
            return
        new = dict(self.store.state.weights)
        new[key] = value
        self.store.update(weights=new)

    def _on_search_change(self, _text):
        self._refresh_rows()
        self.fig.canvas.draw_idle()

    def _on_search_submit(self, _text):
        # only added a school when Enter was pressed (clicking away from the box also sends a submit)
        if not self.search_box.capturekeystrokes:
            return
        for idx in self.row_idx:
            if idx not in self.store.state.selected:
                self._add_school(idx)
                return
        if len(self.row_idx) == 0:
            self._error("no school matches that search")

    def _on_row_click(self, row):
        if row >= len(self.row_idx):
            return
        idx = self.row_idx[row]
        if self.mode == "suggest":
            self._add_school(idx)
        else:
            # clicking a school on my list sends it to the head-to-head comparison
            self._ok(f"comparing {self.schools.iloc[idx]['ab']}")
            self.store.pick_school(idx)

    def _on_remove_click(self, row):
        if self.mode != "list" or row >= len(self.row_idx):
            return
        idx = self.row_idx[row]
        selected = []
        for i in self.store.state.selected:
            if i != idx:
                selected.append(i)
        self._ok(f"removed {self.schools.iloc[idx]['ab']}")
        self.store.update(selected=selected)

    def _add_school(self, idx):
        selected = list(self.store.state.selected)
        name = self.schools.iloc[idx]["ab"]
        if idx in selected:
            self._error(f"{name} is already on your list")
            return
        if len(selected) >= len(self.name_buttons):
            self._error(f"list is full ({len(self.name_buttons)}), remove a school first")
            return
        selected.append(idx)

        # cleared the search first so the rows switch back to my list
        self._set_box(self.search_box, "")
        self.search_box.cursor_index = 0
        self._ok(f"added {name}")
        self.store.update(selected=selected)

    # ================================================================ render
    def render(self, rows, state):
        # synced every widget to the state without firing callbacks (other sections can change state too)
        self.state_button.label.set_text(self._state_text(state.st))

        self._set_check(self.sat_check, state.use_sat)
        self._set_check(self.act_check, state.use_act)
        self._set_box(self.sat_box, str(state.sat))
        self._set_box(self.act_box, str(state.act))

        # grayed out the score of a test that isn't being used
        self.sat_box.text_disp.set_color(TEXT if state.use_sat else MUTED)
        self.act_box.text_disp.set_color(TEXT if state.use_act else MUTED)

        self._set_box(self.budget_box, money(state.budget))
        self._set_slider(self.budget_slider, min(state.budget, BUDGET_MAX))

        self._set_radio(self.major_radio, self.major_keys.index(state.major))
        self._set_radio(self.size_radio, size_to_radio(state.pref_size))

        self._sync_priorities(state)

        self.count_text.set_text(f"{len(state.selected)} / {len(self.name_buttons)}")
        self._refresh_rows()

    def _sync_priorities(self, state):
        # created variable for whether the Size priority is used (it isn't when campus size is "Any")
        size_on = state.pref_size is not None

        for key in WEIGHT_LABELS:
            shown = state.weights[key]

            # showed Size at 0 and locked it when it's off, but kept the saved value for when it comes back
            if key == "size" and not size_on:
                shown = 0
            self._set_slider(self.sliders[key], shown)
            self._set_box(self.weight_boxes[key], str(shown))

        size_label = self.weight_labels["size"]
        if size_on:
            size_label.set_text(WEIGHT_LABELS["size"])
            size_label.set_color(MUTED)
        else:
            size_label.set_text("Size (off)")
            size_label.set_color(GRID)

        active = size_on and not self.popup_open
        self.sliders["size"].active = active
        self.weight_boxes["size"].active = active

        # added up only the priorities in use, each out of 100
        total = 0
        count = 0
        for key in WEIGHT_LABELS:
            if key == "size" and not size_on:
                continue
            total = total + state.weights[key]
            count = count + 1
        self.total_text.set_text(f"total {total} / {100 * count}")

    # ---------------------------------------------------------------- sync helpers
    def _set_slider(self, slider, value):
        if slider.val != value:
            slider.eventson = False
            slider.set_val(value)
            slider.eventson = True

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

    def _set_check(self, check, on):
        if check.get_status()[0] != on:
            check.eventson = False
            check.set_active(0)
            check.eventson = True

    def _ok(self, msg):
        self.status.set_text(msg)
        self.status.set_color(MUTED)

    def _error(self, msg):
        self.status.set_text(msg)
        self.status.set_color(REACH)
        self.fig.canvas.draw_idle()


def size_to_radio(pref_size):
    # turned the state's size (None = any) into the radio button index ("Any" is index 0)
    if pref_size is None:
        return 0
    return pref_size + 1


def radio_to_size(index):
    # turned the radio button index back into the state's size
    if index == 0:
        return None
    return index - 1


def parse_int(text):
    # turned typed text into an int, or None if it isn't a whole number
    try:
        return int(text.strip())
    except ValueError:
        return None


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


def search_schools(schools, query, limit):
    # found schools matching the typed text, best matches first
    # score 0 = exact name, 1 = name starts with it, 2 = a word starts with it, 3 = every typed word is in the name
    q = query.lower()
    words = q.split()
    found = []

    for idx in range(len(schools)):
        short = str(schools.at[idx, "ab"]).lower()
        full = str(schools.at[idx, "n"]).lower()

        if short == q or full == q:
            score = 0
        elif short.startswith(q) or full.startswith(q):
            score = 1
        elif (" " + q) in (" " + full) or (" " + q) in (" " + short):
            score = 2
        elif all(w in full or w in short for w in words):
            score = 3
        else:
            continue

        # broke ties with bigger schools first, since those are the ones people usually mean
        found.append((score, -schools.at[idx, "sz"], idx))

    found.sort()
    result = []
    for score, size, idx in found[:limit]:
        result.append(int(idx))
    return result
