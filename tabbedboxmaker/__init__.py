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

import os
import inkex
import gettext
from copy import deepcopy

_ = gettext.gettext

def log(text: str) -> None:
    if "SCHROFF_LOG" in os.environ:
        f = open(os.environ.get("SCHROFF_LOG"), "a")
        f.write(text + "\n")


def newGroup(canvas: inkex.Effect) -> inkex.Group:
    # Create a new group and add element created from line string
    panelId = canvas.svg.get_unique_id("panel")
    group = canvas.svg.get_current_layer().add(inkex.Group(id=panelId))
    return group


def getLine(XYstring: str,
            linethickness: float) -> inkex.PathElement:
    line = inkex.PathElement()
    line.style = {
        "stroke": "#000000",
        "stroke-width": str(linethickness),
        "fill": "none",
    }
    line.path = XYstring
    # inkex.etree.SubElement(parent, inkex.addNS('path','svg'), drw)
    return line


# jslee - shamelessly adapted from sample code on below Inkscape wiki page 2015-07-28
# http://wiki.inkscape.org/wiki/index.php/Generating_objects_from_extensions

def getCircle(r: float, c: tuple[float, float], linethickness: float) -> inkex.PathElement:
    (cx, cy) = c
    log("putting circle at (%d,%d)" % (cx, cy))
    circle = inkex.PathElement.arc((cx, cy), r)
    circle.style = {
        "stroke": "#000000",
        "stroke-width": str(linethickness),
        "fill": "none",
    }
    return circle

class BoxMaker(inkex.Effect):
    def __init__(self, cli: bool = False, schroff: bool = False):
        # Call the base class constructor.
        inkex.Effect.__init__(self)
        # Define options

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
        boxtype = self.options.boxtype
        divx = self.options.div_l
        divy = self.options.div_w
        self.keydivwalls = 0 if self.options.keydiv == 3 or self.options.keydiv == 1 else 1
        self.keydivfloor = 0 if self.options.keydiv == 3 or self.options.keydiv == 2 else 1
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
            exit()

        # For code spacing consistency, we use two-character abbreviations for the six box faces,
        # where each abbreviation is the first and last letter of the face name:
        # tp=top, bm=bottom, ft=front, bk=back, lt=left, rt=right

        # Determine which faces the box has based on the box type
        hasTp = hasBm = hasFt = hasBk = hasLt = hasRt = True
        if boxtype == 2:
            hasTp = False
        elif boxtype == 3:
            hasTp = hasFt = False
        elif boxtype == 4:
            hasTp = hasFt = hasRt = False
        elif boxtype == 5:
            hasTp = hasBm = False
        elif boxtype == 6:
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

        def fixTabBits(tabbed, tabInfo, bit):
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

        def reduceOffsets(aa, start, dx, dy, dz):
            for ix in range(start + 1, len(aa)):
                (s, x, y, z) = aa[ix]
                aa[ix] = (s - 1, x - dx, y - dy, z - dz)

        # note first two pieces in each set are the X-divider template and
        # Y-divider template respectively
        pieces = []
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
            a = tabs >> 3 & 1
            b = tabs >> 2 & 1
            c = tabs >> 1 & 1
            d = tabs & 1  # extract tab status for each side
            tabbed = piece[5]
            atabs = tabbed >> 3 & 1
            btabs = tabbed >> 2 & 1
            ctabs = tabbed >> 1 & 1
            dtabs = tabbed & 1  # extract tabbed flag for each side
            xspacing = (X - self.thickness) / (divy + 1)
            yspacing = (Y - self.thickness) / (divx + 1)
            xholes = 1 if piece[6] < 3 else 0
            yholes = 1 if piece[6] != 2 else 0
            wall = 1 if piece[6] > 1 else 0
            floor = 1 if piece[6] == 1 else 0
            railholes = 1 if piece[6] == 3 else 0

            group = newGroup(self)
            groups = [group]

            if schroff and railholes:
                log(
                    "rail holes enabled on piece %d at (%d, %d)"
                    % (idx, x + self.thickness, y + self.thickness)
                )
                log("abcd = (%d,%d,%d,%d)" % (a, b, c, d))
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
                    group.add(getCircle(rail_mount_radius, (rhx, rh1y), self.linethickness))
                    group.add(getCircle(rail_mount_radius, (rhx, rh2y), self.linethickness))
                else:
                    for n in range(0, rows):
                        log("drawing row %d, rystart = %d" % (n + 1, rystart))
                        # if holes are offset (eg. Vector T-strut rails), they should be offset
                        # toward each other, ie. toward the centreline of the
                        # Schroff row
                        rh1y = rystart + rail_mount_centre_offset
                        rh2y = rh1y + row_centre_spacing - rail_mount_centre_offset
                        group.add(getCircle(rail_mount_radius, (rhx, rh1y), self.linethickness))
                        group.add(getCircle(rail_mount_radius, (rhx, rh2y), self.linethickness))
                        rystart += row_centre_spacing + row_spacing + rail_height

            # generate and draw the sides of each piece
            self.side(
                group,
                (x, y),
                (d, a),
                (-b, a),
                atabs * (-self.thickness if a else self.thickness),
                dtabs,
                dx,
                (1, 0),
                a,
                # side a
                0,
                (self.keydivfloor | wall) * (self.keydivwalls | floor) * divx * yholes * atabs,
                yspacing,
            )
            self.side(
                group,
                (x + dx, y),
                (-b, a),
                (-b, -c),
                btabs * (self.thickness if b else -self.thickness),
                atabs,
                dy,
                (0, 1),
                # side b
                b,
                0,
                (self.keydivfloor | wall) * (self.keydivwalls | floor) * divy * xholes * btabs,
                xspacing,
            )
            if atabs:
                self.side(
                    group,
                    (x + dx, y + dy),
                    (-b, -c),
                    (d, -c),
                    ctabs *
                    # side c
                    (self.thickness if c else -self.thickness),
                    btabs,
                    dx,
                    (-1, 0),
                    c,
                    0,
                    0,
                    0,
                )
            else:
                self.side(
                    group,
                    (x + dx, y + dy),
                    (-b, -c),
                    (d, -c),
                    ctabs * (self.thickness if c else -self.thickness),
                    btabs,
                    dx,
                    # side c
                    (-1, 0),
                    c,
                    0,
                    (self.keydivfloor | wall)
                    * (self.keydivwalls | floor)
                    * divx
                    * yholes
                    * ctabs,
                    yspacing,
                )
            if btabs:
                self.side(
                    group,
                    (x, y + dy),
                    (d, -c),
                    (d, a),
                    dtabs *
                    # side d
                    (-self.thickness if d else self.thickness),
                    ctabs,
                    dy,
                    (0, -1),
                    d,
                    0,
                    0,
                    0,
                )
            else:
                self.side(
                    group,
                    (x, y + dy),
                    (d, -c),
                    (d, a),
                    dtabs * (-self.thickness if d else self.thickness),
                    ctabs,
                    dy,
                    (0, -1),
                    # side d
                    d,
                    0,
                    (self.keydivfloor | wall)
                    * (self.keydivwalls | floor)
                    * divy
                    * xholes
                    * dtabs,
                    xspacing,
                )

            if idx == 0:
                # remove tabs from dividers if not required
                if not self.keydivfloor:
                    a = c = 1
                    atabs = ctabs = 0
                if not self.keydivwalls:
                    b = d = 1
                    btabs = dtabs = 0

                y = 4 * spacing + 1 * Y + 2 * Z  # root y co-ord for piece
                for n in range(0, divx):  # generate X dividers
                    subGroup = newGroup(self)
                    groups.append(subGroup)
                    x = n * (spacing + X)  # root x co-ord for piece
                    self.side(
                        subGroup,
                        (x, y),
                        (d, a),
                        (-b, a),
                        self.keydivfloor * atabs * (-self.thickness if a else self.thickness),
                        dtabs,
                        dx,
                        (1, 0),
                        a,
                        1,
                        0,
                        0,
                    )  # side a
                    self.side(
                        subGroup,
                        (x + dx, y),
                        (-b, a),
                        (-b, -c),
                        self.keydivwalls
                        * btabs
                        * (
                            self.thickness
                            if b
                            else -
                            # side b
                            self.thickness
                        ),
                        atabs,
                        dy,
                        (0, 1),
                        b,
                        1,
                        divy * xholes,
                        xspacing,
                    )
                    self.side(
                        subGroup,
                        (x + dx, y + dy),
                        (-b, -c),
                        (d, -c),
                        self.keydivfloor * ctabs *
                        # side c
                        (self.thickness if c else -self.thickness),
                        btabs,
                        dx,
                        (-1, 0),
                        c,
                        1,
                        0,
                        0,
                    )
                    self.side(
                        subGroup,
                        (x, y + dy),
                        (d, -c),
                        (d, a),
                        self.keydivwalls * dtabs *
                        # side d
                        (-self.thickness if d else self.thickness),
                        ctabs,
                        dy,
                        (0, -1),
                        d,
                        1,
                        0,
                        0,
                    )
            elif idx == 1:
                y = 5 * spacing + 1 * Y + 3 * Z  # root y co-ord for piece
                for n in range(0, divy):  # generate Y dividers
                    subGroup = newGroup(self)
                    groups.append(subGroup)
                    x = n * (spacing + Z)  # root x co-ord for piece
                    self.side(
                        subGroup,
                        (x, y),
                        (d, a),
                        (-b, a),
                        # side a
                        self.keydivwalls * atabs * (-self.thickness if a else self.thickness),
                        dtabs,
                        dx,
                        (1, 0),
                        a,
                        1,
                        divx * yholes,
                        yspacing,
                    )
                    self.side(
                        subGroup,
                        (x + dx, y),
                        (-b, a),
                        (-b, -c),
                        self.keydivfloor
                        * btabs  # side b
                        * (self.thickness if b else -self.thickness),
                        atabs,
                        dy,
                        (0, 1),
                        b,
                        1,
                        0,
                        0,
                    )
                    self.side(
                        subGroup,
                        (x + dx, y + dy),
                        (-b, -c),
                        (d, -c),
                        self.keydivwalls * ctabs *
                        # side c
                        (self.thickness if c else -self.thickness),
                        btabs,
                        dx,
                        (-1, 0),
                        c,
                        1,
                        0,
                        0,
                    )
                    self.side(
                        subGroup,
                        (x, y + dy),
                        (d, -c),
                        (d, a),
                        self.keydivfloor * dtabs *
                        # side d
                        (-self.thickness if d else self.thickness),
                        ctabs,
                        dy,
                        (0, -1),
                        d,
                        1,
                        0,
                        0,
                    )

            if self.options.optimize:
                # Step 1: Combine paths to form the outer boundary
                for group in groups:
                    for path_element in [
                        child
                        for child in group.descendants()
                        if isinstance(child, inkex.PathElement)
                    ]:
                        path = inkex.Path(path_element.path)

                        if path[-1].letter in "zZ":
                            continue  # Path is already closed

                        path_first = path[0]
                        path_last = path[-1]

                        for other_element in [
                            child
                            for child in group.descendants()
                            if isinstance(child, inkex.PathElement)
                        ]:
                            if other_element == path_element:
                                continue

                            other_path = inkex.Path(other_element.path)

                            if other_path[-1].letter in "zZ":
                                continue

                            other_first = other_path[0]
                            other_last = other_path[-1]

                            if (
                                other_first.x == path_last.x
                                and other_first.y == path_last.y
                            ):
                                other_element.path = str(path + other_path[1:])
                                group.remove(path_element)
                                break
                            elif (
                                other_last.x == path_first.x
                                and other_last.y == path_last.y
                            ):
                                other_element.path = str(other_path + path[1:])
                                group.remove(path_element)
                                break

                        # Try to combine next path
                        last_path_element = path_element

                    # Step 2: Close the first (outline) path, if not already
                    # closed
                    last_path_element = [
                        child
                        for child in group.descendants()
                        if isinstance(child, inkex.PathElement)
                    ][0]
                    path = inkex.Path(last_path_element.path)
                    if (
                        path[-1].letter not in "zZ"
                    ):  # Check if the last command is not 'Z'
                        path.close()  # Append a close path command
                        # Update the element's path
                        last_path_element.path = str(path)

                    # Step 3: Remove unneeded generated nodes (duplicates and
                    # intermediates on h/v lines)
                    for path_element in group.descendants():
                        if not isinstance(path_element, inkex.PathElement):
                            continue

                        path = inkex.Path(path_element.path)

                        simplified_path = []
                        prev = None  # Previous point
                        current_dir = None  # Current direction ('h' or 'v')

                        for segment in path:
                            if isinstance(segment, inkex.paths.ZoneClose):
                                simplified_path.append(segment)
                                continue

                            if isinstance(segment, inkex.paths.Line):
                                if prev is not None:
                                    dx = segment.x - prev.x
                                    dy = segment.y - prev.y

                                    if dx == 0 and dy == 0:
                                        continue  # Skip node

                                    # Determine the direction
                                    direction = (
                                        "h" if dy == 0 else "v" if dx == 0 else None
                                    )

                                    # Skip redundant points on straight lines
                                    if direction == current_dir:
                                        # Replace the last point in
                                        # simplified_path
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

                        path_element.path = str(inkex.Path(simplified_path))

                    # Ok, now we still have a group containing as first element the panel and then optionally some gaps that
                    # should be cut out of the panel

                    # Last step: If the group now just contains one path, remove
                    # the group around this path
                    if len(group) == 1:
                        parent = group.getparent()

                        parent.append(group[0])
                        parent.remove(group)

    def dimpleStr(
            self,
            tabVector: float,
            vectorX: float,
            vectorY: float,
            dirX: int,
            dirY: int,
            dirxN: int,
            diryN: int,
            ddir: int,
            isTab: bool
        ) -> str:
            ds = ""
            if not isTab:
                ddir = -ddir
            if self.dimpleHeight > 0 and tabVector != 0:
                if tabVector > 0:
                    dimpleStart = (tabVector - self.dimpleLength) / 2 - self.dimpleHeight
                    tabSgn = 1
                else:
                    dimpleStart = (tabVector + self.dimpleLength) / 2 + self.dimpleHeight
                    tabSgn = -1
                Vxd = vectorX + dirxN * dimpleStart
                Vyd = vectorY + diryN * dimpleStart
                ds += "L " + str(Vxd) + "," + str(Vyd) + " "
                Vxd = Vxd + (tabSgn * dirxN - ddir * dirX) * self.dimpleHeight
                Vyd = Vyd + (tabSgn * diryN - ddir * dirY) * self.dimpleHeight
                ds += "L " + str(Vxd) + "," + str(Vyd) + " "
                Vxd = Vxd + tabSgn * dirxN * self.dimpleLength
                Vyd = Vyd + tabSgn * diryN * self.dimpleLength
                ds += "L " + str(Vxd) + "," + str(Vyd) + " "
                Vxd = Vxd + (tabSgn * dirxN + ddir * dirX) * self.dimpleHeight
                Vyd = Vyd + (tabSgn * diryN + ddir * dirY) * self.dimpleHeight
                ds += "L " + str(Vxd) + "," + str(Vyd) + " "
            return ds

    def side(
            self,
            group: inkex.Group,
            root: tuple[float, float],
            startOffset: tuple[float, float],
            endOffset: tuple[float, float],
            tabVec: float,
            prevTab: int,
            length: float,
            direction: tuple[int, int],
            isTab: bool,
            isDivider: bool,
            numDividers: int,
            dividerSpacing: float,
        ) -> str:
            rootX, rootY = root
            startOffsetX, startOffsetY = startOffset
            endOffsetX, endOffsetY = endOffset
            dirX, dirY = direction
            notTab = not isTab

            halfkerf = self.kerf / 2


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
            notDirX = 0 if dirX else 1  # used to select operation on x or y
            notDirY = 0 if dirY else 1
            if self.tabSymmetry == 1:
                dividerEdgeOffsetX = dirX * self.thickness
                # dividerEdgeOffsetY = ;
                vectorX = rootX + (0 if dirX and prevTab else startOffsetX * self.thickness)
                vectorY = rootY + (0 if dirY and prevTab else startOffsetY * self.thickness)
                s = "M " + str(vectorX) + "," + str(vectorY) + " "
                vectorX = rootX + (startOffsetX if startOffsetX else dirX) * self.thickness
                vectorY = rootY + (startOffsetY if startOffsetY else dirY) * self.thickness
                if notDirX and tabVec:
                    endOffsetX = 0
                if notDirY and tabVec:
                    endOffsetY = 0
            else:
                (vectorX, vectorY) = (
                    rootX + startOffsetX * self.thickness,
                    rootY + startOffsetY * self.thickness,
                )
                dividerEdgeOffsetX = dirY * self.thickness
                dividerEdgeOffsetY = dirX * self.thickness
                s = "M " + str(vectorX) + "," + str(vectorY) + " "
                if notDirX:
                    vectorY = rootY  # set correct line start for tab generation
                if notDirY:
                    vectorX = rootX

            # generate line as tab or hole using:
            #   last co-ord:Vx,Vy ; tab dir:tabVec  ; direction:dirx,diry ; self.thickness:self.thickness
            #   divisions:divs ; gap width:gapWidth ; tab width:tabWidth

            for tabDivision in range(1, int(divisions)):
                # draw holes for divider tabs to key into side walls
                if (((tabDivision % 2) > 0) != (not isTab)) and numDividers > 0 and not isDivider:
                    w = gapWidth if isTab else tabWidth
                    if tabDivision == 1 and self.tabSymmetry == 0:
                        w -= startOffsetX * self.thickness
                    holeLenX = dirX * w + notDirX * firstVec + first * dirX
                    holeLenY = dirY * w + notDirY * firstVec + first * dirY
                    if first:
                        firstholelenX = holeLenX
                        firstholelenY = holeLenY
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
                            - notDirY * halfkerf
                            + dirY * self.dogbone * halfkerf
                            - self.dogbone * first * dirY
                        )
                        if tabDivision == 1 and self.tabSymmetry == 0:
                            Dx += startOffsetX * self.thickness
                        h = "M " + str(Dx) + "," + str(Dy) + " "
                        Dx = Dx + holeLenX
                        Dy = Dy + holeLenY
                        h += "L " + str(Dx) + "," + str(Dy) + " "
                        Dx = Dx + notDirX * (secondVec - self.kerf)
                        Dy = Dy + notDirY * (secondVec + self.kerf)
                        h += "L " + str(Dx) + "," + str(Dy) + " "
                        Dx = Dx - holeLenX
                        Dy = Dy - holeLenY
                        h += "L " + str(Dx) + "," + str(Dy) + " "
                        Dx = Dx - notDirX * (secondVec - self.kerf)
                        Dy = Dy - notDirY * (secondVec + self.kerf)
                        h += "L " + str(Dx) + "," + str(Dy) + " "
                        group.add(getLine(h, self.linethickness))
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
                            h = "M " + str(Dx) + "," + str(Dy) + " "
                            Dx = Dx + dirX * (first + length / 2)
                            Dy = Dy + dirY * (first + length / 2)
                            h += "L " + str(Dx) + "," + str(Dy) + " "
                            Dx = Dx + notDirX * (self.thickness - self.kerf)
                            Dy = Dy + notDirY * (self.thickness - self.kerf)
                            h += "L " + str(Dx) + "," + str(Dy) + " "
                            Dx = Dx - dirX * (first + length / 2)
                            Dy = Dy - dirY * (first + length / 2)
                            h += "L " + str(Dx) + "," + str(Dy) + " "
                            Dx = Dx - notDirX * (self.thickness - self.kerf)
                            Dy = Dy - notDirY * (self.thickness - self.kerf)
                            h += "L " + str(Dx) + "," + str(Dy) + " "
                            group.add(getLine(h, self.linethickness))
                    # draw the gap
                    vectorX += (
                        dirX
                        * (
                            gapWidth
                            + (first if not(isTab and self.dogbone) else 0)
                            + self.dogbone * self.kerf * isTab
                        )
                        + notDirX * firstVec
                    )
                    vectorY += (
                        dirY
                        * (
                            gapWidth
                            + (first if not(isTab and self.dogbone) else 0)
                            + (self.kerf if self.dogbone and isTab else 0)
                        )
                        + notDirY * firstVec
                    )
                    s += "L " + str(vectorX) + "," + str(vectorY) + " "
                    if self.dogbone and isTab:
                        vectorX -= dirX * halfkerf
                        vectorY -= dirY * halfkerf
                        s += "L " + str(vectorX) + "," + str(vectorY) + " "
                    # draw the starting edge of the tab
                    s += self.dimpleStr(
                        secondVec, vectorX, vectorY, dirX, dirY, notDirX, notDirY, 1, isTab
                    )
                    vectorX += notDirX * secondVec
                    vectorY += notDirY * secondVec
                    s += "L " + str(vectorX) + "," + str(vectorY) + " "
                    if self.dogbone and notTab:
                        vectorX -= dirX * halfkerf
                        vectorY -= dirY * halfkerf
                        s += "L " + str(vectorX) + "," + str(vectorY) + " "

                else:
                    # draw the tab
                    vectorX += dirX * (tabWidth + self.dogbone * self.kerf * notTab) + notDirX * firstVec
                    vectorY += dirY * (tabWidth + self.dogbone * self.kerf * notTab) + notDirY * firstVec
                    s += "L " + str(vectorX) + "," + str(vectorY) + " "
                    if self.dogbone and notTab:
                        vectorX -= dirX * halfkerf
                        vectorY -= dirY * halfkerf
                        s += "L " + str(vectorX) + "," + str(vectorY) + " "
                    # draw the ending edge of the tab
                    s += self.dimpleStr(
                        secondVec, vectorX, vectorY, dirX, dirY, notDirX, notDirY, -1, isTab
                    )
                    vectorX += notDirX * secondVec
                    vectorY += notDirY * secondVec
                    s += "L " + str(vectorX) + "," + str(vectorY) + " "
                    if self.dogbone and isTab:
                        vectorX -= dirX * halfkerf
                        vectorY -= dirY * halfkerf
                        s += "L " + str(vectorX) + "," + str(vectorY) + " "
                (secondVec, firstVec) = (-secondVec, -firstVec)  # swap tab direction
                first = 0

            # finish the line off
            s += (
                "L "
                + str(rootX + endOffsetX * self.thickness + dirX * length)
                + ","
                + str(rootY + endOffsetY * self.thickness + dirY * length)
                + " "
            )

            # draw last for divider joints in side walls
            if isTab and numDividers > 0 and self.tabSymmetry == 0 and not isDivider:
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
                    h = "M " + str(Dx) + "," + str(Dy) + " "
                    Dx = Dx + firstholelenX
                    Dy = Dy + firstholelenY
                    h += "L " + str(Dx) + "," + str(Dy) + " "
                    Dx = Dx + notDirX * (self.thickness - self.kerf)
                    Dy = Dy + notDirY * (self.thickness - self.kerf)
                    h += "L " + str(Dx) + "," + str(Dy) + " "
                    Dx = Dx - firstholelenX
                    Dy = Dy - firstholelenY
                    h += "L " + str(Dx) + "," + str(Dy) + " "
                    Dx = Dx - notDirX * (self.thickness - self.kerf)
                    Dy = Dy - notDirY * (self.thickness - self.kerf)
                    h += "L " + str(Dx) + "," + str(Dy) + " "
                    group.add(getLine(h, self.linethickness))
            group.add(getLine(s, self.linethickness))
            return s
