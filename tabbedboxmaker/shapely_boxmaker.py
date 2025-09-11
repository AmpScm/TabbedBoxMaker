"""
Shapely-based refactor of TabbedBoxMaker

This refactored version builds all geometry using Shapely objects first,
then converts to SVG at the final step. This enables better geometric
calculations and optimizations.
"""

from tabbedboxmaker.geometry import BoxGeometry, GeometrySettings, BoxAssembly, SideGeometry
import inkex
from typing import Tuple, List


class ShapelyBoxMaker:
    """
    Refactored BoxMaker that uses Shapely for all geometry building
    """
    
    def __init__(self, original_boxmaker):
        """Initialize from an existing BoxMaker instance"""
        self.original = original_boxmaker
        
        # Create geometry settings from original BoxMaker properties
        self.settings = GeometrySettings(
            thickness=original_boxmaker.thickness,
            kerf=original_boxmaker.kerf,
            nomTab=original_boxmaker.nomTab,
            equalTabs=original_boxmaker.equalTabs,
            tabSymmetry=original_boxmaker.tabSymmetry,
            dimpleHeight=original_boxmaker.dimpleHeight,
            dimpleLength=original_boxmaker.dimpleLength,
            dogbone=original_boxmaker.dogbone,
            linethickness=original_boxmaker.linethickness
        )
        
        self.geometry_builder = BoxGeometry(self.settings)
        self.assembly = BoxAssembly()
    
    def build_side_geometry(
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
    ) -> SideGeometry:
        """
        Build geometry for a side using Shapely instead of SVG strings
        
        This replaces the original side() method's SVG string building
        with Shapely geometry creation.
        """
        
        side_geometry = self.geometry_builder.create_side_geometry(
            root=root,
            startOffset=startOffset,
            endOffset=endOffset,
            tabVec=tabVec,
            prevTab=prevTab,
            length=length,
            direction=direction,
            isTab=isTab,
            isDivider=isDivider,
            numDividers=numDividers,
            dividerSpacing=dividerSpacing
        )
        
        # Translate to final position
        rootX, rootY = root
        return side_geometry.translate(rootX, rootY)
    
    def build_piece_geometry(
        self,
        piece_config: tuple,
        idx: int,
        spacing: float,
        divx: int,
        divy: int
    ) -> List[SideGeometry]:
        """
        Build all geometry for a single piece (4 sides)
        
        Returns a list of SideGeometry objects representing the piece
        """
        
        # Extract piece configuration (mirrors original effect() method)
        root, dims, tabs, tabbed, pieceType = piece_config[:5]
        (x, y) = (root[0] * spacing, root[1] * spacing) 
        (dx, dy) = (dims[0], dims[1])
        
        # Extract tab status for each side
        aIsMale = 0 < (tabs >> 3 & 1)
        bIsMale = 0 < (tabs >> 2 & 1) 
        cIsMale = 0 < (tabs >> 1 & 1)
        dIsMale = 0 < (tabs & 1)
        
        # Extract tabbed flag for each side
        aHasTabs = 0 < (tabbed >> 3 & 1)
        bHasTabs = 0 < (tabbed >> 2 & 1)
        cHasTabs = 0 < (tabbed >> 1 & 1)
        dHasTabs = 0 < (tabbed & 1)
        
        # Calculate divider spacing
        xspacing = (dims[0] - self.settings.thickness) / (divy + 1)
        yspacing = (dims[1] - self.settings.thickness) / (divx + 1)
        
        # Determine if this piece has divider holes
        xholes = len(piece_config) > 6 and piece_config[6] < 3
        yholes = len(piece_config) > 6 and piece_config[6] != 2
        wall = len(piece_config) > 6 and piece_config[6] > 1
        floor = len(piece_config) > 6 and piece_config[6] == 1
        
        sides = []
        
        # Side A (top)
        side_a = self.build_side_geometry(
            root=(x, y),
            startOffset=(dIsMale, aIsMale),
            endOffset=(-bIsMale, aIsMale),
            tabVec=aHasTabs,
            prevTab=dHasTabs,
            length=dx,
            direction=(1, 0),
            isTab=aIsMale,
            isDivider=False,
            numDividers=((self.original.keydivfloor or wall) and 
                        (self.original.keydivwalls or floor) and 
                        aHasTabs and yholes) * divx,
            dividerSpacing=yspacing,
        )
        sides.append(side_a)
        
        # Side B (right)
        side_b = self.build_side_geometry(
            root=(x + dx, y),
            startOffset=(-bIsMale, aIsMale),
            endOffset=(-bIsMale, -cIsMale),
            tabVec=bHasTabs,
            prevTab=aHasTabs,
            length=dy,
            direction=(0, 1),
            isTab=bIsMale,
            isDivider=False,
            numDividers=((self.original.keydivfloor or wall) and 
                        (self.original.keydivwalls or floor) and 
                        bHasTabs and xholes) * divy,
            dividerSpacing=xspacing,
        )
        sides.append(side_b)
        
        # Side C (bottom)
        side_c = self.build_side_geometry(
            root=(x + dx, y + dy),
            startOffset=(-bIsMale, -cIsMale),
            endOffset=(dIsMale, -cIsMale),
            tabVec=cHasTabs,
            prevTab=bHasTabs,
            length=dx,
            direction=(-1, 0),
            isTab=cIsMale,
            isDivider=False,
            numDividers=((self.original.keydivfloor or wall) and 
                        (self.original.keydivwalls or floor) and 
                        not aHasTabs and cHasTabs and yholes) * divx,
            dividerSpacing=yspacing,
        )
        sides.append(side_c)
        
        # Side D (left)
        side_d = self.build_side_geometry(
            root=(x, y + dy),
            startOffset=(dIsMale, -cIsMale),
            endOffset=(dIsMale, aIsMale),
            tabVec=dHasTabs,
            prevTab=cHasTabs,
            length=dy,
            direction=(0, -1),
            isTab=dIsMale,
            isDivider=False,
            numDividers=((self.original.keydivfloor or wall) and 
                        (self.original.keydivwalls or floor) and 
                        not bHasTabs and dHasTabs and xholes) * divy,
            dividerSpacing=xspacing,
        )
        sides.append(side_d)
        
        return sides
    
    def build_divider_geometry(
        self,
        divider_type: str,  # 'x' or 'y'
        count: int,
        spacing: float,
        dims: Tuple[float, float],
        base_y: float
    ) -> List[SideGeometry]:
        """
        Build geometry for dividers
        """
        dividers = []
        
        # This would implement the divider generation logic
        # from the original effect() method lines 775-900
        
        return dividers
    
    def optimize_assembly(self) -> BoxAssembly:
        """
        Apply Shapely-based optimizations to the complete assembly
        
        This can perform optimizations that weren't possible with
        the string-based approach:
        1. Combine overlapping paths
        2. Remove duplicate geometries  
        3. Simplify complex paths
        4. Detect and fix open paths
        """
        
        # For now, return the assembly as-is
        # Full optimization would use Shapely operations like unary_union
        return self.assembly
    
    def generate_svg_output(self, svg_root) -> List[inkex.Group]:
        """
        Convert the final optimized geometry to SVG groups
        
        This is the final step that converts all Shapely geometries
        to SVG elements for output.
        """
        
        optimized_assembly = self.optimize_assembly()
        return optimized_assembly.to_svg_groups(self.settings, svg_root)


def refactor_boxmaker_effect(original_boxmaker):
    """
    Drop-in replacement for the original effect() method
    
    This function can be called instead of the original effect()
    to use the Shapely-based geometry building approach.
    """
    
    # Create Shapely-based builder
    shapely_builder = ShapelyBoxMaker(original_boxmaker)
    
    # Get the piece configurations from the original logic
    # This would extract the pieces list from the original effect() method
    pieces = original_boxmaker._get_pieces_configuration()
    
    # Build geometry for each piece
    for idx, piece in enumerate(pieces):
        if idx < 2:  # Skip divider templates
            continue
            
        sides = shapely_builder.build_piece_geometry(
            piece_config=piece,
            idx=idx,
            spacing=original_boxmaker.options.spacing,
            divx=original_boxmaker.options.div_l,
            divy=original_boxmaker.options.div_w
        )
        
        # Add sides to assembly
        for side in sides:
            shapely_builder.assembly.add_side(side)
    
    # Generate final SVG output
    svg_groups = shapely_builder.generate_svg_output(original_boxmaker.svg)
    
    # Add groups to the SVG document
    current_layer = original_boxmaker.svg.get_current_layer()
    for group in svg_groups:
        current_layer.add(group)


# Extension point for integrating with the original BoxMaker
def add_shapely_geometry_to_boxmaker():
    """
    Add the Shapely geometry methods to the existing BoxMaker class
    
    This allows the original BoxMaker to use Shapely geometry while
    maintaining compatibility with existing code.
    """
    from tabbedboxmaker import BoxMaker
    
    def create_shapely_side(self, *args, **kwargs):
        """Alternative to the original side() method using Shapely"""
        shapely_builder = ShapelyBoxMaker(self)
        return shapely_builder.build_side_geometry(*args, **kwargs)
    
    def shapely_effect(self):
        """Alternative effect() method using Shapely geometry"""
        return refactor_boxmaker_effect(self)
    
    # Add methods to BoxMaker class
    BoxMaker.create_shapely_side = create_shapely_side
    BoxMaker.shapely_effect = shapely_effect
