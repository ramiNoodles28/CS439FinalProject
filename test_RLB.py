import numpy as np
import matplotlib.pyplot as plt
from ranking_list_bars import create_ranking_list_figure
import ranking_core

items = ranking_core.generate_ranking_list([2104, 588, 511, 597, 896, 2092, 933, 626, 1010, 1890], "IN")

fig, ax = create_ranking_list_figure(
    items,
    scale_mode="relative",
    show_headers=True,
)
plt.show()