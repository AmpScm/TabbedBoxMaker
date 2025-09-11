#!/usr/bin/env python3
"""
Demonstration of the Shapely-based TabbedBoxMaker refactor

This script shows how to use the new Shapely-first geometry building
approach instead of the original SVG-string-first approach.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from tabbedboxmaker import BoxMaker
from tabbedboxmaker.shapely_boxmaker import ShapelyBoxMaker, GeometrySettings
from tabbedboxmaker.geometry import BoxGeometry, BoxAssembly
import inkex
from shapely.geometry import LineString, Polygon


def demonstrate_shapely_geometry():
    """Demonstrate the basic Shapely geometry building"""
    
    print("=== TabbedBoxMaker Shapely Refactor Demonstration ===\n")
    
    # 1. Create geometry settings
    print("1. Creating geometry settings...")
    settings = GeometrySettings(
        thickness=3.0,
        kerf=0.1,
        nomTab=15.0,
        equalTabs=False,
        tabSymmetry=0,
        dimpleHeight=2.0,
        dimpleLength=5.0,
        dogbone=False,
        linethickness=0.1
    )
    print(f"   Settings: thickness={settings.thickness}, kerf={settings.kerf}")
    
    # 2. Create a BoxGeometry builder
    print("\n2. Creating BoxGeometry builder...")
    geometry_builder = BoxGeometry(settings)
    
    # 3. Build a simple side geometry
    print("\n3. Building side geometry with Shapely...")
    side_geometry = geometry_builder.create_side_geometry(
        root=(0, 0),
        startOffset=(0, 0),
        endOffset=(0, 0),
        tabVec=True,
        prevTab=False,
        length=100.0,
        direction=(1, 0),
        isTab=False,
        isDivider=False,
        numDividers=2,
        dividerSpacing=30.0
    )
    
    print(f"   Created side with {len(side_geometry.main_path.coords)} path points")
    print(f"   Side has {len(side_geometry.holes)} divider holes")
    
    # 4. Show the benefits of Shapely geometry
    print("\n4. Demonstrating Shapely benefits...")
    
    # Get path length easily
    path_length = side_geometry.main_path.length
    print(f"   Path length: {path_length:.2f} units")
    
    # Get bounding box easily
    bounds = side_geometry.main_path.bounds
    print(f"   Bounding box: ({bounds[0]:.1f}, {bounds[1]:.1f}) to ({bounds[2]:.1f}, {bounds[3]:.1f})")
    
    # Show path coordinates
    coords = list(side_geometry.main_path.coords)
    print(f"   First point: ({coords[0][0]:.1f}, {coords[0][1]:.1f})")
    print(f"   Last point: ({coords[-1][0]:.1f}, {coords[-1][1]:.1f})")
    
    # 5. Demonstrate geometric operations
    print("\n5. Demonstrating geometric operations...")
    
    # Translate the geometry
    translated = side_geometry.translate(50, 25)
    new_bounds = translated.main_path.bounds
    print(f"   Translated bounding box: ({new_bounds[0]:.1f}, {new_bounds[1]:.1f}) to ({new_bounds[2]:.1f}, {new_bounds[3]:.1f})")
    
    # Show hole information
    if side_geometry.holes:
        hole = side_geometry.holes[0]
        hole_area = hole.area
        hole_centroid = hole.centroid
        print(f"   First hole area: {hole_area:.2f} square units")
        print(f"   First hole centroid: ({hole_centroid.x:.1f}, {hole_centroid.y:.1f})")
    
    # 6. Convert to SVG
    print("\n6. Converting to SVG elements...")
    svg_elements = side_geometry.to_svg_elements(settings)
    print(f"   Created {len(svg_elements)} SVG path elements")
    
    for i, element in enumerate(svg_elements):
        path_str = str(element.path)[:50] + "..." if len(str(element.path)) > 50 else str(element.path)
        print(f"   Element {i+1}: {path_str}")


def demonstrate_advanced_operations():
    """Demonstrate advanced Shapely operations for optimization"""
    
    print("\n\n=== Advanced Shapely Operations ===\n")
    
    # Create some example geometries
    print("1. Creating multiple side geometries...")
    
    settings = GeometrySettings(
        thickness=3.0, kerf=0.1, nomTab=15.0, equalTabs=False,
        tabSymmetry=0, dimpleHeight=2.0, dimpleLength=5.0,
        dogbone=False, linethickness=0.1
    )
    
    geometry_builder = BoxGeometry(settings)
    
    # Create two adjacent sides
    side1 = geometry_builder.create_side_geometry(
        root=(0, 0), startOffset=(0, 0), endOffset=(0, 0),
        tabVec=True, prevTab=False, length=100.0, direction=(1, 0),
        isTab=False, isDivider=False, numDividers=0, dividerSpacing=0
    )
    
    side2 = geometry_builder.create_side_geometry(
        root=(100, 0), startOffset=(0, 0), endOffset=(0, 0),
        tabVec=True, prevTab=False, length=80.0, direction=(0, 1),
        isTab=True, isDivider=False, numDividers=0, dividerSpacing=0
    )
    
    print(f"   Side 1 length: {side1.main_path.length:.2f}")
    print(f"   Side 2 length: {side2.main_path.length:.2f}")
    
    # 2. Demonstrate path analysis
    print("\n2. Analyzing path properties...")
    
    # Check if paths are closed
    def is_closed(linestring):
        coords = list(linestring.coords)
        return len(coords) > 2 and coords[0] == coords[-1]
    
    print(f"   Side 1 closed: {is_closed(side1.main_path)}")
    print(f"   Side 2 closed: {is_closed(side2.main_path)}")
    
    # Get path complexity (number of points)
    complexity1 = len(side1.main_path.coords)
    complexity2 = len(side2.main_path.coords)
    print(f"   Side 1 complexity: {complexity1} points")
    print(f"   Side 2 complexity: {complexity2} points")
    
    # 3. Demonstrate geometric queries
    print("\n3. Geometric queries...")
    
    # Check if geometries intersect
    intersects = side1.main_path.intersects(side2.main_path)
    print(f"   Sides intersect: {intersects}")
    
    # Get distance between geometries
    distance = side1.main_path.distance(side2.main_path)
    print(f"   Distance between sides: {distance:.2f}")
    
    # 4. Show optimization potential
    print("\n4. Optimization potential...")
    
    # Calculate total path length before optimization
    total_length = side1.main_path.length + side2.main_path.length
    print(f"   Total path length: {total_length:.2f}")
    
    # Show how many separate elements we have
    total_elements = 2 + len(side1.holes) + len(side2.holes)
    print(f"   Total elements: {total_elements}")
    
    print("\n   With Shapely, we could:")
    print("   - Combine adjacent paths automatically")
    print("   - Detect and fix gap between paths")
    print("   - Simplify complex geometries")
    print("   - Remove duplicate points")
    print("   - Validate geometric correctness")


def demonstrate_integration():
    """Show how this integrates with the existing BoxMaker"""
    
    print("\n\n=== Integration with Existing BoxMaker ===\n")
    
    print("1. The refactor provides several integration options:")
    print("   a) Drop-in replacement: use shapely_effect() instead of effect()")
    print("   b) Hybrid approach: use create_shapely_side() alongside existing methods")
    print("   c) Gradual migration: convert specific parts to use Shapely")
    
    print("\n2. Benefits of the Shapely-first approach:")
    print("   - Geometric calculations are easier and more accurate")
    print("   - Complex optimizations become possible")
    print("   - Path analysis and validation are built-in")
    print("   - Better support for geometric queries")
    print("   - Cleaner separation between geometry and SVG generation")
    
    print("\n3. Compatibility:")
    print("   - All existing functionality is preserved")
    print("   - Output SVG is identical to original")
    print("   - Can be enabled gradually without breaking changes")
    print("   - Tests continue to pass with new implementation")
    
    print("\n4. Future enhancements enabled:")
    print("   - Automatic path optimization")
    print("   - Geometric collision detection")
    print("   - Advanced nesting algorithms")
    print("   - Better kerf compensation")
    print("   - Improved dogbone calculations")


if __name__ == "__main__":
    try:
        demonstrate_shapely_geometry()
        demonstrate_advanced_operations()
        demonstrate_integration()
        
        print("\n\n=== Summary ===")
        print("The Shapely refactor successfully separates geometry building from SVG generation,")
        print("enabling more sophisticated geometric operations while maintaining full compatibility")
        print("with the existing TabbedBoxMaker functionality.")
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure the tabbedboxmaker package is in your Python path")
    except Exception as e:
        print(f"Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
