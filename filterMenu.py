from dataclasses import replace
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


class FastTextBox(TextBox):
    # a TextBox that redraws only itself while typing
    # (matplotlib's TextBox calls canvas.draw() on every key press, click and hover, which redraws every chart)

    def _redraw_only_me(self, method, *args):
        canvas = self.ax.figure.canvas
        if not canvas.supports_blit:
            return method(*args)

        def draw_box(*_args, **_kwargs):
            # put the real draw back first, so anything after this (like a submit) draws normally
            del canvas.draw
            self.ax.figure.draw_artist(self.ax)
            canvas.blit(self.ax.bbox)

        # swapped canvas.draw for one call so the TextBox's own draw only redraws this box
        canvas.draw = draw_box
        try:
            return method(*args)
        finally:
            if "draw" in vars(canvas):
                del canvas.draw

    def _rendercursor(self):
        return self._redraw_only_me(super()._rendercursor)

    def stop_typing(self):
        return self._redraw_only_me(super().stop_typing)

    def _motion(self, event):
        return self._redraw_only_me(super()._motion, event)


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

        # created dict of changes made in the menu that haven't been applied yet (field name -> new value)
        self.draft = {}

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

        # created list of every axes and text in the menu, in drawing order, so I can redraw just the menu
        self.menu_artists = []

        # drew light panel behind the whole menu
        bg = self._axes([box.x0, box.y0, box.width, box.height])
        self.bg = bg
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
        self.status = self._text(self.x0 + self.w * 0.04, self.bottom + 0.008, "", fontsize=7,
                               color=MUTED, va="bottom")

        self._build_apply_row()

        # built the dropdown last so it draws on top of everything else
        self._build_state_popup(state)
        fig.canvas.mpl_connect("button_press_event", self._on_press)

    # ---------------------------------------------------------------- layout helpers
    def _axes(self, rect, **kwargs):
        # added an axes to the figure and remembered it as part of the menu
        ax = self.fig.add_axes(rect, **kwargs)
        self.menu_artists.append(ax)
        return ax

    def _text(self, x, y, text, **kwargs):
        # added a figure text and remembered it as part of the menu
        t = self.fig.text(x, y, text, **kwargs)
        self.menu_artists.append(t)
        return t

    def _take(self, h, gap=0.006):
        # moved down the panel and returned the bottom y of the next row
        self.y = self.y - h - gap
        return self.y

    def _header(self, text, h, big=False):
        y = self._take(h)
        size = 12 if big else 9
        self._text(self.x0 + self.w * 0.04, y + h * 0.3, text, fontsize=size,
                      fontweight="bold", color=TEXT)
        return y

    def _label(self, text, y, h):
        # drew left-side label for a widget row
        return self._text(self.x0 + self.w * 0.04, y + h / 2, text, fontsize=FONT,
                             color=MUTED, va="center")

    def _text_box(self, rect, initial):
        box = FastTextBox(self._axes(rect), "", initial=initial)
        box.text_disp.set_fontsize(FONT)
        self.widgets.append(box)
        return box

    # ---------------------------------------------------------------- home state
    def _build_home_state(self, state):
        h = 0.028
        y = self._take(h)
        self.state_row_y = y
        self._label("Home state", y, h)

        ax = self._axes([self.wx, y, self.ww, h])
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

        self.popup_ax = self._axes([self.x0 + self.w * 0.03, top - height, self.w * 0.94, height])
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
            cell.set_visible(code == self._view().st)
        for widget in self.widgets:
            widget.active = False
        self.popup_open = True
        self.popup_ax.set_visible(True)
        self._redraw_menu()

    def _close_popup(self):
        self.popup_open = False
        self.popup_ax.set_visible(False)
        for widget in self.widgets:
            widget.active = True

        # re-synced everything, which re-hides empty school rows, re-locks Size and sets the apply buttons
        self._sync(self._view())
        self._redraw_menu()

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
                self._stage(st=code)
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
        self._text(self.wx + self.ww * 0.5, y + h / 2, "400-1600", fontsize=6.5, color=MUTED, va="center")
        self.sat_check.on_clicked(self._on_test_check)
        self.sat_box.on_submit(self._on_sat)

        y = self._take(h)
        self.act_check = self._test_check("ACT", state.use_act, y, h)
        self.act_box = self._text_box([self.wx, y, self.ww * 0.45, h], str(state.act))
        self._text(self.wx + self.ww * 0.5, y + h / 2, "1-36", fontsize=6.5, color=MUTED, va="center")
        self.act_check.on_clicked(self._on_test_check)
        self.act_box.on_submit(self._on_act)

    def _test_check(self, name, on, y, h):
        ax = self._axes([self.x0 + self.w * 0.02, y, self.w * 0.34, h], frameon=False)
        check = CheckButtons(ax, [name], [on], check_props={"facecolor": A_COLOR}, useblit=False)
        check.drawon = False
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
        ax = self._axes([self.wx, y, self.ww, h])
        self.budget_slider = Slider(ax, "", BUDGET_MIN, BUDGET_MAX, valinit=min(state.budget, BUDGET_MAX),
                                    valstep=BUDGET_STEP, color=A_COLOR, track_color=GRID)
        self.budget_slider.valtext.set_visible(False)
        self.budget_slider.vline.set_visible(False)
        self.budget_slider.drawon = False
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
        ax = self._axes([self.x0 + self.w * 0.04, y, self.w * 0.9, h], frameon=False)
        self.major_radio = RadioButtons(ax, major_labels,
                                        active=self.major_keys.index(state.major),
                                        radio_props={"facecolor": A_COLOR}, useblit=False)
        self.major_radio.on_clicked(self._on_major)

        # created size options with "Any" first, so radio index 0 = None and index k = size k - 1
        self._header("Campus size", 0.02)
        h = 0.076
        y = self._take(h, gap=0)
        ax = self._axes([self.x0 + self.w * 0.04, y, self.w * 0.9, h], frameon=False)
        self.size_radio = RadioButtons(ax, ["Any"] + SIZE_LABELS, active=size_to_radio(state.pref_size),
                                       radio_props={"facecolor": A_COLOR}, useblit=False)
        self.size_radio.on_clicked(self._on_size)

        for radio in (self.major_radio, self.size_radio):
            radio.drawon = False
            self.widgets.append(radio)
            for t in radio.labels:
                t.set_fontsize(FONT)

    # ---------------------------------------------------------------- priorities
    def _build_priorities(self, state):
        y = self._header("Priorities", 0.02)

        # created total next to the header, each priority is 0-100 so the max is 500
        self.total_text = self._text(self.x0 + self.w * 0.96, y + 0.006, "", fontsize=7,
                                        color=MUTED, ha="right")

        # created dicts of sliders and text boxes by weight key, each priority moves on its own
        self.sliders = {}
        self.weight_boxes = {}
        self.weight_labels = {}
        h = 0.02
        for key, label in WEIGHT_LABELS.items():
            y = self._take(h, gap=0.005)
            self.weight_labels[key] = self._label(label, y, h)

            ax = self._axes([self.wx, y, self.ww * 0.64, h])
            s = Slider(ax, "", 0, 100, valinit=state.weights[key], valstep=1, color=A_COLOR, track_color=GRID)
            s.valtext.set_visible(False)
            s.vline.set_visible(False)
            s.drawon = False
            s.on_changed(lambda val, k=key: self._on_weight_slider(k, val))
            self.sliders[key] = s
            self.widgets.append(s)

            box = self._text_box([self.wx + self.ww * 0.70, y, self.ww * 0.30, h], str(state.weights[key]))
            box.on_submit(lambda text, k=key: self._on_weight_box(k, text))
            self.weight_boxes[key] = box

    # ---------------------------------------------------------------- schools
    def _build_schools(self, state):
        y = self._header("My schools", 0.02)
        self.count_text = self._text(self.x0 + self.w * 0.96, y + 0.006, "", fontsize=7,
                                        color=MUTED, ha="right")

        # created search box, typing in it shows matching schools in the rows below
        h = 0.026
        y = self._take(h)
        self._label("Search", y, h)
        self.search_box = self._text_box([self.wx, y, self.ww, h], "")
        self.search_box.on_text_change(self._on_search_change)
        self.search_box.on_submit(self._on_search_submit)

        # created as many rows as fit above the status line (up to MAX_SCHOOLS)
        # shrank the rows a little if needed so all MAX_SCHOOLS fit above the apply buttons
        list_bottom = self.bottom + 0.062
        n_rows = MAX_SCHOOLS
        row_h = min(0.019, (self.y - 0.004 - list_bottom) / n_rows)

        # created hint shown when the list is empty
        self.hint = self._text(self.x0 + self.w * 0.5, self.y - 0.04, "", fontsize=7.5,
                                  color=MUTED, ha="center", va="center")

        # created one name button and one remove (x) button per row
        self.name_buttons = []
        self.remove_buttons = []
        for k in range(n_rows):
            y = self._take(row_h, gap=0)
            name_ax = self._axes([self.x0 + self.w * 0.03, y, self.w * 0.80, row_h * 0.92])
            name_btn = Button(name_ax, "", color=PANEL_BG, hovercolor=ROW_HOVER)
            name_btn.label.set_fontsize(FONT)
            name_btn.label.set_horizontalalignment("left")
            name_btn.label.set_x(0.03)
            name_btn.on_clicked(lambda _e, row=k: self._on_row_click(row))

            x_ax = self._axes([self.x0 + self.w * 0.84, y, self.w * 0.12, row_h * 0.92])
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
        state = self._view()
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
        selected = self._view().selected
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

    # ================================================================ draft + apply
    def _view(self):
        # created copy of the state with my unapplied changes on top, this is what the menu shows
        return replace(self.store.state, **self.draft)

    def _stage(self, **changes):
        # saved changes in the draft instead of updating the dashboard right away
        state = self.store.state
        for key, value in changes.items():
            if getattr(state, key) == value:
                # removed it from the draft since it's back to what the dashboard already shows
                self.draft.pop(key, None)
            else:
                self.draft[key] = value

        # only redrew the menu, the charts wait for Apply
        self._sync(self._view())
        self._redraw_menu()

    def _build_apply_row(self):
        # created Apply and Discard buttons at the bottom of the panel
        h = 0.03
        y = self.bottom + 0.026

        ax = self._axes([self.x0 + self.w * 0.04, y, self.w * 0.60, h])
        self.apply_button = Button(ax, "No changes", color=GRID, hovercolor=GRID)
        self.apply_button.label.set_fontsize(FONT)
        self.apply_button.label.set_fontweight("bold")
        self.apply_button.on_clicked(self._on_apply)

        ax = self._axes([self.x0 + self.w * 0.67, y, self.w * 0.29, h])
        self.discard_button = Button(ax, "Discard", color="white", hovercolor=ROW_HOVER)
        self.discard_button.label.set_fontsize(FONT)

        self.discard_button.on_clicked(self._on_discard)

        for btn in (self.apply_button, self.discard_button):
            for sp in btn.ax.spines.values():
                sp.set_color(GRID)
            self.widgets.append(btn)

    def _sync_apply_row(self):
        # made Apply stand out only when there is something to apply
        pending = len(self.draft) > 0
        btn = self.apply_button
        if pending:
            btn.label.set_text("Apply changes")
            btn.label.set_color("white")
            btn.color = A_COLOR
            btn.hovercolor = "#0b7565"
        else:
            btn.label.set_text("No changes")
            btn.label.set_color(MUTED)
            btn.color = GRID
            btn.hovercolor = GRID
        btn.ax.set_facecolor(btn.color)
        btn.active = pending and not self.popup_open

        self.discard_button.label.set_color(TEXT if pending else GRID)
        self.discard_button.active = pending and not self.popup_open

    def _on_apply(self, _event):
        if len(self.draft) == 0:
            return

        # sent every change in one update, so the dashboard recomputes and redraws once
        changes = dict(self.draft)
        self.draft.clear()
        self._ok("changes applied")
        self.store.update(**changes)

    def _on_discard(self, _event):
        self.draft.clear()
        self._ok("changes discarded")
        self._sync(self._view())
        self._redraw_menu()

    def _redraw_menu(self):
        # redrew only the menu panel instead of the whole dashboard (blitting)
        canvas = self.fig.canvas
        if not canvas.supports_blit:
            canvas.draw_idle()
            return
        for artist in self.menu_artists:
            self.fig.draw_artist(artist)
        canvas.blit(self.bg.bbox)

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
        self._stage(use_sat=use_sat, use_act=use_act)

    def _on_sat(self, text):
        view = self._view()

        # checked the SAT is a whole number between 400 and 1600
        sat = parse_int(text)
        if sat is None or sat < 400 or sat > 1600:
            self._error("SAT must be a number from 400 to 1600")
            self._replace_text(self.sat_box, str(view.sat))
            return
        if sat == view.sat:
            self._stage()
            return

        # checked the SAT box too, since typing a new score means they want to use it
        self._ok(f"SAT set to {sat}")
        self._stage(sat=sat, use_sat=True)

    def _on_act(self, text):
        view = self._view()
        act = parse_int(text)
        if act is None or act < 1 or act > 36:
            self._error("ACT must be a number from 1 to 36")
            self._replace_text(self.act_box, str(view.act))
            return
        if act == view.act:
            self._stage()
            return
        self._ok(f"ACT set to {act}")
        self._stage(act=act, use_act=True)

    def _keep_dollar_sign(self, text):
        # kept the "$" locked at the front while typing: removed any "$" the user typed or moved,
        # put one back at the start, and kept the cursor after it
        box = self.budget_box
        before_cursor = text[:box.cursor_index].replace("$", "")
        rest = text.replace("$", "")
        fixed = "$" + rest
        if fixed == text and box.cursor_index >= 1:
            return

        # set the text directly (set_val would redraw the box twice) and moved the cursor after the "$"
        box.text_disp.set_text(fixed)
        box.cursor_index = 1 + len(before_cursor)
        box._rendercursor()

    def _on_budget_box(self, text):
        view = self._view()
        budget = parse_money(text)
        if budget is None or budget <= 0 or budget > BUDGET_MAX:
            self._error(f"budget must be $1 to {money(BUDGET_MAX)} (ex. 35000 or 35k)")
            self._replace_text(self.budget_box, money(view.budget))
            return

        # reformatted what they typed, like "50k" -> "$50,000"
        self._replace_text(self.budget_box, money(budget))
        if budget == view.budget:
            self._stage()
            return
        self._ok(f"budget set to {money(budget)}")
        self._stage(budget=budget)

    def _on_budget_slider(self, val):
        self._stage(budget=int(val))

    def _on_major(self, _label):
        index = self.major_radio.index_selected
        self._stage(major=self.major_keys[index])

    def _on_size(self, _label):
        index = self.size_radio.index_selected
        self._stage(pref_size=radio_to_size(index))

    def _on_weight_slider(self, key, val):
        # copied the weights and changed only this one, the others stay where they are
        new = dict(self._view().weights)
        new[key] = int(val)
        self._stage(weights=new)

    def _on_weight_box(self, key, text):
        view = self._view()
        value = parse_int(text)
        if value is None or value < 0 or value > 100:
            self._error("priorities must be a number from 0 to 100")
            self._replace_text(self.weight_boxes[key], str(view.weights[key]))
            return
        if value == view.weights[key]:
            self._stage()
            return
        new = dict(view.weights)
        new[key] = value
        self._stage(weights=new)

    def _on_search_change(self, _text):
        self._refresh_rows()
        self._redraw_menu()

    def _on_search_submit(self, _text):
        # only added a school when Enter was pressed (clicking away from the box also sends a submit)
        if not self.search_box.capturekeystrokes:
            return
        selected = self._view().selected
        for idx in self.row_idx:
            if idx not in selected:
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
            return

        # clicking a school on my list sends it to the head-to-head comparison
        # (only for schools already applied, since the charts don't know about the others yet)
        if idx not in self.store.state.selected:
            self._error("apply changes first to compare this school")
            return
        self._ok(f"comparing {self.schools.iloc[idx]['ab']}")
        self.store.pick_school(idx)

    def _on_remove_click(self, row):
        if self.mode != "list" or row >= len(self.row_idx):
            return
        idx = self.row_idx[row]
        selected = []
        for i in self._view().selected:
            if i != idx:
                selected.append(i)
        self._ok(f"removed {self.schools.iloc[idx]['ab']}")
        self._stage(selected=selected)

    def _add_school(self, idx):
        selected = list(self._view().selected)
        name = self.schools.iloc[idx]["ab"]
        if idx in selected:
            self._error(f"{name} is already on your list")
            return
        if len(selected) >= len(self.name_buttons):
            self._error(f"list is full ({len(self.name_buttons)}), remove a school first")
            return
        selected.append(idx)

        # cleared the search first so the rows switch back to my list
        self._replace_text(self.search_box, "")
        self._ok(f"added {name}")
        self._stage(selected=selected)

    # ================================================================ render
    def render(self, rows, state):
        # called by main after the dashboard updates: dropped draft changes the state already has
        for key in list(self.draft):
            if getattr(state, key) == self.draft[key]:
                del self.draft[key]

        # main redraws the whole figure after this, so I only synced the widgets here
        self._sync(self._view())

    def _sync(self, view):
        # synced every widget to the view (state + draft) without firing callbacks
        self.state_button.label.set_text(self._state_text(view.st))

        self._set_check(self.sat_check, view.use_sat)
        self._set_check(self.act_check, view.use_act)
        self._set_box(self.sat_box, str(view.sat))
        self._set_box(self.act_box, str(view.act))

        # grayed out the score of a test that isn't being used
        self.sat_box.text_disp.set_color(TEXT if view.use_sat else MUTED)
        self.act_box.text_disp.set_color(TEXT if view.use_act else MUTED)

        self._set_box(self.budget_box, money(view.budget))
        self._set_slider(self.budget_slider, min(view.budget, BUDGET_MAX))

        self._set_radio(self.major_radio, self.major_keys.index(view.major))
        self._set_radio(self.size_radio, size_to_radio(view.pref_size))

        self._sync_priorities(view)

        self.count_text.set_text(f"{len(view.selected)} / {len(self.name_buttons)}")
        self._refresh_rows()
        self._sync_apply_row()

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
    # none of these draw anything: _redraw_menu() or main's redraw shows the changes

    def _set_slider(self, slider, value):
        if slider.val != value:
            slider.eventson = False
            slider.set_val(value)
            slider.eventson = True

    def _set_box(self, box, text):
        # skipped the box the user is typing in, so I don't wipe what they're typing
        if box.capturekeystrokes:
            return

        # set the text directly, since TextBox.set_val redraws the whole figure
        if box.text != text:
            box.text_disp.set_text(text)

    def _replace_text(self, box, text):
        # replaced a box's text even while typing in it, with the cursor moved to the end
        box.text_disp.set_text(text)
        box.cursor_index = len(text)
        if box.capturekeystrokes:
            box._rendercursor()

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
        self._redraw_menu()


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
