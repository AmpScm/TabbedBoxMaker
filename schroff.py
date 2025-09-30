#! /usr/bin/env python -t
"""
Generates Inkscape SVG file containing box components needed to
CNC (laser/mill) cut a box with tabbed joints taking kerf and clearance into account

Original Tabbed Box Maker Copyright (C) 2011 Elliot White

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

import sys
from tabbedboxmaker import BoxMaker

if __name__ == "__main__":
    args = sys.argv[1:]
    inkscape = any(a.startswith('--inkscape=') for a in args)
    args =[a for a in sys.argv[1:] if (not a.startswith("--_") and not a.startswith('--inkscape='))]
    effect = BoxMaker(cli=not inkscape, inkscape=inkscape, schroff=True)
    effect.run(args)
