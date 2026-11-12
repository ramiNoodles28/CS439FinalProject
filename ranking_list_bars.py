import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.text import Text
import numpy as np


# Ordered metric keys and display labels for the 5-part horizontal stacked bar
METRIC_KEYS = ["tuition", "grad", "earning", "admit", "sat"]
METRIC_LABELS = {
    "tuition": "Tuition",
    "grad": "Grad Rate",
    "earning": "Earnings",
    "admit": "Admit Rate",
    "sat": "SAT",
}

# Cohesive UI palette harmonized with the row design's teal (#138A72) & royal blue (#356AE6),
# matching the Blue -> Orange -> Green/Teal -> Red/Coral -> Purple progression
METRIC_COLORS = {
    "tuition": "#2D6CDF",  # UI Royal/Slate Blue
    "grad":    "#E67E22",  # Warm UI Amber/Orange
    "earning": "#138A72",  # Signature UI Teal/Green
    "admit":   "#D14949",  # Muted Crimson/Coral
    "sat":     "#7E57C2",  # Soft Amethyst Purple
}


def _unpack_metric_entry(entry):
    """
    Unpacks a metric entry from `metrics` dict.
    Supports:
    - Tuple/list: (normalized_score, raw_display_value)
    - Single float/int: (normalized_score, None)
    """
    if isinstance(entry, (tuple, list, np.ndarray)) and len(entry) >= 2:
        return float(entry[0]), entry[1]
    elif entry is not None:
        return float(entry), None
    return 0.0, None


def _format_metric_label(key, norm_val, raw_val):
    """
    Formats the raw metric value into a human-readable string for the bar segment.
    Falls back to 3-decimal normalized score if `raw_val` is not provided.
    """
    if raw_val is None:
        return f"{norm_val:.3f}"
    if isinstance(raw_val, str):
        return raw_val

    val = float(raw_val)
    if key in ("tuition", "earning"):
        return f"${val:,.0f}"
    elif key in ("grad", "admit"):
        return f"{round(val, 2):g}%"
    elif key == "sat":
        return f"{val:.0f}"
    return f"{val:g}"


# ---- Resolution-agnostic text metrics ------------------------------------
# All text measurement is done at a FIXED reference DPI in POINTS, then
# converted to data units using a physical (inch-based) ratio. Neither step
# depends on the figure's `dpi`, so the layout is identical at any resolution.
_REF_DPI = 144.0
_ref_renderer = None


def _get_ref_renderer():
    global _ref_renderer
    if _ref_renderer is None:
        from matplotlib.backends.backend_agg import RendererAgg
        _ref_renderer = RendererAgg(1, 1, _REF_DPI)
    return _ref_renderer


def _text_width_points(text, fontsize, bold=True):
    """Width of `text` in POINTS, measured at a fixed reference DPI.

    Points are physical (1/72 in) and the reference DPI is a constant, so this
    is independent of the figure's resolution.
    """
    if not text:
        return 0.0
    from matplotlib.font_manager import FontProperties
    prop = FontProperties(size=fontsize, weight=("bold" if bold else "normal"))
    px = _get_ref_renderer().get_text_width_height_descent(text, prop, False)[0]
    return px / _REF_DPI * 72.0


def _data_units_per_point(ax):
    """Data units per point along the x-axis, computed from physical inches
    (dpi-independent). For this layout the data spans the full figure width,
    and fig_width scales with total_width, so this reduces to a constant."""
    fig = ax.figure
    total = ax.get_xlim()[1] - ax.get_xlim()[0]
    fig_w_in = fig.get_figwidth()
    return total / (fig_w_in * 72.0)


def _text_fits_in_bar(ax, label_str, bar_width, fontsize=8.5, padding=0.55):
    """
    Determines whether `label_str` rendered in bold at `fontsize` points fits
    inside a bar segment of width `bar_width` (data units), leaving `padding`
    data units of margin on each side. Resolution-agnostic (see module notes).
    """
    if not label_str or bar_width <= 0:
        return False
    width = _text_width_points(label_str, fontsize, bold=True) * _data_units_per_point(ax)
    return width + 2.0 * padding <= bar_width


def _text_width_data_units(ax, text, fontsize=11.0):
    """
    Returns the rendered width of `text` (bold) in axes data units.
    Resolution-agnostic (see module notes). Used to size the Institution
    column to the widest school name so it never overlaps the Residency column.
    """
    if not text:
        return 0.0
    return max(0.0, _text_width_points(text, fontsize, bold=True) * _data_units_per_point(ax))


def _setup_bar_tooltips(fig, ax, bounds_ref, fpt=None):
    """
    Wires up a hover tooltip for the bar segments whose labels are too small
    to display. `bounds_ref` is a dict holding the *current* list of segment
    bounds under the key 'bounds'; each entry is a tuple
    `(x, y, width, height, tooltip_text)` in data coordinates.

    The scene is redrawn in place whenever the ranking changes, so the bounds
    list is refreshed in place on every draw (see `draw_scene`) while this
    single motion handler stays connected for the life of the figure.

    Implementation notes
    --------------------
    - Hit-testing uses the current data-space bounds (plain numeric checks).
    - Mouse moves that don't change the hovered segment are no-ops, so there
      is no per-pixel repaint cost while gliding inside one segment.
    - Only on enter/leave/segment-switch is a single coalesced full redraw
      requested via ``draw_idle`` (the standard matplotlib tooltip pattern),
      which renders the annotation through the normal, reliable draw path.
    """
    if "bounds" not in bounds_ref:
        bounds_ref["bounds"] = []
    if "tip" not in bounds_ref:
        bounds_ref["tip"] = None
    if "key" not in bounds_ref:
        bounds_ref["key"] = None
    if fpt is None:
        fpt = lambda v: v

    def on_motion(event):
        idx = -1
        if event.inaxes is ax and event.xdata is not None and event.x is not None:
            for i, (bx, by, bw, bh, _tip) in enumerate(bounds_ref["bounds"]):
                if bx <= event.xdata <= bx + bw and by <= event.ydata <= by + bh:
                    idx = i
                    break

        if idx == bounds_ref["key"]:
            return  # same segment (or still off); nothing to repaint

        if bounds_ref["tip"] is not None:
            try:
                bounds_ref["tip"].remove()
            except Exception:
                pass  # already gone (e.g., scene was redrawn)
            bounds_ref["tip"] = None

        if idx != -1:
            bounds_ref["tip"] = ax.annotate(
                bounds_ref["bounds"][idx][4],
                xy=(event.xdata, event.ydata),
                xytext=(fpt(12), fpt(14)),
                textcoords="offset points",
                fontsize=fpt(8.5),
                fontweight="bold",
                color="#FFFFFF",
                bbox=dict(
                    boxstyle=f"round,pad={fpt(0.4):.3f}",
                    facecolor="#2B343B",
                    edgecolor="none",
                    alpha=0.95,
                ),
                zorder=10,
            )

        # One coalesced full redraw; backends (e.g. TkAgg) handle the
        # buffer->screen transfer inside their own draw().
        fig.canvas.draw_idle()

        bounds_ref["key"] = idx

    fig.canvas.mpl_connect("motion_notify_event", on_motion)


def _draw_capsule(ax, x, y, width, height, color, zorder=3):
    """Draws a horizontal or vertical pill-shaped capsule with rounded ends."""
    if width <= 0 or height <= 0:
        return None
    radius = min(width, height) / 2.0
    patch = FancyBboxPatch(
        (x + radius, y + radius),
        max(1e-4, width - 2 * radius),
        max(1e-4, height - 2 * radius),
        boxstyle=f"round,pad={radius}",
        facecolor=color,
        edgecolor="none",
        mutation_aspect=1.0,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def _draw_rounded_rect(ax, x, y, width, height, radius, color, edgecolor="none", lw=0.0, zorder=3):
    """Draws a rounded rectangle with a specified corner radius."""
    if width <= 0 or height <= 0:
        return None
    radius = min(radius, width / 2.0, height / 2.0)
    patch = FancyBboxPatch(
        (x + radius, y + radius),
        max(1e-4, width - 2 * radius),
        max(1e-4, height - 2 * radius),
        boxstyle=f"round,pad={radius}",
        facecolor=color,
        edgecolor=edgecolor,
        linewidth=lw,
        mutation_aspect=1.0,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def _draw_stacked_metrics_bar(
    ax,
    x_start,
    yc,
    slot_width,
    bar_height,
    metrics_dict,
    max_sum,
    row_bg_color,
    scale_mode="relative",
    show_grid=True,
    label_fontsize=8.5,
):
    """
    Draws the 5-segment horizontal stacked bar inside a rounded UI container.
    Segment widths are proportional to `norm_val` (tuple index 0), while segment
    text labels display the formatted `raw_val` (tuple index 1).

    Any segment whose label does not fit (per `_text_fits_in_bar`) is drawn
    without text; a `(patch, tooltip_text)` pair is collected for it instead so
    the value can be revealed on hover.

    Returns
    -------
    list of (matplotlib.patches.Patch, str)
        Tooltip entries for bar segments whose labels were too small to show.
    """
    y0 = yc - bar_height / 2.0
    corner_r = 0.42

    unpacked = [
        (k, *_unpack_metric_entry(metrics_dict.get(k)))
        for k in METRIC_KEYS
    ]
    norm_vals = [u[1] for u in unpacked]
    row_sum = sum(norm_vals)

    # 1. Background track container
    _draw_rounded_rect(
        ax,
        x_start,
        y0,
        slot_width,
        bar_height,
        radius=corner_r,
        color="#E6ECEE",
        zorder=2.5,
    )

    if row_sum <= 0:
        return []

    # Determine effective total width of the active stacked bar
    if scale_mode == "normalized" or max_sum <= 0:
        active_total_w = slot_width
        scale_factor = slot_width / row_sum
    else:
        active_total_w = slot_width * min(1.0, row_sum / max_sum)
        scale_factor = slot_width / max_sum

    # 2. Clipping mask with rounded outer corners for the active stacked bar
    clip_patch = FancyBboxPatch(
        (x_start + corner_r, y0 + corner_r),
        max(1e-4, active_total_w - 2 * corner_r),
        max(1e-4, bar_height - 2 * corner_r),
        boxstyle=f"round,pad={corner_r}",
        facecolor="none",
        edgecolor="none",
        mutation_aspect=1.0,
        zorder=3,
    )
    ax.add_patch(clip_patch)

    # 3. Draw each of the 5 segments left-to-right
    curr_x = x_start
    tooltip_entries = []
    for idx, (key, norm_val, raw_val) in enumerate(unpacked):
        seg_w = norm_val * scale_factor
        if seg_w <= 0:
            continue

        seg_rect = Rectangle(
            (curr_x, y0),
            seg_w,
            bar_height,
            facecolor=METRIC_COLORS[key],
            edgecolor="none",
            zorder=3.2,
        )
        seg_rect.set_clip_path(clip_patch)
        ax.add_patch(seg_rect)

        # Crisp thin separator between adjacent segments
        if idx > 0:
            ax.plot(
                [curr_x, curr_x],
                [y0, y0 + bar_height],
                color=row_bg_color,
                linewidth=1.1,
                zorder=3.6,
            )

        # Format human-intelligible label (e.g., '$19,318', '27.71%', '$41,266', '57.95%', '938')
        label_str = _format_metric_label(key, norm_val, raw_val)

        if _text_fits_in_bar(ax, label_str, seg_w, fontsize=label_fontsize):
            ax.text(
                curr_x + seg_w / 2.0,
                yc,
                label_str,
                color="#FFFFFF",
                fontsize=label_fontsize,
                fontweight="bold",
                ha="center",
                va="center",
                zorder=4.2,
            )
        else:
            # Label too wide for this segment: show the value on hover instead
            tooltip_entries.append((seg_rect, f"{METRIC_LABELS[key]}: {label_str}"))

        curr_x += seg_w

    return tooltip_entries


def create_ranking_list_figure(
    items,
    row_pitch=4.2,
    row_height=3.6,
    scale_mode="relative",
    show_headers=True,
    dpi=200,
    save_path=None,
    layout="compact",
):
    """
    Creates a Matplotlib figure displaying a vertical list of N horizontal bar items,
    with column headers for Ranking, Institution, Residency, the 5-part Stacked Metrics Bar
    (Tuition, Grad Rate, Earnings, Admit Rate, SAT), Reach/Target/Safety, and Fit Score.

    Parameters
    ----------
    items : list of dict
        List of N dictionaries, each containing:
        - 'name': str (e.g., 'Purdue')
        - 'residency': str, optional (e.g., 'In-state')
        - 'metrics': dict mapping {'tuition', 'grad', 'earning', 'admit', 'sat'}
                     to `(normalized_float, raw_value_float)` tuples.
        - 'category': str (e.g., 'Target', 'Safety', 'Reach')
        - 'fit_score': int or float (0 to 100, e.g., 69)

        The displayed ranking number is derived from each item's position in
        `items` (1 for the first entry, 2 for the second, ...), so no explicit
        rank field is required.
        - 'active': bool, optional (default True; controls left accent bar & row tint)
    row_pitch : float
        Vertical distance between row origins in normalized units.
    row_height : float
        Height of each horizontal bar in normalized units.
    scale_mode : str
        'relative' (scales stacked bars against the max total score)
        or 'normalized' (stretches each row's stacked bar to 100% of the slot width).
    show_headers : bool
        Whether to render the column headers and metric legend above the first row.
    dpi : int
        Resolution of the output figure.
    save_path : str or None
        If provided, saves the figure to this path.
    layout : str
        How to present the content relative to the 16:4 (FIG_RATIO) frame:
        - 'frame': keep the content at its natural, undistorted proportions
          and force the *window* to 4:1; equal aspect centers the content
          (filling the frame's height) with side letterboxing. No squish/stretch.
        - 'compact': keep the column layout, compact the vertical spacing so
          the content itself fills 4:1 (rows get shorter).
        - 'widen': keep the natural row sizes and stretch the horizontal axis
          (more column width / spacing) until the content is 4:1.
        - 'natural': no aspect forcing; the figure matches the content's own
          aspect ratio.

        Default is 'compact'.

    Returns
    -------
    fig, ax : tuple
        The Matplotlib Figure and Axes objects.
    """
    n = len(items)
    if n == 0:
        raise ValueError("The `items` list must contain at least one element.")

    # Interactive state: current display order + active sort. `order` holds the
    # original item indices in top-to-bottom display order. `clickable` maps a
    # header Text's id() to the sort key it triggers (rebuilt each draw).
    # Fixed rank tied to fit score (independent of the current sort). Rank 1 =
    # highest fit score; ties keep their original input order (stable sort).
    # The left rank badge always shows this fit-based rank, even when the list
    # is re-sorted by another metric.
    fit_order = sorted(range(len(items)), key=lambda i: -float(items[i].get("fit_score", 0)))
    fit_rank = {orig: rank for rank, orig in enumerate(fit_order, start=1)}

    state = {
        "order": list(fit_order),   # default view: sorted by fit score, highest first
        "sort_key": "fit_score",
        "sort_dir": "desc",
        "clickable": {},
    }
    tip_holder = {"bounds": []}

    header_extra = 2.4 if show_headers else 0.0
    base_total_width = 100.0
    base_fig_width = 14.8
    FIG_RATIO = 16.0 / 4.0  # requested 16:4 figure window aspect (width:height)
    total_width = base_total_width
    total_height = (n - 1) * row_pitch + row_height + header_extra

    fig_width = base_fig_width
    # Fixed 16:4 window; equal aspect keeps the content undistorted (centered
    # with side padding if the row list's own aspect is narrower than 16:4).
    fig_height = fig_width / FIG_RATIO

    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")

    ax.set_xlim(0, total_width)
    ax.set_ylim(-0.5, total_height + 0.5)
    ax.set_aspect("equal")
    ax.axis("off")

    # Core UI Palette
    TEAL = "#138A72"
    BG_ACTIVE = "#F1F7F6"
    BG_INACTIVE = "#F8FAFC"
    TEXT_PRIMARY = "#2B343B"
    TEXT_MUTED = "#6B7280"
    HEADER_COLOR = "#4B5563"
    TRACK_BG = "#E9EEF2"

    CATEGORY_STYLES = {
        "Target": {"bg": "#E5ECFA", "fg": "#356AE6"},
        "Safety": {"bg": "#E3F5EC", "fg": "#138A72"},
        "Reach":  {"bg": "#FDECEB", "fg": "#D9383A"},
    }

    # Horizontal anchor coordinates (normalized width). The Institution column
    # is sized to the widest school name so it never overlaps Residency; every
    # column to its right is shifted by the resulting `col_delta`.
    X_LEFT_BAR = 0.8
    W_ACCENT = 0.55

    X_RANK_CENTER = 6.0
    X_NAME = 10.7
    COL_GAP = 3.2
    X_RESIDENCY_MIN = 23.0
    X_STACK_MIN = 29.7

    # Size the left columns to their widest text (data units) so neither the
    # Institution name nor the Residency label can overlap its neighbour. The
    # positions are floored at the original design values so short labels keep
    # their generous default spacing. fig_width scales with total_width, so the
    # data-units-per-point ratio (and thus these measurements) stays constant.
    #
    # TODO(ranking-list): this dynamic column auto-sizing is NOT reliably
    #    preventing the Institution / Residency overlap when rendered -- the
    #    measured text widths and the final drawn layout don't always line up,
    #    so the name can still bleed into the Residency column. Parking this
    #    for now; revisit before final polish.
    NAME_FONT = 11.0
    RESIDENCY_FONT = 9.2
    max_name_width = max(
        (_text_width_data_units(ax, str(item.get("name", "")), NAME_FONT) for item in items),
        default=0.0,
    )
    max_residency_width = max(
        (_text_width_data_units(ax, str(item.get("residency", "")), RESIDENCY_FONT) for item in items),
        default=0.0,
    )
    X_RESIDENCY = max(X_RESIDENCY_MIN, X_NAME + max_name_width + COL_GAP)
    X_STACK_START = max(X_STACK_MIN, X_RESIDENCY + max_residency_width + COL_GAP)
    col_delta = max(0.0, X_STACK_START - X_STACK_MIN)

    total_width = base_total_width + col_delta

    # Horizontal Stacked Bar slot
    W_STACK_SLOT = 44.2
    H_STACK_BAR = 2.15

    X_BADGE_CENTER = 76.6 + col_delta
    X_GAUGE_TEXT = 84.4 + col_delta
    X_TRACK_START = 85.6 + col_delta
    W_TRACK = 12.2
    W_BAR = total_width - 2.0 * X_LEFT_BAR

    # --- Fit the layout to a 16:4 (FIG_RATIO) frame -------------------------
    # The row list's natural aspect is ~2.6:1 for 10 rows. Two ways to reach
    # 4:1 while keeping an undistorted, equal-aspect render:
    #   'compact': shrink the vertical layout so content height reaches 4:1.
    #   'widen'  : keep natural row sizes and stretch the horizontal axis so
    #              content width reaches 4:1 (more column width/spacing).
    #   'natural': leave the content at its own aspect (no 4:1 forcing).
    ymargin = 0.5
    natural_total_height = (n - 1) * row_pitch + row_height + header_extra
    h_scale = 1.0
    v_scale = 1.0
    draw_frame = False

    if layout == "widen":
        # Widen so the full data range (content + top/bottom margins) is 4:1.
        target_total_width = (natural_total_height + 2.0 * ymargin) * FIG_RATIO
        h_scale = max(1.0, target_total_width / total_width)
        X_LEFT_BAR *= h_scale
        W_ACCENT *= h_scale
        X_RANK_CENTER *= h_scale
        X_NAME *= h_scale
        X_RESIDENCY *= h_scale
        X_STACK_START *= h_scale
        X_BADGE_CENTER *= h_scale
        X_GAUGE_TEXT *= h_scale
        X_TRACK_START *= h_scale
        W_STACK_SLOT *= h_scale
        W_TRACK *= h_scale
        total_width = total_width * h_scale
        W_BAR = total_width - 2.0 * X_LEFT_BAR
        total_height = natural_total_height
    elif layout == "compact":
        # Content + top/bottom margins should equal total_width/FIG_RATIO so the
        # whole data range is exactly 4:1.
        target_total_height = total_width / FIG_RATIO - 2.0 * ymargin
        v_scale = target_total_height / natural_total_height
        row_pitch *= v_scale
        row_height *= v_scale
        header_extra *= v_scale
        H_STACK_BAR *= v_scale
        total_height = (n - 1) * row_pitch + row_height + header_extra
    elif layout == "frame":
        # LOCK the frame at FIG_RATIO: make the *data range* exactly FIG_RATIO
        # so equal aspect keeps the axes box 4:1 at ANY window size (it resizes
        # to fit the window and stays 4:1).
        #
        # Filling a wide 4:1 frame well: keep the left columns (rank / name /
        # residency) and the right block (category / fit) at their natural size
        # and height (no squish), anchor the right block to the frame's right
        # edge, and let the stacked bar -- the centerpiece -- absorb the extra
        # width so it fills the middle. A thin border marks the locked frame.
        total_height = natural_total_height
        data_W = (natural_total_height + 2.0 * ymargin) * FIG_RATIO
        total_width = data_W
        # Comfortable side margin as a FRACTION of the frame width. Because the
        # frame can be far wider than the 100-unit base layout, a fixed data-unit
        # margin would be only ~2% of the frame (a sliver that a display edge
        # clips at fullscreen). A constant fraction keeps a constant physical
        # margin at any window/resolution size.
        side_margin = total_width * 0.045
        # The left columns sit at base (100-unit) positions, so in this much
        # wider frame they'd be only ~2% from the left edge. Shift the whole
        # left block right so its leftmost element (the "Ranking" header) starts
        # at side_margin; the stacked bar -- the centerpiece -- absorbs the
        # difference so it still fills the middle.
        hdr_half = _text_width_data_units(ax, "Ranking", 8.5) / 2.0
        base_leftmost = X_RANK_CENTER - hdr_half
        shift = max(0.0, side_margin - base_leftmost)
        X_RANK_CENTER += shift
        X_NAME += shift
        X_RESIDENCY += shift
        X_STACK_START += shift
        # Right block (category + fit) anchored to the frame's right edge.
        frame_right = total_width - side_margin
        X_TRACK_START = frame_right - W_TRACK
        X_GAUGE_TEXT = X_TRACK_START - 2.4
        X_BADGE_CENTER = X_GAUGE_TEXT - 8.5
        bar_right = X_BADGE_CENTER - 3.5
        W_STACK_SLOT = max(10.0, bar_right - X_STACK_START)
        X_LEFT_BAR = side_margin
        W_BAR = total_width - 2.0 * side_margin
        draw_frame = True
    else:  # "natural"
        total_height = natural_total_height

    # Size the figure. In frame/widen/compact the *window* is FIG_RATIO; for
    # frame the content is centered inside it, while widen/compact fill it.
    # In natural mode the window matches the content's own aspect.
    fig_width = base_fig_width * (total_width / base_total_width)
    if layout in ("widen", "compact", "frame"):
        fig_height = fig_width / FIG_RATIO
    else:
        fig_height = fig_width * (total_height + 2.0 * ymargin) / total_width
    fig.set_size_inches(fig_width, fig_height)
    ax.set_xlim(0, total_width)
    ax.set_ylim(-ymargin, total_height + ymargin)

    # Compute maximum normalized sum across rows for consistent scaling in 'relative' mode
    row_sums = []
    for item in items:
        m = item.get("metrics", {})
        row_sums.append(sum(_unpack_metric_entry(m.get(k))[0] for k in METRIC_KEYS))
    raw_max = max(row_sums) if row_sums else 1.0
    max_sum = max(raw_max * 1.04, np.ceil(raw_max * 4.0) / 4.0) if raw_max > 0 else 1.0

    # ---- Click-to-sort ----------------------------------------------------
    # The header labels for the 5 metrics + Fit Score are clickable. Clicking
    # one re-ranks the list by that feature; clicking the same label again
    # toggles between highest-first and lowest-first; clicking a different
    # label resets to highest-first. `state` tracks the current order/sort.

    def _sort_value(idx, key):
        if key == "fit_score":
            return float(items[idx].get("fit_score", 0))
        return _unpack_metric_entry(items[idx].get("metrics", {}).get(key))[0]

    # Font sizes are defined relative to the design canvas width so the layout
    # looks identical (same relative density) at ANY window/resolution size.
    # When the window is resized, draw_scene() re-runs and fpt() rescales fonts
    # to the current width, keeping text ~ the same fraction of each column.
    DESIGN_W = max(fig_width, 1e-6)

    def fpt(base):
        return base * (ax.figure.get_figwidth() / DESIGN_W)

    def draw_scene():
        ax.clear()
        ax.set_facecolor("#FFFFFF")
        ax.set_xlim(0, total_width)
        ax.set_ylim(-0.5, total_height + 0.5)
        ax.set_aspect("equal")
        ax.axis("off")

        tip_holder["bounds"] = []
        tip_holder["tip"] = None  # drop any stale hover annotation on redraw
        tip_holder["key"] = None
        clickable = {}

        # ---- Header row (re-rendered on every redraw so it stays in sync) ----
        if show_headers:
            header_y = (n - 1) * row_pitch + row_height + 1.15 * v_scale
            divider_y = (n - 1) * row_pitch + row_height + 0.35 * v_scale

            # Subtle bottom border under the header row
            ax.plot(
                [X_LEFT_BAR, X_LEFT_BAR + W_BAR],
                [divider_y, divider_y],
                color="#E5E7EB",
                linewidth=0.9,
                zorder=2,
            )

            # Left column headers: Ranking, Institution, Residency
            ax.text(X_RANK_CENTER, header_y, "Ranking", color=HEADER_COLOR, fontsize=fpt(8.5),
                    fontweight="bold", ha="center", va="center", zorder=3)
            ax.text(X_NAME, header_y, "Institution", color=HEADER_COLOR, fontsize=fpt(8.5),
                    fontweight="bold", ha="left", va="center", zorder=3)
            ax.text(X_RESIDENCY, header_y, "Residency", color=HEADER_COLOR, fontsize=fpt(8.5),
                    fontweight="bold", ha="left", va="center", zorder=3)

            # Stacked-bar metric legend: Tuition, Grad Rate, Earnings, Admit Rate, SAT.
            # Each (dot + label) item is centered within its equal share of the bar's
            # width, so the legend stays spread out and readable at any frame width.
            # Each label is a clickable sort target.
            # --- Sort affordance (clean / modern) --------------------------------
            # Every sortable column carries a faint up/down glyph (clickable hint).
            # The active column instead shows a solid directional arrow in an accent
            # color:  ↓ highest-first (descending),  ↑ lowest-first (ascending).
            # When no column is active, all show the faint glyph = original order.
            SORT_ACTIVE = "#0D9488"   # accent for the active sort column
            SORT_HINT = "#B4BCC8"     # faint marker on sortable, inactive columns
            def _sort_marker(key):
                if state["sort_key"] == key:
                    return ("\u2193" if state["sort_dir"] == "desc" else "\u2191"), True
                return "\u2195", False   # faint up-down = sortable, currently unsorted

            cell_w = W_STACK_SLOT / len(METRIC_KEYS)
            dot_w, dot_h = 1.15 * h_scale, 0.75 * v_scale
            dot_gap = 0.4 * h_scale
            mk_gap = 0.55 * h_scale
            for i, key in enumerate(METRIC_KEYS):
                cell_center = X_STACK_START + cell_w * (i + 0.5)
                marker, active = _sort_marker(key)
                label_w = _text_width_points(METRIC_LABELS[key], fpt(8.5), True) * _data_units_per_point(ax)
                marker_w = _text_width_points(marker, fpt(8.0), True) * _data_units_per_point(ax)
                item_w = dot_w + dot_gap + label_w + mk_gap + marker_w
                start_x = cell_center - item_w / 2.0
                _draw_rounded_rect(
                    ax, start_x, header_y - dot_h / 2.0, dot_w, dot_h,
                    radius=0.25, color=METRIC_COLORS[key], zorder=3,
                )
                label_color = SORT_ACTIVE if active else HEADER_COLOR
                marker_color = SORT_ACTIVE if active else SORT_HINT
                label_x = start_x + dot_w + dot_gap
                lbl = ax.text(label_x, header_y, METRIC_LABELS[key], color=label_color,
                              fontsize=fpt(8.5), fontweight="bold", ha="left", va="center", zorder=3)
                lbl.set_picker(True)
                clickable[id(lbl)] = key
                mk = ax.text(label_x + label_w + mk_gap, header_y, marker, color=marker_color,
                             fontsize=fpt(8.0), ha="left", va="center", zorder=3)
                mk.set_picker(True)
                clickable[id(mk)] = key

            # Right column headers: Feasibility and Fit Score
            ax.text(X_BADGE_CENTER, header_y, "Feasibility",
                    color=HEADER_COLOR, fontsize=fpt(8.2), fontweight="bold",
                    ha="center", va="center", zorder=3)
            fit_marker, fit_active = _sort_marker("fit_score")
            fit_center_x = (X_GAUGE_TEXT - 1.2 * h_scale + X_TRACK_START + W_TRACK) / 2.0
            fit_label_w = _text_width_points("Fit Score", fpt(8.5), True) * _data_units_per_point(ax)
            fit_marker_w = _text_width_points(fit_marker, fpt(8.0), True) * _data_units_per_point(ax)
            fit_group_w = fit_label_w + mk_gap + fit_marker_w
            fit_x0 = fit_center_x - fit_group_w / 2.0
            fit_color = SORT_ACTIVE if fit_active else HEADER_COLOR
            fit_marker_color = SORT_ACTIVE if fit_active else SORT_HINT
            fit_label = ax.text(fit_x0, header_y, "Fit Score", color=fit_color,
                                fontsize=fpt(8.5), fontweight="bold", ha="left", va="center", zorder=3)
            fit_label.set_picker(True)
            clickable[id(fit_label)] = "fit_score"
            fit_mk = ax.text(fit_x0 + fit_label_w + mk_gap, header_y, fit_marker,
                             color=fit_marker_color, fontsize=fpt(8.0), ha="left", va="center", zorder=3)
            fit_mk.set_picker(True)
            clickable[id(fit_mk)] = "fit_score"

        state["clickable"] = clickable

        # ---- Rows, drawn in the current display order ----
        for display_idx, orig_idx in enumerate(state["order"]):
            item = items[orig_idx]
            y0 = (n - 1 - display_idx) * row_pitch
            yc = y0 + row_height / 2.0

            is_active = item.get("active", True)
            row_bg = BG_ACTIVE if is_active else BG_INACTIVE

            # 1. Row background container
            ax.add_patch(
                Rectangle((X_LEFT_BAR, y0), W_BAR, row_height,
                          facecolor=row_bg, edgecolor="none", zorder=1)
            )

            # 2. Far-left vertical teal status bar
            if is_active:
                ax.add_patch(
                    Rectangle((X_LEFT_BAR, y0), W_ACCENT, row_height,
                              facecolor=TEAL, edgecolor="none", zorder=2)
                )

            # 3. Rank badge -- fixed rank by fit score (constant, not the
            #    current display position, so it stays stable across re-sorts).
            rank_w, rank_h = 1.65 * h_scale, 2.25 * v_scale
            _draw_capsule(ax, X_RANK_CENTER - rank_w / 2.0, yc - rank_h / 2.0,
                          rank_w, rank_h, color=TEAL, zorder=3)
            ax.text(X_RANK_CENTER, yc, str(fit_rank[orig_idx]), color="#FFFFFF",
                    fontsize=fpt(9.5), fontweight="bold", ha="center", va="center", zorder=4)

            # 4. Primary Name Label & Residency descriptor
            ax.text(X_NAME, yc, str(item.get("name", "")), color=TEXT_PRIMARY,
                    fontsize=fpt(11.0), fontweight="bold", ha="left", va="center", zorder=3)
            residency = item.get("residency", "")
            if residency:
                ax.text(X_RESIDENCY, yc, str(residency), color=TEXT_MUTED,
                        fontsize=fpt(9.2), ha="left", va="center", zorder=3)

            # 5. Embedded 5-Segment Horizontal Stacked Bar
            #    Segments whose labels don't fit collect a hover-tooltip bound here.
            metrics_dict = item.get("metrics", {})
            entries = _draw_stacked_metrics_bar(
                ax=ax, x_start=X_STACK_START, yc=yc, slot_width=W_STACK_SLOT,
                bar_height=H_STACK_BAR, metrics_dict=metrics_dict, max_sum=max_sum,
                row_bg_color=row_bg, scale_mode=scale_mode, show_grid=True,
                label_fontsize=fpt(8.5),
            ) or []
            for patch, tip_text in entries:
                tip_holder["bounds"].append(
                    (patch.get_x(), patch.get_y(),
                     patch.get_width(), patch.get_height(), tip_text)
                )

            # 6. Classification Pill Badge (e.g., 'Target', 'Reach', 'Safety')
            cat = str(item.get("category", "Target"))
            style = CATEGORY_STYLES.get(cat, CATEGORY_STYLES["Target"])
            pill_w, pill_h = 4.6 * h_scale, 1.95 * v_scale
            _draw_rounded_rect(
                ax, X_BADGE_CENTER - pill_w / 2.0, yc - pill_h / 2.0, pill_w, pill_h,
                radius=0.45, color=style["bg"], zorder=3,
            )
            ax.text(X_BADGE_CENTER, yc, cat, color=style["fg"], fontsize=fpt(9.0),
                    fontweight="bold", ha="center", va="center", zorder=4)

            # 7. Fit Score Value & Horizontal Progress Bar
            fit_score_val = float(item.get("fit_score", 0))
            fit_score_clamped = max(0.0, min(100.0, fit_score_val))
            ax.text(X_GAUGE_TEXT, yc, f"{int(round(fit_score_val))}", color=TEXT_PRIMARY,
                    fontsize=fpt(10.5), fontweight="bold", ha="right", va="center", zorder=3)
            track_h = 0.72 * v_scale
            _draw_capsule(ax, X_TRACK_START, yc - track_h / 2.0, W_TRACK, track_h,
                          color=TRACK_BG, zorder=3)
            fill_w = W_TRACK * (fit_score_clamped / 100.0)
            if fill_w > 0:
                _draw_capsule(ax, X_TRACK_START, yc - track_h / 2.0, max(track_h, fill_w),
                              track_h, color=TEAL, zorder=4)

        # Visible frame border (locked 4:1 with the data range). Drawn last so
        # it sits on top and always outlines the 4:1 panel at any window size.
        if draw_frame:
            ax.add_patch(
                Rectangle(
                    (X_LEFT_BAR, 0.0), W_BAR, total_height,
                    facecolor="none", edgecolor="#C2CCD4", linewidth=1.6, zorder=6,
                )
            )

        fig.canvas.draw_idle()

    def on_click(event):
        # `event` is a PickEvent (fired by matplotlib's picker when a pickable
        # artist -- one of the header labels -- is clicked). `event.artist` is
        # the picked Text; `event.mouseevent` carries the originating click.
        artist = event.artist
        if artist is None or not isinstance(artist, Text):
            return
        mouse = getattr(event, "mouseevent", None)
        if mouse is not None and getattr(mouse, "button", 1) not in (1, None):
            return  # ignore right/middle clicks
        key = state["clickable"].get(id(artist))
        if key is None:
            return

        # Re-clicking the same title toggles direction; a new title starts desc.
        if state["sort_key"] == key:
            state["sort_dir"] = "asc" if state["sort_dir"] == "desc" else "desc"
        else:
            state["sort_key"] = key
            state["sort_dir"] = "desc"

        sign = -1.0 if state["sort_dir"] == "desc" else 1.0
        state["order"] = sorted(range(n), key=lambda i: sign * _sort_value(i, key))
        draw_scene()

    # Wire the (single, persistent) hover-tooltip + click handlers, then render.
    plt.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)
    _setup_bar_tooltips(fig, ax, tip_holder, fpt)
    # Header labels are pickable; matplotlib reports a clicked pickable artist
    # via the `pick_event` signal (the button-press event itself does not
    # carry `artist` in modern matplotlib), so we listen for pick events.
    fig.canvas.mpl_connect("pick_event", on_click)

    # Re-render on window resize so fonts rescale to the new canvas width and
    # the layout keeps the same relative density at any screen/resolution size.
    def _on_resize(event):
        draw_scene()

    fig.canvas.mpl_connect("resize_event", _on_resize)

    draw_scene()

    if save_path:
        # Save the full figure (no tight-crop) so the output file keeps the
        # exact 16:4 aspect; the content already fills the axes edge-to-edge.
        fig.savefig(save_path, dpi=dpi)

    return fig, ax
