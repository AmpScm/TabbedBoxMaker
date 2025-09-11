"""
Geometry classes for TabbedBoxMaker using Shapely

This module provides Shapely-based geometry building for the TabbedBoxMaker,
separating geometric calculations from SVG generation.
"""

from typing import List, Tuple, Optional, Union
from shapely.geometry import LineString, Polygon, Point, MultiLineString
from shapely.ops import unary_union
import inkex
from dataclasses import dataclass


@dataclass
class GeometrySettings:
    """Settings for geometry generation"""
    thickness: float
    kerf: float
    nomTab: float
    equalTabs: bool
    tabSymmetry: int
    dimpleHeight: float
    dimpleLength: float
    dogbone: bool
    linethickness: float


class BoxGeometry:
    """
    Main geometry builder that creates Shapely objects for box sides
    """
    
    def __init__(self, settings: GeometrySettings):
        self.settings = settings
    
    def create_side_geometry(
        self,
        root: Tuple[float, float],
        startOffset: Tuple[float, float],
        endOffset: Tuple[float, float],
        tabVec: float,
        prevTab: bool,
        length: float,
        direction: Tuple[int, int],
        isTab: bool,
        isDivider: bool = False,
        numDividers: int = 0,
        dividerSpacing: float = 0,
    ) -> 'SideGeometry':
        """
        Create geometry for a box side using Shapely
        
        Returns a SideGeometry object containing:
        - main_path: LineString for the main side outline
        - holes: List of Polygon objects for divider holes
        - circles: List of Point objects for circular holes
        """
        
        # Calculate tab parameters
        if self.settings.tabSymmetry == 1:  # waffle-block style rotationally symmetric tabs
            divisions = int((length - 2 * self.settings.thickness) / self.settings.nomTab)
            if divisions % 2:
                divisions += 1  # make divs even
            divisions = float(divisions)
            tabs = divisions / 2  # tabs for side
        else:
            divisions = int(length / self.settings.nomTab)
            if not divisions % 2:
                divisions -= 1  # make divs odd
            divisions = float(divisions)
            tabs = (divisions - 1) / 2  # tabs for side

        if self.settings.tabSymmetry == 1:  # waffle-block style rotationally symmetric tabs
            gapWidth = tabWidth = (length - 2 * self.settings.thickness) / divisions
        elif self.settings.equalTabs:
            gapWidth = tabWidth = length / divisions
        else:
            tabWidth = (length / tabs) / (1 + (1 / self.settings.nomTab))
            gapWidth = tabWidth / self.settings.nomTab

        # Create path points
        path_points = self._build_side_path(
            startOffset, endOffset, tabVec, prevTab, length, direction,
            isTab, divisions, gapWidth, tabWidth, tabs
        )
        
        # Create holes for dividers
        holes = self._create_divider_holes(
            startOffset, endOffset, length, direction, isTab, isDivider,
            numDividers, dividerSpacing, divisions, gapWidth, tabWidth, tabs
        )
        
        # Create circular holes (for rail mounts, etc.)
        circles = []  # These would be added by calling code if needed
        
        return SideGeometry(
            main_path=LineString(path_points),
            holes=holes,
            circles=circles,
            root=root
        )
    
    def _build_side_path(
        self,
        startOffset: Tuple[float, float],
        endOffset: Tuple[float, float],
        tabVec: float,
        prevTab: bool,
        length: float,
        direction: Tuple[int, int],
        isTab: bool,
        divisions: float,
        gapWidth: float,
        tabWidth: float,
        tabs: float
    ) -> List[Tuple[float, float]]:
        """Build the main path points for a side"""
        
        (dirX, dirY) = direction
        (notDirX, notDirY) = (1 - abs(dirX), 1 - abs(dirY))
        (startOffsetX, startOffsetY) = startOffset
        (endOffsetX, endOffsetY) = endOffset
        
        # Initialize path points
        points = []
        
        if isTab:
            if notDirX and tabVec:
                startOffsetX = 0
            if notDirY and tabVec:
                startOffsetY = 0
            if notDirX and tabVec:
                endOffsetX = 0
            if notDirY and tabVec:
                endOffsetY = 0
        else:
            vectorX = startOffsetX * self.settings.thickness
            vectorY = startOffsetY * self.settings.thickness
            
            # Start point
            points.append((vectorX, vectorY))
            
            vectorX = (startOffsetX if startOffsetX else dirX) * self.settings.thickness
            vectorY = (startOffsetY if startOffsetY else dirY) * self.settings.thickness
            
            # Build the tab pattern
            if divisions == 1:
                firstVec = 0
                secondVec = 0
            else:
                if self.settings.tabSymmetry == 1:
                    firstVec = 0
                    secondVec = self.settings.thickness if not isTab else -self.settings.thickness
                else:
                    firstVec = (self.settings.thickness if isTab else -self.settings.thickness) if prevTab else 0
                    secondVec = self.settings.thickness if not isTab else -self.settings.thickness

            # Generate tab geometry
            for tabDivision in range(1, int(divisions) + 1):
                if divisions == 1:
                    w = length
                    first = 0
                else:
                    w = gapWidth if (tabDivision % 2) == (1 if isTab else 0) else tabWidth
                    first = firstVec if tabDivision == 1 else 0

                vectorX += dirX * (first + w / 2)
                vectorY += dirY * (first + w / 2)
                
                # Add dogbone cuts if enabled
                if self.settings.dogbone and (tabDivision % 2) == (0 if isTab else 1):
                    self._add_dogbone_points(points, vectorX, vectorY, dirX, dirY, notDirX, notDirY, first, w)
                else:
                    points.append((
                        vectorX + notDirX * secondVec,
                        vectorY + notDirY * secondVec
                    ))

                vectorX += dirX * w / 2
                vectorY += dirY * w / 2
                points.append((vectorX, vectorY))

                # Swap tab direction for next iteration
                secondVec, firstVec = -secondVec, -firstVec
                first = 0

            # Finish the line
            points.append((
                endOffsetX * self.settings.thickness + dirX * length,
                endOffsetY * self.settings.thickness + dirY * length
            ))
        
        return points
    
    def _add_dogbone_points(
        self, points: List[Tuple[float, float]], 
        vectorX: float, vectorY: float,
        dirX: int, dirY: int, notDirX: int, notDirY: int,
        first: float, w: float
    ):
        """Add dogbone cut points to the path"""
        halfkerf = self.settings.kerf / 2
        
        # Dogbone geometry is complex - this is a simplified version
        # Full implementation would match the original code exactly
        points.append((
            vectorX + notDirX * (self.settings.thickness - self.settings.kerf) + dirX * halfkerf,
            vectorY + notDirY * (self.settings.thickness - self.settings.kerf) + dirY * halfkerf
        ))
    
    def _create_divider_holes(
        self,
        startOffset: Tuple[float, float],
        endOffset: Tuple[float, float],
        length: float,
        direction: Tuple[int, int],
        isTab: bool,
        isDivider: bool,
        numDividers: int,
        dividerSpacing: float,
        divisions: float,
        gapWidth: float,
        tabWidth: float,
        tabs: float
    ) -> List[Polygon]:
        """Create holes for divider tabs"""
        
        holes = []
        
        if numDividers > 0 and not isDivider:
            (dirX, dirY) = direction
            (notDirX, notDirY) = (1 - abs(dirX), 1 - abs(dirY))
            (startOffsetX, startOffsetY) = startOffset
            
            # Create holes for each tab division that needs them
            for tabDivision in range(1, int(divisions) + 1):
                if (((tabDivision % 2) > 0) != (not isTab)):
                    w = gapWidth if isTab else tabWidth
                    if tabDivision == 1 and self.settings.tabSymmetry == 0:
                        w -= startOffsetX * self.settings.thickness
                    
                    # Calculate hole position and size
                    for dividerNumber in range(numDividers):
                        hole_points = self._calculate_hole_points(
                            startOffsetX, startOffsetY, dirX, dirY, notDirX, notDirY,
                            dividerSpacing, dividerNumber, w, tabDivision
                        )
                        
                        if len(hole_points) >= 3:  # Need at least 3 points for a polygon
                            holes.append(Polygon(hole_points))
        
        return holes
    
    def _calculate_hole_points(
        self, startOffsetX: float, startOffsetY: float,
        dirX: int, dirY: int, notDirX: int, notDirY: int,
        dividerSpacing: float, dividerNumber: int,
        w: float, tabDivision: int
    ) -> List[Tuple[float, float]]:
        """Calculate the points for a divider hole"""
        
        # This is a simplified version - full implementation would match original exactly
        hole_points = []
        
        # Calculate base position
        vectorX = startOffsetX * self.settings.thickness
        vectorY = startOffsetY * self.settings.thickness
        
        # Offset for divider position
        vectorX += dirX * dividerSpacing * dividerNumber
        vectorY += dirY * dividerSpacing * dividerNumber
        
        # Create rectangular hole
        hole_width = self.settings.thickness - self.settings.kerf
        hole_length = w
        
        # Four corners of the hole
        hole_points = [
            (vectorX, vectorY),
            (vectorX + dirX * hole_length, vectorY + dirY * hole_length),
            (vectorX + dirX * hole_length + notDirX * hole_width, 
             vectorY + dirY * hole_length + notDirY * hole_width),
            (vectorX + notDirX * hole_width, vectorY + notDirY * hole_width)
        ]
        
        return hole_points


class SideGeometry:
    """
    Represents the geometry of one box side
    """
    
    def __init__(
        self, 
        main_path: LineString, 
        holes: List[Polygon], 
        circles: List[Point],
        root: Tuple[float, float]
    ):
        self.main_path = main_path
        self.holes = holes
        self.circles = circles
        self.root = root
    
    def translate(self, dx: float, dy: float) -> 'SideGeometry':
        """Return a translated copy of this geometry"""
        from shapely.affinity import translate
        
        return SideGeometry(
            main_path=translate(self.main_path, dx, dy),
            holes=[translate(hole, dx, dy) for hole in self.holes],
            circles=[translate(circle, dx, dy) for circle in self.circles],
            root=(self.root[0] + dx, self.root[1] + dy)
        )
    
    def to_svg_elements(self, settings: GeometrySettings) -> List[inkex.PathElement]:
        """Convert this geometry to SVG path elements"""
        elements = []
        
        # Main path
        main_element = inkex.PathElement()
        main_element.path = self._linestring_to_svg_path(self.main_path)
        main_element.style = {'stroke': '#0000ff', 'stroke-width': str(settings.linethickness), 'fill': 'none'}
        elements.append(main_element)
        
        # Holes
        for hole in self.holes:
            hole_element = inkex.PathElement()
            hole_element.path = self._polygon_to_svg_path(hole)
            hole_element.style = {'stroke': '#0000ff', 'stroke-width': str(settings.linethickness), 'fill': 'none'}
            elements.append(hole_element)
        
        # Circles (would need circle-specific handling)
        for circle in self.circles:
            # Create circle element - this would need proper implementation
            pass
        
        return elements
    
    def _linestring_to_svg_path(self, linestring: LineString) -> str:
        """Convert a Shapely LineString to SVG path string"""
        coords = list(linestring.coords)
        if not coords:
            return ""
        
        path_parts = [f"M {coords[0][0]},{coords[0][1]}"]
        for x, y in coords[1:]:
            path_parts.append(f"L {x},{y}")
        
        return " ".join(path_parts)
    
    def _polygon_to_svg_path(self, polygon: Polygon) -> str:
        """Convert a Shapely Polygon to SVG path string"""
        coords = list(polygon.exterior.coords)
        if not coords:
            return ""
        
        path_parts = [f"M {coords[0][0]},{coords[0][1]}"]
        for x, y in coords[1:]:
            path_parts.append(f"L {x},{y}")
        path_parts.append("Z")  # Close the path
        
        return " ".join(path_parts)


class BoxAssembly:
    """
    Represents a complete box assembly with all sides
    """
    
    def __init__(self):
        self.sides: List[SideGeometry] = []
        self.dividers: List[SideGeometry] = []
    
    def add_side(self, side: SideGeometry):
        """Add a side to the assembly"""
        self.sides.append(side)
    
    def add_divider(self, divider: SideGeometry):
        """Add a divider to the assembly"""
        self.dividers.append(divider)
    
    def optimize_paths(self) -> 'BoxAssembly':
        """
        Optimize the box assembly using Shapely operations
        
        This method can:
        1. Combine adjacent paths using unary_union
        2. Simplify complex geometries
        3. Remove duplicate points
        4. Detect and close open paths
        """
        optimized = BoxAssembly()
        
        # For now, just copy - full optimization would use Shapely operations
        optimized.sides = self.sides[:]
        optimized.dividers = self.dividers[:]
        
        return optimized
    
    def to_svg_groups(self, settings: GeometrySettings, svg_root) -> List[inkex.Group]:
        """Convert the entire assembly to SVG groups"""
        groups = []
        
        # Create group for main sides
        main_group = inkex.Group()
        main_group.set('id', 'box-sides')
        
        for side in self.sides:
            elements = side.to_svg_elements(settings)
            for element in elements:
                main_group.add(element)
        
        groups.append(main_group)
        
        # Create group for dividers
        if self.dividers:
            divider_group = inkex.Group()
            divider_group.set('id', 'dividers')
            
            for divider in self.dividers:
                elements = divider.to_svg_elements(settings)
                for element in elements:
                    divider_group.add(element)
            
            groups.append(divider_group)
        
        return groups
