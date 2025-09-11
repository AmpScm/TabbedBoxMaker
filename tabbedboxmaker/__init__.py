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

from inkex.paths.lines import Line, Move

from copy import deepcopy
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

from tabbedboxmaker.enums import BoxType, Layout, TabSymmetry, DividerKeying
from tabbedboxmaker.InkexShapely import path_to_polygon, polygon_to_path
from tabbedboxmaker.__about__ import __version__ as BOXMAKER_VERSION

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
            dest="equal",
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
            help="Tab type: regular or self.dogbone",
        )
        self.arg_parser.add_argument(
            "--dimpleheight",
            action="store",
            type=float,
            dest="dimpleheight",
            default=0,
            help="Tab Dimple Height",
        )
        self.arg_parser.add_argument(
            "--dimplelength",
            action="store",
            type=float,
            dest="dimplelength",
            default=0,
            help="Tab Dimple Tip Length",
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
            dest="div_l",
            default=25,
            help="Dividers (Length axis)",
        )
        self.arg_parser.add_argument(
            "--div_w",
            action="store",
            type=int,
            dest="div_w",
            default=25,
            help="Dividers (Width axis)",
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

    def effect(self) -> None:
        if self.cli:
            self.options.input_file = None
        # Get access to main SVG document element and get its dimensions.
        svg = self.document.getroot()

        # Get the attributes:
        widthDoc = self.svg.unittouu(svg.get("width"))
        heightDoc = self.svg.unittouu(svg.get("height"))

        # Get script's option values.
        hairline = self.options.hairline
        unit = self.options.unit
        inside = self.options.inside
        schroff = self.options.schroff
        self.kerf = self.svg.unittouu(str(self.options.kerf) + unit)

        # Set the line self.thickness
        if hairline:
            self.linethickness = self.svg.unittouu("0.002in")
        else:
            self.linethickness = 1

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
        self.thickness = self.svg.unittouu(str(self.options.thickness) + unit)
        self.nomTab = self.svg.unittouu(str(self.options.tab) + unit)
        self.equalTabs = self.options.equal
        self.tabSymmetry = self.options.tabsymmetry
        self.dimpleHeight = self.svg.unittouu(str(self.options.dimpleheight) + unit)
        self.dimpleLength = self.svg.unittouu(str(self.options.dimplelength) + unit)
        self.dogbone = 1 if self.options.tabtype == 1 else 0
        layout = self.options.style
        spacing = self.svg.unittouu(str(self.options.spacing) + unit)
        boxtype : BoxType = self.options.boxtype
        divx = self.options.div_l
        divy = self.options.div_w
        self.keydivwalls = self.options.keydiv in [DividerKeying.ALL_SIDES, DividerKeying.WALLS]
        self.keydivfloor = self.options.keydiv in [DividerKeying.ALL_SIDES , DividerKeying.FLOOR_CEILING]
        initOffsetX = 0
        initOffsetY = 0

        if inside:  # if inside dimension selected correct values to outside dimension
            X += self.thickness * 2
            Y += self.thickness * 2
            Z += self.thickness * 2

        # check input values mainly to avoid python errors
        # TODO restrict values to *correct* solutions
        # TODO restrict divisions to logical values
        error = False

        if min(X, Y, Z) == 0:
            inkex.errormsg(_("Error: Dimensions must be non zero"))
            error = True
        if max(X, Y, Z) > max(widthDoc, heightDoc) * 10:  # crude test
            inkex.errormsg(_("Error: Dimensions Too Large"))
            error = True
        if min(X, Y, Z) < 3 * self.nomTab:
            inkex.errormsg(_("Error: Tab size too large"))
            error = True
        if self.nomTab < self.thickness:
            inkex.errormsg(_("Error: Tab size too small"))
            error = True
        if self.thickness == 0:
            inkex.errormsg(_("Error: self.thickness is zero"))
            error = True
        if self.thickness > min(X, Y, Z) / 3:  # crude test
            inkex.errormsg(_("Error: Material too thick"))
            error = True
        if self.kerf > min(X, Y, Z) / 3:  # crude test
            inkex.errormsg(_("Error: self.kerf too large"))
            error = True
        if spacing > max(X, Y, Z) * 10:  # crude test
            inkex.errormsg(_("Error: Spacing too large"))
            error = True
        if spacing < self.kerf:
            inkex.errormsg(_("Error: Spacing too small"))
            error = True

        if error:
            exit(1)

        layer = svg.get_current_layer()
        if self.version: # Allow hiding version for testing purposes
            layer.add(inkex.etree.Comment(f" Generated by BoxMaker version {self.version} "))
            layer.add(inkex.etree.Comment(f" {self.options} "))
            layer.add(inkex.etree.Element('metadata', text=f"createArgs={self.cli_args}"))

        # For code spacing consistency, we use two-character abbreviations for the six box faces,
        # where each abbreviation is the first and last letter of the face name:
        # tp=top, bm=bottom, ft=front, bk=back, lt=left, rt=right

        # Determine which faces the box has based on the box type
        hasTp = hasBm = hasFt = hasBk = hasLt = hasRt = True
        if boxtype == BoxType.ONE_SIDE_OPEN:
            hasTp = False
        elif boxtype == BoxType.TWO_SIDES_OPEN:
            hasTp = hasFt = False
        elif boxtype == BoxType.THREE_SIDES_OPEN:
            hasTp = hasFt = hasRt = False
        elif boxtype == BoxType.OPPOSITE_ENDS_OPEN:
            hasTp = hasBm = False
        elif boxtype == BoxType.TWO_PANELS_ONLY:
            hasTp = hasFt = hasBk = hasRt = False
        # else boxtype==1, full box, has all sides

        # Determine where the tabs go based on the tab style
        if self.tabSymmetry == 2:  # Antisymmetric (deprecated)
            tpTabInfo = 0b0110
            bmTabInfo = 0b1100
            ltTabInfo = 0b1100
            rtTabInfo = 0b0110
            ftTabInfo = 0b1100
            bkTabInfo = 0b1001
        elif self.tabSymmetry == 1:  # Rotationally symmetric (Waffle-blocks)
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
            if inside:
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
        tpFace = 1
        bmFace = 1
        ftFace = 2
        bkFace = 2
        ltFace = 3
        rtFace = 3

        def reduceOffsets(aa : dict[int, tuple[int, int, int, int]], start : int, dx : int, dy : int, dz : int):
            for ix in range(start + 1, len(aa)):
                (s, x, y, z) = aa[ix]
                aa[ix] = (s - 1, x - dx, y - dy, z - dz)

        # note first two pieces in each set are the X-divider template and
        # Y-divider template respectively
        pieces : list[tuple] = []
        if layout == 1:  # Diagramatic Layout
            rr = deepcopy([row0, row1z, row2])
            cc = deepcopy([col0, col1z, col2xz, col3xzz])
            if not hasFt:
                # remove row0, shift others up by Z
                reduceOffsets(rr, 0, 0, 0, 1)
            if not hasLt:
                reduceOffsets(cc, 0, 0, 0, 1)
            if not hasRt:
                reduceOffsets(cc, 2, 0, 0, 1)
            if hasBk:
                pieces.append([cc[1], rr[2], X, Z, bkTabInfo, bkTabbed, bkFace])
            if hasLt:
                pieces.append([cc[0], rr[1], Z, Y, ltTabInfo, ltTabbed, ltFace])
            if hasBm:
                pieces.append([cc[1], rr[1], X, Y, bmTabInfo, bmTabbed, bmFace])
            if hasRt:
                pieces.append([cc[2], rr[1], Z, Y, rtTabInfo, rtTabbed, rtFace])
            if hasTp:
                pieces.append([cc[3], rr[1], X, Y, tpTabInfo, tpTabbed, tpFace])
            if hasFt:
                pieces.append([cc[1], rr[0], X, Z, ftTabInfo, ftTabbed, ftFace])
        elif layout == 2:  # 3 Piece Layout
            rr = deepcopy([row0, row1y])
            cc = deepcopy([col0, col1z])
            if hasBk:
                pieces.append([cc[1], rr[1], X, Z, bkTabInfo, bkTabbed, bkFace])
            if hasLt:
                pieces.append([cc[0], rr[0], Z, Y, ltTabInfo, ltTabbed, ltFace])
            if hasBm:
                pieces.append([cc[1], rr[0], X, Y, bmTabInfo, bmTabbed, bmFace])
        elif layout == 3:  # Inline(compact) Layout
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
                pieces.append([cc[4], rr[0], X, Z, bkTabInfo, bkTabbed, bkFace])
            if hasLt:
                pieces.append([cc[2], rr[0], Z, Y, ltTabInfo, ltTabbed, ltFace])
            if hasTp:
                pieces.append([cc[0], rr[0], X, Y, tpTabInfo, tpTabbed, tpFace])
            if hasBm:
                pieces.append([cc[1], rr[0], X, Y, bmTabInfo, bmTabbed, bmFace])
            if hasRt:
                pieces.append([cc[3], rr[0], Z, Y, rtTabInfo, rtTabbed, rtFace])
            if hasFt:
                pieces.append([cc[5], rr[0], X, Z, ftTabInfo, ftTabbed, ftFace])

        for idx, piece in enumerate(pieces):  # generate and draw each piece of the box
            (xs, xx, xy, xz) = piece[0]
            (ys, yx, yy, yz) = piece[1]
            x = (
                xs * spacing + xx * X + xy * Y + xz * Z + initOffsetX
            )  # root x co-ord for piece
            y = (
                ys * spacing + yx * X + yy * Y + yz * Z + initOffsetY
            )  # root y co-ord for piece
            dx = piece[2]
            dy = piece[3]
            tabs = piece[4]
            aIsMale = 0 < (tabs >> 3 & 1)
            bIsMale = 0 < (tabs >> 2 & 1)
            cIsMale = 0 < (tabs >> 1 & 1)
            dIsMale = 0 < (tabs & 1)  # extract tab status for each side
            tabbed = piece[5]
            aHasTabs = 0 < (tabbed >> 3 & 1)
            bHasTabs = 0 < (tabbed >> 2 & 1)
            cHasTabs = 0 < (tabbed >> 1 & 1)
            dHasTabs = 0 < (tabbed & 1)  # extract tabbed flag for each side
            xspacing = (X - self.thickness) / (divy + 1)
            yspacing = (Y - self.thickness) / (divx + 1)
            xholes = piece[6] < 3
            yholes = piece[6] != 2
            wall = piece[6] > 1
            floor = piece[6] == 1
            railholes = piece[6] == 3

            group = self.newGroup(idPrefix="piece")
            self.svg.get_current_layer().add(group)
            groups = [group]

            if schroff and railholes:
                log(
                    "rail holes enabled on piece %d at (%d, %d)"
                    % (idx, x + self.thickness, y + self.thickness)
                )
                log("abcd = (%d,%d,%d,%d)" % (aIsMale, bIsMale, cIsMale, dIsMale))
                log("dxdy = (%d,%d)" % (dx, dy))
                rhxoffset = rail_mount_depth + self.thickness
                if idx == 1:
                    rhx = x + rhxoffset
                elif idx == 3:
                    rhx = x - rhxoffset + dx
                else:
                    rhx = 0
                log("rhxoffset = %d, rhx= %d" % (rhxoffset, rhx))
                rystart = y + (rail_height / 2) + self.thickness
                if rows == 1:
                    log("just one row this time, rystart = %d" % rystart)
                    rh1y = rystart + rail_mount_centre_offset
                    rh2y = rh1y + (row_centre_spacing - rail_mount_centre_offset)
                    group.add(
                        self.newCirclePath(
                            rail_mount_radius, (rhx, rh1y), self.linethickness))
                    group.add(
                        self.newCirclePath(
                            rail_mount_radius, (rhx, rh2y), self.linethickness))
                else:
                    for n in range(0, rows):
                        log("drawing row %d, rystart = %d" % (n + 1, rystart))
                        # if holes are offset (eg. Vector T-strut rails), they should be offset
                        # toward each other, ie. toward the centreline of the
                        # Schroff row
                        rh1y = rystart + rail_mount_centre_offset
                        rh2y = rh1y + row_centre_spacing - rail_mount_centre_offset
                        group.add(
                            self.newCirclePath(
                                rail_mount_radius, (rhx, rh1y), self.linethickness))
                        group.add(
                            self.newCirclePath(
                                rail_mount_radius, (rhx, rh2y), self.linethickness))
                        rystart += row_centre_spacing + row_spacing + rail_height

            # generate and draw the sides of each piece
            # Side A
            self.side(
                group,
                (x, y),
                (dIsMale, aIsMale),
                (-bIsMale, aIsMale),
                aHasTabs,
                dHasTabs,
                dx,
                (1, 0),
                aIsMale,
                False,
                ((self.keydivfloor or wall) and (self.keydivwalls or floor) and aHasTabs and yholes)
                * divx,
                yspacing,
            )
            # Side B
            self.side(
                group,
                (x + dx, y),
                (-bIsMale, aIsMale),
                (-bIsMale, -cIsMale),
                bHasTabs,
                aHasTabs,
                dy,
                (0, 1),
                bIsMale,
                False,
                ((self.keydivfloor or wall) and (self.keydivwalls or floor) and bHasTabs and xholes)
                * divy,
                xspacing,
            )
            # Side C
            self.side(
                group,
                (x + dx, y + dy),
                (-bIsMale, -cIsMale),
                (dIsMale, -cIsMale),
                cHasTabs,
                bHasTabs,
                dx,
                (-1, 0),
                cIsMale,
                False,
                ((self.keydivfloor or wall) and (self.keydivwalls or floor) and not aHasTabs and cHasTabs and yholes)
                * divx,
                yspacing,
            )
            # Side D
            self.side(
                group,
                (x, y + dy),
                (dIsMale, -cIsMale),
                (dIsMale, aIsMale),
                dHasTabs,
                cHasTabs,
                dy,
                (0, -1),
                dIsMale,
                False,
                ((self.keydivfloor or wall) and (self.keydivwalls or floor) and not bHasTabs and dHasTabs and xholes)
                * divy,
                xspacing,
            )

            if idx == 0:
                # remove tabs from dividers if not required
                if not self.keydivfloor:
                    aIsMale = cIsMale = 1
                    aHasTabs = cHasTabs = 0
                if not self.keydivwalls:
                    bIsMale = dIsMale = 1
                    bHasTabs = dHasTabs = 0

                y = 4 * spacing + 1 * Y + 2 * Z  # root y co-ord for piece
                for n in range(0, divx):  # generate X dividers
                    subGroup = self.newGroup(idPrefix="xdivider")
                    self.svg.get_current_layer().add(subGroup)
                    groups.append(subGroup)
                    x = n * (spacing + X)  # root x co-ord for piece

                    # Side A
                    self.side(
                        subGroup,
                        (x, y),
                        (dIsMale, aIsMale),
                        (-bIsMale, aIsMale),
                        self.keydivfloor and aHasTabs,
                        dHasTabs,
                        dx,
                        (1, 0),
                        aIsMale,
                        True
                    )
                    # Side B
                    self.side(
                        subGroup,
                        (x + dx, y),
                        (-bIsMale, aIsMale),
                        (-bIsMale, -cIsMale),
                        self.keydivwalls and bHasTabs,
                        aHasTabs,
                        dy,
                        (0, 1),
                        bIsMale,
                        True,
                        divy * xholes,
                        xspacing,
                    )
                    # Side C
                    self.side(
                        subGroup,
                        (x + dx, y + dy),
                        (-bIsMale, -cIsMale),
                        (dIsMale, -cIsMale),
                        self.keydivfloor and cHasTabs,
                        bHasTabs,
                        dx,
                        (-1, 0),
                        cIsMale,
                        True,
                    )
                    # Side D
                    self.side(
                        subGroup,
                        (x, y + dy),
                        (dIsMale, -cIsMale),
                        (dIsMale, aIsMale),
                        self.keydivwalls * dHasTabs,
                        cHasTabs,
                        dy,
                        (0, -1),
                        dIsMale,
                        True
                    )
            elif idx == 1:
                y = 5 * spacing + 1 * Y + 3 * Z  # root y co-ord for piece
                for n in range(0, divy):  # generate Y dividers
                    subGroup = self.newGroup(idPrefix="ydivider")
                    self.svg.get_current_layer().add(subGroup)
                    groups.append(subGroup)
                    x = n * (spacing + Z)  # root x co-ord for piece
                    # Side A
                    self.side(
                        subGroup,
                        (x, y),
                        (dIsMale, aIsMale),
                        (-bIsMale, aIsMale),
                        self.keydivwalls and aHasTabs,
                        dHasTabs,
                        dx,
                        (1, 0),
                        aIsMale,
                        True,
                        divx * yholes,
                        yspacing,
                    )
                    # Side B
                    self.side(
                        subGroup,
                        (x + dx, y),
                        (-bIsMale, aIsMale),
                        (-bIsMale, -cIsMale),
                        self.keydivfloor and bHasTabs,
                        aHasTabs,
                        dy,
                        (0, 1),
                        bIsMale,
                        True
                    )
                    # Side C
                    self.side(
                        subGroup,
                        (x + dx, y + dy),
                        (-bIsMale, -cIsMale),
                        (dIsMale, -cIsMale),
                        self.keydivwalls and cHasTabs,
                        bHasTabs,
                        dx,
                        (-1, 0),
                        cIsMale,
                        True
                    )
                    # Side D
                    self.side(
                        subGroup,
                        (x, y + dy),
                        (dIsMale, -cIsMale),
                        (dIsMale, aIsMale),
                        self.keydivfloor and dHasTabs,
                        cHasTabs,
                        dy,
                        (0, -1),
                        dIsMale,
                        True
                    )

            # All pieces drawn, now optimize the paths if required
            if self.options.optimize:
                self.optimizePieces(groups)

        # Fix outer canvas size
        self.fixCanvas()

    def optimizePieces(self, groups) -> None:
        # Step 1: Combine paths to form the outer boundary
        skip_elements = []
        for group in groups:
            paths = [ child for child in group if isinstance(child, inkex.PathElement) ]

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

                    if (other_first.x == path_last.x and other_first.y == path_last.y ):
                        new_id = min(path_element.get_id(), other_element.get_id())
                        path_element.path = path + other_path[1:]
                        group.remove(other_element)
                        path_element.set_id(new_id)
                        skip_elements.append(other_element)

                        # Update step for next iteration
                        path = path_element.path
                        path_last = path[-1]

            # List updated, refresh
            paths = [ child for child in group  if isinstance(child, inkex.PathElement) ]

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

    def fixCanvas(self) -> None:
        """ Adjust the SVG canvas to fit the content """

        unit = self.options.unit
        svg = self.document.getroot()
        layer = svg.get_current_layer()
        # Collect all bboxes
        all_bboxes = []
        for el in layer.descendants():
            if isinstance(el, inkex.PathElement):
                all_bboxes.append(el.bounding_box())

        if all_bboxes:
            minx = min(min(b.left for b in all_bboxes), 0)
            miny = min(min(b.top for b in all_bboxes), 0)
            maxx = max(b.right for b in all_bboxes)
            maxy = max(b.bottom for b in all_bboxes)
            width = maxx - minx
            height = maxy - miny
            svg.set('width', fstr(width) + unit)
            svg.set('height', fstr(height) + unit)
            svg.set('viewBox', f"{fstr(minx)} {fstr(miny)} {fstr(width)} {fstr(height)}")

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


    def makeId(self,
               prefix: str | None) -> str:

        prefix = prefix if prefix is not None else 'id'

        if prefix not in self.nextId:
            id = self.nextId[prefix] = 1
        else:
            id = self.nextId[prefix] + 1
            self.nextId[prefix] += 1

        return f"{prefix}_{id:03d}"


    def newGroup(self,
                 idPrefix: str | None = 'group') -> inkex.Group:
        # Create a new group and add element created from line string
        panelId = self.makeId(idPrefix)
        group = inkex.Group(id=panelId)
        return group

    def newLinePath(self,
                    XYstring: str,
                    linethickness: float,
                    idPrefix : str | None = 'line') -> inkex.PathElement:
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
        (cx, cy) = c
        log("putting circle at (%d,%d)" % (cx, cy))
        circle = inkex.PathElement.arc((cx, cy), r, id=self.makeId(idPrefix))
        circle.style = {
            "stroke": "#000000",
            "stroke-width": str(linethickness),
            "fill": "none",
        }
        return circle

    def side(
        self,
        group: inkex.Group,
        root: tuple[float, float],
        startOffset: tuple[float, float],
        endOffset: tuple[float, float],
        tabVec: float,
        prevTab: bool,
        length: float,
        direction: tuple[int, int],
        isTab: bool,
        isDivider: bool=False,
        numDividers: int=0,
        dividerSpacing: float=0,
    ) -> str:
        rootX, rootY = root
        startOffsetX, startOffsetY = startOffset
        endOffsetX, endOffsetY = endOffset
        dirX, dirY = direction
        notTab = not isTab

        if tabVec:
            # Calculate direction
            tabVec = self.thickness if (direction == (1,0) or direction == (0,-1)) != isTab else -self.thickness

        halfkerf = self.kerf / 2

        sidePath = self.newLinePath('', self.linethickness, idPrefix="side")
        nodes = [sidePath]

        if self.tabSymmetry == 1:  # waffle-block style rotationally symmetric tabs
            divisions = int((length - 2 * self.thickness) / self.nomTab)
            if divisions % 2:
                divisions += 1  # make divs even
            divisions = float(divisions)
            tabs = divisions / 2  # tabs for side
        else:
            divisions = int(length / self.nomTab)
            if not divisions % 2:
                divisions -= 1  # make divs odd
            divisions = float(divisions)
            tabs = (divisions - 1) / 2  # tabs for side

        if self.tabSymmetry == 1:  # waffle-block style rotationally symmetric tabs
            gapWidth = tabWidth = (length - 2 * self.thickness) / divisions
        elif self.equalTabs:
            gapWidth = tabWidth = length / divisions
        else:
            tabWidth = self.nomTab
            gapWidth = (length - tabs * self.nomTab) / (divisions - tabs)

        if isTab:  # self.kerf correction
            gapWidth -= self.kerf
            tabWidth += self.kerf
            first = halfkerf
        else:
            gapWidth += self.kerf
            tabWidth -= self.kerf
            first = -halfkerf
        firstholelenX = 0
        firstholelenY = 0
        s = []
        h = []
        firstVec = 0
        secondVec = tabVec
        dividerEdgeOffsetX = dividerEdgeOffsetY = self.thickness
        notDirX = dirX == 0  # used to select operation on x or y
        notDirY = dirY == 0
        if self.tabSymmetry == 1:
            dividerEdgeOffsetX = dirX * self.thickness
            # dividerEdgeOffsetY = ;
            vectorX = (0 if dirX and prevTab else startOffsetX * self.thickness)
            vectorY = (0 if dirY and prevTab else startOffsetY * self.thickness)
            s.append(Move(vectorX, vectorY))
            vectorX = (startOffsetX if startOffsetX else dirX) * self.thickness
            vectorY = (startOffsetY if startOffsetY else dirY) * self.thickness
            if notDirX and tabVec:
                endOffsetX = 0
            if notDirY and tabVec:
                endOffsetY = 0
        else:
            (vectorX, vectorY) = (
                startOffsetX * self.thickness,
                startOffsetY * self.thickness,
            )
            dividerEdgeOffsetX = dirY * self.thickness
            dividerEdgeOffsetY = dirX * self.thickness
            s.append(Move(vectorX, vectorY))
            if notDirX:
                vectorY = 0  # set correct line start for tab generation
            if notDirY:
                vectorX = 0

        # generate line as tab or hole using:
        #   last co-ord:Vx,Vy ; tab dir:tabVec  ; direction:dirx,diry ; self.thickness:self.thickness
        #   divisions:divs ; gap width:gapWidth ; tab width:tabWidth

        for tabDivision in range(1, int(divisions)):
            # draw holes for divider tabs to key into side walls
            if (((tabDivision % 2) > 0) != (not isTab)) and numDividers > 0 and not isDivider:
                w = gapWidth if isTab else tabWidth
                if tabDivision == 1 and self.tabSymmetry == 0:
                    w -= startOffsetX * self.thickness
                holeLenX = dirX * (w + first) + (firstVec if notDirX else 0)
                holeLenY = dirY * (w + first) + (firstVec if notDirY else 0)
                if first:
                    firstholelenX = holeLenX
                    firstholelenY = holeLenY
                for dividerNumber in range(1, int(numDividers) + 1):
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
                    if tabDivision == 1 and self.tabSymmetry == TabSymmetry.XY_SYMMETRIC:
                        Dx += startOffsetX * self.thickness
                    h = []
                    h.append(Move(Dx, Dy))
                    Dx = Dx + holeLenX
                    Dy = Dy + holeLenY
                    h.append(Line(Dx, Dy))
                    Dx = Dx + notDirX * (secondVec - self.kerf)
                    Dy = Dy + notDirY * (secondVec + self.kerf)
                    h.append(Line(Dx, Dy))
                    Dx = Dx - holeLenX
                    Dy = Dy - holeLenY
                    h.append(Line(Dx, Dy))
                    Dx = Dx - notDirX * (secondVec - self.kerf)
                    Dy = Dy - notDirY * (secondVec + self.kerf)
                    h.append(Line(Dx, Dy))
                    nodes.append(self.newLinePath(h, self.linethickness, idPrefix="hole"))
            if tabDivision % 2:
                if (
                    tabDivision == 1 and numDividers > 0 and isDivider
                ):  # draw slots for dividers to slot into each other
                    for dividerNumber in range(1, int(numDividers) + 1):
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
                        h = []
                        h.append(Move(Dx, Dy))
                        Dx = Dx + dirX * (first + length / 2)
                        Dy = Dy + dirY * (first + length / 2)
                        h.append(Line(Dx, Dy))
                        Dx = Dx + notDirX * (self.thickness - self.kerf)
                        Dy = Dy + notDirY * (self.thickness - self.kerf)
                        h.append(Line(Dx, Dy))
                        Dx = Dx - dirX * (first + length / 2)
                        Dy = Dy - dirY * (first + length / 2)
                        h.append(Line(Dx, Dy))
                        Dx = Dx - notDirX * (self.thickness - self.kerf)
                        Dy = Dy - notDirY * (self.thickness - self.kerf)
                        h.append(Line(Dx, Dy))
                        nodes.append(self.newLinePath(h, self.linethickness, idPrefix="slot"))
                # draw the gap
                vectorX += (
                    dirX
                    * (
                        gapWidth
                        + (first if not (isTab and self.dogbone) else 0)
                        + self.dogbone * self.kerf * isTab
                    )
                    + notDirX * firstVec
                )
                vectorY += (
                    dirY
                    * (
                        gapWidth
                        + (first if not (isTab and self.dogbone) else 0)
                        + (self.kerf if self.dogbone and isTab else 0)
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
                                   self.kerf * notTab) + notDirX * firstVec
                vectorY += dirY * (tabWidth + self.dogbone *
                                   self.kerf * notTab) + notDirY * firstVec
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
            endOffsetX * self.thickness + dirX * length,
            endOffsetY * self.thickness + dirY * length
        ))

        # draw last for divider joints in side walls
        if isTab and numDividers > 0 and self.tabSymmetry == 0 and not isDivider:
            # BH: Find out if this is the right correction. Without it the with_dividers_keyed_all.svg test is broken
            firstholelenX += (holeLenX - self.thickness) if holeLenX else 0
            firstholelenY += (holeLenY - self.thickness) if holeLenY else 0

            for dividerNumber in range(1, int(numDividers) + 1):
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
                h = []
                h.append(Move(Dx, Dy))
                Dx = Dx + firstholelenX
                Dy = Dy + firstholelenY
                h.append(Line(Dx, Dy))
                Dx = Dx + notDirX * (self.thickness - self.kerf)
                Dy = Dy + notDirY * (self.thickness - self.kerf)
                h.append(Line(Dx, Dy))
                Dx = Dx - firstholelenX
                Dy = Dy - firstholelenY
                h.append(Line(Dx, Dy))
                Dx = Dx - notDirX * (self.thickness - self.kerf)
                Dy = Dy - notDirY * (self.thickness - self.kerf)
                h.append(Line(Dx, Dy))
                nodes.append(self.newLinePath(h, self.linethickness, idPrefix="hole"))

        sidePath.path =s

        for i in nodes:
            i.path = i.path.translate(rootX, rootY)
            group.add(i)
        return nodes
