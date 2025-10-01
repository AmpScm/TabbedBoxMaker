#! /usr/bin/env python -t
"""
Generates Inkscape SVG file containing box components needed to
CNC (laser/mill) cut a card board box

Original Tabbed Box Maker Copyright (C) 2011 Elliot White
Cardboard Box Maker Copyright (C) 2024 Brad Goodman

14/05/2024 Brad Goodman:
    - Created from Tabbed Box Maker

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
from copy import deepcopy
from inkex import PathElement, Metadata, Transform
from inkex.paths import Path
from inkex.utils import filename_arg

from tabbedboxmaker.Generators import CliEnabledGenerator
from tabbedboxmaker.boxmaker import IntBoolean

import os
import inkex
import gettext

_ = gettext.gettext


def log(text):
    if "SCHROFF_LOG" in os.environ:
        f = open(os.environ.get("SCHROFF_LOG"), "a")
        f.write(text + "\n")

# Draws each top or bottom edge
# Sidenumber is 1-4
# topside is true of top
# sidetype is the "boxbottom" or "boxtop" as applicable


def boxedge(hh, ww, dd, k2, t5, t2, sidetype, topside, sidenumber):
    h = ""
    if not topside:
        # Invert offsets for bottom side
        dd *= -1
        ww *= -1
        hh *= -1
        t5 *= -1
        t2 *= -1
        k2 *= -1

    if (sidenumber == 1) or (sidenumber == 3):
        wd = ww
        dw = dd
    else:
        wd = dd
        dw = ww

    # if (sidetype == 1) or ((sidetype == 2) and (sidenumber != 1)):
    if sidetype == 1:
        h += f"l {wd + k2},0 "  # Top open (plain flat side)
    else:
        if (sidetype == 2) and (sidenumber != 1):
            # SPECIAL CASE - because this is a double fold (all the way down!)
            # h+=f"l {t5},0 l 0,{-1*((t2*2)-(k2))} l {-1*t5},0 " # DOUBLE
            # Leading Vertical Fold Notch
            # Trailing Vertical Fold Notch
            h += f"a {(t2 + t2 - k2) / 2} {-1 * (t2 + t2 - k2) / 2} 180 1 0 0,{-1 * (t2 + t2 - k2)} "
        else:
            # h+=f"l {t5},0 l 0,{-1*(t2-k2)} l {-1*t5},0 " # Leading Vertical
            # Fold Notch
            # Trailing Vertical Fold Notch
            h += f"a {(t2 - k2) / 2} {-1 * (t2 - k2) / 2} 180 1 0 0,{-1 * (t2 - k2)} "

        if (sidetype == 2) or (sidetype == 5):
            # Flat top w/ Side Folds - Full Depth top on one side, Full height
            # on all else
            if sidenumber == 1:
                # Top side full depth
                h += f"l 0,{-1 * (dw + k2)} "
                # Top Tab - Fill width will be wd+k2
                # h+=f"l {wd+(k2)},0 "
                h += f"l {t5},0 "
                # h+=f"l {t2},0 l 0,{-1*(t2-k2)} l {-1*t2},0 " # Leading
                # Horizontal Fold Notch
                # Trailing Horizontal Fold Notch
                h += f"a {(t2 - k2) / 2} {(t2 - k2) / 2} 180 1 0 0,{-(t2 - k2)} "
                h += f"l {t5},{-(hh + k2)} "
                h += f"l {(wd + k2) - (t5 * 4)},0 "
                h += f"l {t5},{(hh + k2)} "
                # h+=f"l {-1*t2},0 l 0,{t2-k2} l {t2},0 " # Trailing Horizontal
                # Fold Notch
                # Trailing Horizontal Fold Notch
                h += f"a {(t2 - k2) / 2} {(t2 - k2) / 2} 180 1 0 0,{t2 - k2} "
                h += f"l {t5},0 "

                h += f"l 0,{dw + (k2)} "
            elif (sidetype == 5) and (sidenumber == 3):
                # Draw Locking tab
                # h+=f"l 0,{-1*((dw/2)+(k2))} "
                if k2 > 0:
                    h += f"l 0,{-k2} "
                h += f"l {(wd / 3) - t2 + k2},0 "
                h += f"l 0,{hh / 2} "
                h += f"l {t2 - k2},0 "
                h += f"l 0,{(hh / -2)} "

                # Trailing Horizontal Fold Notch
                h += f"a {(t2 - k2) / 2} {(t2 - k2) / 2} 180 1 0 0,{-(t2 - k2)} "
                if k2 > 0:
                    h += f"l 0,{-k2} "
                h += f"l {(t2 * 3)},{(-t2 * 4)} "
                h += f"l {(wd / 3) + k2 - (t2 * 6)},0 "
                h += f"l {(t2 * 3)},{(t2 * 4)} "
                if k2 > 0:
                    h += f"l 0,{k2} "
                # Trailing Horizontal Fold Notch
                h += f"a {(t2 - k2) / 2} {(t2 - k2) / 2} 180 1 0 0,{t2 - k2} "

                h += f"l 0,{(hh / 2)} "
                h += f"l {t2 - k2},0 "
                h += f"l 0,{hh / -2} "
                h += f"l {(wd / 3) - (t2) + k2},0 "
                if k2 > 0:
                    h += f"l 0,{k2} "
                # h+=f"l 0,{(dw/2)+(k2)} "
            else:
                # Side down-folds - since they are 180 degree, will have double
                # knockouts
                h += f"l {t2},{-1 * (hh + k2)} "
                wd3 = (wd + k2 - (2 * t2)) / 3
                h += f"l {wd3 - (k2 / 2)},0 "
                h += f"l {t2 / 2},{-t2} "
                h += f"l {wd3 + k2 - t2},0 "
                h += f"l {t2 / 2},{t2} "
                h += f"l {wd3 - (k2 / 2)},0 "
                h += f"l {t2},{hh + (k2)} "
        elif sidetype == 4:
            # Locking fold - Top and bottom are different, sides are mirrors

            if sidenumber == 1:
                h += f"l 0,{(-1 * ((dd) - t2)) - k2} "
                h += f"l {(dd / 2) + k2},0 "
                h += f"l 0,{(dd / 2) - t2} "
                h += f"l {(ww - k2) - (dd)},0 "
                # h += f"l {(zz*3)},0 "
                h += f"l 0,{-(dd / 2) + t2} "
                h += f"l {(dd / 2) + k2},0 "
                h += f"l 0,{(dd) - t2 + k2} "
                # h+=f"l {wd+k2},0 " # Top open (plain flat side)
            elif sidenumber == 3:
                h += f"l 0,{(-1 * (dd / 2)) - k2} "
                h += f"l {dd / 2},0 "
                h += f"l 0,{-1 * ((dd / 2) - t2)} "
                h += f"l {(ww) - (dd) + k2},0 "
                h += f"l 0,{(dd / 2) - t2} "
                h += f"l {dd / 2},0 "
                h += f"l 0,{(dd / 2) + k2} "
            elif sidenumber == 2:
                h += f"l {t2},{-t5} "
                h += f"l 0,{-1 * (dd + k2 - t5 - t2)} "
                h += f"l {(dd / 2) + (dd / 8)},0 "
                h += f"q {(dd / 4) + (2 * k2)},0 {(-dd / 8) - t2 + k2},{(dd / 2) - t2 - (k2 / 4)} "
                h += f"l {(dd / 2)},{(dd / 2)} "
                if k2 > 0:
                    h += f"l 0,{(k2 / 2)} "
            elif sidenumber == 4:
                if k2 > 0:
                    h += f"l 0,{-k2} "
                h += f"l {(dd / 2)},{(-dd / 2) + (k2 / 2)} "
                h += f"q {(-dd / 2)},{-dd / 3} {(-dd / 8) - t2 + k2},{(-dd / 2) + t2} "
                # h+=f"l {(-dd/2)-(k2/2)},{(-dd/2)+t2-(k2/2)} "
                h += f"l {(dd / 2) + (dd / 8)},0 "
                # h+=f"l 0,{1*(dd-t5-t2+(k2/2))} "
                h += f"l 0,{1 * (dd + k2 - t5 - t2)} "
                h += f"l {t2},{t5} "

        else:
            # Standard fold - half depth/width on each side
            h += f"l 0,{-1 * ((dw / 2) + (k2))} "
            h += f"l {wd + (k2)},0 "
            h += f"l 0,{(dw / 2) + (k2)} "

        if (sidetype == 2) and (sidenumber != 1):
            # SPECIAL CASE - because this is a double fold (all the way down!)
            # h+=f"l {-1*t5},0 l 0,{(2*t2)-(k2)} l {t5},0 " # Trailing Vertical
            # Fold Notch
            # Trailing Vertical Fold Notch
            h += f"a {(t2 + t2 - k2) / 2} {(t2 + t2 - k2) / 2} 180 1 0 0,{(t2 + t2 - k2)} "
        else:
            # h+=f"l {-1*t5},0 l 0,{t2-k2} l {t5},0 " # Trailing Vertical Fold
            # Notch
            # Trailing Vertical Fold Notch
            h += f"a {(t2 - k2) / 2} {(t2 - k2) / 2} 180 1 0 0,{t2 - k2} "

    if ((topside) and (sidenumber != 4)) or ((not topside) and (sidenumber != 1)):
        # h+=f"l 0,{t5} l {t2-(k2)},0 l 0,{-1*t5} " # Trailing Horizontal Fold
        # Notch
        # Trailing Horizontal Fold Notch
        h += f"a {(t2 - k2) / 2} {(t2 - k2) / 2} 180 1 0 {t2 - k2},0 "

    return h


class CardboardBoxMaker(CliEnabledGenerator):
    cli = True
    inkscape = False
    hairline_thickness : float = None
    raw_hairline_thickness : float = None

    def __init__(self, cli=True, inkscape=False):

        self.container_label = "Cardboard Box"
        # Call the base class constructor.
        super().__init__(cli=cli, inkscape=inkscape)
        # Define options


    def add_arguments(self, pars) -> None:
        """Define options"""

        super().add_arguments(pars)

        self.arg_parser.add_argument(
            "--length",
            type=float,
            dest="length",
            default=100,
            help="Height of Box",
        )
        self.arg_parser.add_argument(
            "--width",
            type=float,
            dest="width",
            default=100,
            help="Width of Box",
        )
        self.arg_parser.add_argument(
            "--depth",
            type=float,
            dest="depth",
            default=100,
            help="Depth of Box",
        )
        self.arg_parser.add_argument(
            "--hairline",
            type=IntBoolean,
            dest="hairline",
            default=0,
            help="Hairline",
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
            "--thickness",
            type=float,
            dest="thickness",
            default=10,
            help="Thickness of Material",
        )
        self.arg_parser.add_argument(
            "--kerf",
            type=float,
            dest="kerf",
            default=0.5,
            help="Kerf (width of cut)",
        )
        self.arg_parser.add_argument(
            "--boxtype",
            type=int,
            dest="boxtype",
            default=25,
            help="Box type",
        )
        self.arg_parser.add_argument(
            "--box-top",
            type=int,
            dest="boxtop",
            default=25,
            help="Box Top",
            choices=[1, 2, 3, 4, 5],
        )
        self.arg_parser.add_argument(
            "--box-bottom",
            type=int,
            dest="boxbottom",
            default=25,
            help="Box Bottom",
            choices=[1, 2, 3, 4, 5],
        )
        self.arg_parser.add_argument(
            "--sidetab",
            type=IntBoolean,
            dest="sidetab",
            help="Side Tab",
            choices=[True, False, '0', '1'],
        )
        self.arg_parser.add_argument(
            "--foldlines",
            type=IntBoolean,
            dest="foldlines",
            help="Add Cut Lines",
            choices=[True, False, '0', '1'],
        )

    def generate(self):

        yield Metadata(text=f"$ {os.path.basename(__file__)} {" ".join(a for a in self.cli_args if a != self.options.input_file)}")

        # Get the attributes:
        # inkex.utils.errormsg("Testing")
        unit = self.options.unit
        boxtop = self.options.boxtop
        boxbottom = self.options.boxbottom
        # Set the line thickness

        if not self.hairline_thickness:
            self.raw_hairline_thickness = self.hairline_thickness = round(self.svg.unittouu("1px"), 6)

        if self.options.hairline:
            self.linethickness = self.hairline_thickness
        else:
            self.linethickness = 1

        hh = self.svg.unittouu(str(self.options.width) + unit)
        ww = self.svg.unittouu(str(self.options.length) + unit)
        dd = self.svg.unittouu(str(self.options.depth) + unit)
        t2 = self.svg.unittouu(str(self.options.thickness * 2) + unit)
        t5 = self.svg.unittouu(str(self.options.thickness * 5) + unit)
        k = self.svg.unittouu(str(self.options.kerf) + unit)
        k1 = self.svg.unittouu(str(self.options.kerf) + unit)
        k2 = k1 * 2

        if ((boxtop == 4) or (boxbottom == 4)) and ((dd * 3) > ww):
            inkex.utils.errormsg(
                "For locking folds, width must be at least 3x the depth"
            )
            return

        h = f"M {-k},{-k} "
        # First Side
        h += boxedge(hh, ww, dd, k2, t5, t2, boxtop, True, 1)
        h += boxedge(hh, ww, dd, k2, t5, t2, boxtop, True, 2)
        h += boxedge(hh, ww, dd, k2, t5, t2, boxtop, True, 3)
        h += boxedge(hh, ww, dd, k2, t5, t2, boxtop, True, 4)

        # RIGHT EDGE

        # Add tab along right edge if wanted (else, straight edge)
        if self.options.sidetab:
            if boxtop == 1:
                h += f"l {t5},{t2} l 0,{t2 * 2} "
            else:
                h += f"l 0,{t2 + k2} l {-t2},0"
                # Trailing Vertical Fold Notch
                h += f"l 0,{t2 -
                            k2} a {(t2 -
                                    k2) /
                                   2} {(t2 -
                                        k2) /
                                       2} 180 1 0 {t2 -
                                                   k2},0 "
                h += f"l {t5 + k2},{t2} "
            h += f"l 0,{hh + k2 - (6 * t2)} "

            if boxbottom == 1:
                h += f"l 0,{t2 * 2} l {-1 * (t5)},{t2} "
            else:
                h += f"l {-(t5 + k2)},{t2} "
                # Trailing Vertical Fold Notch
                h += f"a {(t2 - k2) / 2} {(t2 - k2) / 2} 180 1 0 {-1 * (t2 - k2)},0 l 0,{t2 - k2} "
                h += f"l {t2},0 l 0,{t2 + k2} "
        else:
            h += f"l 0,{hh + k2} "

        # BOTTOM SIDE

        h += boxedge(hh, ww, dd, k2, t5, t2, boxbottom, False, 4)
        h += boxedge(hh, ww, dd, k2, t5, t2, boxbottom, False, 3)
        h += boxedge(hh, ww, dd, k2, t5, t2, boxbottom, False, 2)
        h += boxedge(hh, ww, dd, k2, t5, t2, boxbottom, False, 1)

        h += "Z"

        h= Path(h).to_absolute()

        bb = h.bounding_box()
        transform = Transform(translate=(-bb.left, -bb.top))

        yield self.getLine(h.transform(transform, inplace=True), linethickness=self.linethickness)

        # If we had top foldover tabs, add the slots for them
        # but ONLY if there is a box bottom to draw them on
        t = t2 / 2
        if (boxtop == 2) and (boxbottom != 1):
            dd3 = (dd - (2 * t2)) / 3
            ww3 = (ww - (2 * t2)) / 3
            wd3 = dd3
            o = ww + t2 + wd3 + k2 + (t2 / 2)
            for i in range(1, 4):
                h = f"M {o - k},{hh + (t / 4) + k} "
                h += f"l {wd3 + t2 - k2},0 "
                h += f"l 0,{(t * 1.5) - k2} "
                h += f"l {-wd3 + k2 - t2},0 "
                h += f"l 0,{(-t * 1.5) + k2} "
                h += "Z"
                h = Path(h).to_absolute()
                yield self.getLine(h.transform(transform, inplace=True), linethickness=self.linethickness)
                if i == 1:
                    o += dd3 + dd3 + ww3
                    wd3 = ww3
                else:
                    o += ww3 + ww3 + dd3
                    wd3 = dd3
                o += t5 + t

        # Draw slots for locking top
        if boxtop == 5:
            wd3 = (ww - (2 * t2)) / 3
            h = f"M {(ww / 3) + (k / 2)},{-dd - (t2) + k} "
            h += f"l {wd3 + t2 - k},0 "
            # Trailing Horizontal Fold Notch
            h += f"a {(t * 1.0) - k2} {(t * 1.0) - k2} 180 0 1 0,{(t * 2.5) - k2} "
            # h+=f"l 0,{(t*2.5)-k2} "
            h += f"l {-wd3 + k - t2},0 "
            # h+=f"l 0,{(-t*2.5)+k2} "
            # Trailing Horizontal Fold Notch
            h += f"a {(t * 1.0) - k2} {(t * 1.0) - k2} 180 0 1 0,{(-t * 2.5) + k2} "
            h += "Z"
            h = Path(h).to_absolute()
            yield self.getLine(h.transform(transform, inplace=True), linethickness=self.linethickness)

        # If we wanted fold lines - add them
        if self.options.foldlines:

            # Draw horizontal lines for top and/or bottom tabs
            # Only needed when there is a top or bottom to fold over

            sides = []
            if boxtop != 1:
                sides.append([boxtop, -t])
            if boxbottom != 1:
                sides.append([boxbottom, t + hh])

            for box, yy in sides:

                # First Side
                h = f"M {t5},{yy} "
                h += f"l {ww - t2 - t2 - (t2 / 2) - t5},0"
                h = Path(h).to_absolute()
                yield self.getLine(h.transform(transform, inplace=True), stroke="#0000ff", linethickness=self.linethickness)

                if box == 2:
                    yy -= t

                # Second Side
                h = f"M {ww + t2 + t5},{yy} "
                h += f"l {dd - t2 - t2 - (t2 / 2) - t5},0"
                h = Path(h).to_absolute()
                yield self.getLine(h.transform(transform, inplace=True), stroke="#0000ff", linethickness=self.linethickness)

                # Third Side
                h = f"M {ww + t2 + t5 + dd + t2},{yy} "
                h += f"l {ww - t2 - t2 - (t2 / 2) - t5},0"
                h = Path(h).to_absolute()
                yield self.getLine(h.transform(transform, inplace=True), stroke="#0000ff", linethickness=self.linethickness)

                # Fourth Side
                h = f"M {ww + t2 + t5 + dd + t2 + ww + t2},{yy} "
                h += f"l {dd - t2 - t2 - (t2 / 2) - t5},0"
                h = Path(h).to_absolute()
                yield self.getLine(h.transform(transform, inplace=True), stroke="#0000ff", linethickness=self.linethickness)

                if box == 2:
                    # h=f"M {ww+t2+t5 + dd+t2 + ww+t2},{yy} "
                    # h+=f"l {dd-t2-t2-(t2/2)-t5},0"
                    # group.add(self.getLine(h,stroke='#0000ff'))
                    h = f"M {t5 + t5},{-1 * (dd + t2 + (t2 / 2))} "
                    h += f"l {ww - (4 * t5)},0 "
                    h = Path(h).to_absolute()
                    yield self.getLine(h.transform(transform, inplace=True), stroke="#0000ff", linethickness=self.linethickness)

            # Draw Vertical Ones
            # First Side
            h = f"M {ww + t},{t5} "
            h += f"l 0,{hh - (2 * t5)}"
            h = Path(h).to_absolute()
            yield self.getLine(h.transform(transform, inplace=True), stroke="#0000ff", linethickness=self.linethickness)

            h = f"M {ww + t + dd + t2},{t5} "
            h += f"l 0,{hh - (2 * t5)}"
            h = Path(h).to_absolute()
            yield self.getLine(h.transform(transform, inplace=True), stroke="#0000ff", linethickness=self.linethickness)

            h = f"M {ww + t + dd + t2 + ww + t2},{t5} "
            h += f"l 0,{hh - (2 * t5)}"
            h = Path(h).to_absolute()
            yield self.getLine(h.transform(transform, inplace=True), stroke="#0000ff", linethickness=self.linethickness)

            # Tab only if selected
            if self.options.sidetab:
                h = f"M {ww + t + dd + t2 + ww + t2 + dd},{t5 + t2} "
                h += f"l 0,{hh - (t5 + t2 + t5 + t2)}"
                h = Path(h).to_absolute()
                yield self.getLine(h.transform(transform, inplace=True), stroke="#ff0000", linethickness=self.linethickness)

        # End Fold Lines

    def getLine(self, XYstring, stroke="#000000", linethickness : float = 1) -> PathElement:
        line = PathElement(id=self.makeId('line'))

        if linethickness == self.raw_hairline_thickness:
            line.style = { "stroke": stroke, "stroke-width"  : str(self.hairline_thickness), "fill": "none", "vector-effect": "non-scaling-stroke", "-inkscape-stroke": "hairline" }
        else:
            line.style = { "stroke": stroke, "stroke-width"  : str(linethickness), "fill": "none" }

        line.path = XYstring
        return line
