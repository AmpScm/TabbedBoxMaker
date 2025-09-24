from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from tabbedboxmaker.enums import BoxType, Layout, TabSymmetry, Sides, PieceType
from typing import Union

@dataclass
class BoxSettings:
    X: float
    Y: float
    Z: float
    inside_X: float
    inside_Y: float
    inside_Z: float
    thickness: float
    tab_width: float
    equal_tabs: bool
    tab_symmetry: TabSymmetry
    dimple_height: float
    dimple_length: float
    dogbone: bool
    layout: Layout
    spacing: float
    boxtype: BoxType
    piece_types: list[PieceType]  # Which pieces this box includes
    div_x: int
    div_y: int
    div_x_spacing: list[float]  # Custom spacing for X-axis dividers (partition widths)
    div_y_spacing: list[float]  # Custom spacing for Y-axis dividers (partition widths)
    keydiv_walls: bool
    keydiv_floor: bool
    initOffsetX: float
    initOffsetY: float
    hairline: bool
    schroff: bool
    kerf: float
    line_thickness: float
    # Schroff-specific fields (only used when schroff=True)
    unit: str
    rows: int
    rail_height: float
    row_spacing: float
    rail_mount_depth: float
    rail_mount_centre_offset: float
    rail_mount_radius: float
    optimize: bool


@dataclass
class SchroffSettings:
    """Schroff-specific settings when schroff mode is enabled"""
    rows: int
    rail_height: float
    row_centre_spacing: float
    row_spacing: float
    rail_mount_depth: float
    rail_mount_centre_offset: float
    rail_mount_radius: float


@dataclass
class BoxFaces:
    """Which faces the box has based on the box type"""
    hasTp: bool  # top
    hasBm: bool  # bottom
    hasFt: bool  # front
    hasBk: bool  # back
    hasLt: bool  # left
    hasRt: bool  # right


@dataclass
class TabConfiguration:
    """Tab information for each face"""
    tpTabInfo: int
    bmTabInfo: int
    ltTabInfo: int
    rtTabInfo: int
    ftTabInfo: int
    bkTabInfo: int
    tpTabbed: int
    bmTabbed: int
    ltTabbed: int
    rtTabbed: int
    ftTabbed: int
    bkTabbed: int

class Vec(tuple):
    """Simple 2D vector class for basic operations"""
    x: float
    y: float

    def __new__(cls, x : float, y : float):
        return super().__new__(cls, (x, y))

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __add__(self, other: "Vec") -> "Vec":
        return Vec(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec") -> "Vec":
        return Vec(self.x - other.x, self.y - other.y)

    def __mul__(self, other: Union[float, "Vec"]) -> Union["Vec", float]:
        if isinstance(other, Vec):
            return Vec(self.x * other.x, self.y * other.y)
        elif isinstance(other, (int, float)):
            return Vec(self.x * other, self.y * other)
        return NotImplemented
    
    def __neg__(self):
        return Vec(-self.x, -self.y)

    def __truediv__(self, scalar: float) -> "Vec":
        return Vec(self.x / scalar, self.y / scalar)

    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)

    def rotate_clockwise(self, count : int = 1) -> "Vec":
        """Return a vector rotated 90 degrees clockwise"""

        v = (self.x + self.y * 1j)
        for _ in range(count):
            v *= 1j
        return Vec(v.real, v.imag)

    def rotate_counterclockwise(self, count : int = 1) -> "Vec":
        """Return a vector rotated 90 degrees counter-clockwise"""

        v = (self.x + self.y * 1j)
        for _ in range(count):
            v *= -1j
        return Vec(v.real, v.imag)
    
    def swap_xy(self) -> "Vec":
        """Return a vector with x and y swapped"""
        return Vec(self.y, self.x)

    def is_zero(self) -> bool:
        """Return True if both x and y are zero"""
        return Vec(self.x == 0, self.y == 0)

@dataclass
class Side:
    name: Sides
    is_male: bool
    has_tabs: bool
    length: float  # Current length (for backward compatibility)
    direction: Vec
    tab_symmetry: TabSymmetry
    divisions: int
    tab_width: float
    gap_width: float
    thickness: float
    inside_length: float = 0.0  # Inside dimension
    line_thickness: float = 0.1  # default line thickness
    prev: "Side" = None
    next: "Side" = None

    # Geometric offsets (calculated in _calculate_geometric_offsets)
    root_offset: Vec = Vec(0, 0)
    start_offset: Vec = Vec(0, 0)

    # Divider support
    divider_spacings: list[float] = None
    num_dividers: int = 0

    equal_tabs: bool = False
    base_tab_width: float = 0.0

    @property
    def start_hole(self) -> bool:
        """Calculate if this side starts with a hole

        This encapsulates the logic that was previously done with is_male,
        but accounts for different tab symmetry modes.

        Returns True when the side should contribute a thickness offset,
        False when it should not contribute an offset.
        """
        # For now, exactly match existing is_male behavior
        if self.tab_symmetry == TabSymmetry.ROTATE_SYMMETRIC:
            return True # Always use offset for rotational symmetry (starts inside)
        return self.is_male and self.has_tabs

    @property
    def end_hole(self) -> bool:
        """Calculate if this side ends with a hole

        This encapsulates the logic that was previously done with is_male,
        but accounts for different tab symmetry modes.

        Returns True when the side should contribute a thickness offset,
        False when it should not contribute an offset.
        """
        # For now, exactly match existing is_male behavior
        if self.tab_symmetry == TabSymmetry.ROTATE_SYMMETRIC:
            return not self.has_tabs # Always use offset for rotational symmetry (starts inside)
        return self.is_male and self.has_tabs

    def __init__(self, settings : BoxSettings, name: Sides, is_male: bool, has_tabs: bool, length: float, inside_length: float):
        self.name = name
        self.is_male = is_male
        self.has_tabs = has_tabs
        # Current length parameter (outside dimension for backward compatibility)
        self.length = length
        self.inside_length = inside_length  # Inside dimension passed explicitly
        self.divider_spacings = []

        baseDirection = Vec(1, 0)  # default direction

        self.direction = baseDirection.rotate_clockwise(name)  # Rotate direction based on side name (A=0°, B=90°, C=180°, D=270°)
        self.tab_symmetry = settings.tab_symmetry
        self.tab_width = self.base_tab_width = settings.tab_width
        self.thickness = settings.thickness
        self.line_thickness = settings.line_thickness
        self.dogbone = settings.dogbone
        self.equal_tabs = settings.equal_tabs

        self.recalc()

    def recalc(self, pieceType: PieceType = None):
        length = self.length

        if pieceType == PieceType.DividerY and self.name in (Sides.B, Sides.D):
            # Special case for DividerX
            length = self.inside_length + 2 * self.thickness # Same tabs as same piece with outside tabs
        elif pieceType == PieceType.DividerX and self.name in (Sides.A, Sides.C):
            # Special case for DividerX
            length = self.inside_length + 2 * self.thickness # Same tabs as same piece with outside tabs

        if self.tab_symmetry == TabSymmetry.ROTATE_SYMMETRIC:
            self.divisions = int((length - 2 * self.thickness) // self.base_tab_width)
            if self.divisions % 2:
                self.divisions += 1  # make divs even
            tabs = self.divisions // 2  # tabs for side
        else:
            self.divisions = int(length // self.base_tab_width)
            if not self.divisions % 2:
                self.divisions -= 1  # make divs odd
            tabs = (self.divisions - 1) // 2  # tabs for side

        if self.tab_symmetry == TabSymmetry.ROTATE_SYMMETRIC:
            self.gap_width = self.tab_width = (length - 2 * self.thickness) / self.divisions
        elif self.equal_tabs:
            self.gap_width = self.tab_width = length / self.divisions
        else:
            self.tab_width = self.base_tab_width
            self.gap_width = (length - tabs * self.tab_width) / (self.divisions - tabs)

@dataclass
class Piece:
    """A piece of the box with its sides and positioning"""
    sides: list[Side]
    pieceType: PieceType
    dx: float  # outside dimension
    dy: float  # outside dimension
    base: Vec  # (x,y) base co-ordinates for piece

    def __init__(self, sides: list[Side], pieceType: PieceType):
        self.sides = sides
        self.pieceType = pieceType

        # For backward compatibility, dx and dy continue to represent outside dimensions
        self.dx = sides[0].length  # Same as sides[0].length
        self.dy = sides[1].length  # Same as sides[1].length

        # Link sides together
        sides[0].next = sides[1]
        sides[1].next = sides[2]
        sides[2].next = sides[3]
        sides[3].next = sides[0]
        sides[0].prev = sides[3]
        sides[1].prev = sides[0]
        sides[2].prev = sides[1]
        sides[3].prev = sides[2]

        # Initialize at (0,0) - positioning happens in layout phase
        self.base = Vec(0, 0)

        # Phase 2.1: Calculate geometric offsets for each side
        # Keep alongside old system for verification before switching
        self._calculate_geometric_offsets()

    def _calculate_geometric_offsets(self):
        """Calculate geometric offsets for each side based on neighboring side properties.

        Phase 2.1: Pre-calculate the same offset values that are currently calculated
        on-the-fly in render functions. This reduces coupling by moving the geometric
        knowledge from render functions to side/piece creation.

        Key insight: Each side only needs its start point - the end point is the
        start point of the next side. This creates a clean linked geometry.

        Calculates:
        - root_offset: Base position for side's coordinate system
        - start_offset: Position adjustment based on prev/current side male/female
        """

        for side in self.sides:
            side.recalc(self.pieceType)  # Ensure side parameters are up to date

        for side in self.sides:
            # These calculations mirror the offs_cases logic in render functions
            if side.name == Sides.A:
                side.root_offset = Vec(0, 0)
            elif side.name == Sides.B:
                side.root_offset = Vec(side.prev.length, 0)
            elif side.name == Sides.C:
                side.root_offset = Vec(side.length, side.prev.length)
            elif side.name == Sides.D:
                side.root_offset = Vec(0, side.length)

            side.start_offset = Vec(side.prev.end_hole, side.start_hole).rotate_clockwise(side.name)


@dataclass
class BoxConfiguration:
    """Complete box configuration including all computed settings"""
    schroff_settings: Optional[SchroffSettings]
    piece_types: list[PieceType]
    tabs: TabConfiguration

