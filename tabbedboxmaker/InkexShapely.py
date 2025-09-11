#! /usr/bin/env python -t
"""
    Tabbed Box Maker for Inkscape

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
from inkex.paths.lines import Line, Move, move, ZoneClose, zoneClose
from shapely.geometry import Polygon, MultiPolygon, LinearRing

def fstr(f: float) -> str:
    """Format float to string with minimal decimal places, avoiding scientific notation."""
    if f.is_integer():
        return str(int(f))

    r = str(f)

    if r.endswith('.0'):
        return r[:-2]
    else:
        return r

def path_to_polygon(path_obj : inkex.Path) -> Polygon | None:
    # Accepts inkex.Path object, only absolute Move/Line/Close
    from shapely.geometry import Polygon
    coords = []
    for seg in path_obj:
        if seg.letter == 'M':
            coords.append((seg.x, seg.y))
        elif seg.letter == 'L':
            coords.append((seg.x, seg.y))
        elif seg.letter in 'Zz':
            continue
        else:
            raise AssertionError(f"Unexpected path segment type: {seg.letter}")
    if len(coords) > 2:
        return Polygon(coords)
    return None

def polygon_to_path(poly : Polygon) -> inkex.Path:
    # Accepts shapely Polygon, returns inkex.Path string
    coords = list(poly.exterior.coords)

    path = []
    path.append(Move(coords[0][0], coords[0][1]))
    for x, y in coords[1:]:
        path.append(Line(x, y))
    path.append(ZoneClose())

    # Add holes in stable order
    interiors = list(poly.interiors)

    for i in interiors:
        coords = list(i.coords)

        if len(coords) > 3:
            pMin = min(coords, key=lambda c: (c[0], c[1]))

            if pMin != coords[0]:
                # Rotate the coordinates so that pMin is first
                min_index = coords.index(pMin)

                # Remove the old duplicate point (if it exists)
                if coords[-1] == coords[0]:
                    coords = coords[:-1]

                # Rotate the coordinate list to start with pMin
                rotated_coords = coords[min_index:] + coords[:min_index]
                # Ensure the ring is properly closed with the NEW first point
                rotated_coords.append(rotated_coords[0])
                # Update the interior ring with rotated coordinates

                interiors[interiors.index(i)] = LinearRing(rotated_coords)

    # Sort by first coordinate (X, then Y)
    interiors.sort(key=lambda ring: f"{ring.coords[0][0]},{ring.coords[0][1]}")

    for interior in interiors:
        coords = list(interior.coords)
        path.append(Move(coords[0][0], coords[0][1]))
        for x, y in coords[1:]:
            path.append(Line(x, y))
        path.append(ZoneClose())

    return inkex.Path(path)

