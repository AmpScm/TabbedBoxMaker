from dataclasses import dataclass
from typing import Optional
from tabbedboxmaker.enums import BoxType, Layout, TabSymmetry, FaceType, SideEnum, PieceType


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
    inside_length: float = 0.0  # Inside dimension
    outside_length: float = 0.0  # Outside dimension
    line_thickness: float = 0.1  # default line thickness
    prev: "Side" = None
    next: "Side" = None
    
    # Geometric offsets (calculated in _calculate_geometric_offsets)
    root_offset: tuple[float, float] = (0, 0)
    start_offset: tuple[float, float] = (0, 0)
    
    # Divider support
    divider_spacings: list[float] = None
    num_dividers: int = 0
    
    @property
    def start_tab(self) -> bool:
        """Calculate if this side starts with a tab
        
        This encapsulates the logic that was previously done with is_male,
        but accounts for different tab symmetry modes.
        
        Returns True when the side should contribute a thickness offset,
        False when it should not contribute an offset.
        
        For now, this exactly matches is_male behavior to maintain compatibility.
        Future: Will be extended to handle ROTATE_SYMMETRIC and other modes properly.
        """
        # For now, exactly match existing is_male behavior
        if self.tab_symmetry == TabSymmetry.ROTATE_SYMMETRIC:
            return True # Always use offset for rotational symmetry (starts inside)
        return self.is_male 

    @property
    def end_tab(self) -> bool:
        """Calculate if this side starts with a tab
        
        This encapsulates the logic that was previously done with is_male,
        but accounts for different tab symmetry modes.
        
        Returns True when the side should contribute a thickness offset,
        False when it should not contribute an offset.
        
        For now, this exactly matches is_male behavior to maintain compatibility.
        Future: Will be extended to handle ROTATE_SYMMETRIC and other modes properly.
        """
        # For now, exactly match existing is_male behavior
        if self.tab_symmetry == TabSymmetry.ROTATE_SYMMETRIC:
            return not self.has_tabs # Always use offset for rotational symmetry (starts inside)
        return self.is_male 
    # Note: end_offset removed - end point is start_offset of next side

    def __init__(self, settings : BoxSettings, name: SideEnum, is_male: bool, has_tabs: bool, length: float, inside_length: float):
        self.name = name
        self.is_male = is_male
        self.has_tabs = has_tabs
        # Current length parameter (outside dimension for backward compatibility)
        self.length = length
        self.outside_length = length  # Outside dimension
        self.inside_length = inside_length  # Inside dimension passed explicitly
        self.divider_spacings = []

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
        self.line_thickness = settings.line_thickness
        self.dogbone = settings.dogbone

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
            # These calculations mirror the offs_cases logic in render functions
            if side.name == SideEnum.A:
                side.root_offset = (0, 0)
                side.start_offset = (side.prev.end_tab, side.start_tab)
            elif side.name == SideEnum.B:
                side.root_offset = (side.prev.length, 0)
                side.start_offset = (-side.start_tab, side.prev.end_tab)
            elif side.name == SideEnum.C:
                side.root_offset = (side.length, side.prev.length)
                side.start_offset = (-side.prev.end_tab, -side.start_tab)
            elif side.name == SideEnum.D:
                side.root_offset = (0, side.length)
                side.start_offset = (side.start_tab, -side.prev.end_tab)


@dataclass
@dataclass
class BoxConfiguration:
    """Complete box configuration including all computed settings"""
    schroff_settings: Optional[SchroffSettings]
    faces: BoxFaces
    tabs: TabConfiguration
    pieces: list[Piece]
