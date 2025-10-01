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

import math
import sys
import inkex

from inkex import Path, PathElement

from typing import List, Tuple, Set
from inkex.paths.lines import Line, Move, ZoneClose

def fstr(f: float) -> str:
    """Format float to string with minimal decimal places, avoiding scientific notation."""
    if f.is_integer():
        return str(int(f))

    r = str(f)

    if r.endswith('.0'):
        return r[:-2]
    else:
        return r


def path_to_polygon(path_obj : inkex.Path):
    from shapely.geometry import Polygon
    # Accepts inkex.Path object, only absolute Move/Line/Close
    coords = []

    paths = []
    for seg in path_obj:
        if seg.letter == 'M':
            coords.append((seg.x, seg.y))
        elif seg.letter == 'L':
            coords.append((seg.x, seg.y))
        elif seg.letter in 'Zz':
            paths.append(coords)
            coords = []
            continue
        else:
            raise AssertionError(f"Unexpected path segment type: {seg.letter}")

    if len(coords) > 2:
        paths.append(coords)

    if len(paths) == 1:
        return Polygon(paths[0])
    elif len(paths) > 1:
        return Polygon(paths[0], holes=paths[1:])
    return None


def polygon_to_path(poly):
    from shapely.geometry import Polygon, MultiPolygon, LinearRing
    # Accepts shapely Polygon or MultiPolygon, returns inkex.Path string

    path = inkex.Path()

    def add_polygon_to_path(polygon: Polygon, path: inkex.Path):
        coords = list(polygon.exterior.coords)
        path.append(Move(coords[0][0], coords[0][1]))
        for x, y in coords[1:]:
            path.append(Line(x, y))
        path.append(ZoneClose())

        # Add holes in stable order
        interiors = list(polygon.interiors)

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

    # Handle both Polygon and MultiPolygon
    if isinstance(poly, MultiPolygon):
        for polygon in poly.geoms:
            add_polygon_to_path(polygon, path)
    elif isinstance(poly, Polygon):
        add_polygon_to_path(poly, path)
    else:
        raise ValueError(f"Expected Polygon or MultiPolygon, got {type(poly)}")

    return path

def best_effort_inkex_combine_paths(paths: list[inkex.Path]):
    panel = paths[0]
    group = panel.getparent()
    holes = paths[1:]

    panel_bb = panel.bounding_box()
    combined_superpath = panel.path.to_superpath()

    ignore_holes = []

    # Ok, now combine holes using our very simple combiner.
    # LIMITATION: Any hole can be combined only once, so we keep track of which ones
    # have already been combined.
    for hole in holes:
        hole_bb = hole.bounding_box()

        if hole not in ignore_holes:
            for other in holes:
                if hole_bb & other.bounding_box() and other != hole and other not in ignore_holes and len(hole.path) == 5 and len(other.path) == 5:
                    # Merge the two holes
                    new_path = merge_two_rectangles_to_outer_path(hole, other)
                    hole.path = new_path
                    ignore_holes.append(other)
                    ignore_holes.append(hole)
                    group.remove(other)
                    holes.remove(other)
                    break

    dont_touch = []

    for hole in holes:
        hole_bb = hole.bounding_box()

        # Skip if touching or outside panel
        if (hole_bb.left <= panel_bb.left or hole_bb.right >= panel_bb.right or
            hole_bb.top <= panel_bb.top or hole_bb.bottom >= panel_bb.bottom):
            continue

        if any(hole_bb & dont for dont in dont_touch):
            continue

        dont_touch.append(hole_bb)

        combined_superpath.append(hole.path.to_superpath()[0])
        group.remove(hole)

    panel.path = inkex.Path(combined_superpath)


def try_attach_paths(group: list[inkex.BaseElement], tolerance: float = 0.01, reverse: bool = False, replace_group=False) -> bool:
    """Try to attach paths end-to-start if they are close enough, and close paths if start and end meet."""
    updated_one = False
    for i in group:
        if isinstance(i, inkex.Group):
            if try_attach_paths(i, tolerance=tolerance, reverse=reverse, replace_group=True):
                updated_one = True

    if len(group) > 1:
        paths = [x for x in group if isinstance(x, inkex.PathElement) and len(x.path) > 1]
        skip_elements = []

        for path_element in paths:
            path = path_element.path

            if any(i is path_element for i in skip_elements):
                continue
            elif any(el for el in path if isinstance(el, inkex.paths.RelativePathCommand)):
                path_element.path = path = path.to_absolute()

            path_last = path[-1]

            if isinstance(path_last, inkex.paths.ZoneClose):
                continue  # Path is already closed

            loop = True
            while loop:
                loop = False

                for other_element in paths:
                    if any(i is other_element for i in skip_elements) or other_element is path_element:
                        continue

                    other_path = Path(other_element.path)

                    if any(el for el in other_path if isinstance(el, inkex.paths.RelativePathCommand)):
                        other_element.path = other_path = Path(other_path.to_absolute())

                    if isinstance(other_path[-1], inkex.paths.ZoneClose):
                        continue  # Path is already closed

                    (other_first, other_last) = (other_path[0], other_path[-1])

                    if math.fabs(other_first.x-path_last.x) < 0.01 and math.fabs(other_first.y - path_last.y) < tolerance:
                        new_id = min(path_element.get_id(), other_element.get_id())
                        path_element.path = path = Path(path + other_path[1:])
                        other_element.getparent().remove(other_element)
                        path_element.set_id(new_id)
                        skip_elements.append(other_element)

                        # Update step for next iteration
                        path_last = path[-1]
                        updated_one = loop = True
                        break
                    elif math.fabs(other_last.x-path_last.x) < 0.01 and math.fabs(other_last.y - path_last.y) < tolerance:
                        new_id = min(path_element.get_id(), other_element.get_id())
                        path_element.path = path = Path(path + other_path.reverse()[1:])
                        #print(other_element.get_id(), file=sys.stderr)
                        other_element.getparent().remove(other_element)
                        path_element.set_id(new_id)
                        skip_elements.append(other_element)

                        # Update step for next iteration
                        path_last = path[-1]
                        updated_one = loop = True
                        break


            if isinstance(path_last, inkex.paths.ZoneClose) or isinstance(path_last, inkex.paths.zoneClose):
                continue  # Path is already closed. Not sure why we only see this now
            elif path_last.x == path[0].x and path_last.y == path[0].y:
                if reverse:
                    path = path.reverse() # Ensure correct winding order

                path.append(inkex.paths.ZoneClose())
                path_element.path = path

            try_clean_paths([path_element])

    if replace_group and isinstance(group, inkex.Group) and len(group) == 1:
        parent = group.getparent()
        if parent is not None:
            group_id = group.get_id()
            item = group[0]
            parent.replace(group, item)
            item.set_id(group_id)

    return updated_one

def try_clean_paths(paths: list[inkex.BaseElement]):
    """Try to clean paths by removing duplicate points and zero-length segments."""
            # Step 2: Remove unneeded generated nodes (duplicates and intermediates on h/v lines)
    for path_element in paths:

        if not isinstance(path_element, inkex.PathElement) or len(path_element.path) < 1:
            continue

        path = path_element.path

        updated = False
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
                        updated = True
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
                        updated = True
                    else:
                        simplified_path.append(segment)
                    current_dir = direction
                else:
                    if prev is not None:
                        dx = round(segment.x - prev.x, 8)
                        dy = round(segment.y - prev.y, 8)
                        if dx == 0 and dy == 0:
                            updated = True
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

        if updated:
            path_element.path = simplified_path



def try_combine_paths(paths: list[inkex.Path], inkscape: bool = False, no_subtract: bool = False):
    if len(paths) < 2:
        return

    if inkscape or no_subtract:
        return best_effort_inkex_combine_paths(paths)

    try:
        from shapely.ops import unary_union
        panel = paths[0]
        group = panel.getparent()
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
    except Exception as e:
        return best_effort_inkex_combine_paths(paths)

def adjust_canvas(svg,
                  unit: str | None = None) -> None:
    """ Adjust the SVG canvas to fit the content """
    layer = svg.get_current_layer()
    # Collect all bboxes
    all_bboxes = []
    for el in layer.descendants():
        if isinstance(el, inkex.PathElement):
            all_bboxes.append(el.bounding_box())

    if all_bboxes:
        minx = min(min(b.left for b in all_bboxes), 0)
        miny = min(min(b.top for b in all_bboxes), 0)
        maxx = max(max(b.right for b in all_bboxes), 0)
        maxy = max(max(b.bottom for b in all_bboxes), 0)
        width = maxx - minx + 1
        height = maxy - miny + 1
        svg.set('width', fstr(width) + unit if unit else svg.unit)
        svg.set('height', fstr(height) + unit if unit else svg.unit)
        svg.set('viewBox', f"{fstr(minx)} {fstr(miny)} {fstr(width)} {fstr(height)}")


###
def merge_two_rectangles_to_outer_path(rect1: inkex.PathElement, rect2: inkex.PathElement) -> inkex.Path:
    """
    Merge two axis-aligned rectangles into a single outer contour using only coordinate math.
    """

    def extract_rectangle_bounds(path_elem: inkex.PathElement) -> Tuple[float, float, float, float]:
        """Extract bounding box from a rectangle path element."""
        path = path_elem.path

        # Convert path to absolute coordinates
        path = path.to_absolute()

        # Extract all points from the path
        points = []
        for seg in path:
            if seg.letter in ['M', 'L']:  # Move or Line commands
                points.append((seg.x, seg.y))

        # Validate rectangle (should have 4-5 points, with first and last being same if closed)
        if len(points) < 4:
            raise ValueError("Path does not contain enough points for a rectangle")

        # If closed path, last point might be same as first
        if len(points) == 5 and points[0] == points[4]:
            points = points[:-1]  # Remove duplicate closing point
        elif len(points) != 4:
            raise ValueError(f"Expected 4 corner points, got {len(points)}")

        # Extract bounding box
        x_coords = [p[0] for p in points]
        y_coords = [p[1] for p in points]

        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)

        # Validate it's axis-aligned (all points should be at corners)
        corner_count = 0
        for x, y in points:
            if (x == min_x or x == max_x) and (y == min_y or y == max_y):
                corner_count += 1

        if corner_count != 4:
            raise ValueError("Rectangle is not axis-aligned")

        return min_x, min_y, max_x, max_y

    def rectangles_overlap(r1: Tuple[float, float, float, float],
                          r2: Tuple[float, float, float, float]) -> bool:
        """Check if two rectangles overlap."""
        x1_min, y1_min, x1_max, y1_max = r1
        x2_min, y2_min, x2_max, y2_max = r2

        return not (x1_max <= x2_min or x2_max <= x1_min or
                   y1_max <= y2_min or y2_max <= y1_min)

    def compute_overlap(r1: Tuple[float, float, float, float],
                       r2: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        """Compute overlap rectangle of two rectangles."""
        x1_min, y1_min, x1_max, y1_max = r1
        x2_min, y2_min, x2_max, y2_max = r2

        overlap_min_x = max(x1_min, x2_min)
        overlap_min_y = max(y1_min, y2_min)
        overlap_max_x = min(x1_max, x2_max)
        overlap_max_y = min(y1_max, y2_max)

        return overlap_min_x, overlap_min_y, overlap_max_x, overlap_max_y

    def fragment_rectangle(rect: Tuple[float, float, float, float],
                          overlap: Tuple[float, float, float, float]) -> List[Tuple[float, float, float, float]]:
        """Fragment a rectangle by removing the overlap area."""
        min_x, min_y, max_x, max_y = rect
        ov_min_x, ov_min_y, ov_max_x, ov_max_y = overlap

        fragments = []

        # Left fragment
        if min_x < ov_min_x:
            fragments.append((min_x, min_y, ov_min_x, max_y))

        # Right fragment
        if max_x > ov_max_x:
            fragments.append((ov_max_x, min_y, max_x, max_y))

        # Bottom fragment (excluding corners already covered)
        if min_y < ov_min_y:
            fragments.append((max(min_x, ov_min_x), min_y, min(max_x, ov_max_x), ov_min_y))

        # Top fragment (excluding corners already covered)
        if max_y > ov_max_y:
            fragments.append((max(min_x, ov_min_x), ov_max_y, min(max_x, ov_max_x), max_y))

        return fragments

    def get_all_critical_points(fragments: List[Tuple[float, float, float, float]]) -> Set[Tuple[float, float]]:
        """Get all unique corner points from all fragments."""
        points = set()
        for min_x, min_y, max_x, max_y in fragments:
            points.add((min_x, min_y))
            points.add((min_x, max_y))
            points.add((max_x, min_y))
            points.add((max_x, max_y))
        return points

    def point_on_boundary(point: Tuple[float, float], fragments: List[Tuple[float, float, float, float]]) -> bool:
        """Check if a point is on the boundary of the union."""
        x, y = point

        # Count how many fragments contain this point
        containing_fragments = []
        for i, (min_x, min_y, max_x, max_y) in enumerate(fragments):
            if min_x <= x <= max_x and min_y <= y <= max_y:
                containing_fragments.append(i)

        if not containing_fragments:
            return False

        # Check if point is on the exterior boundary
        # A point is on the boundary if it's on the edge of at least one fragment
        # and not completely interior to the union
        for i in containing_fragments:
            min_x, min_y, max_x, max_y = fragments[i]
            # Point is on edge of this fragment
            if x == min_x or x == max_x or y == min_y or y == max_y:
                # Check if this edge is external (not shared with another fragment)
                if is_external_edge(point, fragments, i):
                    return True

        return False

    def is_external_edge(point: Tuple[float, float], fragments: List[Tuple[float, float, float, float]], frag_idx: int) -> bool:
        """Check if a point on a fragment edge is external to the union."""
        x, y = point
        min_x, min_y, max_x, max_y = fragments[frag_idx]

        # Determine which edge(s) the point is on
        edges = []
        if x == min_x: edges.append('left')
        if x == max_x: edges.append('right')
        if y == min_y: edges.append('bottom')
        if y == max_y: edges.append('top')

        for edge in edges:
            if is_edge_external(point, edge, fragments):
                return True

        return False

    def is_edge_external(point: Tuple[float, float], edge: str, fragments: List[Tuple[float, float, float, float]]) -> bool:
        """Check if a specific edge at a point is external."""
        x, y = point
        epsilon = 1e-9

        # Define test points slightly outside each edge
        test_points = {
            'left': (x - epsilon, y),
            'right': (x + epsilon, y),
            'bottom': (x, y - epsilon),
            'top': (x, y + epsilon)
        }

        test_point = test_points[edge]

        # If test point is not contained in any fragment, then this edge is external
        for min_x, min_y, max_x, max_y in fragments:
            if min_x < test_point[0] < max_x and min_y < test_point[1] < max_y:
                return False

        return True

    def get_outer_boundary_points(fragments: List[Tuple[float, float, float, float]]) -> List[Tuple[float, float]]:
        """Get the outer boundary points by walking around the perimeter."""
        # Create a grid of all critical x and y coordinates
        all_x_coords = set()
        all_y_coords = set()

        for min_x, min_y, max_x, max_y in fragments:
            all_x_coords.update([min_x, max_x])
            all_y_coords.update([min_y, max_y])

        x_coords = sorted(all_x_coords)
        y_coords = sorted(all_y_coords)

        # Create a 2D grid to mark which cells are filled
        grid = {}
        for i in range(len(x_coords) - 1):
            for j in range(len(y_coords) - 1):
                cell_x1, cell_x2 = x_coords[i], x_coords[i + 1]
                cell_y1, cell_y2 = y_coords[j], y_coords[j + 1]
                cell_center_x = (cell_x1 + cell_x2) / 2
                cell_center_y = (cell_y1 + cell_y2) / 2

                # Check if this cell is covered by any fragment
                cell_filled = False
                for min_x, min_y, max_x, max_y in fragments:
                    if min_x <= cell_center_x <= max_x and min_y <= cell_center_y <= max_y:
                        cell_filled = True
                        break

                grid[(i, j)] = cell_filled

        # Extract the outer boundary by walking around filled cells
        boundary_points = []

        # Find bottom-left corner of the bounding box
        min_x_idx = 0
        min_y_idx = 0

        # Walk around the outer boundary
        visited_edges = set()

        def add_boundary_rectangle_points():
            """Add points by tracing the outline of filled regions."""
            boundary_segments = []

            # Collect all edges of filled cells
            for (i, j), filled in grid.items():
                if filled:
                    x1, x2 = x_coords[i], x_coords[i + 1]
                    y1, y2 = y_coords[j], y_coords[j + 1]

                    # Check each edge to see if it's on the boundary
                    # Bottom edge
                    if j == 0 or not grid.get((i, j - 1), False):
                        boundary_segments.append(((x1, y1), (x2, y1)))
                    # Top edge
                    if j == len(y_coords) - 2 or not grid.get((i, j + 1), False):
                        boundary_segments.append(((x2, y2), (x1, y2)))
                    # Left edge
                    if i == 0 or not grid.get((i - 1, j), False):
                        boundary_segments.append(((x1, y2), (x1, y1)))
                    # Right edge
                    if i == len(x_coords) - 2 or not grid.get((i + 1, j), False):
                        boundary_segments.append(((x2, y1), (x2, y2)))

            return boundary_segments

        segments = add_boundary_rectangle_points()

        if not segments:
            return []

        # Connect segments to form a continuous boundary
        # Start with leftmost-bottom point
        all_points = set()
        for seg in segments:
            all_points.add(seg[0])
            all_points.add(seg[1])

        if not all_points:
            return []

        start_point = min(all_points, key=lambda p: (p[1], p[0]))  # Bottom-most, then left-most

        # Build adjacency list
        adjacency = {}
        for p1, p2 in segments:
            if p1 not in adjacency:
                adjacency[p1] = []
            if p2 not in adjacency:
                adjacency[p2] = []
            adjacency[p1].append(p2)
            adjacency[p2].append(p1)

        # Trace boundary
        boundary_points = [start_point]
        current = start_point
        prev = None

        while True:
            candidates = [p for p in adjacency.get(current, []) if p != prev]
            if not candidates:
                break

            # Choose next point (prefer continuing in same direction when possible)
            if len(candidates) == 1:
                next_point = candidates[0]
            else:
                # Choose the point that makes the smallest left turn (counterclockwise)
                next_point = candidates[0]  # Simple fallback

            if next_point == start_point and len(boundary_points) > 2:
                break

            boundary_points.append(next_point)
            prev = current
            current = next_point

            if len(boundary_points) > len(all_points):  # Prevent infinite loops
                break

        return boundary_points

    # Main algorithm
    # Extract bounds of both rectangles
    bounds1 = extract_rectangle_bounds(rect1)
    bounds2 = extract_rectangle_bounds(rect2)

    # Check if rectangles overlap or touch
    if not rectangles_overlap(bounds1, bounds2):
        # No overlap - create union of both rectangles
        all_fragments = [bounds1, bounds2]
    else:
        # Compute overlap
        overlap = compute_overlap(bounds1, bounds2)

        # Fragment both rectangles
        fragments1 = fragment_rectangle(bounds1, overlap)
        fragments2 = fragment_rectangle(bounds2, overlap)

        # Combine all fragments plus the overlap
        all_fragments = fragments1 + fragments2 + [overlap]

    # Get outer boundary points using proper boundary tracing
    boundary_points = get_outer_boundary_points(all_fragments)

    # Create the path
    if not boundary_points:
        return inkex.Path()

    path_data = f"M {boundary_points[0][0]},{boundary_points[0][1]}"
    for point in boundary_points[1:]:
        path_data += f" L {point[0]},{point[1]}"
    path_data += " Z"  # Close the path

    return inkex.Path(path_data)
