"""Penny, the simulator's friendly pig-farmer mascot.

Penny is drawn with matplotlib's object API (no pyplot, no image files) and
rendered to transparent PNG bytes. The result is cached and embedded directly
in the GUI and in exported HTML reports, so packaged builds and shared reports
stay self-contained.

The character is an anthropomorphic pig in faded bib overalls: cream shirt,
rolled sleeves, patched knees and cloven hooves. Her pig head keeps the round
glasses, snout and coin slot used throughout the app.
"""

from functools import lru_cache
import base64
import io

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Arc, Circle, Ellipse, FancyBboxPatch, PathPatch
from matplotlib.path import Path

from src import theme

PINK = '#F6B3AA'
PINK_DARK = '#C9786D'
PINK_LIGHT = '#FBD3CB'
SNOUT = '#F19B91'
NOSTRIL = '#A95B52'
COIN_EDGE = '#C9972B'

OVERALLS = '#52737A'
OVERALLS_DARK = '#38545B'
OVERALLS_EDGE = '#2E464C'
SHIRT = '#F8E8C9'
SHIRT_DARK = '#DDC49C'
HOOF = '#8A5B51'
HOOF_DARK = '#5A3A35'
PATCH = '#D8B37E'
STITCH = '#F0D28F'


def _ear_path(points):
    """Build a soft, curved ear from a compact points list."""
    return Path(points, [
        Path.MOVETO,
        Path.CURVE4, Path.CURVE4, Path.CURVE4,
        Path.CURVE4, Path.CURVE4, Path.CURVE4,
        Path.CLOSEPOLY,
    ])


def _draw_hoof(ax, cx, top, width, height, zorder):
    """Draw a cloven hoof as two rounded lobes over a dark base."""
    bottom = top - height
    ax.add_patch(FancyBboxPatch(
        (cx - width / 2, bottom), width, height,
        boxstyle='round,pad=0,rounding_size=0.06',
        facecolor=HOOF_DARK, edgecolor=HOOF_DARK, linewidth=1.0,
        zorder=zorder,
    ))
    gap = 0.012
    lobe_width = (width - gap) / 2
    for x in (cx - width / 2 + 0.005, cx + gap / 2):
        ax.add_patch(FancyBboxPatch(
            (x, bottom + 0.006), lobe_width, height - 0.012,
            boxstyle='round,pad=0,rounding_size=0.052',
            facecolor=HOOF, edgecolor='none', zorder=zorder + 0.1,
        ))
    # A small satin highlight makes the hoof read at menu size.
    ax.add_patch(Ellipse(
        (cx - width * 0.23, bottom + height * 0.58),
        width * 0.09, height * 0.20,
        facecolor='#B27B6C', edgecolor='none', alpha=0.55,
        zorder=zorder + 0.2,
    ))


def _draw_penny(ax, size: int) -> None:
    """Draw Penny in a 2.6 x 2.6 coordinate box."""
    # Soft ground shadow keeps the character from floating.
    ax.add_patch(Ellipse(
        (1.30, 0.16), 1.04, 0.12,
        facecolor='#000000', edgecolor='none', alpha=0.07, zorder=0,
    ))

    # Curly tail peeking out beside the overalls.
    tail_t = np.linspace(0, 2.5 * np.pi, 160)
    tail_r = 0.085 * (1 - 0.18 * tail_t / tail_t.max())
    ax.plot(1.76 + tail_r * np.cos(tail_t),
            0.90 + tail_r * np.sin(tail_t),
            color=PINK_DARK, linewidth=1.6, solid_capstyle='round',
            zorder=1)

    # Legs and feet. The trouser legs run up under the overalls; the hooves
    # sit below folded cuffs so no leg joint is left floating.
    for cx in (1.04, 1.56):
        _draw_hoof(ax, cx, 0.40, 0.30, 0.24, zorder=2)
        ax.add_patch(FancyBboxPatch(
            (cx - 0.15, 0.43), 0.30, 0.52,
            boxstyle='round,pad=0,rounding_size=0.055',
            facecolor=OVERALLS, edgecolor=OVERALLS_EDGE, linewidth=1.25,
            zorder=3,
        ))
        # Folded overall cuff.
        ax.add_patch(FancyBboxPatch(
            (cx - 0.18, 0.37), 0.36, 0.11,
            boxstyle='round,pad=0,rounding_size=0.035',
            facecolor=OVERALLS_DARK, edgecolor=OVERALLS_EDGE, linewidth=1.1,
            zorder=4,
        ))
        ax.plot([cx - 0.13, cx + 0.13], [0.415, 0.415],
                color=OVERALLS_EDGE, linewidth=0.7, alpha=0.8, zorder=5)

    # A worn knee patch on the farmer's left leg.
    ax.add_patch(FancyBboxPatch(
        (0.96, 0.59), 0.17, 0.14,
        boxstyle='round,pad=0,rounding_size=0.025',
        facecolor=PATCH, edgecolor=STITCH, linewidth=0.9,
        linestyle=(0, (2, 1)), zorder=4,
    ))

    # Shirt sleeves and hoof hands.
    for cx, angle in ((0.79, -18), (1.81, 18)):
        ax.add_patch(Ellipse(
            (cx, 1.10), 0.23, 0.56, angle=angle,
            facecolor=SHIRT, edgecolor=SHIRT_DARK, linewidth=1.2,
            zorder=3,
        ))
    _draw_hoof(ax, 0.68, 0.88, 0.20, 0.19, zorder=3.5)
    _draw_hoof(ax, 1.92, 0.88, 0.20, 0.19, zorder=3.5)
    for cx, angle in ((0.69, -18), (1.91, 18)):
        ax.add_patch(Ellipse(
            (cx, 0.86), 0.23, 0.09, angle=angle,
            facecolor=SHIRT_DARK, edgecolor=SHIRT_DARK, linewidth=0.9,
            zorder=4,
        ))

    # Cream shirt, with the overalls layered over it.
    ax.add_patch(FancyBboxPatch(
        (0.86, 0.77), 0.88, 0.66,
        boxstyle='round,pad=0,rounding_size=0.14',
        facecolor=SHIRT, edgecolor=SHIRT_DARK, linewidth=1.2,
        zorder=4,
    ))
    ax.add_patch(FancyBboxPatch(
        (0.84, 0.73), 0.92, 0.44,
        boxstyle='round,pad=0,rounding_size=0.12',
        facecolor=OVERALLS, edgecolor=OVERALLS_EDGE, linewidth=1.4,
        zorder=5,
    ))
    ax.add_patch(FancyBboxPatch(
        (1.01, 1.08), 0.58, 0.24,
        boxstyle='round,pad=0,rounding_size=0.035',
        facecolor=OVERALLS, edgecolor=OVERALLS_EDGE, linewidth=1.4,
        zorder=5,
    ))

    # Shoulder straps and brass buttons.
    for x in (1.035, 1.475):
        ax.add_patch(FancyBboxPatch(
            (x, 1.28), 0.09, 0.18,
            boxstyle='round,pad=0,rounding_size=0.02',
            facecolor=OVERALLS, edgecolor=OVERALLS_EDGE, linewidth=1.1,
            zorder=5,
        ))
        ax.add_patch(Circle(
            (x + 0.045, 1.285), 0.032,
            facecolor=theme.GOLD, edgecolor=COIN_EDGE, linewidth=0.8,
            zorder=6,
        ))
    for x in (0.87, 1.73):
        ax.add_patch(Circle(
            (x, 0.98), 0.032,
            facecolor=theme.GOLD, edgecolor=COIN_EDGE, linewidth=0.8,
            zorder=6,
        ))

    # Bib pocket, with a couple of visible stitches.
    ax.add_patch(FancyBboxPatch(
        (1.16, 1.13), 0.28, 0.115,
        boxstyle='round,pad=0,rounding_size=0.02',
        facecolor=OVERALLS_DARK, edgecolor=OVERALLS_EDGE, linewidth=0.9,
        zorder=6,
    ))
    ax.plot([1.17, 1.43], [1.235, 1.235],
            color=STITCH, linewidth=0.7, linestyle=(0, (2, 1)), zorder=7)

    # Curved back ears, then the pig head.
    left_ear = [
        (1.03, 1.94),
        (0.79, 2.04), (0.64, 2.35), (0.84, 2.49),
        (1.00, 2.47), (1.13, 2.17), (1.09, 1.97),
        (1.03, 1.94),
    ]
    right_ear = [
        (1.57, 1.94),
        (1.81, 2.04), (1.96, 2.35), (1.76, 2.49),
        (1.60, 2.47), (1.47, 2.17), (1.51, 1.97),
        (1.57, 1.94),
    ]
    for points in (left_ear, right_ear):
        ax.add_patch(PathPatch(
            _ear_path(points), facecolor=PINK, edgecolor=PINK_DARK,
            linewidth=1.5, joinstyle='round', zorder=7,
        ))
    left_inner = [
        (1.01, 1.99),
        (0.84, 2.08), (0.74, 2.31), (0.87, 2.40),
        (0.97, 2.39), (1.05, 2.16), (1.04, 2.02),
        (1.01, 1.99),
    ]
    right_inner = [
        (1.59, 1.99),
        (1.76, 2.08), (1.86, 2.31), (1.73, 2.40),
        (1.63, 2.39), (1.55, 2.16), (1.56, 2.02),
        (1.59, 1.99),
    ]
    for points in (left_inner, right_inner):
        ax.add_patch(PathPatch(
            _ear_path(points), facecolor=theme.CORAL_SOFT,
            edgecolor='none', alpha=0.9, zorder=8,
        ))

    # Neck and head. The head overlaps the shirt and straps deliberately.
    ax.add_patch(Ellipse(
        (1.30, 1.43), 0.26, 0.14,
        facecolor=PINK, edgecolor='none', zorder=7,
    ))
    ax.add_patch(Ellipse(
        (1.30, 1.84), 1.04, 0.82,
        facecolor=PINK, edgecolor=PINK_DARK, linewidth=1.6, zorder=8,
    ))
    ax.add_patch(Ellipse(
        (1.03, 2.00), 0.37, 0.17,
        facecolor=PINK_LIGHT, edgecolor='none', alpha=0.65, zorder=9,
    ))

    # Coin slot stays part of Penny's piggy-bank identity.
    ax.add_patch(FancyBboxPatch(
        (1.13, 2.12), 0.34, 0.043,
        boxstyle='round,pad=0,rounding_size=0.020',
        facecolor=theme.NAVY, edgecolor='none', alpha=0.95, zorder=9,
    ))
    ax.plot([1.17, 1.43], [2.135, 2.135], color='white',
            linewidth=0.6, alpha=0.18, zorder=10)

    # Snout, nostrils and smile.
    ax.add_patch(Ellipse(
        (1.30, 1.74), 0.40, 0.25,
        facecolor=SNOUT, edgecolor=PINK_DARK, linewidth=1.2, zorder=9,
    ))
    for x in (1.20, 1.40):
        ax.add_patch(Ellipse(
            (x, 1.76), 0.050, 0.075,
            facecolor=NOSTRIL, edgecolor='none', zorder=10,
        ))
    ax.add_patch(Arc(
        (1.30, 1.65), 0.23, 0.13,
        theta1=205, theta2=335, color=NOSTRIL, linewidth=1.2, zorder=10,
    ))

    # Blush.
    for x in (0.94, 1.66):
        ax.add_patch(Ellipse(
            (x, 1.74), 0.16, 0.08,
            facecolor=theme.CORAL_SOFT, edgecolor='none',
            alpha=0.8, zorder=9,
        ))

    # Friendly eyes and round glasses with both temples.
    for x in (1.10, 1.50):
        ax.add_patch(Circle(
            (x, 1.98), 0.085, facecolor='white',
            edgecolor='none', zorder=10,
        ))
        ax.add_patch(Circle(
            (x + 0.014, 1.975), 0.040, facecolor=theme.NAVY,
            edgecolor='none', zorder=11,
        ))
        ax.add_patch(Circle(
            (x - 0.004, 1.995), 0.012, facecolor='white',
            edgecolor='none', zorder=12,
        ))
        ax.add_patch(Circle(
            (x, 1.98), 0.105, facecolor='none',
            edgecolor=theme.NAVY, linewidth=1.4, zorder=12,
        ))
    ax.plot([1.205, 1.395], [1.98, 1.98], color=theme.NAVY,
            linewidth=1.4, zorder=12)
    ax.plot([0.997, 0.84], [1.98, 2.04], color=theme.NAVY,
            linewidth=1.2, solid_capstyle='round', zorder=12)
    ax.plot([1.603, 1.76], [1.98, 2.04], color=theme.NAVY,
            linewidth=1.2, solid_capstyle='round', zorder=12)

    # Gold coin and heart.
    ax.add_patch(Circle(
        (2.13, 2.13), 0.18, facecolor=theme.GOLD,
        edgecolor=COIN_EDGE, linewidth=1.1, zorder=13,
    ))
    ax.add_patch(Circle(
        (2.13, 2.13), 0.135, facecolor='none',
        edgecolor='#E0B64A', linewidth=0.7, zorder=14,
    ))
    ax.text(
        2.13, 2.12, '$', ha='center', va='center',
        fontsize=max(7, size * 0.055), fontweight='bold',
        color=theme.NAVY, zorder=15,
    )
    for x, y in ((1.95, 2.35), (2.32, 2.34), (2.34, 1.91)):
        ax.plot([x, x + 0.035], [y, y + 0.035],
                color=COIN_EDGE, linewidth=1.2, solid_capstyle='round',
                zorder=13)

    ax.add_patch(Circle(
        (0.47, 2.23), 0.060, facecolor=theme.CORAL,
        edgecolor='none', zorder=13,
    ))
    ax.add_patch(Circle(
        (0.57, 2.23), 0.060, facecolor=theme.CORAL,
        edgecolor='none', zorder=13,
    ))
    ax.add_patch(PathPatch(
        Path([(0.415, 2.21), (0.625, 2.21), (0.520, 2.08), (0.415, 2.21)],
             [Path.MOVETO, Path.LINETO, Path.LINETO, Path.CLOSEPOLY]),
        facecolor=theme.CORAL, edgecolor='none', zorder=13,
    ))
    ax.add_patch(Circle(
        (0.50, 2.26), 0.016, facecolor='white',
        edgecolor='none', alpha=0.55, zorder=14,
    ))


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
