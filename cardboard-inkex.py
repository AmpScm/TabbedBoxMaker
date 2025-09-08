#! /usr/bin/env python -t
'''
Generates Inkscape SVG file containing box components needed to 
CNC (laser/mill) cut a card board box

Original Tabbed Box Maker Copyright (C) 2011 elliot white
Cardboard Box Maker Copyright (C) 2024 Brad Goodman

Changelog:
14/05/2024 Brad Goodman:
    - Created from Tabbed Box Maker

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
'''

from tabbedboxmaker.cardboard import main

if __name__ == "__main__":
  main(cli=False)