"""Penny, the simulator's friendly piggy-bank mascot.

Penny is drawn with matplotlib's object API (no pyplot, no image files) and
rendered to transparent PNG bytes.  The result is cached and embedded directly
in the GUI and in exported HTML reports, so packaged builds and shared reports
stay self-contained.
"""

from functools import lru_cache
import base64
import io

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Arc, Circle, Ellipse, FancyBboxPatch, Polygon

from src import theme

PINK = '#F7B2A9'
PINK_DARK = '#D9857A'
PINK_LIGHT = '#F9C4BC'
SNOUT = '#F49C93'
NOSTRIL = '#B96A5E'


def _draw_penny(ax, size: int) -> None:
    """Draw Penny in a 2.6 x 2.6 coordinate box."""
    # Curly tail, tucked behind the body.
    t = np.linspace(0, 2.6 * np.pi, 140)
    taper = 1 - t / (3.4 * np.pi)
    ax.plot(2.08 + 0.13 * np.cos(t) * taper,
            1.00 + 0.13 * np.sin(t) * taper,
            color=PINK_DARK, linewidth=2.0, solid_capstyle='round', zorder=1)

    # Little trotters.
    for x in (0.72, 1.06, 1.54, 1.88):
        ax.add_patch(FancyBboxPatch(
            (x, 0.33), 0.22, 0.30,
            boxstyle='round,pad=0,rounding_size=0.09',
            facecolor=PINK, edgecolor=PINK_DARK, linewidth=1.2, zorder=2,
        ))

    # Ears.
    for points in (
        [(0.66, 1.68), (0.80, 2.14), (1.14, 1.82)],
        [(1.46, 1.82), (1.80, 2.14), (1.94, 1.68)],
    ):
        ax.add_patch(Polygon(points, closed=True, facecolor=PINK,
                             edgecolor=PINK_DARK, linewidth=1.4, zorder=2))
    for points in (
        [(0.80, 1.76), (0.86, 2.00), (1.04, 1.82)],
        [(1.56, 1.82), (1.74, 2.00), (1.80, 1.76)],
    ):
        ax.add_patch(Polygon(points, closed=True, facecolor=theme.CORAL_SOFT,
                             edgecolor='none', zorder=3))

    # Body.
    ax.add_patch(Ellipse((1.30, 1.12), 1.66, 1.18, facecolor=PINK,
                         edgecolor=PINK_DARK, linewidth=1.8, zorder=3))
    ax.add_patch(Ellipse((1.02, 1.45), 0.52, 0.30, facecolor=PINK_LIGHT,
                         edgecolor='none', alpha=0.75, zorder=4))

    # Coin slot.
    ax.add_patch(FancyBboxPatch(
        (1.02, 1.64), 0.56, 0.10,
        boxstyle='round,pad=0,rounding_size=0.05',
        facecolor=theme.NAVY, edgecolor='none', zorder=5,
    ))

    # Snout and nostrils.
    ax.add_patch(Ellipse((1.30, 1.04), 0.60, 0.36, facecolor=SNOUT,
                         edgecolor=PINK_DARK, linewidth=1.4, zorder=6))
    for x in (1.18, 1.42):
        ax.add_patch(Ellipse((x, 1.07), 0.07, 0.11, facecolor=NOSTRIL,
                             edgecolor='none', zorder=7))

    # Smile and blush.
    ax.add_patch(Arc((1.30, 0.94), 0.32, 0.20, theta1=200, theta2=340,
                     color=NOSTRIL, linewidth=1.6, zorder=7))
    for x in (0.66, 1.94):
        ax.add_patch(Ellipse((x, 1.14), 0.20, 0.11,
                             facecolor=theme.CORAL_SOFT, edgecolor='none',
                             alpha=0.95, zorder=6))

    # Eyes and round glasses.
    for x in (1.00, 1.60):
        ax.add_patch(Circle((x, 1.32), 0.11, facecolor='white',
                            edgecolor='none', zorder=6))
        ax.add_patch(Circle((x + 0.02, 1.31), 0.055, facecolor=theme.NAVY,
                            edgecolor='none', zorder=7))
        ax.add_patch(Circle((x - 0.005, 1.335), 0.018, facecolor='white',
                            edgecolor='none', zorder=8))
        ax.add_patch(Circle((x, 1.32), 0.16, facecolor='none',
                            edgecolor=theme.NAVY, linewidth=1.8, zorder=8))
    ax.plot([1.16, 1.44], [1.33, 1.33], color=theme.NAVY, linewidth=1.8,
            zorder=8)
    ax.plot([1.76, 1.90], [1.33, 1.40], color=theme.NAVY, linewidth=1.5,
            zorder=8)

    # A coin worth saving for.
    ax.add_patch(Circle((2.23, 1.99), 0.24, facecolor=theme.GOLD,
                        edgecolor='#C99A2E', linewidth=1.4, zorder=9))
    ax.text(2.23, 1.99, '$', ha='center', va='center',
            fontsize=max(7, size * 0.065), fontweight='bold',
            color=theme.NAVY, zorder=10)
    for dx, dy in ((-0.36, 0.18), (0.34, 0.22), (0.30, -0.28)):
        ax.plot([2.23 + dx, 2.23 + dx * 1.13],
                [1.99 + dy, 1.99 + dy * 1.13],
                color='#C99A2E', linewidth=1.4, solid_capstyle='round',
                zorder=9)

    # A tiny heart above Penny's ear.
    ax.add_patch(Circle((0.49, 2.06), 0.075, facecolor=theme.CORAL,
                        edgecolor='none', zorder=9))
    ax.add_patch(Circle((0.60, 2.06), 0.075, facecolor=theme.CORAL,
                        edgecolor='none', zorder=9))
    ax.add_patch(Polygon([(0.415, 2.04), (0.675, 2.04), (0.545, 1.91)],
                         closed=True, facecolor=theme.CORAL,
                         edgecolor='none', zorder=9))


@lru_cache(maxsize=8)
def mascot_png(size: int = 220) -> bytes:
    """Return Penny as transparent PNG bytes at roughly ``size`` pixels."""
    size = max(64, int(size))
    dpi = 100
    figure = Figure(figsize=(size / dpi, size / dpi), dpi=dpi)
    FigureCanvasAgg(figure)
    ax = figure.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 2.6)
    ax.set_ylim(0, 2.6)
    ax.set_aspect('equal')
    ax.axis('off')

    _draw_penny(ax, size)

    buffer = io.BytesIO()
    figure.savefig(buffer, format='png', transparent=True, dpi=dpi)
    return buffer.getvalue()


def mascot_data_uri(size: int = 220) -> str:
    """Return Penny as a data URI suitable for HTML reports."""
    encoded = base64.b64encode(mascot_png(size)).decode('ascii')
    return f'data:image/png;base64,{encoded}'
