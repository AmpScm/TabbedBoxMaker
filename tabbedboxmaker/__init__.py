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

class TabbedBoxMaker(inkex.Effect):
    nextId: dict[str, int]
    linethickness: float = 1
    thickness: float
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
    settings : BoxSettings


    def __init__(self, cli=True, schroff=False, inkscape=False):
        # Call the base class constructor.
        super().__init__()

        self.cli = cli
        self.schroff = schroff

        self.nextId = {}

        self._setup_arguments()


    def makeId(self, prefix: str | None) -> str:
        """Generate a new unique ID with the given prefix."""

        prefix = prefix if prefix is not None else "id"
        if prefix not in self.nextId:
            id = self.nextId[prefix] = 0

        self.nextId[prefix] = id = self.nextId[prefix] + 1

        return f"{prefix}_{id:03d}"


    def makeGroup(self, id="piece") -> inkex.Group:
        # Create a new group and add element created from line string
        group = inkex.Group(id=self.makeId(id))

        self.svg.get_current_layer().add(group)
        return group



    def makeLine(self, path , id : str = "line") -> inkex.PathElement:
        line = inkex.PathElement(id=self.makeId(id))
        line.style = { "stroke": "#000000", "stroke-width"  : str(self.linethickness), "fill": "none" }
        line.path = inkex.paths.Path(path)
        return line



    def makeCircle(self,r, c, id : str = "circle"):
        (cx, cy) = c
        log("putting circle at (%d,%d)" % (cx,cy))
        circle = inkex.PathElement.arc((cx, cy), r, id=self.makeId(id))
        circle.style = { "stroke": "#000000", "stroke-width": str(self.linethickness), "fill": "none" }
        return circle



    def _setup_arguments(self) -> None:
        """Define options"""

        if self.cli:
            # We don"t need an input file in CLI mode
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
            default=self.schroff,
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
            help="Line Thickness",
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
            "--div_l_spacing",
            action="store",
            type=str,
            dest="div_l_spacing",
            default="",
            help="Custom spacing for X-axis dividers (semicolon separated widths)",
        )
        self.arg_parser.add_argument(
            "--div_w_spacing",
            action="store",
            type=str,
            dest="div_w_spacing",
            default="",
            help="Custom spacing for Y-axis dividers (semicolon separated widths)",
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

        super().parse_arguments(args)
        self.cli_args = deepcopy(args)

        if self.cli and self.options.input_file is None:
            self.options.input_file = os.path.join(
                os.path.dirname(__file__), "blank.svg"
            )




    def effect(self) -> None:
        """Runs the effect. Public api"""
        svg = self.document.getroot()

        layer = svg.get_current_layer()
        layer.add(inkex.etree.Element("metadata", text=f"createArgs={self.cli_args}"))

        self._run_effect()

        adjust_canvas(svg, unit=self.options.unit)


    def parse_divider_spacing(self, spacing_str: str, unit: str, available_width: float,
                            thickness: float, num_dividers: int) -> list[float]:
        """Parse semicolon-separated spacing values and validate them"""
        if not spacing_str.strip():
            return []

        # Parse the spacing values (these represent section widths, not divider positions)
        try:
            values = [float(v.strip()) for v in spacing_str.split(';') if v.strip()]
        except ValueError as e:
            inkex.errormsg(f"Error: Invalid divider spacing format: {e}")
            exit(1)

        # Convert to document units
        values = [self.svg.unittouu(str(v) + unit) for v in values]

        # num_dividers represents the total number of dividers to place
        # values represents the widths of the first N sections (before each specified divider)
        # We need num_dividers + 1 total sections (sections between and around dividers)

        num_sections = num_dividers + 1

        # Validate number of values
        if len(values) > num_sections:
            inkex.errormsg(f"Error: Too many divider spacing values ({len(values)}) for {num_dividers} dividers (max {num_sections} sections)")
            exit(1)

        # Calculate remaining space for auto-sized sections
        used_width = sum(values)  # width of specified sections

        remaining_sections = num_sections - len(values)

        if remaining_sections > 0:
            remaining_width = available_width - used_width
            if remaining_width <= 0:
                inkex.errormsg(f"Error: Specified section widths exceed available space")
                exit(1)
            auto_width = remaining_width / remaining_sections
            values.extend([auto_width] * remaining_sections)
        else:
            # Check if total width fits
            total_used = used_width
            if total_used > available_width:
                inkex.errormsg(f"Error: Total section widths ({total_used:.2f}) exceed available space ({available_width:.2f})")
                exit(1)

        return values



    def parse_options_to_settings(self) -> BoxSettings:
        """Parse command line options into a BoxSettings object"""
    
        # Get access to main SVG document element and get its dimensions.
        svg = self.document.getroot()

        # Get script's option values.
        hairline = self.options.hairline
        unit = self.options.unit
        inside = self.options.inside
        schroff = self.options.schroff
        kerf = self.svg.unittouu(str(self.options.kerf) + unit)

        # Set the line thickness
        line_thickness = round(self.svg.unittouu("0.002in"), 8) if hairline else 1

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
        base_corr = 0.0  # mm correction to get to pure outside dimension
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
            base_corr = self.options.kerf

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

        # Parse custom divider spacing using pure user dimensions (without kerf)
        div_x_spacing = self.parse_divider_spacing(
            self.options.div_l_spacing, unit, Y - 2 * thickness - base_corr, thickness, int(div_x)
        ) if div_x > 0 else []

        div_y_spacing = self.parse_divider_spacing(
            self.options.div_w_spacing, unit, X - 2 * thickness - base_corr, thickness, int(div_y)
        ) if div_y > 0 else []

        return BoxSettings(
            X=X, Y=Y, Z=Z, thickness=thickness, tab_width=tab_width, equal_tabs=equal_tabs,
            tab_symmetry=tabSymmetry, dimple_height=dimpleHeight, dimple_length=dimpleLength,
            dogbone=dogbone, layout=layout, spacing=spacing, boxtype=boxtype,
            div_x=div_x, div_y=div_y, div_x_spacing=div_x_spacing, div_y_spacing=div_y_spacing,
            keydiv_walls=keydivwalls, keydiv_floor=keydivfloor,
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

        def make_sides(settings : BoxSettings, dx : float, dy : float, tabInfo : int, tabbed : int, faceType: FaceType) -> list[Side]:
            # Determine which divider spacings to use based on face type
            # X-axis dividers run along the Y direction, so they need Y spacing
            # Y-axis dividers run along the X direction, so they need X spacing

            def calculate_even_spacing(num_dividers: int, available_width: float, thickness: float) -> list[float]:
                """Calculate even spacing for dividers when no custom spacing is provided"""
                if num_dividers <= 0:
                    return []
                # Original calculation: equal spacing between and around dividers
                partition_width = (available_width - thickness) / (num_dividers + 1)
                return [partition_width] * num_dividers

            if faceType == FaceType.XY:  # Top/Bottom faces
                # Side A/C (horizontal) gets Y-axis divider spacing (div_x)
                # Side B/D (vertical) gets X-axis divider spacing (div_y)"
                horizontal_spacing = settings.div_x_spacing if settings.div_x_spacing else calculate_even_spacing(int(settings.div_x), settings.Y, settings.thickness)
                vertical_spacing = settings.div_y_spacing if settings.div_y_spacing else calculate_even_spacing(int(settings.div_y), settings.X, settings.thickness)
            elif faceType == FaceType.XZ:  # Front/Back faces
                # Side A/C (horizontal) gets no dividers (Z direction)
                # Side B/D (vertical) gets X-axis divider spacing (div_y)
                horizontal_spacing = []
                vertical_spacing = settings.div_y_spacing if settings.div_y_spacing else calculate_even_spacing(int(settings.div_y), settings.X, settings.thickness)
            elif faceType == FaceType.ZY:  # Left/Right faces"
                # Side A/C (horizontal) gets Y-axis divider spacing (div_x)
                # Side B/D (vertical) gets no dividers (Z direction)
                horizontal_spacing = settings.div_x_spacing if settings.div_x_spacing else calculate_even_spacing(int(settings.div_x), settings.Y, settings.thickness)
                vertical_spacing = []
            else:
                horizontal_spacing = []
                vertical_spacing = []

            # Sides: A=top, B=right, C=bottom, D=left
            sides = [
                Side(settings, SideEnum.A, bool(tabInfo & 0b1000), bool(tabbed & 0b1000), (tabInfo >> 3) & 1, (tabbed >> 3) & 1, dx),
                Side(settings, SideEnum.B, bool(tabInfo & 0b0100), bool(tabbed & 0b0100), (tabInfo >> 2) & 1, (tabbed >> 2) & 1, dy),
                Side(settings, SideEnum.C, bool(tabInfo & 0b0010), bool(tabbed & 0b0010), (tabInfo >> 1) & 1, (tabbed >> 1) & 1, dx),
                Side(settings, SideEnum.D, bool(tabInfo & 0b0001), bool(tabbed & 0b0001), tabInfo & 1, tabbed & 1, dy)
            ]

            # Assign divider spacings to appropriate sides
            sides[0].divider_spacings = horizontal_spacing  # A (top)
            sides[1].divider_spacings = vertical_spacing    # B (right)
            sides[2].divider_spacings = horizontal_spacing  # C (bottom)
            sides[3].divider_spacings = vertical_spacing    # D (left)

            return sides

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
                pieces_list.append(PieceSettings(cc[1], rr[2], make_sides(settings, settings.X, settings.Z, bkTabInfo, bkTabbed, bkFace), bkFace))
            if hasLt:
                pieces_list.append(PieceSettings(cc[0], rr[1], make_sides(settings,settings.Z, settings.Y, ltTabInfo, ltTabbed, ltFace), ltFace))
            if hasBm:
                pieces_list.append(PieceSettings(cc[1], rr[1], make_sides(settings, settings.X, settings.Y, bmTabInfo, bmTabbed, bmFace), bmFace))
            if hasRt:
                pieces_list.append(PieceSettings(cc[2], rr[1], make_sides(settings, settings.Z, settings.Y, rtTabInfo, rtTabbed, rtFace), rtFace))
            if hasTp:
                pieces_list.append(PieceSettings(cc[3], rr[1], make_sides(settings, settings.X, settings.Y, tpTabInfo, tpTabbed, tpFace), tpFace))
            if hasFt:
                pieces_list.append(PieceSettings(cc[1], rr[0], make_sides(settings, settings.X, settings.Z, ftTabInfo, ftTabbed, ftFace), ftFace))
        elif settings.layout == Layout.THREE_PIECE:  # 3 Piece Layout
            rr = deepcopy([row0, row1y])
            cc = deepcopy([col0, col1z])
            if hasBk:
                pieces_list.append(PieceSettings(cc[1], rr[1], make_sides(settings, settings.X, settings.Z, bkTabInfo, bkTabbed, bkFace), bkFace))
            if hasLt:
                pieces_list.append(PieceSettings(cc[0], rr[0], make_sides(settings, settings.Z, settings.Y, ltTabInfo, ltTabbed, ltFace), ltFace))
            if hasBm:
                pieces_list.append(PieceSettings(cc[1], rr[0], make_sides(settings, settings.X, settings.Y, bmTabInfo, bmTabbed, bmFace), bmFace))
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
                pieces_list.append(PieceSettings(cc[4], rr[0], make_sides(settings, settings.X, settings.Z, bkTabInfo, bkTabbed, bkFace), bkFace))
            if hasLt:
                pieces_list.append(PieceSettings(cc[2], rr[0], make_sides(settings, settings.Z, settings.Y, ltTabInfo, ltTabbed, ltFace), ltFace))
            if hasTp:
                pieces_list.append(PieceSettings(cc[0], rr[0], make_sides(settings, settings.X, settings.Y, tpTabInfo, tpTabbed, tpFace), tpFace))
            if hasBm:
                pieces_list.append(PieceSettings(cc[1], rr[0], make_sides(settings, settings.X, settings.Y, bmTabInfo, bmTabbed, bmFace), bmFace))
            if hasRt:
                pieces_list.append(PieceSettings(cc[3], rr[0], make_sides(settings, settings.Z, settings.Y, rtTabInfo, rtTabbed, rtFace), rtFace))
            if hasFt:
                pieces_list.append(PieceSettings(cc[5], rr[0], make_sides(settings, settings.X, settings.Z, ftTabInfo, ftTabbed, ftFace), ftFace))

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

            group = self.makeGroup("piece")
            self.svg.get_current_layer().add(group)
            groups = [group]

            if settings.schroff and railholes and config.schroff_settings:
                schroff = config.schroff_settings
                dx = piece.dx
                dy = piece.dy

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
                log("rhxoffset = %d, rhx= %d" % (rhxoffset, rhx))
                rystart = y + (settings.schroff.rail_height / 2) + self.thickness
                if settings.rows == 1:
                    log("just one row this time, rystart = %d" % rystart)
                    rh1y = rystart + settings.schroff.rail_mount_centre_offset
                    rh2y = rh1y + (settings.schroff.row_centre_spacing - settings.schroff.rail_mount_centre_offset)
                    group.add(
                        self.makeCircle(
                            settings.schroff.rail_mount_radius, (rhx, rh1y)))
                    group.add(
                        self.makeCircle(
                            settings.schroff.rail_mount_radius, (rhx, rh2y)))
                else:
                    for n in range(0, schroff.rows):
                        log(f"drawing row {n + 1}, rystart = {rystart}")
                        # if holes are offset (eg. Vector T-strut rails), they should be offset
                        # toward each other, ie. toward the centreline of the
                        # Schroff row
                        rh1y = rystart + settings.schroff.rail_mount_centre_offset
                        rh2y = rh1y + settings.schroff.row_centre_spacing - settings.schroff.rail_mount_centre_offset
                        group.add(
                            self.makeCircle(
                                settings.schroff.rail_mount_radius, (rhx, rh1y)))
                        group.add(
                            self.makeCircle(
                                settings.schroff.rail_mount_radius, (rhx, rh2y)))
                        rystart += settings.schroff.row_centre_spacing + settings.schroff.row_spacing + settings.schroff.rail_height

            # generate and draw the sides of each piece
            # Calculate average spacing for each side's dividers (for uniform spacing assumption in render functions)

            # Side A
            self.render_side(
                group,
                (x, y),
                aSide,
                False,
                ((self.keydivfloor or wall) and (self.keydivwalls or floor) and aSide.has_tabs and yholes)
                * settings.div_x,
            )
            # Side B
            self.render_side(
                group,
                (x, y),
                bSide,
                False,
                ((self.keydivfloor or wall) and (self.keydivwalls or floor) and bSide.has_tabs and xholes)
                * settings.div_y,
            )
            # Side C
            self.render_side(
                group,
                (x, y),
                cSide,
                False,
                ((self.keydivfloor or wall) and (self.keydivwalls or floor) and not aSide.has_tabs and cSide.has_tabs and yholes)
                * settings.div_x,
            )
            # Side D
            self.render_side(
                group,
                (x, y),
                dSide,
                False,
                ((self.keydivfloor or wall) and (self.keydivwalls or floor) and not bSide.has_tabs and dSide.has_tabs and xholes)
                * settings.div_y,
            )

            if idx == 0:
                # remove tabs from dividers if not required
                aSideX, bSideX, cSideX, dSideX = deepcopy([aSide, bSide, cSide, dSide])
                if not self.keydivfloor:
                    aSideX.is_male = cSideX.is_male = 1
                    aSideX.has_tabs = cSideX.has_tabs = 0
                if not self.keydivwalls:
                    bSideX.is_male = dSideX.is_male = 1
                    bSideX.has_tabs = dSideX.has_tabs = 0

                divider_y = 4 * settings.spacing + 1 * settings.Y + 2 * settings.Z  # root y co-ord for piece
                for n in range(0, settings.div_x):  # generate X dividers
                    subGroup = self.makeGroup('xdivider')
                    groups.append(subGroup)
                    divider_x = n * (settings.spacing + settings.X)  # root x co-ord for piece

                    # Side A
                    self.render_side(
                        subGroup,
                        (divider_x, divider_y),
                        aSideX,
                        True
                    )
                    # Side B
                    self.render_side(
                        subGroup,
                        (divider_x, divider_y),
                        bSideX,
                        True,
                        settings.div_y * divider_x_holes,
                    )
                    # Side C
                    self.render_side(
                        subGroup,
                        (divider_x, divider_y),
                        cSideX,
                        True,
                    )
                    # Side D
                    self.render_side(
                        subGroup,
                        (divider_x, divider_y),
                        dSideX,
                        True
                    )
            elif idx == 1:
                # remove tabs from dividers if not required
                aSideX, bSideX, cSideX, dSideX = deepcopy([aSide, bSide, cSide, dSide])
                if not self.keydivwalls:
                    aSideX.is_male = cSideX.is_male = 1
                    aSideX.has_tabs = cSideX.has_tabs = 0
                if not self.keydivfloor:
                    bSideX.is_male = dSideX.is_male = 1
                    bSideX.has_tabs = dSideX.has_tabs = 0

                divider_y = 5 * settings.spacing + 1 * settings.Y + 3 * settings.Z  # root y co-ord for piece
                for n in range(0, settings.div_y):  # generate Y dividers
                    subGroup = self.makeGroup("ydivider")
                    self.svg.get_current_layer().add(subGroup)
                    groups.append(subGroup)
                    divider_x = n * (settings.spacing + settings.Z)  # root x co-ord for piece
                    # Side A
                    self.render_side(
                        subGroup,
                        (divider_x, divider_y),
                        aSideX,
                        True,
                        settings.div_x * divider_y_holes,
                    )
                    # Side B
                    self.render_side(
                        subGroup,
                        (divider_x, divider_y),
                        bSideX,
                        True
                    )
                    # Side C
                    self.render_side(
                        subGroup,
                        (divider_x, divider_y),
                        cSideX,
                        True
                    )
                    # Side D
                    self.render_side(
                        subGroup,
                        (divider_x, divider_y),
                        dSideX,
                        True
                    )

            # All pieces drawn, now optimize the paths if required
            if self.options.optimize:
                self.optimizePieces(groups)

    def _run_effect(self) -> None:

        # Step 1: Parse options into settings
        settings = self.parse_options_to_settings()

        # Store values needed for other methods
        self.dimpleHeight = settings.dimple_height
        self.dimpleLength = settings.dimple_length
        self.keydivwalls = settings.keydiv_walls
        self.keydivfloor = settings.keydiv_floor
        self.kerf = settings.kerf
        self.linethickness = settings.line_thickness

        # Step 2: Parse settings into complete configuration with pieces
        config = self.parse_settings_to_configuration(settings)

        # Add comments and metadata to SVG
        svg = self.document.getroot()
        layer = svg.get_current_layer()

        # Allow hiding version for testing purposes
        if self.version:
            layer.add(inkex.etree.Comment(f" Generated by BoxMaker version {self.version} "))
            layer.add(inkex.etree.Comment(f" {settings} "))

        # Step 3: Generate and draw all pieces
        self.generate_pieces(config, settings)

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

                path = path_element.path.reverse()
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
                    elif isinstance(segment, inkex.paths.Line):
                        if isinstance(prev, inkex.paths.Line):
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
                                current_dir = direction
                            else:
                                current_dir = None
                            simplified_path.append(segment)
                        prev = segment
                    elif isinstance(segment, inkex.paths.Move):
                        simplified_path.append(segment)
                        prev = segment
                        current_dir = None
                        direction = None
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
        isMale: bool
    ) -> inkex.Path:
        ds = []
        if not isMale:
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

    def render_side(
        self,
        group: inkex.Group,
        root: tuple[float, float],
        side: Side,
        isDivider: bool = False,
        numDividers: int = 0
    ) -> None:
        """Draw one side of a piece, with tabs or holes as required. Returns result in group"""

        for i in self.render_side_side(root, side) + \
                self.render_side_slots(root, side, isDivider, numDividers) + \
                self.render_side_holes(root, side, isDivider, numDividers):
            group.add(i)

    def render_side_side(
        self,
        root: tuple[float, float],
        side: Side
    ) -> list[inkex.PathElement]:
        """Draw one side of a piece"""

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

        isMale = side.is_male
        notMale = not isMale
        thickness = side.thickness

        if side.has_tabs:
            # Calculate direction
            tabVec = thickness if (direction == (1, 0) or direction == (0, -1)) != isMale else -thickness
        else:
            tabVec = 0

        prevTab = side.prev.has_tabs

        kerf = side.kerf
        halfkerf = kerf / 2
        line_thickness = side.line_thickness
        dogbone = side.dogbone

        sidePath = self.makeLine('', "side")
        nodes = [sidePath]

        divisions = side.divisions
        gapWidth = side.gap_width
        tabWidth = side.tab_width
        first = side.first

        firstVec = 0
        secondVec = tabVec
        notDirX, notDirY = self._get_perpendicular_flags(direction)
        s = inkex.Path()
        if side.tab_symmetry == TabSymmetry.ROTATE_SYMMETRIC:
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
            vectorX = startOffsetX * thickness
            vectorY = startOffsetY * thickness
            s.append(Move(vectorX, vectorY))
            if notDirX:
                vectorY = 0  # set correct line start for tab generation
            if notDirY:
                vectorX = 0

        # generate line as tab or hole using:
        #   last co-ord:Vx,Vy ; tab dir:tabVec  ; direction:dirx,diry ; thickness:thickness
        #   divisions:divs ; gap width:gapWidth ; tab width:tabWidth

        for tabDivision in range(1, int(divisions)):
            if tabDivision % 2:
                # draw the gap
                vectorX += (
                    dirX
                    * (
                        gapWidth
                        + (first if not (isMale and dogbone) else 0)
                        + dogbone * kerf * isMale
                    )
                    + notDirX * firstVec
                )
                vectorY += (
                    dirY
                    * (
                        gapWidth
                        + (first if not (isMale and dogbone) else 0)
                        + (kerf if dogbone and isMale else 0)
                    )
                    + notDirY * firstVec
                )
                s.append(Line(vectorX, vectorY))
                if dogbone and isMale:
                    vectorX -= dirX * halfkerf
                    vectorY -= dirY * halfkerf
                    s.append(Line(vectorX, vectorY))
                # draw the starting edge of the tab
                s += self.dimpleStr(
                    secondVec, vectorX, vectorY, dirX, dirY, notDirX, notDirY, 1, isMale
                )
                vectorX += notDirX * secondVec
                vectorY += notDirY * secondVec
                s.append(Line(vectorX, vectorY))
                if dogbone and notMale:
                    vectorX -= dirX * halfkerf
                    vectorY -= dirY * halfkerf
                    s.append(Line(vectorX, vectorY))

            else:
                # draw the tab
                vectorX += dirX * (tabWidth + dogbone *
                                   kerf * notMale) + notDirX * firstVec
                vectorY += dirY * (tabWidth + dogbone *
                                   kerf * notMale) + notDirY * firstVec
                s.append(Line(vectorX, vectorY))
                if dogbone and notMale:
                    vectorX -= dirX * halfkerf
                    vectorY -= dirY * halfkerf
                    s.append(Line(vectorX, vectorY))
                # draw the ending edge of the tab
                s += self.dimpleStr(
                    secondVec, vectorX, vectorY, dirX, dirY, notDirX, notDirY, -1, isMale
                )
                vectorX += notDirX * secondVec
                vectorY += notDirY * secondVec
                s.append(Line(vectorX, vectorY))
                if dogbone and isMale:
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

        rootX, rootY = root
        rootX += root_offs[0]
        rootY += root_offs[1]

        sidePath.path = s
        sidePath.path = sidePath.path.translate(rootX, rootY)
        return [sidePath]

    # Calculate cumulative positions for dividers
    @staticmethod
    def calculate_cumulative_position(divider_number: int, divider_spacings: list[float], side_thickness: float) -> float:
        """Calculate cumulative position for divider number (1-based)"""

        if not divider_spacings:
            return 0  # No custom spacing provided, fall back to default even spacing calculation

        cumulative = 0
        # Divider N comes after section N, so add sections 1 through N
        for i in range(divider_number):
            if i < len(divider_spacings):
                cumulative += divider_spacings[i]
            else:
                # This should not happen as parse_divider_spacing should fill all slots
                break

        return cumulative


    def render_side_slots(
        self,
        root: tuple[float, float],
        side: Side,
        isDivider: bool = False,
        numDividers: int = 0,
        dividerSpacings: list[float] = None,
    ) -> list[inkex.PathElement]:
        """Draw tabs or holes as required"""

        if numDividers == 0 or not isDivider:
            return []

        dividerSpacings = side.divider_spacings


        direction = side.direction
        dirX, dirY = direction

        # TODO: Use rotation matrix to simplify this logic
        # All values are booleans so results will be -1, 0, or 1

        offs_cases = {
            SideEnum.A: [(0,0), (side.prev.is_male, side.is_male)],
            SideEnum.B: [(side.prev.length, 0), (-side.is_male, side.prev.is_male)],
            SideEnum.C: [(side.length, side.prev.length), (-side.prev.is_male, -side.is_male)],
            SideEnum.D: [(0, side.length), (side.is_male, -side.prev.is_male)],
        }
        root_offs, startOffset = offs_cases[side.name]

        #if not side.has_tabs and side.is_male:
        #if not side.has_tabs and side.is_male:
        #    startOffset = (0, 0)

        startOffsetX, startOffsetY = startOffset
        length = side.length

        thickness = side.thickness

        kerf = side.kerf
        halfkerf = kerf / 2

        nodes = []

        first = side.first

        notDirX, notDirY = self._get_perpendicular_flags(direction)
        if side.tab_symmetry == TabSymmetry.ROTATE_SYMMETRIC:
            dividerEdgeOffsetX = dirX * thickness
            dividerEdgeOffsetY = thickness
            vectorX = (startOffsetX if startOffsetX else dirX) * thickness
            vectorY = (startOffsetY if startOffsetY else dirY) * thickness
        else:
            vectorX = startOffsetX * thickness
            vectorY = startOffsetY * thickness

            dividerEdgeOffsetX = dirY * thickness
            dividerEdgeOffsetY = dirX * thickness
            if notDirX:
                vectorY = 0  # set correct line start for tab generation
            if notDirY:
                vectorX = 0

        for dividerNumber in range(1, int(numDividers) + 1):
            base_pos = (vectorX, vectorY)
            cumulative_position = self.calculate_cumulative_position(dividerNumber, dividerSpacings, thickness)
            divider_offset = (-dirY * cumulative_position, dirX * cumulative_position)
            edge_offset = (-dividerEdgeOffsetX, -dividerEdgeOffsetY)
            kerf_offset = (notDirX * halfkerf, notDirY * halfkerf)

            start_pos = self._point_add(base_pos, self._point_add(divider_offset,
                                      self._point_add(edge_offset, kerf_offset)))

            h = []
            h.append(Move(*start_pos))

            slot_end = self._point_add(start_pos, self._point_scale(direction, first + length / 2))
            h.append(Line(*slot_end))

            side_offset = self._point_add(slot_end, (notDirX * (thickness - kerf), notDirY * (thickness - kerf)))
            h.append(Line(*side_offset))

            back_to_start = self._point_subtract(side_offset, self._point_scale(direction, first + length / 2))
            h.append(Line(*back_to_start))

            final_pos = self._point_subtract(back_to_start, (notDirX * (thickness - kerf), notDirY * (thickness - kerf)))
            h.append(Line(*final_pos))
            h.append(ZoneClose())
            nodes.append(self.makeLine(h, "slot"))

        rootX, rootY = root
        rootX += root_offs[0]
        rootY += root_offs[1]
        for node in nodes:
            node.path = node.path.translate(rootX, rootY)

        return nodes

    def render_side_holes(
        self,
        root: tuple[float, float],
        side: Side,
        isDivider: bool = False,
        numDividers: int = 0,
    ) -> list[inkex.PathElement]:
        """Draw tabs or holes as required"""

        dividerSpacings = side.divider_spacings


        direction = side.direction
        dirX, dirY = direction

        # TODO: Use rotation matrix to simplify this logic
        # All values are booleans so results will be -1, 0, or 1

        offs_cases = {
            SideEnum.A: [(0,0), (side.prev.is_male, side.is_male)],
            SideEnum.B: [(side.prev.length, 0), (-side.is_male, side.prev.is_male)],
            SideEnum.C: [(side.length, side.prev.length), (-side.prev.is_male, -side.is_male)],
            SideEnum.D: [(0, side.length), (side.is_male, -side.prev.is_male)],
        }
        root_offs, startOffset = offs_cases[side.name]

        startOffsetX, startOffsetY = startOffset

        isMale = side.is_male
        notMale = not isMale
        thickness = side.thickness


        if side.has_tabs:
            # Calculate direction
            tabVec = thickness if (direction == (1, 0) or direction == (0, -1)) != isMale else -thickness
        else:
            tabVec = 0

        kerf = side.kerf
        halfkerf = kerf / 2
        dogbone = side.dogbone

        nodes = []

        divisions = side.divisions
        gapWidth = side.gap_width
        tabWidth = side.tab_width
        first = side.first

        firstVec = 0
        secondVec = tabVec
        notDirX, notDirY = self._get_perpendicular_flags(direction)

        if side.tab_symmetry == TabSymmetry.ROTATE_SYMMETRIC:
            dividerEdgeOffsetX = dirX * thickness
            dividerEdgeOffsetY = thickness
            vectorX = (startOffsetX if startOffsetX else dirX) * thickness
            vectorY = (startOffsetY if startOffsetY else dirY) * thickness
        else:
            dividerEdgeOffsetX = dirY * thickness
            dividerEdgeOffsetY = dirX * thickness
            vectorX = (startOffsetX * thickness) if notDirX else 0
            vectorY = (startOffsetY * thickness) if notDirY else 0

        w = gapWidth if isMale else tabWidth
        if side.tab_symmetry == TabSymmetry.XY_SYMMETRIC:
            w -= startOffsetX * thickness

        # generate line as tab or hole using:
        #   last co-ord:Vx,Vy ; tab dir:tabVec  ; direction:dirx,diry ; thickness:thickness
        #   divisions:divs ; gap width:gapWidth ; tab width:tabWidth
        firstHole = True
        for tabDivision in range(1, int(divisions)):
            # draw holes for divider tabs to key into side walls
            if (((tabDivision % 2) > 0) != (not isMale)) and numDividers > 0 and not isDivider:
                w = gapWidth if isMale else tabWidth
                if tabDivision == 1 and side.tab_symmetry == TabSymmetry.XY_SYMMETRIC:
                    w -= startOffsetX * thickness
                holeLenX = dirX * (w + first) + (firstVec if notDirX else 0)
                holeLenY = dirY * (w + first) + (firstVec if notDirY else 0)
                if firstHole:
                    firstHoleLenX = holeLenX
                    firstHoleLenY = holeLenY
                    firstHole = False
                for dividerNumber in range(1, int(numDividers) + 1):
                    base_pos = (vectorX, vectorY)
                    cumulative_position = self.calculate_cumulative_position(dividerNumber, dividerSpacings, thickness)
                    divider_offset = (-dirY * cumulative_position, dirX * cumulative_position)
                    kerf_offset = (halfkerf if notDirX else 0, -(halfkerf if notDirY else 0))
                    dogbone_offset = ((dirX * halfkerf - first * dirX) if dogbone else 0,
                                    (dirY * halfkerf - first * dirY) if dogbone else 0)

                    start_pos = self._point_add(base_pos, self._point_add(divider_offset,
                                              self._point_add(kerf_offset, dogbone_offset)))

                    if tabDivision == 1 and side.tab_symmetry == TabSymmetry.XY_SYMMETRIC:
                        start_pos = self._point_add(start_pos, (startOffsetX * thickness, 0))

                    h = []
                    h.append(Move(*start_pos))

                    hole_end = self._point_add(start_pos, (holeLenX, holeLenY))
                    h.append(Line(*hole_end))

                    side_offset = self._point_add(hole_end, (notDirX * (secondVec - kerf), notDirY * (secondVec + kerf)))
                    h.append(Line(*side_offset))

                    back_to_start = self._point_subtract(side_offset, (holeLenX, holeLenY))
                    h.append(Line(*back_to_start))

                    final_pos = self._point_subtract(back_to_start, (notDirX * (secondVec - kerf), notDirY * (secondVec + kerf)))
                    h.append(Line(*final_pos))
                    h.append(ZoneClose())
                    nodes.append(self.makeLine(h, "hole"))
            if tabDivision % 2:
                # draw the gap
                vectorX += (
                    dirX
                    * (
                        gapWidth
                        + (first if not (isMale and dogbone) else 0)
                        + dogbone * kerf * isMale
                    )
                    + notDirX * firstVec
                )
                vectorY += (
                    dirY
                    * (
                        gapWidth
                        + (first if not (isMale and dogbone) else 0)
                        + (kerf if dogbone and isMale else 0)
                    )
                    + notDirY * firstVec
                )

                if dogbone and isMale:
                    vectorX -= dirX * halfkerf
                    vectorY -= dirY * halfkerf
            else:
                # draw the tab
                vectorX += dirX * (tabWidth + dogbone *
                                   kerf * notMale) + notDirX * firstVec
                vectorY += dirY * (tabWidth + dogbone *
                                   kerf * notMale) + notDirY * firstVec

            if dogbone and notMale:
                vectorX -= dirX * halfkerf
                vectorY -= dirY * halfkerf
            vectorX += notDirX * secondVec
            vectorY += notDirY * secondVec

            (secondVec, firstVec) = (-secondVec, -firstVec)  # swap tab direction
            first = 0

        # draw last for divider joints in side walls
        if isMale and numDividers > 0 and side.tab_symmetry == 0 and not isDivider:
            for dividerNumber in range(1, int(numDividers) + 1):
                base_pos = (vectorX, vectorY)
                cumulative_position = self.calculate_cumulative_position(dividerNumber, dividerSpacings, thickness)
                divider_offset = (-dirY * cumulative_position, dirX * cumulative_position)
                kerf_offset = (notDirX * halfkerf, notDirY * halfkerf)
                edge_offset = (-dividerEdgeOffsetX, -dividerEdgeOffsetY)

                start_pos = self._point_add(
                            self._point_add(base_pos, self._point_add(divider_offset,
                            self._point_add(kerf_offset, edge_offset))),
                            (0, firstHoleLenY + notDirY * (thickness-self.kerf)))

                h = []
                h.append(Move(*start_pos))

                hole_end = self._point_add(start_pos, (firstHoleLenX, -firstHoleLenY))
                h.append(Line(*hole_end))

                side_offset = self._point_add(hole_end, (notDirX * (thickness - kerf), -notDirY * (thickness - kerf)))
                h.append(Line(*side_offset))

                back_to_start = self._point_subtract(side_offset, (firstHoleLenX, -firstHoleLenY))
                h.append(Line(*back_to_start))

                final_pos = self._point_subtract(back_to_start, (notDirX * (thickness - kerf), -notDirY * (thickness - kerf)))
                h.append(Line(*final_pos))
                h.append(ZoneClose())
                nodes.append(self.makeLine(h, "hole"))

        rootX, rootY = root
        rootX += root_offs[0]
        rootY += root_offs[1]
        for node in nodes:
            node.path = node.path.translate(rootX, rootY)

        return nodes

    def _point_add(self, p1: tuple[float, float], p2: tuple[float, float]) -> tuple[float, float]:
        """Add two points/vectors"""
        return (p1[0] + p2[0], p1[1] + p2[1])

    def _point_subtract(self, p1: tuple[float, float], p2: tuple[float, float]) -> tuple[float, float]:
        """Subtract two points/vectors"""
        return (p1[0] - p2[0], p1[1] - p2[1])

    def _point_scale(self, point: tuple[float, float], scale: float) -> tuple[float, float]:
        """Scale a point/vector by a scalar"""
        return (point[0] * scale, point[1] * scale)

    def _get_perpendicular_flags(self, direction: tuple[float, float]) -> tuple[bool, bool]:
        """Get perpendicular direction flags for easier axis selection"""
        dirX, dirY = direction
        return (dirX == 0, dirY == 0)  # (notDirX, notDirY)


if __name__ == "__main__":
  # Create effect instance and apply it.
  effect = TabbedBoxMaker(cli=True)
  effect.run()
