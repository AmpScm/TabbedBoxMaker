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
import sys

from inkex import Group, PathElement, Metadata, Desc
from inkex.paths import Path
from inkex.paths.lines import Line, Move, ZoneClose

from copy import deepcopy

from tabbedboxmaker.enums import BoxType, Layout, TabSymmetry, DividerKeying, Sides, PieceType
from tabbedboxmaker.InkexShapely import try_combine_paths, try_attach_paths, try_clean_paths
from tabbedboxmaker.__about__ import __version__ as BOXMAKER_VERSION
from tabbedboxmaker.settings import BoxSettings, BoxConfiguration, TabConfiguration, Piece, SchroffSettings, Side, Vec
from tabbedboxmaker.Generators import CliEnabledGenerator

_ = gettext.gettext

def log(text: str) -> None:
    if "STDERR_LOG" in os.environ:
        print(text, file=sys.stderr)

def IntBoolean(value):
    """ArgParser function to turn a boolean string into a python boolean"""

    b = inkex.utils.Boolean(value)

    if b is None:
        if value == "0":
            return False
        elif value == "1":
            return True
    return b

class TabbedBoxMaker(CliEnabledGenerator):
    line_thickness: float = 1
    version = BOXMAKER_VERSION
    settings : BoxSettings
    raw_hairline_thickness: float = None
    hairline_thickness: float = None
    schroff = False
    line_color = '#000000'
    no_subtract = False

    def __init__(self, cli=True, schroff=False, inkscape=False):
        """Initialize the BoxMaker extension."""
        self.schroff = schroff

        self.container_label = "Tabbed Box" if not schroff else "Schroff Box"

        # Call the base class constructor.
        super().__init__(cli=cli, inkscape=inkscape)

    def makeGroup(self, id="piece") -> Group:
        # Create a new group and add element created from line string
        group = Group(id=self.makeId(id))

        return group

    def makeLine(self, path , id : str = "line") -> PathElement:
        line = PathElement(id=self.makeId(id))

        if self.line_thickness == self.raw_hairline_thickness:
            line.style = { "stroke": self.line_color, "stroke-width"  : str(self.hairline_thickness), "fill": "none", "vector-effect": "non-scaling-stroke", "-inkscape-stroke": "hairline"}
        else:
            line.style = { "stroke": self.line_color, "stroke-width"  : str(self.line_thickness), "fill": "none" }
        line.path = Path(path)
        return line



    def makeCircle(self, r, c, id : str = "circle"):
        (cx, cy) = c
        log("putting circle at (%d,%d)" % (cx,cy))
        line = PathElement.arc((cx, cy), r, id=self.makeId(id))
        if self.line_thickness == self.hairline_thickness:
            line.style = { "stroke": self.line_color, "stroke-width"  : str(self.hairline_thickness), "fill": "none", "vector-effect": "non-scaling-stroke", "-inkscape-stroke": "hairline" }
        else:
            line.style = { "stroke": self.line_color, "stroke-width"  : str(self.line_thickness), "fill": "none" }
        return line



    def add_arguments(self, pars) -> None:
        """Define options"""

        super().add_arguments(pars)

        if self.schroff:
            self.arg_parser.add_argument(
                "--rail_height",
                type=float,
                dest="rail_height",
                default=10.0,
                help="Height of rail (float)",
            )
            self.arg_parser.add_argument(
                "--rail_mount_depth",
                type=float,
                dest="rail_mount_depth",
                default=17.4,
                help="Depth at which to place hole for rail mount bolt (float)",
            )
            self.arg_parser.add_argument(
                "--rail_mount_centre_offset",
                type=float,
                dest="rail_mount_centre_offset",
                default=0.0,
                help="How far toward row centreline to offset rail mount bolt (from rail centreline) (float)",
            )
            self.arg_parser.add_argument(
                "--rows",
                type=int,
                dest="rows",
                default=0,
                help="Number of Schroff rows (int)",
            )
            self.arg_parser.add_argument(
                "--hp",
                type=int,
                dest="hp",
                default=0,
                help="Width (TE/HP units) of Schroff rows (int)",
            )
            self.arg_parser.add_argument(
                "--row_spacing",
                type=float,
                dest="row_spacing",
                default=10.0,
                help="Height of rail (float)",
            )
        else:
            self.arg_parser.add_argument(
                "--inside",
                type=IntBoolean,
                dest="inside",
                default=0,
                help="Int/Ext Dimension",
                choices=[True, False, '0', '1'],
            )
            self.arg_parser.add_argument(
                "--length",
                type=float,
                dest="length",
                default=100,
                help="Length of Box (float)",
            )
            self.arg_parser.add_argument(
                "--width",
                type=float,
                dest="width",
                default=100,
                help="Width of Box (float)",
            )
        self.arg_parser.add_argument(
            "--depth",
            type=float,
            dest="height",
            default=100,
            help="Height of Box (float)",
        )
        self.arg_parser.add_argument(
            "--tab",
            type=float,
            dest="tab",
            default=5,
            help="Nominal Tab Width (float)",
        )
        self.arg_parser.add_argument(
            "--equal",
            type=IntBoolean,
            dest="equal_tabs",
            default=False,
            help="Equal/Prop Tabs",
            choices=[True, False, '0', '1'],
        )
        self.arg_parser.add_argument(
            "--tabsymmetry",
            type=int,
            dest="tabsymmetry",
            default=0,
            help="Tab style (0=XY symmetric, 1=Rotationally symmetric, 2=Antisymmetric)",
            choices=[0, 1, 2],
        )
        self.arg_parser.add_argument(
            "--tabtype",
            type=IntBoolean,
            dest="tabtype",
            default=False,
            help="Tab type: 0=regular or 1=dogbone",
            choices=[0, 1],
        )
        self.arg_parser.add_argument(
            "--dimpleheight",
            type=float,
            dest="dimpleheight",
            default=0,
            help="Tab Dimple Height",
        )
        self.arg_parser.add_argument(
            "--dimplelength",
            type=float,
            dest="dimplelength",
            default=0,
            help="Tab Dimple Tip Length",
        )
        self.arg_parser.add_argument(
            "--hairline",
            type=IntBoolean,
            dest="hairline",
            default=False,
            help="Line Thickness (True/False)",
            choices=[True, False, '0', '1'],
        )
        self.arg_parser.add_argument(
            "--line-thickness",
            type=float,
            dest="line_thickness",
            default=0.1,
            help="Line Thickness (if not hairline)",
        )
        self.arg_parser.add_argument(
            "--line-color",
            type=str,
            dest="color",
            default="black",
            help="Line Color",
            choices=["black", "red", "blue", "green"]
        )
        self.arg_parser.add_argument(
            "--thickness",
            type=float,
            dest="thickness",
            default=5.0,
            help="Thickness of Material",
        )
        self.arg_parser.add_argument(
            "--kerf",
            type=float,
            dest="kerf",
            default=0,
            help="Kerf (width of cut)",
        )
        self.arg_parser.add_argument(
            "--style",
            type=int,
            dest="style",
            default=1,
            help="Layout/Style",
        )
        self.arg_parser.add_argument(
            "--spacing",
            type=float,
            dest="spacing",
            default=3,
            help="Part Spacing",
        )
        self.arg_parser.add_argument(
            "--boxtype",
            type=int,
            dest="boxtype",
            default=1,
            help="Box type",
        )
        self.arg_parser.add_argument(
            "--div-l",
            type=int,
            dest="div_x",
            default=0,
            help="Dividers (Length axis / X axis)",
        )
        self.arg_parser.add_argument(
            "--div-w",
            type=int,
            dest="div_y",
            default=0,
            help="Dividers (Width axis / Y axis)",
        )
        self.arg_parser.add_argument(
            "--keydiv",
            type=int,
            dest="keydiv",
            default=3,
            help="Key dividers into walls/floor",
        )
        self.arg_parser.add_argument(
            "--div-l-spacing",
            type=str,
            dest="div_x_spacing",
            default="",
            help="Custom spacing for X-axis dividers (semicolon separated widths)",
        )
        self.arg_parser.add_argument(
            "--div-w-spacing",
            type=str,
            dest="div_y_spacing",
            default="",
            help="Custom spacing for Y-axis dividers (semicolon separated widths)",
        )
        self.arg_parser.add_argument(
            "--combine",
            type=IntBoolean,
            dest="combine",
            default=True,
            help="Combine and clean paths",
            choices=[True, False, '0', '1'],
        )
        self.arg_parser.add_argument(
            "--cutout",
            type=IntBoolean,
            dest="cutout",
            default=True,
            help="Cut holes from parent pieces",
            choices=[True, False, '0', '1'],
        )

    @staticmethod
    def parse_divider_spacing(spacing_str: str, available_width: float,
                            thickness: float, num_dividers: int, reverse: bool=False) -> list[float]:
        """Parse semicolon-separated spacing values and validate them"""
        if num_dividers <= 0:
            return []
        available_width -= num_dividers * thickness
        spacing_str = spacing_str if spacing_str else ""

        # Parse the spacing values (these represent section widths, not divider positions)
        try:
            values = [float(v.strip()) for v in spacing_str.split(';') if v.strip()]
        except ValueError as e:
            inkex.errormsg(f"Error: Invalid divider spacing format: {e}")
            exit(1)

        # num_dividers represents the total number of dividers to place
        # values represents the widths of the first N sections (before each specified divider)
        # We need num_dividers + 1 total sections (sections between and around dividers)

        num_sections = num_dividers + 1

        # Validate number of values
        if len(values) > num_sections:
            inkex.errormsg(f"Error: Too many divider spacing values ({len(values)}) for {num_dividers} dividers (max {num_sections} sections)")
            exit(1)

        # Calculate remaining space for auto-sized sections
        used_width = sum(values)
        remaining_sections = num_sections - len(values)

        if remaining_sections > 0:
            remaining_width = available_width - used_width
            if remaining_width <= 0:
                inkex.errormsg(f"Error: Specified section widths exceed available space (remaining width {remaining_width:.2f})")
                exit(1)
            auto_width = max(remaining_width / remaining_sections, 0)
            values.extend([auto_width] * remaining_sections)
            used_width += auto_width * remaining_sections

        if used_width > available_width:
            inkex.errormsg(f"Error: Total section widths ({used_width:.2f}) exceed available space ({available_width:.2f})")
            exit(1)
        elif used_width < available_width:
            inkex.errormsg(f"Error: Total section widths ({used_width:.2f}) are less than available space ({available_width:.2f})")
            exit(1)

        if reverse:
            values.reverse()
        return values


    def parse_options_to_settings(self) -> BoxSettings:
        """Parse command line options into a BoxSettings object"""

        # Get access to main SVG document element and get its dimensions.
        svg = self.document.getroot()

        # Get script's option values.
        hairline = self.options.hairline
        unit = str(self.options.unit).lower()
        inside = self.options.inside

        if unit == 'document':
            unit = svg.document_unit

        kerf = self.svg.unittouu(str(self.options.kerf) + unit)

        # Set the line thickness
        line_thickness = self.hairline_thickness if hairline else self.svg.unittouu(str(self.options.line_thickness) + unit)
        if line_thickness == 1.0:
            line_thickness = 1 # Reproduce old output

        schroff = self.schroff
        if schroff:
            # schroffmaker.inx

            # minimally different behaviour for schroffmaker.inx vs. boxmaker.inx
            # essentially schroffmaker.inx is just an alternate interface with different
            # default settings, some options removed, and a tiny amount of extra
            # logic

            rows = self.options.rows
            rail_height = self.svg.unittouu(str(self.options.rail_height) + unit)
            row_centre_spacing = self.svg.unittouu(str(122.5) + unit)
            row_spacing = self.svg.unittouu(str(self.options.row_spacing) + unit)
            rail_mount_depth = self.svg.unittouu(str(self.options.rail_mount_depth) + unit)
            rail_mount_centre_offset = self.svg.unittouu(str(self.options.rail_mount_centre_offset) + unit)
            rail_mount_radius = self.svg.unittouu(str(2.5) + unit)

            X = self.svg.unittouu(str(self.options.hp * 5.08) + unit)
            # 122.5mm vertical distance between mounting hole centres of 3U
            # Schroff panels
            row_height = rows * (row_centre_spacing + rail_height)
            # rail spacing in between rows but never between rows and case
            # panels
            row_spacing_total = (rows - 1) * row_spacing
            Y = row_height + row_spacing_total
            inside = False
        else:
            # boxmaker.inx
            X = self.svg.unittouu(str(self.options.length) + unit)
            Y = self.svg.unittouu(str(self.options.width) + unit)

            # Default values when not in Schroff mode
            rows = 0
            rail_height = 0.0
            row_spacing = 0.0
            rail_mount_depth = 0.0
            rail_mount_centre_offset = 0.0
            rail_mount_radius = 0.0


        Z = self.svg.unittouu(str(self.options.height) + unit)
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
        cutout = self.options.cutout
        combine = self.options.combine

        piece_types = [PieceType.Back, PieceType.Left, PieceType.Bottom, PieceType.Right, PieceType.Top, PieceType.Front]
        if box_type == BoxType.ONE_SIDE_OPEN:
            piece_types = [PieceType.Bottom, PieceType.Front, PieceType.Back, PieceType.Left, PieceType.Right]
        elif box_type == BoxType.TWO_SIDES_OPEN:
            piece_types = [PieceType.Bottom, PieceType.Front, PieceType.Left, PieceType.Right]
        elif box_type == BoxType.THREE_SIDES_OPEN:
            piece_types = [PieceType.Bottom,PieceType.Front, PieceType.Left]
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
        div_x_spacing = self.parse_divider_spacing(self.options.div_x_spacing, inside_Y, thickness, div_x, reverse=True)
        div_y_spacing = self.parse_divider_spacing(self.options.div_y_spacing, inside_X, thickness, div_y, reverse=True)

        return BoxSettings(
            X=X, Y=Y, Z=Z,
            inside_X=inside_X, inside_Y=inside_Y, inside_Z=inside_Z,
            thickness=thickness, tab_width=tab_width, equal_tabs=equal_tabs,
            tab_symmetry=tabSymmetry, dimple_height=dimpleHeight, dimple_length=dimpleLength,
            dogbone=dogbone, layout=layout, spacing=spacing, boxtype=box_type,
            piece_types=piece_types, div_x=div_x, div_y=div_y, div_x_spacing=div_x_spacing, div_y_spacing=div_y_spacing,
            keydiv_walls=keydivwalls, keydiv_floor=keydivfloor,
            initOffsetX=initOffsetX, initOffsetY=initOffsetY,
            hairline=hairline, line_color=self.options.color,
            schroff=schroff, kerf=kerf, line_thickness=line_thickness, unit=unit, rows=rows,
            rail_height=rail_height, row_spacing=row_spacing, rail_mount_depth=rail_mount_depth,
            rail_mount_centre_offset=rail_mount_centre_offset, rail_mount_radius=rail_mount_radius,
            cutout=cutout, combine=combine
        )

    def parse_settings_to_configuration(self, settings: BoxSettings) -> BoxConfiguration:
        """Parse settings into a complete box configuration with pieces"""

        # check input values mainly to avoid python errors
        # TODO restrict values to *correct* solutions
        # TODO restrict divisions to logical values

        # Validate input values
        error = False

        if settings.unit not in ['mm', 'cm', 'in', 'ft', 'px', 'pt', 'pc']:
            inkex.errormsg(_("Error: Invalid unit") + f': {settings.unit}')
            error = True
        if min(settings.X, settings.Y, settings.Z) == 0:
            inkex.errormsg(_("Error: Dimensions must be non zero")+ f': ({settings.X}, {settings.Y}, {settings.Z})')
            error = True
        if min(settings.X, settings.Y, settings.Z) < 3 * settings.tab_width:
            inkex.errormsg(_("Error: Tab size too large") + f': ({3 * settings.tab_width} > {min(settings.X, settings.Y, settings.Z)})')
            error = True
        if settings.tab_width < settings.thickness:
            inkex.errormsg(_("Error: Tab size too small") + f': ({settings.tab_width} < {settings.thickness})')
            error = True
        if settings.thickness == 0:
            inkex.errormsg(_("Error: thickness is zero"))
            error = True
        if settings.thickness > min(settings.X, settings.Y, settings.Z) / 3:  # crude test
            inkex.errormsg(_("Error: Material too thick"))
            error = True
        if settings.kerf > min(settings.X, settings.Y, settings.Z) / 3:  # crude test
            inkex.errormsg(_("Error: kerf too large")+ f': ({settings.kerf} > {min(settings.X, settings.Y, settings.Z) / 3})')
            error = True
        if settings.spacing > max(settings.X, settings.Y, settings.Z) * 10:  # crude test
            inkex.errormsg(_("Error: Spacing too large") + f': ({settings.spacing} > {max(settings.X, settings.Y, settings.Z) * 10})')
            error = True
        if settings.spacing < settings.kerf:
            inkex.errormsg(_("Error: Spacing too small") + f': ({settings.spacing} < {settings.kerf})')
            error = True
        if settings.line_color not in ['black', 'red', 'blue', 'green']:
            inkex.errormsg(_("Error: Invalid line color") + f': {settings.line_color}')
            error = True

        if error:
            inkex.errormsg(f'Provided arguments: {self.cli_args}')
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


        def get_pieces(ptype: PieceType) -> list[Piece]:
            return [p for p in created_pieces if p.pieceType == ptype]

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

        spacing = max(settings.spacing, 0 if settings.hairline else (settings.line_thickness)) + settings.kerf
        initOffsetX = settings.initOffsetX - settings.kerf / 2
        initOffsetY = settings.initOffsetY - settings.kerf / 2

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
            rr = [row0, row1z, row2]
            cc = [col0, col1z, col2xz, col3xzz]
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

                x = xs * spacing + xx * settings.X + xy * settings.Y + xz * settings.Z + initOffsetX
                y = ys * spacing + yx * settings.X + yy * settings.Y + yz * settings.Z + initOffsetY

                return Vec(x, y)

            for piece in get_pieces(PieceType.Back):
                piece.base = calculate_position(cc[1], rr[2])  # cc[1], rr[2] - Back piece
                pieces_list.append(piece)

            # Add X dividers after Back piece (as in original)
            divider_x_pos = calculate_position(cc[1], rr[2])  # cc[1], rr[2] - Back piece
            if PieceType.Back in piece_types:
                divider_x_pos += Vec(0, settings.Z + spacing)
            if not settings.keydiv_walls:
                divider_x_pos += Vec(settings.thickness, 0)
            for divider in get_pieces(PieceType.DividerX):
                divider.base = divider_x_pos
                divider_x_pos += Vec(0, spacing + divider.dy)
                pieces_list.append(divider)

            for piece in get_pieces(PieceType.Left):
                piece.base = calculate_position(cc[0], rr[1])  # cc[0], rr[1] - Left piece
                pieces_list.append(piece)


            divider_y_pos = calculate_position(cc[3], rr[1])  # cc[3], rr[1] - Top piece
            if PieceType.Top in piece_types:
                divider_y_pos += Vec(settings.X + spacing, 0)
            if not settings.keydiv_walls:
                divider_y_pos += Vec(0, settings.thickness)
            # Add Y dividers after Left piece (as in original)
            for divider in get_pieces(PieceType.DividerY):
                divider.base = divider_y_pos
                divider_y_pos += Vec(spacing + divider.dx, 0)
                pieces_list.append(divider)

            for piece in get_pieces(PieceType.Bottom):
                piece.base = calculate_position(cc[1], rr[1])  # cc[1], rr[1] - Bottom piece
                pieces_list.append(piece)

            for piece in get_pieces(PieceType.Right):
                piece.base = calculate_position(cc[2], rr[1])  # cc[2], rr[1] - Right piece
                pieces_list.append(piece)

            for piece in get_pieces(PieceType.Top):
                piece.base = calculate_position(cc[3], rr[1])  # cc[3], rr[1] - Top piece
                pieces_list.append(piece)

            for piece in get_pieces(PieceType.Front):
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

                x = xs * spacing + xx * settings.X + xy * settings.Y + xz * settings.Z + initOffsetX
                y = ys * spacing + yx * settings.X + yy * settings.Y + yz * settings.Z + initOffsetY

                return Vec(x, y)

            # Separate pieces by type for proper ordering
            for piece in get_pieces(PieceType.Back):
                piece.base = calculate_position(cc[1], rr[1])  # cc[1], rr[1] - Back piece
                pieces_list.append(piece)


            # Add X dividers after Back piece (as in original)
            for idx, divider in enumerate(get_pieces(PieceType.DividerX)):
                # Original divider positioning: divider_y = 4 * spacing + 1 * Y + 2 * Z
                divider_y = 4 * spacing + 1 * settings.Y + 2 * settings.Z
                divider_x = idx * (spacing + settings.X) + spacing
                divider.base = Vec(divider_x, divider_y)
                pieces_list.append(divider)

            for piece in get_pieces(PieceType.Left):
                piece.base = calculate_position(cc[0], rr[0])  # cc[0], rr[0] - Left piece
                pieces_list.append(piece)

            # Add Y dividers after Left piece (as in original)
            for idx, divider in enumerate(get_pieces(PieceType.DividerY)):
                # Original divider positioning: divider_y = 5 * spacing + 1 * Y + 3 * Z
                divider_y = 5 * spacing + 1 * settings.Y + 3 * settings.Z
                divider_x = idx * (spacing + settings.Z) + spacing
                divider.base = Vec(divider_x, divider_y)
                pieces_list.append(divider)

            for piece in get_pieces(PieceType.Bottom):
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

                x = xs * spacing + xx * settings.X + xy * settings.Y + xz * settings.Z + initOffsetX
                y = ys * spacing + yx * settings.X + yy * settings.Y + yz * settings.Z + initOffsetY

                return Vec(x, y)


            # Follow exact original INLINE_COMPACT order: Back -> X dividers -> Left -> Y dividers -> Top -> Bottom -> Right -> Front
            for piece in get_pieces(PieceType.Back):
                piece.base = calculate_position(cc[4], rr[0])  # cc[4], rr[0] - Back piece
                pieces_list.append(piece)

            # Add X dividers after Back piece (as in original)
            for idx, divider in enumerate(get_pieces(PieceType.DividerX)):
                divider_y = 4 * spacing + 1 * settings.Y + 2 * settings.Z
                divider_x = idx * (spacing + settings.X) + spacing
                divider.base = Vec(divider_x, divider_y)
                pieces_list.append(divider)

            for piece in get_pieces(PieceType.Left):
                piece.base = calculate_position(cc[2], rr[0])  # cc[2], rr[0] - Left piece
                pieces_list.append(piece)

            # Add Y dividers after Left piece (as in original)
            for idx, divider in enumerate(get_pieces(PieceType.DividerY)):
                divider_y = 5 * spacing + 1 * settings.Y + 3 * settings.Z
                divider_x = idx * (spacing + settings.Z)
                divider.base = Vec(divider_x, divider_y)
                pieces_list.append(divider)

            for piece in get_pieces(PieceType.Top):
                piece.base = calculate_position(cc[0], rr[0])  # cc[0], rr[0] - Top piece
                pieces_list.append(piece)

            for piece in get_pieces(PieceType.Bottom):
                piece.base = calculate_position(cc[1], rr[0])  # cc[1], rr[0] - Bottom piece
                pieces_list.append(piece)

            for piece in get_pieces(PieceType.Right):
                piece.base = calculate_position(cc[3], rr[0])  # cc[3], rr[0] - Right piece
                pieces_list.append(piece)

            for piece in get_pieces(PieceType.Front):
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
                PieceType.DividerX: (tabs.ftTabInfo, tabs.ftTabbed),  # Like Front face
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

            if pieceType in [PieceType.Top, PieceType.Bottom]:  # Top/Bottom faces
                # Side A/C (horizontal) gets Y-axis divider spacing (div_x)
                # Side B/D (vertical) gets X-axis divider spacing (div_y)"
                horizontal_spacing = settings.div_x_spacing
                vertical_spacing = settings.div_y_spacing
            elif pieceType in [PieceType.Front, PieceType.Back, PieceType.DividerX]:  # Front/Back faces
                # Side A/C (horizontal) gets no dividers (Z direction)
                # Side B/D (vertical) gets X-axis divider spacing (div_y)
                horizontal_spacing = []
                vertical_spacing = settings.div_y_spacing
            elif pieceType in [PieceType.Left, PieceType.Right, PieceType.DividerY]:  # Left/Right faces
                # Side A/C (horizontal) gets Y-axis divider spacing (div_x)
                # Side B/D (vertical) gets no dividers (Z direction)
                horizontal_spacing = settings.div_x_spacing
                vertical_spacing = []
            else:
                horizontal_spacing = []
                vertical_spacing = []

            # Sides: A=top, B=right, C=bottom, D=left
            sides = [
                Side(settings, Sides.A, bool(tabInfo & 0b1000), bool(tabbed & 0b1000), inside_dx),
                Side(settings, Sides.B, bool(tabInfo & 0b0100), bool(tabbed & 0b0100), inside_dy),
                Side(settings, Sides.C, bool(tabInfo & 0b0010), bool(tabbed & 0b0010), inside_dx),
                Side(settings, Sides.D, bool(tabInfo & 0b0001), bool(tabbed & 0b0001), inside_dy)
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
                if not settings.keydiv_floor:
                    sides[0].has_tabs = sides[2].has_tabs = False # sides A and C
                    sides[0].is_male = sides[2].is_male = False
                if not settings.keydiv_walls:
                    sides[1].has_tabs = sides[3].has_tabs = False # sides B and D
                    sides[1].is_male = sides[3].is_male = False

                sides[1].num_dividers = sides[3].num_dividers = settings.div_y * (settings.div_x > 0)
                piece = Piece(sides, PieceType.DividerX)

                pieces.append(piece)

        if settings.div_y > 0:
            for n in range(int(settings.div_y)):
                sides = make_sides(settings, tabs, PieceType.DividerY)

                # Remove tabs from dividers if not required
                # NOTE: Setting is_male=True is a workaround for geometric offset calculation
                # when has_tabs=False. This coupling should be cleaned up in future refactoring.
                if not settings.keydiv_walls:
                    sides[0].has_tabs = sides[2].has_tabs = False # sides A and C
                    sides[0].is_male = sides[2].is_male = False
                if not settings.keydiv_floor:
                    sides[1].has_tabs = sides[3].has_tabs = False # sides B and D
                    sides[1].is_male = sides[3].is_male = False

                sides[0].num_dividers = sides[2].num_dividers = settings.div_x * (settings.div_x > 0)
                piece = Piece(sides, PieceType.DividerY)
                pieces.append(piece)

        return pieces

    def generate_pieces(self, pieces: list[Piece], config: BoxConfiguration, settings: BoxSettings):
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
            if settings.cutout or settings.combine:
                self.optimizePiece(group, settings)

            # Last step: If the group now just contains one path, remove
            # the group around this path
            if len(group) == 1:
                item = group[0]
                group.remove(item)  # Detach item before replacing to avoid issues
                item.set_id(group.get_id())
                yield item
            else:
                yield group

    def generate(self):

        if self.inkscape:
            desc = Desc()
            desc.text=f"$ {os.path.basename(__file__) if not self.schroff else 'schroff.py'} {" ".join(a for a in self.cli_args if a != self.options.input_file)}"
            yield desc
        else:
            yield Metadata(text=f"$ {os.path.basename(__file__) if not self.schroff else 'schroff.py'} {" ".join(a for a in self.cli_args if a != self.options.input_file)}")

        # Step 1: Parse options into settings
        settings = self.parse_options_to_settings()

        # Store values needed for other methods
        self.line_thickness = settings.line_thickness
        self.line_color = {'black': '#000000', 'red': '#FF0000', 'green': '#00FF00', 'blue': '#0000FF'}.get(str(settings.line_color).lower(), "#000000")

        # Step 2: Parse settings into complete configuration with pieces
        config = self.parse_settings_to_configuration(settings)

        # Add comments and metadata to SVG
        svg = self.document.getroot()

        # Allow hiding version for testing purposes
        if self.version:
            yield inkex.etree.Comment(f" Generated by BoxMaker version {self.version} ")
            yield inkex.etree.Comment(f" {str(settings).replace('--', '-')} ")


        tabs = self.create_tabs_configuration(settings, config.piece_types)
        pieces = self.create_pieces(settings, tabs)

        pieces = self.apply_layout(pieces, settings)

        # Step 3: Generate and draw all pieces
        for i in self.generate_pieces(pieces, config, settings):
            yield i

    def optimizePiece(self, group: Group, settings: BoxSettings) -> None:
        # Step 1: Combine paths to form the outer boundary
        paths = [child for child in group if isinstance(child, PathElement)]

        if settings.combine:
            try_attach_paths(paths, reverse=True)
            paths = [child for child in group if isinstance(child, PathElement)]

        if settings.combine:
            try_clean_paths(paths)

        # Step 3: Include gaps in the panel outline by removing them from the panel path
        if len(paths) > 1:
            try_combine_paths(paths, inkscape=self.inkscape, no_subtract=self.no_subtract)

    @staticmethod
    def dimpleStr(
        tabVector: float,
        vector: Vec,
        direction: Vec,
        toInside: Vec,
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
            Vd = vector + toInside * dimpleStart
            ds.append(Line(*Vd))
            Vd += (toInside * tabSign * dimpleHeight) - (direction * ddir * dimpleHeight)
            ds.append(Line(*Vd))
            Vd += toInside * (tabSign * dimpleLength)
            ds.append(Line(*Vd))
            Vd += (toInside * tabSign * dimpleHeight) + (direction * ddir * dimpleHeight)
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

        for i in self.render_side_side(root, piece, side, settings) + \
                ( self.render_side_slots(root, piece, side, settings)
                    if piece.pieceType in [PieceType.DividerY, PieceType.DividerX]
                    else self.render_side_holes(root, piece,side, settings)):
            group.add(i)

    def render_side_side(
        self,
        root: Vec,
        piece: Piece,
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
            tabVec = -thickness if isMale else thickness
        else:
            tabVec = 0

        kerf = settings.kerf
        halfkerf = kerf / 2
        dogbone = side.dogbone

        divisions = side.divisions
        gapWidth = side.gap_width
        tabWidth = side.tab_width


        if isMale:  # kerf correction
            gapWidth -= settings.kerf
            tabWidth += settings.kerf
            first = kerf
        else:
            gapWidth += settings.kerf
            tabWidth -= settings.kerf
            first = 0

        toInside = direction.rotate_clockwise(1)
        s = Path()

        startOffsetX, startOffsetY = startOffset = side.start_offset
        vecHalfKerf = direction * halfkerf

        vector = startOffset * thickness

        s.append(Move(*vector))

        if side.has_tabs or not (settings.combine or settings.cutout):
            if (side.has_tabs and side.prev.has_tabs and side.tab_symmetry == TabSymmetry.ROTATE_SYMMETRIC and piece.pieceType in [PieceType.Bottom, PieceType.Top]) or \
                (side.has_tabs and side.prev.has_tabs and side.tab_symmetry == TabSymmetry.ANTISYMMETRIC and piece.pieceType ==  PieceType.Top and side.is_male and not side.prev.is_male):
                p = vector + toInside * -(thickness + halfkerf)
                s.append(Line(*p))

                p += direction * (thickness + kerf)
                s.append(Line(*p))

                ## TODO: Add dimple if necessary
                p -= toInside * -(thickness + halfkerf)
                s.append(Line(*p))


            # Set vector for tab generation
            if side.tab_symmetry == TabSymmetry.ROTATE_SYMMETRIC:
                vector = Vec(startOffsetX if startOffsetX else dirX, startOffsetY if startOffsetY else dirY) * thickness
            else:
                if toInside.x:
                    vector = Vec(vector.x, 0) # set correct line start for tab generation
                if toInside.y:
                    vector = Vec(0, vector.y) # set correct line start for tab generation

            if piece.pieceType == PieceType.DividerY and side.name in (Sides.B, Sides.D) and not side.prev.has_tabs:
                # Special case for DividerY
                vector -= direction * thickness # Move start back by thickness
            elif piece.pieceType == PieceType.DividerX and side.name in (Sides.A, Sides.C) and not side.prev.has_tabs:
                # Special case for DividerX
                vector -= direction * thickness # Move start back by thickness


            if not(isMale and dogbone) and first != 0:
                vector += direction * first

            # generate line as tab or hole using:
            #   last co-ord:Vx,Vy ; tab dir:tabVec  ; direction:dirx,diry ; thickness:thickness
            #   divisions:divs ; gap width:gapWidth ; tab width:tabWidth

            for tabDivision in range(1, int(divisions)):
                if tabDivision % 2:
                    # draw the gap
                    vector += direction * (gapWidth
                                            + (kerf if dogbone and isMale else 0))
                    s.append(Line(*vector))
                    if dogbone and isMale:
                        vector -= vecHalfKerf
                        s.append(Line(*vector))
                    # draw the starting edge of the tab
                    s.extend(self.dimpleStr(
                        tabVec, vector, direction, toInside, 1, isMale,
                        settings.dimple_length, settings.dimple_height
                    ))
                    vector += toInside * tabVec
                    s.append(Line(*vector))
                    if dogbone and notMale:
                        vector -= vecHalfKerf
                        s.append(Line(*vector))

                else:
                    # draw the tab
                    vector += direction * (tabWidth + (kerf if dogbone and notMale else 0))
                    s.append(Line(*vector))
                    if dogbone and notMale:
                        vector -= vecHalfKerf
                        s.append(Line(*vector))
                    # draw the ending edge of the tab
                    s.extend(self.dimpleStr(
                        tabVec, vector, direction, toInside, -1, isMale,
                        settings.dimple_length, settings.dimple_height
                    ))
                    vector += toInside * tabVec
                    s.append(Line(*vector))
                    if dogbone and isMale:
                        vector -= vecHalfKerf
                        s.append(Line(*vector))
                tabVec = -tabVec  # swap tab direction
            first = 0  # only apply first offset once

        end_point = side.next.start_offset * thickness + direction * (length + kerf)
        if side.tab_symmetry == TabSymmetry.ANTISYMMETRIC and piece.pieceType == PieceType.Bottom and side.is_male and not side.next.is_male and side.has_tabs and side.next.has_tabs:
            # Antisymmetric case for bottom side, we need an additional corner to avoid a void
            p = end_point - direction * (thickness + kerf)

            s.append(Line(*p))

            ## TODO: Add dimple if necessary
            p += toInside * -(thickness + halfkerf)
            s.append(Line(*p))

            p += direction * (thickness + kerf)
            s.append(Line(*p))


        # finish the line off
        s.append(Line(*end_point))

        rootX, rootY = root + side.root_offset + direction * -halfkerf + toInside * -halfkerf

        sidePath = self.makeLine(s.translate(rootX, rootY, inplace=True), "side")
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

        return cumulative + side_thickness * i


    def render_side_slots(
        self,
        root: Vec,
        piece: Piece,
        side: Side,
        settings: BoxSettings
    ) -> list[PathElement]:
        """Draw tabs or holes as required"""

        numDividers = side.num_dividers
        if numDividers == 0 or side.name not in (Sides.A, Sides.D):
            return []

        divider_spacings = side.divider_spacings.copy()
        if side.name >= Sides.C:
            divider_spacings.reverse()

        direction = side.direction
        thickness = side.thickness
        kerf = settings.kerf
        halfkerf = kerf / 2

        nodes = []

        toInside = direction.rotate_clockwise(1)
        vector = root + side.root_offset + toInside * side.has_tabs * thickness
        kerf_offset = toInside * halfkerf


        for dividerNumber in range(numDividers):
            cumulative_position = self.calculate_cumulative_position(dividerNumber + 1, divider_spacings, thickness)
            divider_offset = direction.rotate_clockwise(1) * cumulative_position

            start_pos = vector + divider_offset + kerf_offset - direction * halfkerf
            width = side.inside_length / 2

            if side.prev.has_tabs:
                width += thickness

            h = Path()
            h.append(Move(*start_pos))

            pos = start_pos + direction * width
            if side.dogbone:
                db = pos + direction * halfkerf
                h.append(Line(*db))
            h.append(Line(*pos))

            pos += toInside * (thickness - kerf)
            h.append(Line(*pos))

            if side.dogbone:
                db = pos + direction * halfkerf
                h.append(Line(*db))

            pos -= direction * width
            h.append(Line(*pos))

            h.append(Line(*start_pos))
            h.append(ZoneClose())
            nodes.append(self.makeLine(h, "slot"))

        return nodes

    def render_side_holes(
        self,
        root: Vec,
        piece: Piece,
        side: Side,
        settings: BoxSettings
    ) -> list[PathElement]:
        """Draw tabs or holes as required"""

        numDividers = side.num_dividers
        if numDividers == 0:
            return []

        dividerSpacings = side.divider_spacings

        direction = side.direction

        isMale = side.is_male
        thickness = side.thickness

        kerf = settings.kerf
        halfkerf = kerf / 2

        nodes = []

        divisions = side.divisions
        gapWidth = side.gap_width
        tabWidth = side.tab_width

        first = halfkerf if isMale else -halfkerf
        corr = -kerf if isMale else kerf

        gapWidth += corr
        tabWidth -= corr

        toInside = direction.rotate_clockwise()

        kerf_offset = Vec(1 if toInside.x else 0, -(1 if toInside.y else 0)) * halfkerf

        vector = root + side.root_offset + toInside * (side.has_tabs * thickness + halfkerf)

        if side.tab_symmetry == TabSymmetry.ROTATE_SYMMETRIC:
            vector += direction * (side.prev.has_tabs * thickness - halfkerf)

        kerf_offset = Vec(1 if toInside.x else 0, -(1 if toInside.y else 0)) * halfkerf
        log(f"TabWidth {tabWidth}, GapWidth {gapWidth}, Total={gapWidth+tabWidth}, Divisions {divisions}, isMale {isMale}, numDividers {numDividers}, Spacings {dividerSpacings}, vector {vector}, dir {direction}, toInside {toInside}")

        # generate line as tab or hole using:
        #   last co-ord:Vx,Vy ; tab dir:tabVec  ; direction:dirx,diry ; thickness:thickness
        #   divisions:divs ; gap width:gapWidth ; tab width:tabWidth
        for tabDivision in range(divisions):
            # draw holes for divider tabs to key into side walls
            if ((tabDivision % 2) == 0) != (not isMale):
                ww = w = gapWidth if isMale else tabWidth
                if (tabDivision == 0 or tabDivision == (divisions - 1)) and (side.tab_symmetry == TabSymmetry.XY_SYMMETRIC or side.tab_symmetry == TabSymmetry.ANTISYMMETRIC):
                    if tabDivision == 0 and side.prev.has_tabs:
                        w -= thickness - halfkerf
                    elif tabDivision > 0 and ((side.next.has_tabs and side.tab_symmetry == TabSymmetry.XY_SYMMETRIC) or \
                                              (side.tab_symmetry == TabSymmetry.ANTISYMMETRIC and piece.pieceType == PieceType.Bottom)):
                        w -= thickness - kerf
                holeLen = direction * (w + first)
                for dividerNumber in range(numDividers):
                    cumulative_position = self.calculate_cumulative_position(dividerNumber + 1, dividerSpacings, thickness)
                    divider_offset = direction.rotate_clockwise(1) * (cumulative_position + halfkerf)

                    pos = vector + divider_offset + kerf_offset

                    if tabDivision == 0 and (side.tab_symmetry == TabSymmetry.XY_SYMMETRIC or (isMale and side.tab_symmetry == TabSymmetry.ANTISYMMETRIC)):
                        pos += direction * (side.prev.has_tabs * thickness - halfkerf)

                    h = Path()
                    h.append(Move(*pos))
                    if side.dogbone and ww == w:
                        db = pos - direction * halfkerf
                        h.append(Line(*db))

                    pos += holeLen
                    if side.dogbone and ww == w:
                        db = pos + direction * halfkerf
                        h.append(Line(*db))
                    h.append(Line(*pos))

                    thickVec = toInside * (thickness - kerf)
                    pos += thickVec
                    h.append(Line(*pos))

                    if side.dogbone and ww == w:
                        db = pos + direction * halfkerf
                        h.append(Line(*db))

                    pos -= holeLen

                    if side.dogbone and ww == w:
                        db = pos - direction * halfkerf
                        h.append(Line(*db))

                    h.append(Line(*pos))

                    pos -= thickVec
                    #if side.dogbone and ww == w:
                    #    db = pos - direction * halfkerf
                    #    h.append(Line(*db))
                    h.append(Line(*pos))
                    h.append(ZoneClose())
                    nodes.append(self.makeLine(h, "hole"))

            if (tabDivision % 2) == 0:
                # draw the gap
                vector += direction * (gapWidth + first)
            else:
                # draw the tab
                vector += direction * tabWidth

            first = 0

        return nodes
