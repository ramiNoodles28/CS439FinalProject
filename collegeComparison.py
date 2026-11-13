from matplotlib.widgets import TextBox, Button
from matplotlib.patches import Rectangle

# Colors and helper functions shared with the rest of the dashboard
from core import A_COLOR, B_COLOR, TEXT, GRID, MUTED, CHANCE_COLOR, SIZE_LABELS
from core import money, pct, tuition_for, chance, size_index

# Comparison rows - label, column in schools, formatting, higher vals
# Each tuple becomes one row of bars, higher vals = True means bigger number wins
METRICS = [
    ('Your tuition', 'tuition', 'money', False),
    ('Earnings (10 yr)', 'earn', 'money', True),
    ('Graduation rate', 'gr', 'pct', True),
    ('Retention rate', 'ret', 'pct', True),
    ('Admit rate', 'adm', 'pct', True),
    ('Average SAT', 'sat', 'num', True),
    ('Student to Faculty', 'sfr', 'ratio', False)
]

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
        return f"{SIZE_LABELS[size_index(school['sz'])]} ({school['sz'] / 1000:.0f}K)"

    # Called by main.py every time the state changes, redraws the whole section
    def render(self, rows, state):
        # Clear everything from the last render so nothing stacks up
        self.head.clear()
        self.ax.clear()
        self.banner.clear()
        self.head.axis("off")
        self.ax.axis("off")
        self.banner.axis("off")

        # Need two schools to compare
        if len(state.pair) < 2 or None in state.pair:
            self.ax.text(0.5, 0.5, "Pick two schools", ha="center", va="center", color=MUTED,
                         transform=self.ax.transAxes)
            return

        # Get the row of data for each school
        school_a = self.schools.loc[state.pair[0]]
        school_b = self.schools.loc[state.pair[1]]

        # Draw each part, draw_bars gives back how many metrics each school won
        self.draw_header(school_a, school_b)
        wins = self.draw_bars(school_a, school_b, state)
        self.draw_bottom(school_a, school_b, wins, state)

    # Title and a colored box for each school
    def draw_header(self, school_a, school_b):
        head = self.head
        # x goes -1 to 1 so 0 is the middle, same as the bars
        head.set_xlim(-1, 1)
        head.set_ylim(0, 1)
        head.text(0, 1.15, "HEAD-TO-HEAD", ha="center", va="center", fontsize=8, fontweight="bold", color=MUTED)

        # School A box on the left, school B box on the right
        self.draw_name_box(school_a, -1, A_COLOR, 'left')
        self.draw_name_box(school_b, .30, B_COLOR, 'right')

    # Box with school name and state, colored by school A or B
    def draw_name_box(self, school, x, color, align):
        head = self.head
        # Box width lines up with the bars (1 - gap of .30)
        width = 0.70
        head.add_patch(Rectangle((x, 0.1), width, 0.8, facecolor=color, edgecolor='none', alpha=0.3))

        # Cut off long names so they fit in the box
        name = school['ab']
        if len(name) > 20:
            name = name[:17] + "..."

        # Text goes on the outside edge of the box
        if align == 'left':
            text_x = x + 0.04

        else:
            text_x = x + width - 0.04

        head.text(text_x, 0.62, name, ha=align, va='center', fontsize=10, fontweight='bold', color=TEXT)
        head.text(text_x, 0.3, school['st'], ha=align, va='center', fontsize=8, color=MUTED)

    # Mirrored bars, school A goes left and school B goes right, returns [A wins, B wins]
    def draw_bars(self, school_a, school_b, state):
        ax = self.ax
        # x from -1 to 1 with 0 in the middle, y flipped so the first metric is on top
        ax.set_xlim(-1, 1)
        ax.set_ylim(len(METRICS)-0.5, -0.5)

        # Longest a bar can be, leaves room on the outside for the numbers
        span = .45
        wins = [0,0]

        # Compare each metric and determine which school wins, then draw the bars for each metric
        for i, (label, col, fmt, higher_better) in enumerate(METRICS):
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

            # Scale both bars to the bigger value so dollars, percents, and SAT all fit
            biggest = max(val_a, val_b)
            if biggest == 0:
                biggest = 1
            len_a = span * val_a / biggest
            len_b = span * val_b / biggest

            # Draw bar for both, starting at the gap edge (.30) and going outward
            # Winner is solid, loser is faded
            ax.barh(i, -len_a, left=-.30, height=0.55, color=A_COLOR, alpha=1 if a_wins else 0.3)
            ax.barh(i, len_b, left=.30, height=0.55, color=B_COLOR, alpha=1 if b_wins else 0.3)

            # Metric name in middle
            ax.text(0, i, label, ha='center', va='center', fontsize=6, fontweight='bold', color=MUTED)

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

            # Add text labels for each bar, just past the end of the bar
            ax.text(-.30 - len_a - 0.03, i, text_a, ha='right', va='center', fontsize=8, color=TEXT)
            ax.text(.30 + len_b + 0.03, i, text_b, ha='left', va='center', fontsize=8, color=TEXT)

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
        bottom.text(0, 0.8, 'Your chance', ha='center', va='center', fontsize=7.5, color=MUTED)
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
            bottom.text(0, y, label, ha='center', va='center', fontsize=7.5, color=MUTED)
            bottom.text(-0.5, y, a_text, ha='center', va='center', fontsize=8, fontweight='bold', color=TEXT)
            bottom.text(0.5, y, b_text, ha='center', va='center', fontsize=8, fontweight='bold', color=TEXT)

        # How many metrics each school won
        edge = f"Edge on the numbers:  {school_a['ab']} {wins[0]}  –  {wins[1]} {school_b['ab']}"
        bottom.text(0, 3.6, edge, ha='center', va='center', fontsize=8, fontweight='bold', color=TEXT)

