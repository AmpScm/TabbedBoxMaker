"""
Enums for TabbedBoxMaker to replace magic integers.

This module defines all the enums used in the boxmaker to make the code
more readable and maintainable while maintaining backward compatibility.
"""

from enum import IntEnum


class BoxType(IntEnum):
    """Box type enumeration - defines which sides of the box are included."""

    FULLY_ENCLOSED = 1  # 6 sides
    ONE_SIDE_OPEN = 2  # One side open (LxW) - 5 sides
    TWO_SIDES_OPEN = 3  # Two sides open (LxW and LxH) - 4 sides
    THREE_SIDES_OPEN = 4  # Three sides open (LxW, LxH, HxW) - 3 sides
    OPPOSITE_ENDS_OPEN = 5  # Opposite ends open (LxW) - 4 sides (tube)
    TWO_PANELS_ONLY = 6  # Two panels only (LxW and LxH) - 2 sides


class TabSymmetry(IntEnum):
    """Tab symmetry style enumeration."""

    XY_SYMMETRIC = 0  # Each piece is symmetric in both X and Y axes
    # Each piece is symmetric under 180-degree rotation (waffle-block)
    ROTATE_SYMMETRIC = 1
    ANTISYMMETRIC = 2  # Deprecated - antisymmetric style


class TabType(IntEnum):
    """Tab type enumeration."""

    REGULAR = 0  # Regular tabs for laser cutting
    DOGBONE = 1  # Dogbone tabs for CNC milling


class Layout(IntEnum):
    """Layout style enumeration."""

    DIAGRAMMATIC = 1  # Diagrammatic layout
    THREE_PIECE = 2  # 3 piece layout
    INLINE_COMPACT = 3  # Inline (compact) layout


class TabWidth(IntEnum):
    """Tab width calculation method."""

    FIXED = 0  # Fixed tab width
    PROPORTIONAL = 1  # Proportional tab width


class DividerKeying(IntEnum):
    """Divider keying options."""

    ALL_SIDES = 0  # Key dividers into all sides
    FLOOR_CEILING = 1  # Key dividers into floor/ceiling only
    WALLS = 2  # Key dividers into walls only
    NONE = 3  # No keying - dividers slide freely


class LineThickness(IntEnum):
    """Line thickness options."""

    DEFAULT = 0  # Default line thickness
    HAIRLINE = 1  # Hairline thickness (0.002" for Epilog lasers)


class BoxDimensions(IntEnum):
    """Box dimension interpretation."""

    OUTSIDE = 0  # Dimensions are outside measurements
    INSIDE = 1  # Dimensions are inside measurements
