from dataclasses import dataclass
from typing import Optional
from tabbedboxmaker.enums import BoxType, Layout, TabSymmetry, FaceType, SideEnum, PieceType, SideTabbing


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
    div_x: float
    div_y: float
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



@dataclass
class Side:
    name: SideEnum
    is_male: bool
    has_tabs: bool
    length: float  # Current length (for backward compatibility)
    direction: tuple[int, int]
    tab_symmetry: TabSymmetry
    divisions: int
    tab_width: float
    gap_width: float
    thickness: float
    kerf: float
    inside_length: float = 0.0  # Inside dimension
    outside_length: float = 0.0  # Outside dimension
    line_thickness: float = 0.1  # default line thickness
    prev: "Side" = None
    next: "Side" = None
    dogbone: bool = False
    divider_spacings: list[float] = None  # Pre-calculated divider spacings (partition widths)
    num_dividers: int = 0  # Number of dividers (partitions) on this side
    tabbing: SideTabbing = None  # Clean enum representation of tabbing type

    def __init__(self, settings : BoxSettings, name: SideEnum, is_male: bool, has_tabs: bool, length: float, inside_length: float):
        self.name = name
        self.is_male = is_male
        self.has_tabs = has_tabs
        # Current length parameter (outside dimension for backward compatibility)
        self.length = length
        self.outside_length = length  # Outside dimension
        self.inside_length = inside_length  # Inside dimension passed explicitly
        self.divider_spacings = []

        # Calculate clean tabbing enum from the boolean flags
        self.tabbing = self._calculate_tabbing(is_male, has_tabs)

        dir_cases = {
            SideEnum.A: (1, 0),
            SideEnum.B: (0, 1),
            SideEnum.C: (-1, 0),
            SideEnum.D: (0, -1),
        }

        self.direction = dir_cases.get(name, (0, 0))
        self.tab_symmetry = settings.tab_symmetry
        self.tab_width = settings.tab_width
        self.thickness = settings.thickness
        self.kerf = settings.kerf
        self.line_thickness = settings.line_thickness
        self.dogbone = settings.dogbone

        halfkerf = settings.kerf / 2

        if self.tab_symmetry == TabSymmetry.ROTATE_SYMMETRIC:
            self.divisions = int((length - 2 * settings.thickness) / self.tab_width)
            if self.divisions % 2:
                self.divisions += 1  # make divs even
            tabs = self.divisions // 2  # tabs for side
        else:
            self.divisions = int(length // self.tab_width)
            if not self.divisions % 2:
                self.divisions -= 1  # make divs odd
            tabs = (self.divisions - 1) // 2  # tabs for side

        if self.tab_symmetry == TabSymmetry.ROTATE_SYMMETRIC:
            self.gap_width = self.tab_width = (length - 2 * settings.thickness) / self.divisions
        elif settings.equal_tabs:
            self.gap_width = self.tab_width = length / self.divisions
        else:
            self.tab_width = self.tab_width
            self.gap_width = (length - tabs * self.tab_width) / (self.divisions - tabs)

        if is_male:  # self.kerf correction
            self.gap_width -= settings.kerf
            self.tab_width += settings.kerf
            self.first = halfkerf
        else:
            self.gap_width += settings.kerf
            self.tab_width -= settings.kerf
            self.first = -halfkerf

    def _calculate_tabbing(self, is_male: bool, has_tabs: bool) -> SideTabbing:
        """Calculate the clean tabbing enum from boolean flags."""
        if not has_tabs:
            return SideTabbing.NONE
        elif is_male:
            return SideTabbing.MALE
        else:
            return SideTabbing.FEMALE


@dataclass
class Piece:
    """A piece of the box with its sides and positioning"""
    sides: list[Side]
    pieceType: PieceType
    faceType: FaceType
    dx: float  # outside dimension
    dy: float  # outside dimension
    base: tuple[float, float]  # (x,y) base co-ordinates for piece

    @property
    def outside_dx(self) -> float:
        """Outside X dimension"""
        return self.sides[0].outside_length
    
    @property
    def outside_dy(self) -> float:
        """Outside Y dimension"""
        return self.sides[1].outside_length
    
    @property
    def inside_dx(self) -> float:
        """Inside X dimension"""
        return self.sides[0].inside_length
    
    @property
    def inside_dy(self) -> float:
        """Inside Y dimension"""
        return self.sides[1].inside_length


    @staticmethod
    def calculate_face_type(piece_type: PieceType) -> FaceType:
        """Calculate face type from piece type"""
        face_type_mapping = {
            PieceType.Top: FaceType.XY,
            PieceType.Bottom: FaceType.XY,
            PieceType.Front: FaceType.XZ,
            PieceType.Back: FaceType.XZ,
            PieceType.Left: FaceType.ZY,
            PieceType.Right: FaceType.ZY,
            PieceType.DividerX: FaceType.XZ,
            PieceType.DividerY: FaceType.ZY,
        }
        return face_type_mapping.get(piece_type, FaceType.XY)

    def __init__(self, sides: list[Side], pieceType: PieceType):
        self.sides = sides
        self.faceType = self.calculate_face_type(pieceType)
        self.pieceType = pieceType
        
        # For backward compatibility, dx and dy continue to represent outside dimensions
        self.dx = sides[0].outside_length  # Same as sides[0].length
        self.dy = sides[1].outside_length  # Same as sides[1].length

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
        self.base = (0, 0)


@dataclass
class BoxConfiguration:
    """Complete box configuration including all computed settings"""
    schroff_settings: Optional[SchroffSettings]
    faces: BoxFaces
    tabs: TabConfiguration
    pieces: list[Piece]
