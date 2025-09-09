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


# For backward compatibility with old naming
DividerStyle = DividerKeying


class LineThickness(IntEnum):
    """Line thickness options."""

    DEFAULT = 0  # Default line thickness
    HAIRLINE = 1  # Hairline thickness (0.002" for Epilog lasers)


class BoxDimensions(IntEnum):
    """Box dimension interpretation."""

    OUTSIDE = 0  # Dimensions are outside measurements
    INSIDE = 1  # Dimensions are inside measurements


# Backward compatibility mappings for string parsing
BOX_TYPE_NAMES = {
    "fully_enclosed": BoxType.FULLY_ENCLOSED,
    "one_side_open": BoxType.ONE_SIDE_OPEN,
    "two_sides_open": BoxType.TWO_SIDES_OPEN,
    "three_sides_open": BoxType.THREE_SIDES_OPEN,
    "opposite_ends_open": BoxType.OPPOSITE_ENDS_OPEN,
    "two_panels_only": BoxType.TWO_PANELS_ONLY,
}

TAB_SYMMETRY_NAMES = {
    "xy_symmetric": TabSymmetry.XY_SYMMETRIC,
    "rotate_symmetric": TabSymmetry.ROTATE_SYMMETRIC,
    "antisymmetric": TabSymmetry.ANTISYMMETRIC,
}

TAB_TYPE_NAMES = {
    "regular": TabType.REGULAR,
    "laser": TabType.REGULAR,
    "dogbone": TabType.DOGBONE,
    "mill": TabType.DOGBONE,
}

LAYOUT_NAMES = {
    "diagrammatic": Layout.DIAGRAMMATIC,
    "three_piece": Layout.THREE_PIECE,
    "inline": Layout.INLINE_COMPACT,
    "compact": Layout.INLINE_COMPACT,
}

TAB_WIDTH_NAMES = {
    "fixed": TabWidth.FIXED,
    "proportional": TabWidth.PROPORTIONAL,
}

DIVIDER_KEYING_NAMES = {
    "none": DividerKeying.NONE,
    "walls": DividerKeying.WALLS,
    "floor_ceiling": DividerKeying.FLOOR_CEILING,
    "all_sides": DividerKeying.ALL_SIDES,
}

LINE_THICKNESS_NAMES = {
    "default": LineThickness.DEFAULT,
    "hairline": LineThickness.HAIRLINE,
}

BOX_DIMENSIONS_NAMES = {
    "outside": BoxDimensions.OUTSIDE,
    "inside": BoxDimensions.INSIDE,
}


def parse_enum_value(enum_class, value, name_mapping=None):
    """
    Parse an enum value from various input types.

    Args:
        enum_class: The enum class to convert to
        value: The value to convert (int, str, or enum instance)
        name_mapping: Optional dict mapping string names to enum values

    Returns:
        enum_class instance

    Raises:
        ValueError: If the value cannot be converted
    """
    if isinstance(value, enum_class):
        return value

    if isinstance(value, int):
        try:
            return enum_class(value)
        except ValueError:
            raise ValueError(f"Invalid {enum_class.__name__} value: {value}")

    if isinstance(value, str):
        # Try to convert string to int first (for command line args)
        try:
            int_value = int(value)
            return enum_class(int_value)
        except (ValueError, TypeError):
            pass

        # Try by name
        try:
            return enum_class[value.upper()]
        except KeyError:
            pass

        # Try name mapping if provided
        if name_mapping:
            lower_value = value.lower().replace(' ', '_').replace('-', '_')
            if lower_value in name_mapping:
                return name_mapping[lower_value]

        raise ValueError(f"Invalid {enum_class.__name__} name: {value}")

    raise ValueError(f"Cannot convert {type(value)} to {enum_class.__name__}")


# Converter functions for command line arguments
def box_type_converter(value):
    """Convert command line argument to BoxType enum."""
    return parse_enum_value(BoxType, value, BOX_TYPE_NAMES)


def tab_symmetry_converter(value):
    """Convert command line argument to TabSymmetry enum."""
    return parse_enum_value(TabSymmetry, value, TAB_SYMMETRY_NAMES)


def tab_type_converter(value):
    """Convert command line argument to TabType enum."""
    return parse_enum_value(TabType, value, TAB_TYPE_NAMES)


def layout_converter(value):
    """Convert command line argument to Layout enum."""
    return parse_enum_value(Layout, value, LAYOUT_NAMES)


def tab_width_converter(value):
    """Convert command line argument to TabWidth enum."""
    return parse_enum_value(TabWidth, value, TAB_WIDTH_NAMES)


def divider_style_converter(value):
    """Convert command line argument to DividerKeying enum."""
    return parse_enum_value(DividerKeying, value, DIVIDER_KEYING_NAMES)


def divider_keying_converter(value):
    """Convert command line argument to DividerKeying enum."""
    return parse_enum_value(DividerKeying, value, DIVIDER_KEYING_NAMES)


def line_thickness_converter(value):
    """Convert command line argument to LineThickness enum."""
    return parse_enum_value(LineThickness, value, LINE_THICKNESS_NAMES)


def box_dimensions_converter(value):
    """Convert command line argument to BoxDimensions enum."""
    return parse_enum_value(BoxDimensions, value, BOX_DIMENSIONS_NAMES)
