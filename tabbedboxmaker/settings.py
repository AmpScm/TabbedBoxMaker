from dataclasses import dataclass
from typing import Optional
from tabbedboxmaker.enums import BoxType, Layout, TabSymmetry, FaceType, SideEnum


@dataclass
class BoxSettings:
    X: float
    Y: float
    Z: float
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
    div_x: float
    div_y: float
    div_x_spacing: list[float]  # Custom spacing for X-axis dividers (partition widths)
    div_y_spacing: list[float]  # Custom spacing for Y-axis dividers (partition widths)
    keydiv_walls: bool
    keydiv_floor: bool
    initOffsetX: float
    initOffsetY: float
    inside: bool
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
    tab_info: int
    tabbed: int
    length: float
    direction: tuple[int, int]
    tab_symmetry: TabSymmetry
    divisions: int
    tab_width: float
    gap_width: float
    thickness: float
    kerf: float
    line_thickness: float = 0.1  # default line thickness
    prev: "Side" = None
    next: "Side" = None
    dogbone: bool = False
    divider_spacings: list[float] = None  # Pre-calculated divider spacings (partition widths)

    def __init__(self, settings : BoxSettings, name: SideEnum, is_male: bool, has_tabs: bool, tab_info: int, tabbed: int, length: float):
        self.name = name
        self.is_male = is_male
        self.has_tabs = has_tabs
        self.tab_info = tab_info
        self.tabbed = tabbed
        self.length = length
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



@dataclass
class PieceSettings:
    """Settings for a single piece"""
    rootx: tuple[int, int, int, int]  # (spacing,X,Y,Z) multipliers
    rooty: tuple[int, int, int, int]  # (spacing,X,Y,Z) multipliers
    dx: float  # X dimension
    dy: float  # Y dimension
    sides: list[Side]
    faceType: FaceType

    def __init__(self, rootx: tuple[int, int, int, int], rooty: tuple[int, int, int, int], sides: list[Side], faceType: FaceType):
        self.rootx = rootx
        self.rooty = rooty
        self.sides = sides
        self.faceType = faceType
        self.dx = sides[0].length
        self.dy = sides[1].length

        sides[0].next = sides[1]
        sides[1].next = sides[2]
        sides[2].next = sides[3]
        sides[3].next = sides[0]
        sides[0].prev = sides[3]
        sides[1].prev = sides[0]
        sides[2].prev = sides[1]
        sides[3].prev = sides[2]


@dataclass
class BoxConfiguration:
    """Complete box configuration including all computed settings"""
    schroff_settings: Optional[SchroffSettings]
    faces: BoxFaces
    tabs: TabConfiguration
    pieces: list[PieceSettings]
