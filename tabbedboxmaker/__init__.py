#! /usr/bin/env python -t
"""
Generates Inkscape SVG file containing box components needed to
CNC (laser/mill) cut a box with tabbed joints taking kerf and clearance into account

Original Tabbed Box Maker Copyright (C) 2011 elliot white

See changelog in tabbedboxmaker/__about__.py

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from inkex.utils import filename_arg

import math
import os
import inkex
import gettext

from inkex.paths import Path
from inkex.paths.lines import Line, Move, ZoneClose

from copy import deepcopy
from shapely.ops import unary_union

from tabbedboxmaker.enums import BoxType, Layout, TabSymmetry, DividerKeying, FaceType, SideEnum
from tabbedboxmaker.InkexShapely import path_to_polygon, polygon_to_path, adjust_canvas
from tabbedboxmaker.__about__ import __version__ as BOXMAKER_VERSION
from tabbedboxmaker.settings import BoxSettings, BoxConfiguration, BoxFaces, TabConfiguration, PieceSettings, SchroffSettings, Side

_ = gettext.gettext


def log(text: str) -> None:
    if "SCHROFF_LOG" in os.environ:
        f = open(os.environ.get("SCHROFF_LOG"), "a")
        f.write(text + "\n")


def fstr(f: float) -> str:
    """Format float to string with minimal decimal places, avoiding scientific notation."""
    if f.is_integer():
        return str(int(f))

    r = str(f)

    if r.endswith('.0'):
        return r[:-2]
    else:
        return r


class BoxMaker(inkex.Effect):
    linethickness: float = 1
    thickess: float
    tab_width: float
    equal_tabs: bool
    dimpleHeight: float
    dimpleLength: float
    dogbone: bool
    layout: Layout
    spacing: float
    boxtype: BoxType
    div_x: float
    div_y: float
    keydivwalls: bool
    keydivfloor: bool
    nextId: dict[str, int]
    version = BOXMAKER_VERSION

    def __init__(self, cli: bool = False, schroff: bool = False):
        # Call the base class constructor.
        inkex.Effect.__init__(self)
        # Define options

        self.nextId = {}

        self.cli = cli
        self.schroff = schroff
        if cli:
            # We don't need an input file in CLI mode
            for action in self.arg_parser._actions:
                if action.dest == "input_file":
                    self.arg_parser._actions.remove(action)

            self.arg_parser.add_argument(
                "--input-file",
                dest="input_file",
                metavar="INPUT_FILE",
                type=filename_arg,
                help="Filename of the input file",
                default=None,
            )

        self.arg_parser.add_argument(
            "--schroff",
            action="store",
            type=bool,
            dest="schroff",
            default=schroff,
            help="Enable Schroff mode",
        )
        self.arg_parser.add_argument(
            "--rail_height",
            action="store",
            type=float,
            dest="rail_height",
            default=10.0,
            help="Height of rail (float)",
        )
        self.arg_parser.add_argument(
            "--rail_mount_depth",
            action="store",
            type=float,
            dest="rail_mount_depth",
            default=17.4,
            help="Depth at which to place hole for rail mount bolt (float)",
        )
        self.arg_parser.add_argument(
            "--rail_mount_centre_offset",
            action="store",
            type=float,
            dest="rail_mount_centre_offset",
            default=0.0,
            help="How far toward row centreline to offset rail mount bolt (from rail centreline) (float)",
        )
        self.arg_parser.add_argument(
            "--rows",
            action="store",
            type=int,
            dest="rows",
            default=0,
            help="Number of Schroff rows (int)",
        )
        self.arg_parser.add_argument(
            "--hp",
            action="store",
            type=int,
            dest="hp",
            default=0,
            help="Width (TE/HP units) of Schroff rows (int)",
        )
        self.arg_parser.add_argument(
            "--row_spacing",
            action="store",
            type=float,
            dest="row_spacing",
            default=10.0,
            help="Height of rail (float)",
        )
        self.arg_parser.add_argument(
            "--unit",
            action="store",
            type=str,
            dest="unit",
            default="mm",
            help="Measure Units",
        )
        self.arg_parser.add_argument(
            "--inside",
            action="store",
            type=int,
            dest="inside",
            default=0,
            help="Int/Ext Dimension",
        )
        self.arg_parser.add_argument(
            "--length",
            action="store",
            type=float,
            dest="length",
            default=100,
            help="Length of Box (float)",
        )
        self.arg_parser.add_argument(
            "--width",
            action="store",
            type=float,
            dest="width",
            default=100,
            help="Width of Box (float)",
        )
        self.arg_parser.add_argument(
            "--depth",
            action="store",
            type=float,
            dest="height",
            default=100,
            help="Height of Box (float)",
        )
        self.arg_parser.add_argument(
            "--tab",
            action="store",
            type=float,
            dest="tab",
            default=25,
            help="Nominal Tab Width (float)",
        )
        self.arg_parser.add_argument(
            "--equal",
            action="store",
            type=int,
            dest="equal_tabs",
            default=0,
            help="Equal/Prop Tabs",
        )
        self.arg_parser.add_argument(
            "--tabsymmetry",
            action="store",
            type=int,
            dest="tabsymmetry",
            default=0,
            help="Tab style",
        )
        self.arg_parser.add_argument(
            "--tabtype",
            action="store",
            type=int,
            dest="tabtype",
            default=0,
            help="Tab type: regular or dogbone",
        )
        self.arg_parser.add_argument(
            "--dimpleheight",
            action="store",
            type=float,
            dest="dimpleheight",
            default=0,
            help="Tab Dimple Height (float)",
        )
        self.arg_parser.add_argument(
            "--dimplelength",
            action="store",
            type=float,
            dest="dimplelength",
            default=0,
            help="Tab Dimple Tip Length (float)",
        )
        self.arg_parser.add_argument(
            "--hairline",
            action="store",
            type=int,
            dest="hairline",
            default=0,
            help="Line thickness",
        )
        self.arg_parser.add_argument(
            "--thickness",
            action="store",
            type=float,
            dest="thickness",
            default=10,
            help="Thickness of Material",
        )
        self.arg_parser.add_argument(
            "--kerf",
            action="store",
            type=float,
            dest="kerf",
            default=0.5,
            help="Kerf (width of cut)",
        )
        self.arg_parser.add_argument(
            "--style",
            action="store",
            type=int,
            dest="style",
            default=25,
            help="Layout/Style",
        )
        self.arg_parser.add_argument(
            "--spacing",
            action="store",
            type=float,
            dest="spacing",
            default=25,
            help="Part Spacing",
        )
        self.arg_parser.add_argument(
            "--boxtype",
            action="store",
            type=int,
            dest="boxtype",
            default=25,
            help="Box type",
        )
        self.arg_parser.add_argument(
            "--div_l",
            action="store",
            type=int,
            dest="div_x",
            default=25,
            help="Dividers (Length axis / X axis)",
        )
        self.arg_parser.add_argument(
            "--div_w",
            action="store",
            type=int,
            dest="div_y",
            default=25,
            help="Dividers (Width axis / Y axis)",
        )
        self.arg_parser.add_argument(
            "--keydiv",
            action="store",
            type=int,
            dest="keydiv",
            default=3,
            help="Key dividers into walls/floor",
        )
        self.arg_parser.add_argument(
            "--optimize",
            action="store",
            type=inkex.utils.Boolean,
            dest="optimize",
            default=True,
            help="Optimize paths",
        )

    def parse_arguments(self, args: list[str]) -> None:
        """Parse the given arguments and set 'self.options'"""
        self.options = self.arg_parser.parse_args(args)
        self.cli_args = deepcopy(args)

        if self.cli and self.options.input_file is None:
            self.options.input_file = os.path.join(
                os.path.dirname(__file__), "blank.svg"
            )

    def parse_options_to_settings(self) -> BoxSettings:
        """Parse command line options into a BoxSettings object"""

        # Get script's option values.
        hairline = self.options.hairline
        unit = self.options.unit
        inside = self.options.inside
        schroff = self.options.schroff
        kerf = self.svg.unittouu(str(self.options.kerf) + unit)

        # Set the line thickness
        if hairline:
            line_thickness = self.svg.unittouu("0.002in")
        else:
            line_thickness = 1

        if schroff:
            rows = self.options.rows
            rail_height = self.svg.unittouu(str(self.options.rail_height) + unit)
            row_centre_spacing = self.svg.unittouu(str(122.5) + unit)
            row_spacing = self.svg.unittouu(str(self.options.row_spacing) + unit)
            rail_mount_depth = self.svg.unittouu(
                str(self.options.rail_mount_depth) + unit
            )
            rail_mount_centre_offset = self.svg.unittouu(
                str(self.options.rail_mount_centre_offset) + unit
            )
            rail_mount_radius = self.svg.unittouu(str(2.5) + unit)
        else:
            # Default values when not in Schroff mode
            rows = 0
            rail_height = 0.0
            row_spacing = 0.0
            rail_mount_depth = 0.0
            rail_mount_centre_offset = 0.0
            rail_mount_radius = 0.0

        # minimally different behaviour for schroffmaker.inx vs. boxmaker.inx
        # essentially schroffmaker.inx is just an alternate interface with different
        # default settings, some options removed, and a tiny amount of extra
        # logic
        if schroff:
            # schroffmaker.inx
            X = self.svg.unittouu(str(self.options.hp * 5.08) + unit)
            # 122.5mm vertical distance between mounting hole centres of 3U
            # Schroff panels
            row_height = rows * (row_centre_spacing + rail_height)
            # rail spacing in between rows but never between rows and case
            # panels
            row_spacing_total = (rows - 1) * row_spacing
            Y = row_height + row_spacing_total
        else:
            # boxmaker.inx
            X = self.svg.unittouu(str(self.options.length + self.options.kerf) + unit)
            Y = self.svg.unittouu(str(self.options.width + self.options.kerf) + unit)

        Z = self.svg.unittouu(str(self.options.height + self.options.kerf) + unit)
        thickness = self.svg.unittouu(str(self.options.thickness) + unit)
        tab_width = self.svg.unittouu(str(self.options.tab) + unit)
        equal_tabs = self.options.equal_tabs
        tabSymmetry = TabSymmetry(self.options.tabsymmetry)
        dimpleHeight = self.svg.unittouu(str(self.options.dimpleheight) + unit)
        dimpleLength = self.svg.unittouu(str(self.options.dimplelength) + unit)
        dogbone = self.options.tabtype == 1
        layout = Layout(self.options.style)
        spacing = self.svg.unittouu(str(self.options.spacing) + unit)
        boxtype = BoxType(self.options.boxtype)
        div_x = self.options.div_x
        div_y = self.options.div_y
        keydivwalls = self.options.keydiv in [DividerKeying.ALL_SIDES, DividerKeying.WALLS]
        keydivfloor = self.options.keydiv in [DividerKeying.ALL_SIDES, DividerKeying.FLOOR_CEILING]
        initOffsetX = 0
        initOffsetY = 0

        if inside:  # if inside dimension selected correct values to outside dimension
            X += thickness * 2
            Y += thickness * 2
            Z += thickness * 2

        return BoxSettings(
            X=X, Y=Y, Z=Z, thickness=thickness, tab_width=tab_width, equal_tabs=equal_tabs,
            tab_symmetry=tabSymmetry, dimple_height=dimpleHeight, dimple_length=dimpleLength,
            dogbone=dogbone, layout=layout, spacing=spacing, boxtype=boxtype,
            div_x=div_x, div_y=div_y, keydiv_walls=keydivwalls, keydiv_floor=keydivfloor,
            initOffsetX=initOffsetX, initOffsetY=initOffsetY, inside=inside,
            hairline=hairline, schroff=schroff, kerf=kerf, line_thickness=line_thickness, unit=unit, rows=rows,
            rail_height=rail_height, row_spacing=row_spacing, rail_mount_depth=rail_mount_depth,
            rail_mount_centre_offset=rail_mount_centre_offset, rail_mount_radius=rail_mount_radius
        )

    def parse_settings_to_configuration(self, settings: BoxSettings) -> BoxConfiguration:
        """Parse settings into a complete box configuration with pieces"""

        # check input values mainly to avoid python errors
        # TODO restrict values to *correct* solutions
        # TODO restrict divisions to logical values

        # Validate input values
        error = False
        if min(settings.X, settings.Y, settings.Z) == 0:
            inkex.errormsg(_("Error: Dimensions must be non zero"))
            error = True
        if min(settings.X, settings.Y, settings.Z) < 3 * settings.tab_width:
            inkex.errormsg(_("Error: Tab size too large"))
            error = True
        if settings.tab_width < settings.thickness:
            inkex.errormsg(_("Error: Tab size too small"))
            error = True
        if settings.thickness == 0:
            inkex.errormsg(_("Error: thickness is zero"))
            error = True
        if settings.thickness > min(settings.X, settings.Y, settings.Z) / 3:  # crude test
            inkex.errormsg(_("Error: Material too thick"))
            error = True
        if settings.kerf > min(settings.X, settings.Y, settings.Z) / 3:  # crude test
            inkex.errormsg(_("Error: kerf too large"))
            error = True
        if settings.spacing > max(settings.X, settings.Y, settings.Z) * 10:  # crude test
            inkex.errormsg(_("Error: Spacing too large"))
            error = True
        if settings.spacing < settings.kerf:
            inkex.errormsg(_("Error: Spacing too small"))
            error = True

        if error:
            exit(1)

        # For code spacing consistency, we use two-character abbreviations for the six box faces,
        # where each abbreviation is the first and last letter of the face name:
        # tp=top, bm=bottom, ft=front, bk=back, lt=left, rt=right
        # Determine which faces the box has based on the box type
        hasTp = hasBm = hasFt = hasBk = hasLt = hasRt = True
        if settings.boxtype == BoxType.ONE_SIDE_OPEN:
            hasTp = False
        elif settings.boxtype == BoxType.TWO_SIDES_OPEN:
            hasTp = hasFt = False
        elif settings.boxtype == BoxType.THREE_SIDES_OPEN:
            hasTp = hasFt = hasRt = False
        elif settings.boxtype == BoxType.OPPOSITE_ENDS_OPEN:
            hasTp = hasBm = False
        elif settings.boxtype == BoxType.TWO_PANELS_ONLY:
            hasTp = hasFt = hasBk = hasRt = False
        # else boxtype==1, full box, has all sides

        faces = BoxFaces(hasTp=hasTp, hasBm=hasBm, hasFt=hasFt, hasBk=hasBk, hasLt=hasLt, hasRt=hasRt)

        # Determine where the tabs go based on the tab style
        if settings.tab_symmetry == TabSymmetry.ANTISYMMETRIC:  # deprecated
            tpTabInfo = 0b0110
            bmTabInfo = 0b1100
            ltTabInfo = 0b1100
            rtTabInfo = 0b0110
            ftTabInfo = 0b1100
            bkTabInfo = 0b1001
        elif settings.tab_symmetry == TabSymmetry.ROTATE_SYMMETRIC:  # Rotationally symmetric (Waffle-blocks)
            tpTabInfo = 0b1111
            bmTabInfo = 0b1111
            ltTabInfo = 0b1111
            rtTabInfo = 0b1111
            ftTabInfo = 0b1111
            bkTabInfo = 0b1111
        else:  # XY symmetric
            tpTabInfo = 0b0000
            bmTabInfo = 0b0000
            ltTabInfo = 0b1111
            rtTabInfo = 0b1111
            ftTabInfo = 0b1010
            bkTabInfo = 0b1010

        def fixTabBits(tabbed : bool, tabInfo : int, bit : int) -> tuple[bool, int]:
            newTabbed = tabbed & ~bit
            if settings.inside:
                newTabInfo = tabInfo | bit  # set bit to 1 to use tab base line
            else:
                newTabInfo = tabInfo & ~bit  # set bit to 0 to use tab tip line
            return newTabbed, newTabInfo

        # Update the tab bits based on which sides of the box don't exist
        tpTabbed = bmTabbed = ltTabbed = rtTabbed = ftTabbed = bkTabbed = 0b1111
        if not hasTp:
            bkTabbed, bkTabInfo = fixTabBits(bkTabbed, bkTabInfo, 0b0010)
            ftTabbed, ftTabInfo = fixTabBits(ftTabbed, ftTabInfo, 0b1000)
            ltTabbed, ltTabInfo = fixTabBits(ltTabbed, ltTabInfo, 0b0001)
            rtTabbed, rtTabInfo = fixTabBits(rtTabbed, rtTabInfo, 0b0100)
            tpTabbed = 0
        if not hasBm:
            bkTabbed, bkTabInfo = fixTabBits(bkTabbed, bkTabInfo, 0b1000)
            ftTabbed, ftTabInfo = fixTabBits(ftTabbed, ftTabInfo, 0b0010)
            ltTabbed, ltTabInfo = fixTabBits(ltTabbed, ltTabInfo, 0b0100)
            rtTabbed, rtTabInfo = fixTabBits(rtTabbed, rtTabInfo, 0b0001)
            bmTabbed = 0
        if not hasFt:
            tpTabbed, tpTabInfo = fixTabBits(tpTabbed, tpTabInfo, 0b1000)
            bmTabbed, bmTabInfo = fixTabBits(bmTabbed, bmTabInfo, 0b1000)
            ltTabbed, ltTabInfo = fixTabBits(ltTabbed, ltTabInfo, 0b1000)
            rtTabbed, rtTabInfo = fixTabBits(rtTabbed, rtTabInfo, 0b1000)
            ftTabbed = 0
        if not hasBk:
            tpTabbed, tpTabInfo = fixTabBits(tpTabbed, tpTabInfo, 0b0010)
            bmTabbed, bmTabInfo = fixTabBits(bmTabbed, bmTabInfo, 0b0010)
            ltTabbed, ltTabInfo = fixTabBits(ltTabbed, ltTabInfo, 0b0010)
            rtTabbed, rtTabInfo = fixTabBits(rtTabbed, rtTabInfo, 0b0010)
            bkTabbed = 0
        if not hasLt:
            tpTabbed, tpTabInfo = fixTabBits(tpTabbed, tpTabInfo, 0b0100)
            bmTabbed, bmTabInfo = fixTabBits(bmTabbed, bmTabInfo, 0b0001)
            bkTabbed, bkTabInfo = fixTabBits(bkTabbed, bkTabInfo, 0b0001)
            ftTabbed, ftTabInfo = fixTabBits(ftTabbed, ftTabInfo, 0b0001)
            ltTabbed = 0
        if not hasRt:
            tpTabbed, tpTabInfo = fixTabBits(tpTabbed, tpTabInfo, 0b0001)
            bmTabbed, bmTabInfo = fixTabBits(bmTabbed, bmTabInfo, 0b0100)
            bkTabbed, bkTabInfo = fixTabBits(bkTabbed, bkTabInfo, 0b0100)
            ftTabbed, ftTabInfo = fixTabBits(ftTabbed, ftTabInfo, 0b0100)
            rtTabbed = 0

        tabs = TabConfiguration(
            tpTabInfo=tpTabInfo, bmTabInfo=bmTabInfo, ltTabInfo=ltTabInfo, rtTabInfo=rtTabInfo,
            ftTabInfo=ftTabInfo, bkTabInfo=bkTabInfo, tpTabbed=tpTabbed, bmTabbed=bmTabbed,
            ltTabbed=ltTabbed, rtTabbed=rtTabbed, ftTabbed=ftTabbed, bkTabbed=bkTabbed
        )

        # Layout positions are specified in a grid of rows and columns
        row0 = (1, 0, 0, 0)  # top row
        row1y = (2, 0, 1, 0)  # second row, offset by Y
        row1z = (2, 0, 0, 1)  # second row, offset by Z
        row2 = (3, 0, 1, 1)  # third row, always offset by Y+Z

        col0 = (1, 0, 0, 0)  # left column
        col1x = (2, 1, 0, 0)  # second column, offset by X
        col1z = (2, 0, 0, 1)  # second column, offset by Z
        col2xx = (3, 2, 0, 0)  # third column, offset by 2*X
        col2xz = (3, 1, 0, 1)  # third column, offset by X+Z
        col3xzz = (4, 1, 0, 2)  # fourth column, offset by X+2*Z
        col3xxz = (4, 2, 0, 1)  # fourth column, offset by 2*X+Z
        col4 = (5, 2, 0, 2)  # fifth column, always offset by 2*X+2*Z
        col5 = (6, 3, 0, 2)  # sixth column, always offset by 3*X+2*Z

        # layout format:(rootx),(rooty),Xlength,Ylength,tabInfo,tabbed,pieceType
        # root= (spacing,X,Y,Z) * values in tuple
        # tabInfo= <abcd> 0=holes 1=tabs
        # tabbed= <abcd> 0=no tabs 1=tabs on this side
        # (sides: a=top, b=right, c=bottom, d=left)
        # pieceType: 1=XY, 2=XZ, 3=ZY
        tpFace = FaceType.XY
        bmFace = FaceType.XY
        ftFace = FaceType.XZ
        bkFace = FaceType.XZ
        ltFace = FaceType.ZY
        rtFace = FaceType.ZY

        def make_sides(settings : BoxSettings, dx : float, dy : float, tabInfo : int, tabbed : int) -> list[Side]:
            # Sides: A=top, B=right, C=bottom, D=left
            return [
                Side(settings, SideEnum.A, bool(tabInfo & 0b1000), bool(tabbed & 0b1000), (tabInfo >> 3) & 1, (tabbed >> 3) & 1, dx),
                Side(settings, SideEnum.B, bool(tabInfo & 0b0100), bool(tabbed & 0b0100), (tabInfo >> 2) & 1, (tabbed >> 2) & 1, dy),
                Side(settings, SideEnum.C, bool(tabInfo & 0b0010), bool(tabbed & 0b0010), (tabInfo >> 1) & 1, (tabbed >> 1) & 1, dx),
                Side(settings, SideEnum.D, bool(tabInfo & 0b0001), bool(tabbed & 0b0001), tabInfo & 1, tabbed & 1, dy)
            ]

        def reduceOffsets(aa : list, start : int, dx : int, dy : int, dz : int):
            for ix in range(start + 1, len(aa)):
                (s, x, y, z) = aa[ix]
                aa[ix] = (s - 1, x - dx, y - dy, z - dz)

        # note first two pieces in each set are the X-divider template and
        # Y-divider template respectively
        pieces_list : list[PieceSettings] = []
        if settings.layout == Layout.DIAGRAMMATIC:  # Diagramatic Layout
            rr = deepcopy([row0, row1z, row2])
            cc = deepcopy([col0, col1z, col2xz, col3xzz])
            if not hasFt:
                reduceOffsets(rr, 0, 0, 0, 1)
            if not hasLt:
                reduceOffsets(cc, 0, 0, 0, 1)
            if not hasRt:
                reduceOffsets(cc, 2, 0, 0, 1)
            if hasBk:
                pieces_list.append(PieceSettings(cc[1], rr[2], make_sides(settings, settings.X, settings.Z, bkTabInfo, bkTabbed), bkFace))
            if hasLt:
                pieces_list.append(PieceSettings(cc[0], rr[1], make_sides(settings,settings.Z, settings.Y, ltTabInfo, ltTabbed), ltFace))
            if hasBm:
                pieces_list.append(PieceSettings(cc[1], rr[1], make_sides(settings, settings.X, settings.Y, bmTabInfo, bmTabbed), bmFace))
            if hasRt:
                pieces_list.append(PieceSettings(cc[2], rr[1], make_sides(settings, settings.Z, settings.Y, rtTabInfo, rtTabbed), rtFace))
            if hasTp:
                pieces_list.append(PieceSettings(cc[3], rr[1], make_sides(settings, settings.X, settings.Y, tpTabInfo, tpTabbed), tpFace))
            if hasFt:
                pieces_list.append(PieceSettings(cc[1], rr[0], make_sides(settings, settings.X, settings.Z, ftTabInfo, ftTabbed), ftFace))
        elif settings.layout == Layout.THREE_PIECE:  # 3 Piece Layout
            rr = deepcopy([row0, row1y])
            cc = deepcopy([col0, col1z])
            if hasBk:
                pieces_list.append(PieceSettings(cc[1], rr[1], make_sides(settings, settings.X, settings.Z, bkTabInfo, bkTabbed), bkFace))
            if hasLt:
                pieces_list.append(PieceSettings(cc[0], rr[0], make_sides(settings, settings.Z, settings.Y, ltTabInfo, ltTabbed), ltFace))
            if hasBm:
                pieces_list.append(PieceSettings(cc[1], rr[0], make_sides(settings, settings.X, settings.Y, bmTabInfo, bmTabbed), bmFace))
        elif settings.layout == Layout.INLINE_COMPACT:  # Inline(compact) Layout
            rr = deepcopy([row0])
            cc = deepcopy([col0, col1x, col2xx, col3xxz, col4, col5])
            if not hasTp:
                # remove col0, shift others left by X
                reduceOffsets(cc, 0, 1, 0, 0)
            if not hasBm:
                reduceOffsets(cc, 1, 1, 0, 0)
            if not hasLt:
                reduceOffsets(cc, 2, 0, 0, 1)
            if not hasRt:
                reduceOffsets(cc, 3, 0, 0, 1)
            if not hasBk:
                reduceOffsets(cc, 4, 1, 0, 0)
            if hasBk:
                pieces_list.append(PieceSettings(cc[4], rr[0], make_sides(settings, settings.X, settings.Z, bkTabInfo, bkTabbed), bkFace))
            if hasLt:
                pieces_list.append(PieceSettings(cc[2], rr[0], make_sides(settings, settings.Z, settings.Y, ltTabInfo, ltTabbed), ltFace))
            if hasTp:
                pieces_list.append(PieceSettings(cc[0], rr[0], make_sides(settings, settings.X, settings.Y, tpTabInfo, tpTabbed), tpFace))
            if hasBm:
                pieces_list.append(PieceSettings(cc[1], rr[0], make_sides(settings, settings.X, settings.Y, bmTabInfo, bmTabbed), bmFace))
            if hasRt:
                pieces_list.append(PieceSettings(cc[3], rr[0], make_sides(settings, settings.Z, settings.Y, rtTabInfo, rtTabbed), rtFace))
            if hasFt:
                pieces_list.append(PieceSettings(cc[5], rr[0], make_sides(settings, settings.X, settings.Z, ftTabInfo, ftTabbed), ftFace))

        # Handle Schroff settings if needed
        schroff_settings = None
        if settings.schroff:
            schroff_settings = SchroffSettings(
                rows=settings.rows,
                rail_height=settings.rail_height,
                row_centre_spacing=self.svg.unittouu(str(122.5) + settings.unit),
                row_spacing=settings.row_spacing,
                rail_mount_depth=settings.rail_mount_depth,
                rail_mount_centre_offset=settings.rail_mount_centre_offset,
                rail_mount_radius=settings.rail_mount_radius
            )

        return BoxConfiguration(
            schroff_settings=schroff_settings,
            faces=faces,
            tabs=tabs,
            pieces=pieces_list
        )

    def generate_pieces(self, config: BoxConfiguration, settings: BoxSettings) -> None:
        """Generate and draw all pieces based on the configuration"""

        groups = []

        # Calculate divider spacing and hole flags once for the entire box
        xspacing = (settings.X - settings.thickness) / (settings.div_y + 1)
        yspacing = (settings.Y - settings.thickness) / (settings.div_x + 1)
        # For divider intersections: X dividers need holes for Y dividers, Y dividers need holes for X dividers
        divider_x_holes = settings.div_y > 0  # X dividers need holes if there are Y dividers
        divider_y_holes = settings.div_x > 0  # Y dividers need holes if there are X dividers

        for idx, piece in enumerate(config.pieces):  # generate and draw each piece of the box
            (xs, xx, xy, xz) = piece.rootx
            (ys, yx, yy, yz) = piece.rooty
            x = (
                xs * settings.spacing + xx * settings.X + xy * settings.Y + xz * settings.Z + settings.initOffsetX
            )  # root x co-ord for piece
            y = (
                ys * settings.spacing + yx * settings.X + yy * settings.Y + yz * settings.Z + settings.initOffsetY
            )  # root y co-ord for piece
            dx = piece.dx
            dy = piece.dy
            # Use new sides list
            sides = piece.sides
            # Sides: [A, B, C, D]
            aSide, bSide, cSide, dSide = sides
            faceType = piece.faceType

            # Already extracted above from Side objects
            xholes = faceType != FaceType.ZY
            yholes = faceType != FaceType.XZ
            wall = faceType != FaceType.XY
            floor = faceType == FaceType.XY

            railholes = faceType == FaceType.ZY

            group = self.newGroup(idPrefix="piece")
            self.svg.get_current_layer().add(group)
            groups.append(group)

            if settings.schroff and railholes and config.schroff_settings:
                schroff = config.schroff_settings
                log(f"rail holes enabled on piece {idx} at ({x + settings.thickness}, {y + settings.thickness})")
                log(f"abcd = ({aSide.is_male},{bSide.is_male},{cSide.is_male},{dSide.is_male})")
                log(f"dxdy = ({dx},{dy})")
                rhxoffset = schroff.rail_mount_depth + settings.thickness
                if idx == 1:
                    rhx = x + rhxoffset
                elif idx == 3:
                    rhx = x - rhxoffset + dx
                else:
                    rhx = 0
                log(f"rhxoffset = {rhxoffset}, rhx= {rhx}")
                rystart = y + (schroff.rail_height / 2) + settings.thickness
                if schroff.rows == 1:
                    log(f"just one row this time, rystart = {rystart}")
                    rh1y = rystart + schroff.rail_mount_centre_offset
                    rh2y = rh1y + (schroff.row_centre_spacing - schroff.rail_mount_centre_offset)
                    group.add(
                        self.newCirclePath(
                            schroff.rail_mount_radius, (rhx, rh1y), settings.line_thickness))
                    group.add(
                        self.newCirclePath(
                            schroff.rail_mount_radius, (rhx, rh2y), settings.line_thickness))
                else:
                    for n in range(0, schroff.rows):
                        log(f"drawing row {n + 1}, rystart = {rystart}")
                        # if holes are offset (eg. Vector T-strut rails), they should be offset
                        # toward each other, ie. toward the centreline of the
                        # Schroff row
                        rh1y = rystart + schroff.rail_mount_centre_offset
                        rh2y = rh1y + schroff.row_centre_spacing - schroff.rail_mount_centre_offset
                        group.add(
                            self.newCirclePath(
                                schroff.rail_mount_radius, (rhx, rh1y), settings.line_thickness))
                        group.add(
                            self.newCirclePath(
                                schroff.rail_mount_radius, (rhx, rh2y), settings.line_thickness))
                        rystart += schroff.row_centre_spacing + schroff.row_spacing + schroff.rail_height

            # generate and draw the sides of each piece
            # Side A
            self.render_side(
                group,
                (x, y),
                aSide,
                False,
                ((self.keydivfloor or wall) and (self.keydivwalls or floor) and aSide.has_tabs and yholes)
                * settings.div_x,
                yspacing,
            )
            # Side B
            self.render_side(
                group,
                (x, y),
                bSide,
                False,
                ((self.keydivfloor or wall) and (self.keydivwalls or floor) and bSide.has_tabs and xholes)
                * settings.div_y,
                xspacing,
            )
            # Side C
            self.render_side(
                group,
                (x, y),
                cSide,
                False,
                ((self.keydivfloor or wall) and (self.keydivwalls or floor) and not aSide.has_tabs and cSide.has_tabs and yholes)
                * settings.div_x,
                yspacing,
            )
            # Side D
            self.render_side(
                group,
                (x, y),
                dSide,
                False,
                ((self.keydivfloor or wall) and (self.keydivwalls or floor) and not bSide.has_tabs and dSide.has_tabs and xholes)
                * settings.div_y,
                xspacing,
            )

            if idx == 0:
                # remove tabs from dividers if not required
                aSide, bSide, cSide, dSide = deepcopy([aSide, bSide, cSide, dSide])
                if not self.keydivfloor:
                    aSide.is_male = cSide.is_male = 1
                    aSide.has_tabs = cSide.has_tabs = 0
                if not self.keydivwalls:
                    bSide.is_male = dSide.is_male = 1
                    bSide.has_tabs = dSide.has_tabs = 0

                y = 4 * settings.spacing + 1 * settings.Y + 2 * settings.Z  # root y co-ord for piece
                for n in range(0, settings.div_x):  # generate X dividers
                    subGroup = self.newGroup(idPrefix="xdivider")
                    self.svg.get_current_layer().add(subGroup)
                    groups.append(subGroup)
                    x = n * (settings.spacing + settings.X) + settings.spacing # root x co-ord for piece

                    # Side A
                    self.render_side(
                        subGroup,
                        (x, y),
                        aSide,
                        True
                    )
                    # Side B
                    self.render_side(
                        subGroup,
                        (x, y),
                        bSide,
                        True,
                        settings.div_y * divider_x_holes,
                        xspacing,
                    )
                    # Side C
                    self.render_side(
                        subGroup,
                        (x, y),
                        cSide,
                        True,
                    )
                    # Side D
                    self.render_side(
                        subGroup,
                        (x, y),
                        dSide,
                        True
                    )
            elif idx == 1:
                # remove tabs from dividers if not required
                aSide, bSide, cSide, dSide = deepcopy([aSide, bSide, cSide, dSide])
                if not self.keydivwalls:
                    aSide.is_male = cSide.is_male = 1
                    aSide.has_tabs = cSide.has_tabs = 0
                if not self.keydivfloor:
                    bSide.is_male = dSide.is_male = 1
                    bSide.has_tabs = dSide.has_tabs = 0

                y = 5 * settings.spacing + 1 * settings.Y + 3 * settings.Z  # root y co-ord for piece
                for n in range(0, settings.div_y):  # generate Y dividers
                    subGroup = self.newGroup(idPrefix="ydivider")
                    self.svg.get_current_layer().add(subGroup)
                    groups.append(subGroup)
                    x = n * (settings.spacing + settings.Z)  # root x co-ord for piece
                    # Side A
                    self.render_side(
                        subGroup,
                        (x, y),
                        aSide,
                        True,
                        settings.div_x * divider_y_holes,
                        yspacing,
                    )
                    # Side B
                    self.render_side(
                        subGroup,
                        (x, y),
                        bSide,
                        True
                    )
                    # Side C
                    self.render_side(
                        subGroup,
                        (x, y),
                        cSide,
                        True
                    )
                    # Side D
                    self.render_side(
                        subGroup,
                        (x, y),
                        dSide,
                        True
                    )

        # All pieces drawn, now optimize the paths if required
        if self.options.optimize:
            self.optimizePieces(groups)

    def effect(self) -> None:
        if self.cli:
            self.options.input_file = None

        # Step 1: Parse options into settings
        settings = self.parse_options_to_settings()

        # Store values needed for other methods
        self.dimpleHeight = settings.dimple_height
        self.dimpleLength = settings.dimple_length
        self.dogbone = settings.dogbone
        self.keydivwalls = settings.keydiv_walls
        self.keydivfloor = settings.keydiv_floor

        # Step 2: Parse settings into complete configuration with pieces
        config = self.parse_settings_to_configuration(settings)

        # Add comments and metadata to SVG
        svg = self.document.getroot()
        layer = svg.get_current_layer()

        # Allow hiding version for testing purposes
        if self.version:
            layer.add(inkex.etree.Comment(f" Generated by BoxMaker version {self.version} "))
            layer.add(inkex.etree.Comment(f" {settings} "))
            layer.add(inkex.etree.Element('metadata', text=f"createArgs={self.cli_args}"))

        # Step 3: Generate and draw all pieces
        self.generate_pieces(config, settings)

        # Fix outer canvas size
        adjust_canvas(svg)

    def optimizePieces(self, groups) -> None:
        # Step 1: Combine paths to form the outer boundary
        skip_elements = []
        for group in groups:
            paths = [child for child in group if isinstance(child, inkex.PathElement)]

            for path_element in paths:
                path = path_element.path
                path_last = path[-1]

                if isinstance(path_last, inkex.paths.ZoneClose):
                    continue  # Path is already closed

                skip_elements.append(path_element)

                for other_element in paths:
                    if other_element in skip_elements:
                        continue

                    other_path = other_element.path

                    if isinstance(other_path[-1], inkex.paths.ZoneClose):
                        continue  # Path is already closed

                    other_first = other_path[0]

                    if (other_first.x == path_last.x and other_first.y == path_last.y):
                        new_id = min(path_element.get_id(), other_element.get_id())
                        path_element.path = path + other_path[1:]
                        group.remove(other_element)
                        path_element.set_id(new_id)
                        skip_elements.append(other_element)

                        # Update step for next iteration
                        path = path_element.path
                        path_last = path[-1]

            # List updated, refresh
            paths = [child for child in group if isinstance(child, inkex.PathElement)]

            # Step 2: Close the the paths, if not already closed
            for path_element in paths:
                if path[-1].letter in "zZ":
                    continue

                path = path_element.path
                path.close()
                path_element.path = path

            # Step 3: Remove unneeded generated nodes (duplicates and intermediates on h/v lines)
            for path_element in paths:
                path = path_element.path

                simplified_path = []
                prev = None  # Previous point
                current_dir = None  # Current direction

                for segment in path:
                    if isinstance(segment, inkex.paths.ZoneClose):
                        simplified_path.append(segment)
                        continue

                    if isinstance(segment, inkex.paths.Line):
                        if prev is not None:
                            dx = round(segment.x - prev.x, 8)
                            dy = round(segment.y - prev.y, 8)

                            if dx == 0 and dy == 0:
                                continue  # Skip node

                            # Determine the direction
                            direction = (
                                0 if dx == 0 else math.copysign(1, dx),
                                0 if dy == 0 else math.copysign(1, dy),
                            )

                            if (dx == 0 or dy == 0) and direction == current_dir:
                                # Skip redundant points on straight lines
                                # Replace the last point with the current point
                                simplified_path[-1] = segment
                            else:
                                simplified_path.append(segment)
                                current_dir = direction
                        else:
                            simplified_path.append(segment)
                        prev = segment
                    else:
                        simplified_path.append(segment)
                        prev = None
                        current_dir = None
                        direction = None

                path_element.path = simplified_path

            # Step 4: Include gaps in the panel outline by removing them from the panel path
            if len(paths) > 1:
                panel = paths[0]
                panel_poly = path_to_polygon(panel.path)

                if panel_poly is not None:
                    # Collect all holes as polygons
                    holes = []
                    for candidate in paths[1:]:
                        poly = path_to_polygon(candidate.path)
                        if poly is not None:
                            group.remove(candidate)
                            holes.append(poly)

                    # Subtract holes from panel
                    result = panel_poly.difference(unary_union(holes))

                    # Replace panel path with result
                    panel.path = polygon_to_path(result)

            # Last step: If the group now just contains one path, remove
            # the group around this path
            if len(group) == 1:
                parent = group.getparent()
                group_id = group.get_id()
                item = group[0]
                parent.replace(group, item)
                item.set_id(group_id)

    def dimpleStr(
        self,
        tabVector: float,
        vectorX: float,
        vectorY: float,
        dirX: int,
        dirY: int,
        notDirX: bool,
        notDirY: bool,
        ddir: int,
        isTab: bool
    ) -> inkex.Path:
        ds = []
        if not isTab:
            ddir = -ddir
        if self.dimpleHeight > 0 and tabVector != 0:
            if tabVector > 0:
                dimpleStart = (tabVector - self.dimpleLength) / 2 - self.dimpleHeight
                tabSgn = 1
            else:
                dimpleStart = (tabVector + self.dimpleLength) / 2 + self.dimpleHeight
                tabSgn = -1
            Vxd = vectorX + notDirX * dimpleStart
            Vyd = vectorY + notDirY * dimpleStart
            ds.append(Line(Vxd, Vyd))
            Vxd = Vxd + (tabSgn * notDirX - ddir * dirX) * self.dimpleHeight
            Vyd = Vyd + (tabSgn * notDirY - ddir * dirY) * self.dimpleHeight
            ds.append(Line(Vxd, Vyd))
            Vxd = Vxd + tabSgn * notDirX * self.dimpleLength
            Vyd = Vyd + tabSgn * notDirY * self.dimpleLength
            ds.append(Line(Vxd, Vyd))
            Vxd = Vxd + (tabSgn * notDirX + ddir * dirX) * self.dimpleHeight
            Vyd = Vyd + (tabSgn * notDirY + ddir * dirY) * self.dimpleHeight
            ds.append(Line(Vxd, Vyd))
        return ds

    def makeId(self, prefix: str | None) -> str:
        """Generate a new unique ID with the given prefix."""

        prefix = prefix if prefix is not None else 'id'

        if prefix not in self.nextId:
            id = self.nextId[prefix] = 1
        else:
            id = self.nextId[prefix] + 1
            self.nextId[prefix] += 1

        return f"{prefix}_{id:03d}"

    def newGroup(self, idPrefix: str | None = 'group') -> inkex.Group:
        """Create a new group with a unique ID and return it."""
        panelId = self.makeId(idPrefix)
        group = inkex.Group(id=panelId)
        return group

    def newLinePath(self,
                    XYstring: Path,
                    linethickness: float,
                    idPrefix : str | None = 'line') -> inkex.PathElement:
        """Create a new line path element with the given path data and line thickness."""
        line = inkex.PathElement(id=self.makeId(idPrefix))
        line.style = {
            "stroke": "#000000",
            "stroke-width": str(round(linethickness, 8)),
            "fill": "none",
        }
        line.path = XYstring
        # inkex.etree.SubElement(parent, inkex.addNS('path','svg'), drw)
        return line

    # jslee - shamelessly adapted from sample code on below Inkscape wiki page 2015-07-28
    # http://wiki.inkscape.org/wiki/index.php/Generating_objects_from_extensions
    def newCirclePath(self,
                      r: float,
                      c: tuple[float, float],
                      linethickness: float,
                      idPrefix: str | None = 'circle') -> inkex.PathElement:
        """Create a new circle path element with the given radius, center, and line thickness."""
        (cx, cy) = c
        log("putting circle at (%d,%d)" % (cx, cy))
        circle = inkex.PathElement.arc((cx, cy), r, id=self.makeId(idPrefix))
        circle.style = {
            "stroke": "#000000",
            "stroke-width": str(round(linethickness, 8)),
            "fill": "none",
        }
        return circle

    def create_divider_hole(
        self,
        side: Side,
        vectorX: float,
        vectorY: float,
        dividerSpacing: float,
        dividerNumber: int,
        holeLenX: float,
        holeLenY: float,
        secondVec: float,
        first: float,
        startOffsetX: float = 0,
        tabDivision: int = 1
    ) -> inkex.PathElement:
        """Create a hole for divider tabs to key into side walls"""
        dirX, dirY = side.direction
        notDirX = dirX == 0
        notDirY = dirY == 0
        halfkerf = side.kerf / 2
        
        Dx = (
            vectorX
            + -dirY * dividerSpacing * dividerNumber
            + (halfkerf if notDirX else 0)
            + ((dirX * halfkerf - first * dirX) if self.dogbone else 0)
        )
        Dy = (
            vectorY
            + dirX * dividerSpacing * dividerNumber
            - (halfkerf if notDirY else 0)
            + ((dirY * halfkerf - first * dirY) if self.dogbone else 0)
        )
        
        # Adjust for XY symmetric tab style
        if tabDivision == 1 and side.tab_symmetry == TabSymmetry.XY_SYMMETRIC:
            Dx += startOffsetX * side.thickness
            
        h = inkex.Path()
        h.append(Move(Dx, Dy))
        Dx = Dx + holeLenX
        Dy = Dy + holeLenY
        h.append(Line(Dx, Dy))
        Dx = Dx + notDirX * (secondVec - side.kerf)
        Dy = Dy + notDirY * (secondVec + side.kerf)
        h.append(Line(Dx, Dy))
        Dx = Dx - holeLenX
        Dy = Dy - holeLenY
        h.append(Line(Dx, Dy))
        Dx = Dx - notDirX * (secondVec - side.kerf)
        Dy = Dy - notDirY * (secondVec + side.kerf)
        h.append(Line(Dx, Dy))
        h.append(ZoneClose())
        
        return self.newLinePath(h, side.line_thickness, idPrefix="hole")

    def create_divider_slot(
        self,
        side: Side,
        vectorX: float,
        vectorY: float,
        dividerSpacing: float,
        dividerNumber: int,
        dividerEdgeOffsetX: float,
        dividerEdgeOffsetY: float,
        first: float
    ) -> inkex.PathElement:
        """Create slots for dividers to slot into each other"""
        dirX, dirY = side.direction
        notDirX = dirX == 0
        notDirY = dirY == 0
        halfkerf = side.kerf / 2
        
        Dx = (
            vectorX
            + -dirY * dividerSpacing * dividerNumber
            - dividerEdgeOffsetX
            + notDirX * halfkerf
        )
        Dy = (
            vectorY
            + dirX * dividerSpacing * dividerNumber
            - dividerEdgeOffsetY
            + notDirY * halfkerf
        )
        
        h = inkex.Path()
        h.append(Move(Dx, Dy))
        Dx = Dx + dirX * (first + side.length / 2)
        Dy = Dy + dirY * (first + side.length / 2)
        h.append(Line(Dx, Dy))
        Dx = Dx + notDirX * (side.thickness - side.kerf)
        Dy = Dy + notDirY * (side.thickness - side.kerf)
        h.append(Line(Dx, Dy))
        Dx = Dx - dirX * (first + side.length / 2)
        Dy = Dy - dirY * (first + side.length / 2)
        h.append(Line(Dx, Dy))
        Dx = Dx - notDirX * (side.thickness - side.kerf)
        Dy = Dy - notDirY * (side.thickness - side.kerf)
        h.append(Line(Dx, Dy))
        h.append(ZoneClose())
        
        return self.newLinePath(h, side.line_thickness, idPrefix="slot")

    def create_final_divider_hole(
        self,
        side: Side,
        vectorX: float,
        vectorY: float,
        dividerSpacing: float,
        dividerNumber: int,
        firstholelenX: float,
        firstholelenY: float,
        dividerEdgeOffsetY: float,
        first: float
    ) -> inkex.PathElement:
        """Create final holes for divider joints in side walls"""
        dirX, dirY = side.direction
        notDirX = dirX == 0
        notDirY = dirY == 0
        halfkerf = side.kerf / 2
        
        Dx = (
            vectorX
            + -dirY * dividerSpacing * dividerNumber
            + notDirX * halfkerf
            + dirX * self.dogbone * halfkerf
            - self.dogbone * first * dirX
        )
        Dy = (
            vectorY
            + dirX * dividerSpacing * dividerNumber
            - dividerEdgeOffsetY
            + notDirY * halfkerf
        )
        
        h = inkex.Path()
        h.append(Move(Dx, Dy))
        Dx = Dx + firstholelenX
        Dy = Dy + firstholelenY
        h.append(Line(Dx, Dy))
        Dx = Dx + notDirX * (side.thickness - side.kerf)
        Dy = Dy + notDirY * (side.thickness - side.kerf)
        h.append(Line(Dx, Dy))
        Dx = Dx - firstholelenX
        Dy = Dy - firstholelenY
        h.append(Line(Dx, Dy))
        Dx = Dx - notDirX * (side.thickness - side.kerf)
        Dy = Dy - notDirY * (side.thickness - side.kerf)
        h.append(Line(Dx, Dy))
        h.append(ZoneClose())
        
        return self.newLinePath(h, side.line_thickness, idPrefix="hole")

    def render_side(
        self,
        group: inkex.Group,
        root: tuple[float, float],
        side: Side,
        isDivider: bool = False,
        numDividers: int = 0,
        dividerSpacing: float = 0,
    ) -> None:
        """Draw one side of a piece, with tabs or holes as required"""

        direction = side.direction
        dirX, dirY = direction

        # TODO: Use rotation matrix to simplify this logic
        # All values are booleans so results will be -1, 0, or 1
        
        offs_cases = {
            SideEnum.A: [(0,0), (side.prev.is_male, side.is_male), (-side.next.is_male, side.is_male)],
            SideEnum.B: [(side.prev.length, 0), (-side.is_male, side.prev.is_male), (-side.is_male, -side.next.is_male)],
            SideEnum.C: [(side.length, side.prev.length), (-side.prev.is_male, -side.is_male), (side.next.is_male, -side.is_male)],
            SideEnum.D: [(0, side.length), (side.is_male, -side.prev.is_male), (side.is_male, side.next.is_male)],
        }
        root_offs, startOffset, endOffset = offs_cases[side.name]

        startOffsetX, startOffsetY = startOffset
        endOffsetX, endOffsetY = endOffset
        length = side.length

        isTab = side.is_male
        notTab = not isTab
        thickness = side.thickness


        if side.has_tabs:
            # Calculate direction
            tabVec = thickness if (direction == (1, 0) or direction == (0, -1)) != isTab else -thickness
        else:
            tabVec = 0

        prevTab = side.prev.has_tabs

        kerf = side.kerf
        halfkerf = kerf / 2
        line_thickness = side.line_thickness

        sidePath = self.newLinePath('', line_thickness, idPrefix="side")
        nodes = [sidePath]

        divisions = side.divisions
        gapWidth = side.gap_width
        tabWidth = side.tab_width
        first = side.first

        firstholelenX = 0
        firstholelenY = 0
        s = inkex.Path()
        h = []
        firstVec = 0
        secondVec = tabVec
        dividerEdgeOffsetX = dividerEdgeOffsetY = thickness
        notDirX = dirX == 0  # used to select operation on x or y
        notDirY = dirY == 0
        if side.tab_symmetry == TabSymmetry.ROTATE_SYMMETRIC:
            dividerEdgeOffsetX = dirX * thickness
            # dividerEdgeOffsetY = ;
            vectorX = (0 if dirX and prevTab else startOffsetX * thickness)
            vectorY = (0 if dirY and prevTab else startOffsetY * thickness)
            s.append(Move(vectorX, vectorY))
            vectorX = (startOffsetX if startOffsetX else dirX) * thickness
            vectorY = (startOffsetY if startOffsetY else dirY) * thickness
            if notDirX and tabVec:
                endOffsetX = 0
            if notDirY and tabVec:
                endOffsetY = 0
        else:
            (vectorX, vectorY) = (
                startOffsetX * thickness,
                startOffsetY * thickness,
            )
            dividerEdgeOffsetX = dirY * thickness
            dividerEdgeOffsetY = dirX * thickness
            s.append(Move(vectorX, vectorY))
            if notDirX:
                vectorY = 0  # set correct line start for tab generation
            if notDirY:
                vectorX = 0

        # generate line as tab or hole using:
        #   last co-ord:Vx,Vy ; tab dir:tabVec  ; direction:dirx,diry ; thickness:thickness
        #   divisions:divs ; gap width:gapWidth ; tab width:tabWidth

        for tabDivision in range(1, int(divisions)):
            # draw holes for divider tabs to key into side walls
            if (((tabDivision % 2) > 0) != (not isTab)) and numDividers > 0 and not isDivider:
                w = gapWidth if isTab else tabWidth
                if tabDivision == 1 and side.tab_symmetry == TabSymmetry.XY_SYMMETRIC:
                    w -= startOffsetX * thickness
                holeLenX = dirX * (w + first) + (firstVec if notDirX else 0)
                holeLenY = dirY * (w + first) + (firstVec if notDirY else 0)
                if first:
                    firstholelenX = holeLenX
                    firstholelenY = holeLenY
                for dividerNumber in range(1, int(numDividers) + 1):
                    hole = self.create_divider_hole(
                        side, vectorX, vectorY, dividerSpacing, dividerNumber,
                        holeLenX, holeLenY, secondVec, first, startOffsetX, tabDivision
                    )
                    nodes.append(hole)
            if tabDivision % 2:
                if (
                    tabDivision == 1 and numDividers > 0 and isDivider
                ):  # draw slots for dividers to slot into each other
                    for dividerNumber in range(1, int(numDividers) + 1):
                        slot = self.create_divider_slot(
                            side, vectorX, vectorY, dividerSpacing, dividerNumber,
                            dividerEdgeOffsetX, dividerEdgeOffsetY, first
                        )
                        nodes.append(slot)
                # draw the gap
                vectorX += (
                    dirX
                    * (
                        gapWidth
                        + (first if not (isTab and self.dogbone) else 0)
                        + self.dogbone * kerf * isTab
                    )
                    + notDirX * firstVec
                )
                vectorY += (
                    dirY
                    * (
                        gapWidth
                        + (first if not (isTab and self.dogbone) else 0)
                        + (kerf if self.dogbone and isTab else 0)
                    )
                    + notDirY * firstVec
                )
                s.append(Line(vectorX, vectorY))
                if self.dogbone and isTab:
                    vectorX -= dirX * halfkerf
                    vectorY -= dirY * halfkerf
                    s.append(Line(vectorX, vectorY))
                # draw the starting edge of the tab
                s += self.dimpleStr(
                    secondVec, vectorX, vectorY, dirX, dirY, notDirX, notDirY, 1, isTab
                )
                vectorX += notDirX * secondVec
                vectorY += notDirY * secondVec
                s.append(Line(vectorX, vectorY))
                if self.dogbone and notTab:
                    vectorX -= dirX * halfkerf
                    vectorY -= dirY * halfkerf
                    s.append(Line(vectorX, vectorY))

            else:
                # draw the tab
                vectorX += dirX * (tabWidth + self.dogbone *
                                   kerf * notTab) + notDirX * firstVec
                vectorY += dirY * (tabWidth + self.dogbone *
                                   kerf * notTab) + notDirY * firstVec
                s.append(Line(vectorX, vectorY))
                if self.dogbone and notTab:
                    vectorX -= dirX * halfkerf
                    vectorY -= dirY * halfkerf
                    s.append(Line(vectorX, vectorY))
                # draw the ending edge of the tab
                s += self.dimpleStr(
                    secondVec, vectorX, vectorY, dirX, dirY, notDirX, notDirY, -1, isTab
                )
                vectorX += notDirX * secondVec
                vectorY += notDirY * secondVec
                s.append(Line(vectorX, vectorY))
                if self.dogbone and isTab:
                    vectorX -= dirX * halfkerf
                    vectorY -= dirY * halfkerf
                    s.append(Line(vectorX, vectorY))
            (secondVec, firstVec) = (-secondVec, -firstVec)  # swap tab direction
            first = 0

        # finish the line off
        s.append(Line(
            endOffsetX * thickness + dirX * length,
            endOffsetY * thickness + dirY * length
        ))

        sidePath.path = s

        # draw last for divider joints in side walls
        if isTab and numDividers > 0 and side.tab_symmetry == 0 and not isDivider:
            # BH: Find out if this is the right correction. Without it the with_dividers_keyed_all.svg test is broken
            if firstholelenX == 0 and firstholelenY == 0:
                firstholelenX += (holeLenX - thickness) if holeLenX else 0
                firstholelenY += (holeLenY - thickness) if holeLenY else 0

            for dividerNumber in range(1, int(numDividers) + 1):
                hole = self.create_final_divider_hole(
                    side, vectorX, vectorY, dividerSpacing, dividerNumber,
                    firstholelenX, firstholelenY, dividerEdgeOffsetY, first
                )
                nodes.append(hole)

        rootX, rootY = root
        rootX += root_offs[0]
        rootY += root_offs[1]
        for i in nodes:
            i.path = i.path.translate(rootX, rootY)
            group.add(i)
