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

import inkex
import math
import os
import gettext

from inkex import Effect, Group, PathElement
from inkex.paths import Path
from inkex.paths.lines import Line, Move, ZoneClose

from copy import deepcopy
from shapely.ops import unary_union

from tabbedboxmaker.enums import BoxType, Layout, TabSymmetry, DividerKeying, Sides, PieceType
from tabbedboxmaker.InkexShapely import path_to_polygon, polygon_to_path, adjust_canvas
from tabbedboxmaker.__about__ import __version__ as BOXMAKER_VERSION
from tabbedboxmaker.settings import BoxSettings, BoxConfiguration, BoxFaces, TabConfiguration, Piece, SchroffSettings, Side, Vec



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


class TabbedBoxMaker(Effect):
    nextId: dict[str, int]
    linethickness: float = 1
    nextId: dict[str, int]
    version = BOXMAKER_VERSION
    settings : BoxSettings

    def __init__(self, cli=True, schroff=False):
        # Call the base class constructor.
        super().__init__()

        self.nextId = {}
        self.cli = cli
        self.schroff = schroff



        self._setup_arguments()


    def makeId(self, prefix: str | None) -> str:
        """Generate a new unique ID with the given prefix."""

        prefix = prefix if prefix is not None else "id"
        if prefix not in self.nextId:
            id = self.nextId[prefix] = 0

        self.nextId[prefix] = id = self.nextId[prefix] + 1

        return f"{prefix}_{id:03d}"


    def makeGroup(self, id="piece") -> Group:
        # Create a new group and add element created from line string
        group = Group(id=self.makeId(id))

        self.svg.get_current_layer().add(group)
        return group



    def makeLine(self, path , id : str = "line") -> PathElement:
        line = PathElement(id=self.makeId(id))
        line.style = { "stroke": "#000000", "stroke-width"  : str(self.linethickness), "fill": "none" }
        line.path = Path(path)
        return line



    def makeCircle(self,r, c, id : str = "circle"):
        (cx, cy) = c
        log("putting circle at (%d,%d)" % (cx,cy))
        circle = PathElement.arc((cx, cy), r, id=self.makeId(id))
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
                type=inkex.utils.filename_arg,
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
            default=5,
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
            default=1,
            help="Layout/Style",
        )
        self.arg_parser.add_argument(
            "--spacing",
            action="store",
            type=float,
            dest="spacing",
            default=3,
            help="Part Spacing",
        )
        self.arg_parser.add_argument(
            "--boxtype",
            action="store",
            type=int,
            dest="boxtype",
            default=1,
            help="Box type",
        )
        self.arg_parser.add_argument(
            "--div_l",
            action="store",
            type=int,
            dest="div_x",
            default=0,
            help="Dividers (Length axis / X axis)",
        )
        self.arg_parser.add_argument(
            "--div_w",
            action="store",
            type=int,
            dest="div_y",
            default=0,
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
        box_type = BoxType(self.options.boxtype)
        div_x = int(self.options.div_x)
        div_y = int(self.options.div_y)
        keydivwalls = self.options.keydiv in [DividerKeying.ALL_SIDES, DividerKeying.WALLS]
        keydivfloor = self.options.keydiv in [DividerKeying.ALL_SIDES, DividerKeying.FLOOR_CEILING]
        initOffsetX = 0
        initOffsetY = 0


        piece_types = [PieceType.Back, PieceType.Left, PieceType.Bottom, PieceType.Right, PieceType.Top, PieceType.Front]
        if box_type == BoxType.ONE_SIDE_OPEN:
            piece_types = [PieceType.Bottom, PieceType.Front, PieceType.Back, PieceType.Left, PieceType.Right]
        elif box_type == BoxType.TWO_SIDES_OPEN:
            piece_types = [PieceType.Bottom, PieceType.Back, PieceType.Left, PieceType.Right]
        elif box_type == BoxType.THREE_SIDES_OPEN:
            piece_types = [PieceType.Bottom,PieceType.Back, PieceType.Left]
        elif box_type == BoxType.OPPOSITE_ENDS_OPEN:
            piece_types = [PieceType.Back, PieceType.Left, PieceType.Right, PieceType.Front]
        elif box_type == BoxType.TWO_PANELS_ONLY:
            piece_types = [PieceType.Left, PieceType.Bottom]

        if inside:  # if inside dimension selected correct values to outside dimension
            inside_X, inside_Y, inside_Z = X, Y, Z

            X += thickness * ((PieceType.Left in piece_types) + (PieceType.Right in piece_types))
            Y += thickness * ((PieceType.Front in piece_types) + (PieceType.Back  in piece_types))
            Z += thickness * ((PieceType.Top  in piece_types) + (PieceType.Bottom in piece_types))
        else:
            inside_X = X - thickness * ((PieceType.Left in piece_types) + (PieceType.Right in piece_types))
            inside_Y = Y - thickness * ((PieceType.Front in piece_types) + (PieceType.Back  in piece_types))
            inside_Z = Z - thickness * ((PieceType.Top  in piece_types) + (PieceType.Bottom in piece_types))

        # Parse custom divider spacing using pure user dimensions (without kerf)
        div_x_spacing = self.parse_divider_spacing(
            self.options.div_l_spacing, unit, Y - 2 * thickness - base_corr, thickness, int(div_x)
        ) if div_x > 0 else []

        div_y_spacing = self.parse_divider_spacing(
            self.options.div_w_spacing, unit, X - 2 * thickness - base_corr, thickness, int(div_y)
        ) if div_y > 0 else []

        return BoxSettings(
            X=X, Y=Y, Z=Z,
            inside_X=inside_X, inside_Y=inside_Y, inside_Z=inside_Z,
            thickness=thickness, tab_width=tab_width, equal_tabs=equal_tabs,
            tab_symmetry=tabSymmetry, dimple_height=dimpleHeight, dimple_length=dimpleLength,
            dogbone=dogbone, layout=layout, spacing=spacing, boxtype=box_type,
            piece_types=piece_types, div_x=div_x, div_y=div_y, div_x_spacing=div_x_spacing, div_y_spacing=div_y_spacing,
            keydiv_walls=keydivwalls, keydiv_floor=keydivfloor,
            initOffsetX=initOffsetX, initOffsetY=initOffsetY,
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
            piece_types=settings.piece_types,
            tabs=self.create_tabs_configuration(settings, settings.piece_types)
        )

    def create_tabs_configuration(self, settings: BoxSettings, pieceTypes: list[PieceType]) -> TabConfiguration:
        """Create the tab configuration based on box settings"""

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
            newTabInfo = tabInfo & ~bit  # set bit to 0 to use tab tip line
            return newTabbed, newTabInfo

        # Update the tab bits based on which sides of the box don't exist
        tpTabbed = bmTabbed = ltTabbed = rtTabbed = ftTabbed = bkTabbed = 0b1111
        if PieceType.Top not in pieceTypes:
            bkTabbed, bkTabInfo = fixTabBits(bkTabbed, bkTabInfo, 0b0010)
            ftTabbed, ftTabInfo = fixTabBits(ftTabbed, ftTabInfo, 0b1000)
            ltTabbed, ltTabInfo = fixTabBits(ltTabbed, ltTabInfo, 0b0001)
            rtTabbed, rtTabInfo = fixTabBits(rtTabbed, rtTabInfo, 0b0100)
            tpTabbed = 0
        if PieceType.Bottom not in pieceTypes:
            bkTabbed, bkTabInfo = fixTabBits(bkTabbed, bkTabInfo, 0b1000)
            ftTabbed, ftTabInfo = fixTabBits(ftTabbed, ftTabInfo, 0b0010)
            ltTabbed, ltTabInfo = fixTabBits(ltTabbed, ltTabInfo, 0b0100)
            rtTabbed, rtTabInfo = fixTabBits(rtTabbed, rtTabInfo, 0b0001)
            bmTabbed = 0
        if PieceType.Front not in pieceTypes:
            tpTabbed, tpTabInfo = fixTabBits(tpTabbed, tpTabInfo, 0b1000)
            bmTabbed, bmTabInfo = fixTabBits(bmTabbed, bmTabInfo, 0b1000)
            ltTabbed, ltTabInfo = fixTabBits(ltTabbed, ltTabInfo, 0b1000)
            rtTabbed, rtTabInfo = fixTabBits(rtTabbed, rtTabInfo, 0b1000)
            ftTabbed = 0
        if PieceType.Back not in pieceTypes:
            tpTabbed, tpTabInfo = fixTabBits(tpTabbed, tpTabInfo, 0b0010)
            bmTabbed, bmTabInfo = fixTabBits(bmTabbed, bmTabInfo, 0b0010)
            ltTabbed, ltTabInfo = fixTabBits(ltTabbed, ltTabInfo, 0b0010)
            rtTabbed, rtTabInfo = fixTabBits(rtTabbed, rtTabInfo, 0b0010)
            bkTabbed = 0
        if PieceType.Left not in pieceTypes:
            tpTabbed, tpTabInfo = fixTabBits(tpTabbed, tpTabInfo, 0b0100)
            bmTabbed, bmTabInfo = fixTabBits(bmTabbed, bmTabInfo, 0b0001)
            bkTabbed, bkTabInfo = fixTabBits(bkTabbed, bkTabInfo, 0b0001)
            ftTabbed, ftTabInfo = fixTabBits(ftTabbed, ftTabInfo, 0b0001)
            ltTabbed = 0
        if PieceType.Right not in pieceTypes:
            tpTabbed, tpTabInfo = fixTabBits(tpTabbed, tpTabInfo, 0b0001)
            bmTabbed, bmTabInfo = fixTabBits(bmTabbed, bmTabInfo, 0b0100)
            bkTabbed, bkTabInfo = fixTabBits(bkTabbed, bkTabInfo, 0b0100)
            ftTabbed, ftTabInfo = fixTabBits(ftTabbed, ftTabInfo, 0b0100)
            rtTabbed = 0

        return TabConfiguration(
            tpTabInfo=tpTabInfo, bmTabInfo=bmTabInfo, ltTabInfo=ltTabInfo, rtTabInfo=rtTabInfo,
            ftTabInfo=ftTabInfo, bkTabInfo=bkTabInfo, tpTabbed=tpTabbed, bmTabbed=bmTabbed,
            ltTabbed=ltTabbed, rtTabbed=rtTabbed, ftTabbed=ftTabbed, bkTabbed=bkTabbed
        )


    @staticmethod
    def apply_layout(created_pieces : list[Piece], settings: BoxSettings) -> list[Piece]:
        """Apply the selected layout to position the pieces"""

        piece_types = settings.piece_types

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

        def reduceOffsets(aa : list, start : int, dx : int, dy : int, dz : int):
            for ix in range(start + 1, len(aa)):
                (s, x, y, z) = aa[ix]
                aa[ix] = (s - 1, x - dx, y - dy, z - dz)

        # note first two pieces in each set are the X-divider template and
        # Y-divider template respectively
        pieces_list : list[Piece] = []
        if settings.layout == Layout.DIAGRAMMATIC:  # Diagramatic Layout
            rr = deepcopy([row0, row1z, row2])
            cc = deepcopy([col0, col1z, col2xz, col3xzz])
            if PieceType.Front not in piece_types:
                reduceOffsets(rr, 0, 0, 0, 1)
            if PieceType.Left not in piece_types:
                reduceOffsets(cc, 0, 0, 0, 1)
            if PieceType.Right not in piece_types:
                reduceOffsets(cc, 2, 0, 0, 1)

            # Position pieces using original coordinate calculation
            def calculate_position(col_tuple, row_tuple) -> Vec:
                # Formula: x = xs * spacing + xx * X + xy * Y + xz * Z + initOffsetX
                # col_tuple = (xs, xx, xy, xz), row_tuple = (ys, yx, yy, yz)
                xs, xx, xy, xz = col_tuple
                ys, yx, yy, yz = row_tuple

                x = xs * settings.spacing + xx * settings.X + xy * settings.Y + xz * settings.Z + settings.initOffsetX
                y = ys * settings.spacing + yx * settings.X + yy * settings.Y + yz * settings.Z + settings.initOffsetY

                return Vec(x, y)

            # Create pieces in the correct order as original DIAGRAMMATIC layout
            divider_x_counter = 0
            divider_y_counter = 0

            # Separate dividers from other pieces to avoid double processing
            main_pieces = [p for p in created_pieces if p.pieceType not in [PieceType.DividerX, PieceType.DividerY]]
            x_dividers = [p for p in created_pieces if p.pieceType == PieceType.DividerX]
            y_dividers = [p for p in created_pieces if p.pieceType == PieceType.DividerY]

            # Track if dividers have been added
            x_dividers_added = False
            y_dividers_added = False

            for piece in main_pieces:
                if piece.pieceType == PieceType.Back:
                    piece.base = calculate_position(cc[1], rr[2])  # cc[1], rr[2] - Back piece
                    pieces_list.append(piece)

                    # Add X dividers after Back piece (as in original)
                    for divider in x_dividers:
                        # Original divider positioning from working code:
                        # divider_y = 4 * spacing + 1 * Y + 2 * Z
                        # divider_x = n * (spacing + X)
                        divider_y = 4 * settings.spacing + 1 * settings.Y + 2 * settings.Z
                        divider_x = divider_x_counter * (settings.spacing + settings.X)
                        divider.base = Vec(divider_x, divider_y)
                        pieces_list.append(divider)
                        divider_x_counter += 1
                    x_dividers_added = True

                elif piece.pieceType == PieceType.Left:
                    piece.base = calculate_position(cc[0], rr[1])  # cc[0], rr[1] - Left piece
                    pieces_list.append(piece)

                    # Add X dividers after Left piece if Back piece doesn't exist (fallback)
                    if not x_dividers_added:
                        for divider in x_dividers:
                            divider_y = 4 * settings.spacing + 1 * settings.Y + 2 * settings.Z
                            divider_x = divider_x_counter * (settings.spacing + settings.X)
                            divider.base = Vec(divider_x, divider_y)
                            pieces_list.append(divider)
                            divider_x_counter += 1
                        x_dividers_added = True

                    # Add Y dividers after Left piece (as in original)
                    for divider in y_dividers:
                        # Original divider positioning from working code:
                        # divider_y = 5 * spacing + 1 * Y + 3 * Z
                        # divider_x = n * (spacing + Z)
                        divider_y = 5 * settings.spacing + 1 * settings.Y + 3 * settings.Z
                        divider_x = divider_y_counter * (settings.spacing + settings.Z)
                        divider.base = Vec(divider_x, divider_y)
                        pieces_list.append(divider)
                        divider_y_counter += 1
                    y_dividers_added = True

                elif piece.pieceType == PieceType.Bottom:
                    piece.base = calculate_position(cc[1], rr[1])  # cc[1], rr[1] - Bottom piece
                    pieces_list.append(piece)

                    # Add any remaining dividers after Bottom piece if neither Back nor Left exist (fallback)
                    if not x_dividers_added:
                        for divider in x_dividers:
                            divider_y = 4 * settings.spacing + 1 * settings.Y + 2 * settings.Z
                            divider_x = divider_x_counter * (settings.spacing + settings.X)
                            divider.base = Vec(divider_x, divider_y)
                            pieces_list.append(divider)
                            divider_x_counter += 1
                        x_dividers_added = True

                    if not y_dividers_added:
                        for divider in y_dividers:
                            divider_y = 5 * settings.spacing + 1 * settings.Y + 3 * settings.Z
                            divider_x = divider_y_counter * (settings.spacing + settings.Z)
                            divider.base = Vec(divider_x, divider_y)
                            pieces_list.append(divider)
                            divider_y_counter += 1
                        y_dividers_added = True
                elif piece.pieceType == PieceType.Right:
                    piece.base = calculate_position(cc[2], rr[1])  # cc[2], rr[1] - Right piece
                    pieces_list.append(piece)
                elif piece.pieceType == PieceType.Top:
                    piece.base = calculate_position(cc[3], rr[1])  # cc[3], rr[1] - Top piece
                    pieces_list.append(piece)
                elif piece.pieceType == PieceType.Front:
                    piece.base = calculate_position(cc[1], rr[0])  # cc[1], rr[0] - Front piece
                    pieces_list.append(piece)
        elif settings.layout == Layout.THREE_PIECE:  # 3 Piece Layout - compact vertical layout
            # THREE_PIECE layout uses coordinate tuples to calculate positions
            # Original coordinate tuple definitions:
            row0 = (1, 0, 0, 0)  # top row
            row1y = (2, 0, 1, 0)  # second row, offset by Y
            row2 = (3, 0, 1, 1)  # third row, always offset by Y+Z

            col0 = (1, 0, 0, 0)  # left column
            col1z = (2, 0, 0, 1)  # second column, offset by Z

            rr = [row0, row1y, row2]
            cc = [col0, col1z]

            # Position pieces using original coordinate calculation
            def calculate_position(col_tuple, row_tuple) -> Vec:
                # Formula: x = xs * spacing + xx * X + xy * Y + xz * Z + initOffsetX
                # col_tuple = (xs, xx, xy, xz), row_tuple = (ys, yx, yy, yz)
                xs, xx, xy, xz = col_tuple
                ys, yx, yy, yz = row_tuple

                x = xs * settings.spacing + xx * settings.X + xy * settings.Y + xz * settings.Z + settings.initOffsetX
                y = ys * settings.spacing + yx * settings.X + yy * settings.Y + yz * settings.Z + settings.initOffsetY

                return Vec(x, y)

            # Create pieces in the correct order as original THREE_PIECE layout
            divider_x_counter = 0
            divider_y_counter = 0

            # Separate dividers from other pieces to avoid double processing
            main_pieces = [p for p in created_pieces if p.pieceType not in [PieceType.DividerX, PieceType.DividerY]]
            x_dividers = [p for p in created_pieces if p.pieceType == PieceType.DividerX]
            y_dividers = [p for p in created_pieces if p.pieceType == PieceType.DividerY]

            for piece in main_pieces:
                if piece.pieceType == PieceType.Back:
                    piece.base = calculate_position(cc[1], rr[1])  # cc[1], rr[1] - Back piece
                    pieces_list.append(piece)

                    # Add X dividers after Back piece (as in original)
                    for divider in x_dividers:
                        # Original divider positioning: divider_y = 4 * spacing + 1 * Y + 2 * Z
                        divider_y = 4 * settings.spacing + 1 * settings.Y + 2 * settings.Z
                        divider_x = divider_x_counter * (settings.spacing + settings.X)
                        divider.base = Vec(divider_x, divider_y)
                        pieces_list.append(divider)
                        divider_x_counter += 1

                elif piece.pieceType == PieceType.Left:
                    piece.base = calculate_position(cc[0], rr[0])  # cc[0], rr[0] - Left piece
                    pieces_list.append(piece)

                    # Add Y dividers after Left piece (as in original)
                    for divider in y_dividers:
                        # Original divider positioning: divider_y = 5 * spacing + 1 * Y + 3 * Z
                        divider_y = 5 * settings.spacing + 1 * settings.Y + 3 * settings.Z
                        divider_x = divider_y_counter * (settings.spacing + settings.Z)
                        divider.base = Vec(divider_x, divider_y)
                        pieces_list.append(divider)
                        divider_y_counter += 1

                elif piece.pieceType == PieceType.Bottom:
                    piece.base = calculate_position(cc[1], rr[0])  # cc[1], rr[0] - Bottom piece
                    pieces_list.append(piece)
        elif settings.layout == Layout.INLINE_COMPACT:  # Inline(compact) Layout
            # INLINE_COMPACT layout uses coordinate tuples to calculate positions
            # Original coordinate tuple definitions:
            row0 = (1, 0, 0, 0)  # top row
            row1y = (2, 0, 1, 0)  # second row, offset by Y
            row2 = (3, 0, 1, 1)  # third row, always offset by Y+Z

            col0 = (1, 0, 0, 0)  # left column
            col1x = (2, 1, 0, 0)  # second column, offset by X
            col2xx = (3, 2, 0, 0)  # third column, offset by 2*X
            col3xxz = (4, 2, 0, 1)  # fourth column, offset by 2*X+Z
            col4 = (5, 2, 0, 2)  # fifth column, always offset by 2*X+2*Z
            col5 = (6, 3, 0, 2)  # sixth column, always offset by 3*X+2*Z

            rr = [row0, row1y, row2]
            cc = [col0, col1x, col2xx, col3xxz, col4, col5]

            # Apply reductions based on missing pieces (from original code)
            def reduceOffsets(aa, start, dx, dy, dz):
                for ix in range(start + 1, len(aa)):
                    (s, x, y, z) = aa[ix]
                    aa[ix] = (s - 1, x - dx, y - dy, z - dz)

            if PieceType.Top not in piece_types:
                # remove col0, shift others left by X
                reduceOffsets(cc, 0, 1, 0, 0)
            if PieceType.Bottom not in piece_types:
                reduceOffsets(cc, 1, 1, 0, 0)
            if PieceType.Left not in piece_types:
                reduceOffsets(cc, 2, 0, 0, 1)
            if PieceType.Right not in piece_types:
                reduceOffsets(cc, 3, 0, 0, 1)
            if PieceType.Back not in piece_types:
                reduceOffsets(cc, 4, 1, 0, 0)

            # Position pieces using original coordinate calculation
            def calculate_position(col_tuple, row_tuple) -> Vec:
                # Formula: x = xs * spacing + xx * X + xy * Y + xz * Z + initOffsetX
                # col_tuple = (xs, xx, xy, xz), row_tuple = (ys, yx, yy, yz)
                xs, xx, xy, xz = col_tuple
                ys, yx, yy, yz = row_tuple

                x = xs * settings.spacing + xx * settings.X + xy * settings.Y + xz * settings.Z + settings.initOffsetX
                y = ys * settings.spacing + yx * settings.X + yy * settings.Y + yz * settings.Z + settings.initOffsetY

                return Vec(x, y)

            # Create pieces in the correct order as original INLINE_COMPACT layout
            divider_x_counter = 0
            divider_y_counter = 0

            # Separate pieces by type for proper ordering
            pieces_by_type = {}
            for piece in created_pieces:
                pieces_by_type[piece.pieceType] = piece

            # Follow exact original INLINE_COMPACT order: Back -> X dividers -> Left -> Y dividers -> Top -> Bottom -> Right -> Front
            if PieceType.Back in pieces_by_type:
                piece = pieces_by_type[PieceType.Back]
                piece.base = calculate_position(cc[4], rr[0])  # cc[4], rr[0] - Back piece
                pieces_list.append(piece)

            # Add X dividers after Back piece (as in original)
            divider_y = 4 * settings.spacing + 1 * settings.Y + 2 * settings.Z
            divider_x = divider_x_counter * (settings.spacing + settings.X)
            for i in created_pieces:
                if i.pieceType == PieceType.DividerX:
                    i.base = Vec(divider_x, divider_y)
                    pieces_list.append(i)
                    divider_x += (settings.spacing + settings.X)

            if PieceType.Left in pieces_by_type:
                piece = pieces_by_type[PieceType.Left]
                piece.base = calculate_position(cc[2], rr[0])  # cc[2], rr[0] - Left piece
                pieces_list.append(piece)

            # Add Y dividers after Left piece (as in original)
            divider_y = 5 * settings.spacing + 1 * settings.Y + 3 * settings.Z
            divider_x = divider_y_counter * (settings.spacing + settings.Z)
            for i in created_pieces:
                if i.pieceType == PieceType.DividerY:
                    i.base = Vec(divider_x, divider_y)
                    pieces_list.append(i)
                    divider_y += (settings.spacing + settings.Z)

            if PieceType.Top in pieces_by_type:
                piece = pieces_by_type[PieceType.Top]
                piece.base = calculate_position(cc[0], rr[0])  # cc[0], rr[0] - Top piece
                pieces_list.append(piece)

            if PieceType.Bottom in pieces_by_type:
                piece = pieces_by_type[PieceType.Bottom]
                piece.base = calculate_position(cc[1], rr[0])  # cc[1], rr[0] - Bottom piece
                pieces_list.append(piece)

            if PieceType.Right in pieces_by_type:
                piece = pieces_by_type[PieceType.Right]
                piece.base = calculate_position(cc[3], rr[0])  # cc[3], rr[0] - Right piece
                pieces_list.append(piece)

            if PieceType.Front in pieces_by_type:
                piece = pieces_by_type[PieceType.Front]
                piece.base = calculate_position(cc[5], rr[0])  # cc[5], rr[0] - Front piece
                pieces_list.append(piece)

        return pieces_list

    @staticmethod
    def create_pieces(settings: BoxSettings, tabs: TabConfiguration) -> list[Piece]:
        """Generate all pieces needed for the box without layout positioning"""

        def get_piece_tab_config(tabs: TabConfiguration, pieceType: PieceType) -> tuple[int, int]:
            """Get tab configuration for a specific piece type.
            Returns: (tabInfo, tabbed)"""
            tab_config_mapping = {
                PieceType.Back: (tabs.bkTabInfo, tabs.bkTabbed),
                PieceType.Front: (tabs.ftTabInfo, tabs.ftTabbed),
                PieceType.Left: (tabs.ltTabInfo, tabs.ltTabbed),
                PieceType.Right: (tabs.rtTabInfo, tabs.rtTabbed),
                PieceType.Bottom: (tabs.bmTabInfo, tabs.bmTabbed),
                PieceType.Top: (tabs.tpTabInfo, tabs.tpTabbed),
                # Dividers use the same tab config as their corresponding face
                PieceType.DividerX: (tabs.bkTabInfo, tabs.bkTabbed),  # Like Back face
                PieceType.DividerY: (tabs.ltTabInfo, tabs.ltTabbed),  # Like Left face
            }
            return tab_config_mapping.get(pieceType, (0, 0))

        def get_piece_dimensions(settings: BoxSettings, pieceType: PieceType) -> tuple[float, float, float, float]:
            """Calculate outside and inside dimensions for a piece type.
            Returns: (dx, dy, inside_dx, inside_dy)"""
            dimension_mapping = {
                PieceType.Back: (settings.X, settings.Z, settings.inside_X, settings.inside_Z),
                PieceType.Front: (settings.X, settings.Z, settings.inside_X, settings.inside_Z),
                PieceType.Left: (settings.Z, settings.Y, settings.inside_Z, settings.inside_Y),
                PieceType.Right: (settings.Z, settings.Y, settings.inside_Z, settings.inside_Y),
                PieceType.Bottom: (settings.X, settings.Y, settings.inside_X, settings.inside_Y),
                PieceType.Top: (settings.X, settings.Y, settings.inside_X, settings.inside_Y),
                PieceType.DividerX: (settings.X, settings.Z, settings.inside_X, settings.inside_Z),
                PieceType.DividerY: (settings.Z, settings.Y, settings.inside_Z, settings.inside_Y),
            }
            return dimension_mapping.get(pieceType, (0, 0, 0, 0))

        def make_sides(settings : BoxSettings, tabs: TabConfiguration, pieceType: PieceType) -> list[Side]:
            """Create sides for a piece using dimensions and tab config from settings."""
            dx, dy, inside_dx, inside_dy = get_piece_dimensions(settings, pieceType)
            tabInfo, tabbed = get_piece_tab_config(tabs, pieceType)
            # Calculate face type from piece type

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

            if pieceType in [PieceType.Top, PieceType.Bottom]:  # Top/Bottom faces
                # Side A/C (horizontal) gets Y-axis divider spacing (div_x)
                # Side B/D (vertical) gets X-axis divider spacing (div_y)"
                horizontal_spacing = settings.div_x_spacing if settings.div_x_spacing else calculate_even_spacing(settings.div_x, settings.Y, settings.thickness)
                vertical_spacing = settings.div_y_spacing if settings.div_y_spacing else calculate_even_spacing(settings.div_y, settings.X, settings.thickness)
            elif pieceType in [PieceType.Front, PieceType.Back, PieceType.DividerX]:  # Front/Back faces
                # Side A/C (horizontal) gets no dividers (Z direction)
                # Side B/D (vertical) gets X-axis divider spacing (div_y)
                horizontal_spacing = []
                vertical_spacing = settings.div_y_spacing if settings.div_y_spacing else calculate_even_spacing(settings.div_y, settings.X, settings.thickness)
            elif pieceType in [PieceType.Left, PieceType.Right, PieceType.DividerY]:  # Left/Right faces
                # Side A/C (horizontal) gets Y-axis divider spacing (div_x)
                # Side B/D (vertical) gets no dividers (Z direction)
                horizontal_spacing = settings.div_x_spacing if settings.div_x_spacing else calculate_even_spacing(settings.div_x, settings.Y, settings.thickness)
                vertical_spacing = []
            else:
                horizontal_spacing = []
                vertical_spacing = []

            # Sides: A=top, B=right, C=bottom, D=left
            sides = [
                Side(settings, Sides.A, bool(tabInfo & 0b1000), bool(tabbed & 0b1000), dx, inside_dx),
                Side(settings, Sides.B, bool(tabInfo & 0b0100), bool(tabbed & 0b0100), dy, inside_dy),
                Side(settings, Sides.C, bool(tabInfo & 0b0010), bool(tabbed & 0b0010), dx, inside_dx),
                Side(settings, Sides.D, bool(tabInfo & 0b0001), bool(tabbed & 0b0001), dy, inside_dy)
            ]

            # Assign divider spacings to appropriate sides
            sides[Sides.A].divider_spacings = horizontal_spacing  # A (top)
            sides[Sides.B].divider_spacings = vertical_spacing    # B (right)
            sides[Sides.C].divider_spacings = horizontal_spacing  # C (bottom)
            sides[Sides.D].divider_spacings = vertical_spacing    # D (left)


            if pieceType not in [PieceType.DividerX, PieceType.DividerY]:
                # Already extracted above from Side objects
                wall = pieceType not in [PieceType.Top, PieceType.Bottom]
                floor = pieceType in [PieceType.Bottom, PieceType.Top]

                if pieceType not in [PieceType.Front, PieceType.Back] and (settings.keydiv_floor or wall) and (settings.keydiv_walls or floor):
                    if sides[Sides.A].has_tabs:
                        sides[Sides.A].num_dividers = settings.div_x
                    elif sides[Sides.C].has_tabs:
                        sides[Sides.C].num_dividers = settings.div_x


                if pieceType not in [PieceType.Left, PieceType.Right] and ((settings.keydiv_floor or wall) and (settings.keydiv_walls or floor)):
                    if sides[Sides.B].has_tabs:
                        sides[Sides.B].num_dividers = settings.div_y
                    elif sides[Sides.D].has_tabs:
                        sides[Sides.D].num_dividers = settings.div_y

            return sides

        pieces = []

        # Create main box faces using piece-driven approach
        if PieceType.Back in settings.piece_types:
            sides = make_sides(settings, tabs, PieceType.Back)
            pieces.append(Piece(sides, PieceType.Back))

        if PieceType.Left in settings.piece_types:
            sides = make_sides(settings, tabs, PieceType.Left)
            pieces.append(Piece(sides, PieceType.Left))

        if PieceType.Bottom in settings.piece_types:
            sides = make_sides(settings, tabs, PieceType.Bottom)
            pieces.append(Piece(sides, PieceType.Bottom))

        if PieceType.Right in settings.piece_types:
            sides = make_sides(settings, tabs, PieceType.Right)
            pieces.append(Piece(sides, PieceType.Right))

        if PieceType.Top in settings.piece_types:
            sides = make_sides(settings, tabs, PieceType.Top)
            pieces.append(Piece(sides, PieceType.Top))

        if PieceType.Front in settings.piece_types:
            sides = make_sides(settings, tabs, PieceType.Front)
            pieces.append(Piece(sides, PieceType.Front))

        # Create dividers using piece-driven approach
        if settings.div_x > 0:
            for n in range(int(settings.div_x)):
                sides = make_sides(settings, tabs, PieceType.DividerX)

                # Remove tabs from dividers if not required
                # NOTE: Setting is_male=True is a workaround for geometric offset calculation
                # when has_tabs=False. This coupling should be cleaned up in future refactoring.
                if not settings.keydiv_floor:
                    sides[0].is_male = sides[2].is_male = True # sides A and C
                    sides[0].has_tabs = sides[2].has_tabs = False
                if not settings.keydiv_walls:
                    sides[1].is_male = sides[3].is_male = True # sides B and D
                    sides[1].has_tabs = sides[3].has_tabs = False

                sides[1].num_dividers = settings.div_y * (settings.div_x > 0)
                piece = Piece(sides, PieceType.DividerX)

                pieces.append(piece)

        if settings.div_y > 0:
            for n in range(int(settings.div_y)):
                sides = make_sides(settings, tabs, PieceType.DividerY)

                # Remove tabs from dividers if not required
                # NOTE: Setting is_male=True is a workaround for geometric offset calculation
                # when has_tabs=False. This coupling should be cleaned up in future refactoring.
                if not settings.keydiv_walls:
                    #sides[1].length = sides[3].length = settings.inside_Y
                    #sides[0].is_male = sides[2].is_male = False # sides A and C
                    sides[0].is_male = sides[2].is_male = True # sides A and C
                    sides[0].has_tabs = sides[2].has_tabs = False
                if not settings.keydiv_floor:
                    #sides[0].length = sides[2].length = settings.inside_Z
                    #sides[1].is_male = sides[3].is_male = False # sides B and D
                    sides[1].is_male = sides[3].is_male = True # sides B and D
                    sides[1].has_tabs = sides[3].has_tabs = False
                sides[0].num_dividers = settings.div_x * (settings.div_x > 0)
                piece = Piece(sides, PieceType.DividerY)
                pieces.append(piece)

        return pieces

    def generate_pieces(self, pieces: list[Piece], config: BoxConfiguration, settings: BoxSettings) -> None:
        """Generate and draw all pieces based on the configuration"""

        for piece in pieces:  # generate and draw each piece of the box
            pieceType = piece.pieceType

            group = self.makeGroup("xdivider" if pieceType == PieceType.DividerX else ("ydivider" if pieceType == PieceType.DividerY else "piece"))

            if settings.schroff and pieceType in [PieceType.Left, PieceType.Right] and config.schroff_settings:
                aSide, bSide, cSide, dSide = piece.sides
                (x, y) = piece.base

                schroff = config.schroff_settings
                dx = piece.dx
                dy = piece.dy

                log(f"rail holes enabled on piece at ({x + settings.thickness}, {y + settings.thickness})")
                log(f"abcd = ({aSide.has_tabs and aSide.is_male},{bSide.has_tabs and bSide.is_male},{cSide.has_tabs and cSide.is_male},{dSide.has_tabs and dSide.is_male})")
                log(f"dxdy = ({dx},{dy})")
                rhxoffset = schroff.rail_mount_depth + settings.thickness
                if piece.pieceType == PieceType.Left:
                    rhx = x + rhxoffset
                elif piece.pieceType == PieceType.Right:
                    rhx = x - rhxoffset + dx
                else:
                    rhx = 0
                log("rhxoffset = %d, rhx= %d" % (rhxoffset, rhx))
                rystart = y + (settings.schroff.rail_height / 2) + settings.thickness
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
            for side in piece.sides:
                self.render_side(group, piece, side, settings)

            # All pieces drawn, now optimize the paths if required
            if self.options.optimize:
                self.optimizePiece(group)

    def _run_effect(self) -> None:

        # Step 1: Parse options into settings
        settings = self.parse_options_to_settings()

        # Store values needed for other methods
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


        tabs = self.create_tabs_configuration(settings, config.piece_types)
        pieces = self.create_pieces(settings, tabs)

        pieces = self.apply_layout(pieces, settings)

        # Step 3: Generate and draw all pieces
        self.generate_pieces(pieces, config, settings)

    def optimizePiece(self, group : Group) -> None:
        # Step 1: Combine paths to form the outer boundary
        skip_elements = []
        paths = [child for child in group if isinstance(child, PathElement)]

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
        paths = [child for child in group if isinstance(child, PathElement)]

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

    @staticmethod
    def dimpleStr(
        tabVector: float,
        vector: Vec,
        dir: Vec,
        notDir: Vec,
        ddir: int,
        isMale: bool,
        dimpleLength: float,
        dimpleHeight: float
    ) -> Path:
        ds = Path()
        if not isMale:
            ddir = -ddir
        if dimpleHeight > 0 and tabVector != 0:
            if tabVector > 0:
                dimpleStart = (tabVector - dimpleLength) / 2 - dimpleHeight
                tabSign = 1
            else:
                dimpleStart = (tabVector + dimpleLength) / 2 + dimpleHeight
                tabSign = -1
            Vd = vector + notDir * dimpleStart
            ds.append(Line(*Vd))
            Vd += (notDir * tabSign * dimpleHeight) - (dir * ddir * dimpleHeight)
            ds.append(Line(*Vd))
            Vd += notDir * (tabSign * dimpleLength)
            ds.append(Line(*Vd))
            Vd += (notDir * tabSign * dimpleHeight) + (dir * ddir * dimpleHeight)
            ds.append(Line(*Vd))
        return ds

    def render_side(
        self,
        group: Group,
        piece: Piece,
        side: Side,
        settings: BoxSettings = None
    ) -> None:
        """Draw one side of a piece, with tabs or holes as required. Returns result in group"""

        root = piece.base

        for i in self.render_side_side(root, side, settings) + \
                ( self.render_side_slots(root, side, settings)
                    if piece.pieceType in [PieceType.DividerY, PieceType.DividerX]
                    else self.render_side_holes(root, side, settings)):
            group.add(i)

    def render_side_side(
        self,
        root: Vec,
        side: Side,
        settings: BoxSettings = None
    ) -> list[PathElement]:
        """Draw one side of a piece"""

        dirX, dirY = direction = side.direction

        length = side.length

        isMale = side.is_male
        notMale = not isMale
        thickness = side.thickness

        if side.has_tabs:
            # Calculate direction
            tabDepth = thickness if (direction == (1, 0) or direction == (0, -1)) != isMale else -thickness
        else:
            tabDepth = 0

        kerf = settings.kerf
        halfkerf = kerf / 2
        dogbone = side.dogbone

        divisions = side.divisions
        gapWidth = side.gap_width
        tabWidth = side.tab_width


        if isMale:  # kerf correction
            gapWidth -= settings.kerf
            tabWidth += settings.kerf
            first = halfkerf
        else:
            gapWidth += settings.kerf
            tabWidth -= settings.kerf
            first = -halfkerf

        firstVec = 0
        secondVec = tabDepth
        notDirX, notDirY = notDir = self._get_perpendicular_flags(direction)
        s = Path()

        startOffsetX, startOffsetY = startOffset = side.start_offset

        vector = startOffset * thickness

        s.append(Move(*vector))

        # Set vector for tab generation
        if side.tab_symmetry == TabSymmetry.ROTATE_SYMMETRIC:
            vector = Vec(startOffsetX if startOffsetX else dirX, startOffsetY if startOffsetY else dirY) * thickness
        else:
            if notDirX:
                vector = Vec(vector.x, 0) # set correct line start for tab generation
            if notDirY:
                vector = Vec(0, vector.y) # set correct line start for tab generation

        # generate line as tab or hole using:
        #   last co-ord:Vx,Vy ; tab dir:tabVec  ; direction:dirx,diry ; thickness:thickness
        #   divisions:divs ; gap width:gapWidth ; tab width:tabWidth

        vecHalfKerf = Vec(dirX * halfkerf, dirY * halfkerf)

        for tabDivision in range(1, int(divisions)):
            if tabDivision % 2:
                # draw the gap
                vector += direction * (gapWidth
                                            + (first if not (isMale and dogbone) else 0)
                                            + dogbone * kerf * isMale
                                            + firstVec)
                s.append(Line(*vector))
                if dogbone and isMale:
                    vector -= vecHalfKerf
                    s.append(Line(*vector))
                # draw the starting edge of the tab
                s.extend(self.dimpleStr(
                    secondVec, vector, direction, notDir, 1, isMale,
                    settings.dimple_length, settings.dimple_height
                ))
                vector += notDir * secondVec
                s.append(Line(*vector))
                if dogbone and notMale:
                    vector -= vecHalfKerf
                    s.append(Line(*vector))

            else:
                # draw the tab
                vector += direction * (tabWidth + dogbone * kerf * notMale + firstVec)
                s.append(Line(*vector))
                if dogbone and notMale:
                    vector -= vecHalfKerf
                    s.append(Line(*vector))
                # draw the ending edge of the tab
                s.extend(self.dimpleStr(
                    secondVec, vector, direction, notDir, -1, isMale,
                    settings.dimple_length, settings.dimple_height
                ))
                vector += notDir * secondVec
                s.append(Line(*vector))
                if dogbone and isMale:
                    vector -= vecHalfKerf
                    s.append(Line(*vector))
            (secondVec, firstVec) = (-secondVec, -firstVec)  # swap tab direction
            first = 0

        # finish the line off
        s.append(Line(*(side.next.start_offset * thickness + direction * length)))

        rootX, rootY = root + side.root_offset

        # Drop some precision to avoid fp differences # Practially rounds floats to 4 decimals
        s = Path(str(s))
        sidePath = self.makeLine(s.translate(rootX, rootY), "side")
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
        root: Vec,
        side: Side,
        settings: BoxSettings
    ) -> list[PathElement]:
        """Draw tabs or holes as required"""

        numDividers = side.num_dividers
        if numDividers == 0 or side.name not in (Sides.A, Sides.B):
            return []

        dividerSpacings = side.divider_spacings

        dirX, dirY = direction = side.direction

        root_offs = side.root_offset
        startOffset = side.start_offset

        startOffsetX, startOffsetY = startOffset
        length = side.length

        thickness = side.thickness

        kerf = settings.kerf
        halfkerf = kerf / 2

        nodes = []

        if side.is_male:  # kerf correction
            first = halfkerf
        else:
            first = -halfkerf

        notDirX, notDirY = self._get_perpendicular_flags(direction)
        if side.tab_symmetry == TabSymmetry.ROTATE_SYMMETRIC:
            dividerEdgeOffsetX = dirX * thickness
            dividerEdgeOffsetY = thickness
            vectorX = (startOffsetX if startOffsetX else dirX) * thickness
            vectorY = (startOffsetY if startOffsetY else dirY) * thickness
        else:
            dividerEdgeOffsetX = dirY * thickness #* side.prev.has_tabs
            dividerEdgeOffsetY = dirX * thickness #* side.prev.has_tabs
            vectorX = startOffsetX * thickness
            vectorY = startOffsetY * thickness
            if notDirX:
                vectorY = 0  # set correct line start for tab generation
            if notDirY:
                vectorX = 0

        for dividerNumber in range(numDividers):
            base_pos = Vec(vectorX, vectorY)
            cumulative_position = self.calculate_cumulative_position(dividerNumber + 1, dividerSpacings, thickness)
            divider_offset = Vec(-dirY * cumulative_position, dirX * cumulative_position)
            edge_offset = Vec(-dividerEdgeOffsetX, -dividerEdgeOffsetY)
            kerf_offset = Vec(notDirX * halfkerf, notDirY * halfkerf)

            start_pos = base_pos + divider_offset + edge_offset + kerf_offset

            h = Path()
            h.append(Move(*start_pos))

            slot_end = start_pos + direction * (first + length / 2)
            h.append(Line(*slot_end))

            side_offset = slot_end + Vec(notDirX * (thickness - kerf), notDirY * (thickness - kerf))
            h.append(Line(*side_offset))

            back_to_start = side_offset - direction * (first + length / 2)
            h.append(Line(*back_to_start))

            final_pos = back_to_start - Vec(notDirX * (thickness - kerf), notDirY * (thickness - kerf))
            h.append(Line(*final_pos))
            h.append(ZoneClose())
            nodes.append(self.makeLine(h, "slot"))

        rootX, rootY = root + root_offs
        for node in nodes:
             node.path = node.path.translate(rootX, rootY)

        return nodes

    def render_side_holes(
        self,
        root: Vec,
        side: Side,
        settings: BoxSettings
    ) -> list[PathElement]:
        """Draw tabs or holes as required"""

        numDividers = side.num_dividers
        if numDividers == 0:
            return []

        dividerSpacings = side.divider_spacings

        dirX, dirY = direction = side.direction

        startOffsetX, startOffsetY = startOffset = side.start_offset

        isMale = side.is_male
        notMale = not isMale
        thickness = side.thickness

        if side.has_tabs:
            # Calculate direction
            tabDepth = thickness if (direction == (1, 0) or direction == (0, -1)) != isMale else -thickness
        else:
            tabDepth = 0

        kerf = settings.kerf
        halfkerf = kerf / 2
        dogbone = side.dogbone

        nodes = []

        divisions = side.divisions
        gapWidth = side.gap_width
        tabWidth = side.tab_width

        if isMale:  # kerf correction
            gapWidth -= settings.kerf
            tabWidth += settings.kerf
            first = halfkerf
        else:
            gapWidth += settings.kerf
            tabWidth -= settings.kerf
            first = -halfkerf

        vec = tabDepth
        notDirX, notDirY = notDirection = self._get_perpendicular_flags(direction)

        if side.tab_symmetry == TabSymmetry.ROTATE_SYMMETRIC:
            vector = Vec((startOffsetX if startOffsetX else dirX) * thickness,
                    (startOffsetY if startOffsetY else dirY) * thickness)
        else:
            vector = startOffset * thickness
            if notDirX:
                vector = Vec(vector.x, 0) # set correct line start for tab generation
            if notDirY:
                vector = Vec(0, vector.y)  # set correct line start for tab generation

        w = gapWidth if isMale else tabWidth
        if side.tab_symmetry == TabSymmetry.XY_SYMMETRIC:
            w -= startOffsetX * thickness

        # generate line as tab or hole using:
        #   last co-ord:Vx,Vy ; tab dir:tabVec  ; direction:dirx,diry ; thickness:thickness
        #   divisions:divs ; gap width:gapWidth ; tab width:tabWidth
        firstHole = True
        for tabDivision in range(divisions):
            # draw holes for divider tabs to key into side walls
            if ((tabDivision % 2) == 0) != (not isMale) and numDividers > 0:
                w = gapWidth if isMale else tabWidth
                if tabDivision == 0 and side.tab_symmetry == TabSymmetry.XY_SYMMETRIC:
                    w -= startOffsetX * thickness
                holeLen = direction * (w + first)
                if firstHole:
                    firstHoleLen = holeLen
                    firstHole = False
                if (tabDivision == 0 or tabDivision == (divisions - 1)) and side.tab_symmetry == TabSymmetry.XY_SYMMETRIC:
                    holeLen = firstHoleLen
                for dividerNumber in range(numDividers):
                    base_pos = vector
                    cumulative_position = self.calculate_cumulative_position(dividerNumber + 1, dividerSpacings, thickness)
                    divider_offset = Vec(-dirY * cumulative_position, dirX * cumulative_position)
                    kerf_offset = Vec(halfkerf if notDirX else 0, -(halfkerf if notDirY else 0))
                    dogbone_offset = Vec((dirX * halfkerf - first * dirX) if dogbone else 0,
                                    (dirY * halfkerf - first * dirY) if dogbone else 0)

                    pos = base_pos + divider_offset + kerf_offset + dogbone_offset

                    if tabDivision == 0 and side.tab_symmetry == TabSymmetry.XY_SYMMETRIC:
                        pos += Vec(startOffsetX * thickness, 0)

                    h = Path()
                    h.append(Move(*pos))

                    pos += holeLen
                    h.append(Line(*pos))

                    thickVec = Vec(notDirX * (vec - kerf), notDirY * (vec + kerf))
                    pos += thickVec
                    h.append(Line(*pos))

                    pos -= holeLen
                    h.append(Line(*pos))

                    pos -= thickVec
                    h.append(Line(*pos))
                    h.append(ZoneClose())
                    nodes.append(self.makeLine(h, "hole"))

            if (tabDivision % 2) == 0:
                # draw the gap
                vector += direction * (
                        gapWidth
                        + (first if not (isMale and dogbone) else 0)
                        + dogbone * kerf * isMale
                    )

                if dogbone and isMale:
                    vector -= direction * halfkerf
            else:
                # draw the tab
                vector += direction * (tabWidth + dogbone * kerf * notMale)

            if dogbone and notMale:
                vector -= direction * halfkerf
            vector += notDirection * vec

            vec = - vec  # swap tab direction
            first = 0

        rootX, rootY = root + side.root_offset
        for node in nodes:
            node.path = node.path.translate(rootX, rootY)

        return nodes

    def _get_perpendicular_flags(self, direction: tuple[float, float]) -> Vec:
        """Get perpendicular direction flags for easier axis selection"""
        dirX, dirY = direction
        return Vec(dirX == 0, dirY == 0)  # (notDirX, notDirY)


if __name__ == "__main__":
  # Create effect instance and apply it.
  effect = TabbedBoxMaker(cli=True)
  effect.run()
