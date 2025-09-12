from dataclasses import dataclass
from typing import Optional
from tabbedboxmaker.enums import BoxType, Layout, TabSymmetry, DividerKeying

@dataclass
class BoxSettings:
    X: float
    Y: float
    Z: float
    thickness: float
    nomTab: float
    equalTabs: bool
    tabSymmetry: TabSymmetry
    dimpleHeight: float
    dimpleLength: float
    dogbone: bool
    layout: Layout
    spacing: float
    boxtype: BoxType
    divx: float
    divy: float
    keydivwalls: bool
    keydivfloor: bool
    initOffsetX: float
    initOffsetY: float
    inside: bool
    hairline: bool
    schroff: bool
    kerf: float

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
class PieceSettings:
    """Settings for a single piece"""
    rootx: tuple[int, int, int, int]  # (spacing,X,Y,Z) multipliers
    rooty: tuple[int, int, int, int]  # (spacing,X,Y,Z) multipliers
    dx: float  # X dimension
    dy: float  # Y dimension
    tabInfo: int  # tab pattern
    tabbed: int   # which sides have tabs
    faceType: int # piece type (1=XY, 2=XZ, 3=ZY)

@dataclass
class BoxConfiguration:
    """Complete box configuration including all computed settings"""
    schroff_settings: Optional[SchroffSettings]
    faces: BoxFaces
    tabs: TabConfiguration
    pieces: list[PieceSettings]
