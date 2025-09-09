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
from tabbedboxmaker import BoxMaker
from tabbedboxmaker.enums import BoxType, TabSymmetry, TabType, Layout, TabWidth, DividerKeying

# Create effect instance and apply it.


def main(cli=False, schroff=False):
    effect = BoxMaker(cli=cli, schroff=schroff)
    effect.run()


def print_enum_help():
    print("\nAvailable enum options:")
    print("BoxType:")
    for e in BoxType:
        print(f"  {e.value}: {e.name}")
    print("TabSymmetry:")
    for e in TabSymmetry:
        print(f"  {e.value}: {e.name}")
    print("TabType:")
    for e in TabType:
        print(f"  {e.value}: {e.name}")
    print("Layout:")
    for e in Layout:
        print(f"  {e.value}: {e.name}")
    print("TabWidth:")
    for e in TabWidth:
        print(f"  {e.value}: {e.name}")
    print("DividerKeying:")
    for e in DividerKeying:
        print(f"  {e.value}: {e.name}")


def main_cli():
    """Entry point for command-line boxmaker."""
    import sys
    if '--enums' in sys.argv:
        print_enum_help()
        return
    main(cli=True, schroff=False)


def main_schroff():
    """Entry point for Schroff box maker CLI."""
    main(cli=True, schroff=True)
