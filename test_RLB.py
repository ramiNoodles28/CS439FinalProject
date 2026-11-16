import numpy as np
import matplotlib.pyplot as plt
from ranking_list_bars import create_ranking_list_figure
import ranking_core

items = ranking_core.generate_ranking_list([867, 192, 152, 197, 338, 861, 356, 215, 395, 773], "IN")

fig, ax = create_ranking_list_figure(
    items,
    scale_mode="relative",
    show_headers=True,
)
plt.show()