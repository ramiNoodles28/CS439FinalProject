from matplotlib.widgets import TextBox, Button
from matplotlib.patches import Rectangle
from matplotlib.patches import Rectangle, FancyBboxPatch

# Colors and helper functions shared with the rest of the dashboard
from core import A_COLOR, B_COLOR, TEXT, GRID, CHANCE_COLOR, SIZE_LABELS
from core import money, pct, tuition_for, chance, size_index

# Comparison rows: label, column in schools, formatting, higher vals, scale low, scale high
# Each tuple becomes one row of bars, higher vals = True means bigger number wins
# Scale low/high is the range a full bar covers, picked to fit each metric:
#   tuition: $0 to $75K (most expensive school in the data)
#   earnings: $0 to $130K (only a dozen schools go past this)
#   rates: 0 to 100%
#   SAT: 400 to 1600 (the real SAT range)
#   student to faculty: 0 to 30 (only a few schools go past this)
# Values outside the range get cut off at the end of the bar
METRICS = [
    ('Your tuition', 'tuition', 'money', False, 0, 75000),
    ('Earnings (10 yr)', 'earn', 'money', True, 0, 130000),
    ('Graduation rate', 'gr', 'pct', True, 0, 100),
    ('Retention rate', 'ret', 'pct', True, 0, 100),
    ('Admit rate', 'adm', 'pct', True, 0, 100),
    ('Average SAT', 'sat', 'num', True, 400, 1600),
    ('Student to Faculty', 'sfr', 'ratio', False, 0, 30)
]

# Space between the center line and where the bars start
GAP = 0.03

# Head to head section
class CollegeComparison:
    # store holds the current state (pair, home state, SAT), schools is the dataframe from load_schools
    def __init__(self, store, schools):
        self.store = store
        self.schools = schools

    # Called once by main.py
    # Spec is the slot for section, fig is whole figure
    # This sets up the three subplots for the section, header, bars, and bottom
    def build(self, fig, spec):
        # Splits into 1 column and 3 rows (header, bars, bottom)
        subgrid = spec.subgridspec(3, 1, hspace=0.05, height_ratios=[1, 6, 2.2])

        # header with school names
        self.head = fig.add_subplot(subgrid[0, 0])
        self.head.axis("off")

        # Bars go in middle
        self.ax = fig.add_subplot(subgrid[1, 0])
        self.ax.axis("off")

        # Chance, residency, size on bottom
        self.banner = fig.add_subplot(subgrid[2, 0])
        self.banner.axis("off")

        # Clicking a school name box picks which side the next ranking click replaces
        fig.canvas.mpl_connect("button_press_event", self.on_click)

    # Click on the blue box picks side A, click on the orange box picks side B
    # The picked side gets an outline, then clicking a school in the ranking puts it there
    def on_click(self, event):
        # Only clicks in the header, and only when two schools are showing
        if event.inaxes is not self.head or event.button != 1:
            return
        if len(self.store.state.pair) < 2:
            return

        # Left of the middle is A, right of the middle is B (x goes -1 to 1)
        if event.xdata < 0:
            side = 0
        else:
            side = 1
        if side != self.store.state.pair_target:
            self.store.update(pair_target=side)

    # Get the value for one metric
    # Tuition is different since it depends on home state
    def get_value(self, school, column, state):
        if column == 'tuition':
            return tuition_for(school, state.st)
        elif column == 'earn':
            return school['earn']
        elif column == 'gr':
            return school['gr']
        elif column == 'ret':
            return school['ret']
        elif column == 'adm':
            return school['adm']
        elif column == 'sat':
            return school['sat']
        elif column == 'sfr':
            return school['sfr']
        else:
            raise ValueError(f"Unknown col: {column}")

    # In-state if the school is in the same state as the user
    def residency_text(self, school, state):
        if state.st == school['st']:
            return "In-state"
        else:
            return "Out-of-state"

    # Size label plus student count in thousands, ex. Very large (45K)
    def size_text(self, school):
        return f"{school['sz'] / 1000:.0f}K"

    # Called by main.py every time the state changes, redraws the whole section
    def render(self, rows, state):
        # Clear everything from the last render so nothing stacks up
        self.head.clear()
        self.ax.clear()
        self.banner.clear()
        self.head.axis("off")
        self.ax.axis("off")
        self.banner.axis("off")

        # Need two schools to compare, show the empty skeleton until there are two
        if len(state.pair) < 2 or None in state.pair:
            self.draw_skeleton()
            return

        # Get the row of data for each school
        school_a = self.schools.loc[state.pair[0]]
        school_b = self.schools.loc[state.pair[1]]

        # Draw each part, draw_bars gives back how many metrics each school won
        self.draw_header(school_a, school_b, state.pair_target)
        wins = self.draw_bars(school_a, school_b, state)
        self.draw_bottom(school_a, school_b, wins, state)

    # Empty version of the section, same layout as a real comparison but with no schools
    # Grey boxes, empty tracks, and dashes so the user can see what will show up
    def draw_skeleton(self):
        head = self.head
        ax = self.ax
        bottom = self.banner

        # Header, two grey boxes in the same spots as the school name boxes
        head.set_xlim(-1, 1)
        head.set_ylim(0, 1)
        head.text(0, 1.15, "HEAD-TO-HEAD", ha="center", va="center", fontsize=8, fontweight="bold", color=TEXT)
        width = 1 - GAP
        head.add_patch(Rectangle((-1, 0.1), width, 0.8, facecolor=GRID, edgecolor='none'))
        head.add_patch(Rectangle((GAP, 0.1), width, 0.8, facecolor=GRID, edgecolor='none'))
        head.text(-1 + 0.04, 0.5, "Select a school", ha='left', va='center', fontsize=9, color=TEXT, alpha=0.5)
        head.text(GAP + width - 0.04, 0.5, "Select a school", ha='right', va='center', fontsize=9, color=TEXT,
                  alpha=0.5)

        # Bars, same sizes as draw_bars but only the empty tracks
        ax.set_xlim(-1, 1)
        ax.set_ylim(len(METRICS)-0.5, -0.5)
        span = .62
        bar_h = 0.4
        box = ax.get_window_extent()
        aspect = (len(METRICS) / box.height) / (2 / box.width)
        radius = bar_h / 2 / aspect

        for i in range(len(METRICS)):
            label = METRICS[i][0]
            ax.add_patch(FancyBboxPatch((-GAP - span, i + 0.12 - bar_h / 2), span, bar_h,
                                        boxstyle=f"round,pad=0,rounding_size={radius}", mutation_aspect=aspect,
                                        facecolor=GRID, edgecolor='none', alpha=0.6))
            ax.add_patch(FancyBboxPatch((GAP, i + 0.12 - bar_h / 2), span, bar_h,
                                        boxstyle=f"round,pad=0,rounding_size={radius}", mutation_aspect=aspect,
                                        facecolor=GRID, edgecolor='none', alpha=0.6))
            ax.text(0, i - 0.26, label, ha='center', va='center', fontsize=7, fontweight='bold', color=TEXT)
            ax.text(-GAP - span - 0.03, i + 0.12, "—", ha='right', va='center', fontsize=8, color=TEXT, alpha=0.5)
            ax.text(GAP + span + 0.03, i + 0.12, "—", ha='left', va='center', fontsize=8, color=TEXT, alpha=0.5)

        # Bottom rows with dashes, plus a hint for how to fill it in
        bottom.set_xlim(-1, 1)
        bottom.set_ylim(4, 0)
        bottom.axhline(0.2, xmin=0.05, xmax=0.95, color=GRID, linewidth=1)
        for y, label in [(0.8, 'Your chance'), (1.7, 'Residency'), (2.6, 'Campus size')]:
            bottom.text(0, y, label, ha='center', va='center', fontsize=7.5, color=TEXT)
            bottom.text(-0.5, y, "—", ha='center', va='center', fontsize=8, color=TEXT, alpha=0.5)
            bottom.text(0.5, y, "—", ha='center', va='center', fontsize=8, color=TEXT, alpha=0.5)
        bottom.text(0, 3.6, "Click schools in the ranking to compare them", ha='center', va='center',
                    fontsize=7.5, fontstyle='italic', color=TEXT, alpha=0.6)

    # Title and a colored box for each school, target is the side the next ranking click replaces
    def draw_header(self, school_a, school_b, target):
        head = self.head
        # x goes -1 to 1 so 0 is the middle, same as the bars
        head.set_xlim(-1, 1)
        head.set_ylim(0, 1)
        head.text(0, 1.15, "HEAD-TO-HEAD", ha="center", va="center", fontsize=8, fontweight="bold", color=TEXT)

        # School A box on the left, school B box on the right
        self.draw_name_box(school_a, -1, A_COLOR, 'left', target == 0)
        self.draw_name_box(school_b, GAP, B_COLOR, 'right', target == 1)

    # Box with school name and state, colored by school A or B
    # The side that the next click will replace gets a dark outline
    def draw_name_box(self, school, x, color, align, targeted):
        head = self.head
        # Box width lines up with the bars
        width = 1 - GAP
        if targeted:
            head.add_patch(Rectangle((x, 0.1), width, 0.8, facecolor=color, edgecolor='#8a93a6', linewidth=1.2))
        else:
            head.add_patch(Rectangle((x, 0.1), width, 0.8, facecolor=color, edgecolor='none'))

        # Cut off long names so they fit in the box
        name = school['ab']
        if len(name) > 20:
            name = name[:17] + "..."

        # Text goes on the outside edge of the box
        if align == 'left':
            text_x = x + 0.04

        else:
            text_x = x + width - 0.04
            
        head.text(text_x, 0.62, name, ha=align, va='center', fontsize=10, fontweight='bold', color='white')
        head.text(text_x, 0.3, school['st'], ha=align, va='center', fontsize=8, color='white', alpha=0.8)

    # Mirrored bars, school A goes left and school B goes right, returns [A wins, B wins]
    def draw_bars(self, school_a, school_b, state):
        ax = self.ax
        # x from -1 to 1 with 0 in the middle, y flipped so the first metric is on top
        ax.set_xlim(-1, 1)
        ax.set_ylim(len(METRICS)-0.5, -0.5)

        # Longest a bar can be, leaves room on the outside for the numbers
        span = .62
        wins = [0,0]
        # Data units per pixel are different in x and y, aspect fixes that so the rounded ends are circles
        box = ax.get_window_extent()
        aspect = (len(METRICS) / box.height) / (2 / box.width)


        # Compare each metric and determine which school wins, then draw the bars for each metric
        for i, (label, col, fmt, higher_better, low, high) in enumerate(METRICS):
            val_a = self.get_value(school_a, col, state)
            val_b = self.get_value(school_b, col, state)

            # Who wins this metric (ties mean nobody wins)
            a_wins = False
            b_wins = False
            if higher_better:
                if val_a > val_b:
                    a_wins = True
                elif val_b > val_a:
                    b_wins = True
            else:
                if val_a < val_b:
                    a_wins = True
                elif val_b < val_a:
                    b_wins = True

            # Count wins for the edge at the bottom
            if a_wins:
                wins[0] += 1
            elif b_wins:
                wins[1] += 1

            # Where each value sits in this metric's range, 0 = low end and 1 = high end
            frac_a = (val_a - low) / (high - low)
            frac_b = (val_b - low) / (high - low)

            # Keep it between 0 and 1 so outliers don't run past the end of the track
            frac_a = max(0, min(1, frac_a))
            frac_b = max(0, min(1, frac_b))
            len_a = span * frac_a
            len_b = span * frac_b

            # Draw bar for both, starting at the gap edge and going outward
            # Winner is solid, loser is faded
            # Rounded bars with box starts at the bottom left corner, so A's box starts at its outer end
            # Bars sit a little below the row center (+0.12) to leave room for the label above
            bar_h = 0.4

            # Light full-length track behind each bar so you can see where the scale ends
            radius = bar_h / 2 / aspect
            ax.add_patch(FancyBboxPatch((-GAP - span, i + 0.12 - bar_h / 2), span, bar_h,
                                        boxstyle=f"round,pad=0,rounding_size={radius}", mutation_aspect=aspect,
                                        facecolor=GRID, edgecolor='none', alpha=0.6))
            ax.add_patch(FancyBboxPatch((GAP, i + 0.12 - bar_h / 2), span, bar_h,
                                        boxstyle=f"round,pad=0,rounding_size={radius}", mutation_aspect=aspect,
                                        facecolor=GRID, edgecolor='none', alpha=0.6))

            radius = min(bar_h / 2 / aspect, len_a / 2)
            ax.add_patch(FancyBboxPatch((-GAP - len_a, i + 0.12 - bar_h / 2), len_a, bar_h,
                                        boxstyle=f"round,pad=0,rounding_size={radius}", mutation_aspect=aspect,
                                        facecolor=A_COLOR, edgecolor='none', alpha=1 if a_wins else 0.3))
            radius = min(bar_h / 2 / aspect, len_b / 2)
            ax.add_patch(FancyBboxPatch((GAP, i + 0.12 - bar_h / 2), len_b, bar_h,
                                        boxstyle=f"round,pad=0,rounding_size={radius}", mutation_aspect=aspect,
                                        facecolor=B_COLOR, edgecolor='none', alpha=1 if b_wins else 0.3))


            # Metric name above the bars (y is flipped so minus goes up)
            ax.text(0, i - 0.26, label, ha='center', va='center', fontsize=7, fontweight='bold', color=TEXT)

            # Turn numbers into text based on the metric type
            if fmt == 'money':
                text_a = money(val_a)
                text_b = money(val_b)
            elif fmt == 'pct':
                text_a = pct(val_a)
                text_b = pct(val_b)
            elif fmt == 'num':
                text_a = f"{val_a:.0f}"
                text_b = f"{val_b:.0f}"
            elif fmt == 'ratio':
                text_a = f"{val_a:.0f} : 1"
                text_b = f"{val_b:.0f} : 1"
            else:
                text_a = f"{val_a}"
                text_b = f"{val_b}"

            # Add text labels for each bar, just past the end of the track so they line up
            ax.text(-GAP - span - 0.03, i + 0.12, text_a, ha='right', va='center', fontsize=8, color=TEXT)
            ax.text(GAP + span + 0.03, i + 0.12, text_b, ha='left', va='center', fontsize=8, color=TEXT)

        return wins

    # Chance, residency, campus size, and the total edge at the bottom
    def draw_bottom(self, school_a, school_b, wins, state):
        bottom = self.banner
        # y is flipped so rows go top to bottom, line separates it from the bars
        bottom.set_xlim(-1, 1)
        bottom.set_ylim(4, 0)
        bottom.axhline(0.2, xmin=0.05, xmax=0.95, color=GRID, linewidth=1)

        # chance gives back (probability, label), only need the label
        chance_a = chance(school_a, state.sat)[1]
        chance_b = chance(school_b, state.sat)[1]

        # Chance row colored by Likely/Target/Reach
        bottom.text(0, 0.8, 'Your chance', ha='center', va='center', fontsize=7.5, color=TEXT)
        bottom.text(-0.5, 0.8, chance_a, ha='center', va='center', fontsize=8, fontweight='bold',
                    color=CHANCE_COLOR[chance_a])
        bottom.text(0.5, 0.8, chance_b, ha='center', va='center', fontsize=8, fontweight='bold',
                    color=CHANCE_COLOR[chance_b])

        # Plain text rows - y position, label, school A text, school B text
        other_rows = [
            (1.7, 'Residency', self.residency_text(school_a, state), self.residency_text(school_b, state)),
            (2.6, 'Campus size', self.size_text(school_a), self.size_text(school_b)),
        ]
        for y, label, a_text, b_text in other_rows:
            bottom.text(0, y, label, ha='center', va='center', fontsize=7.5, color=TEXT)
            bottom.text(-0.5, y, a_text, ha='center', va='center', fontsize=8, fontweight='bold', color=TEXT)
            bottom.text(0.5, y, b_text, ha='center', va='center', fontsize=8, fontweight='bold', color=TEXT)

        # Hint that says which school the next ranking click replaces
        if state.pair_target == 0:
            replace_name = school_a['ab']
        else:
            replace_name = school_b['ab']
        bottom.text(0, 3.6, f"Click a school in the ranking to replace {replace_name}  ·  click a name to switch side",
                    ha='center', va='center', fontsize=7, fontstyle='italic', color=TEXT, alpha=0.6)

