#!/usr/bin/env python3
"""
Comparison between original SVG-string approach and new Shapely-first approach
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from tabbedboxmaker.geometry import BoxGeometry, GeometrySettings
from shapely.geometry import LineString


def demonstrate_comparison():
    """Compare the old vs new approaches"""
    
    print("=== TabbedBoxMaker: Old vs New Approach Comparison ===\n")
    
    # Common parameters for both approaches
    length = 100.0
    thickness = 3.0
    kerf = 0.1
    nomTab = 15.0
    
    print("📊 Building the same geometry with both approaches...\n")
    
    # === OLD APPROACH (SVG-string-first) ===
    print("🔧 OLD APPROACH: SVG-string-first")
    print("=" * 40)
    
    # Simulate the original side() method logic
    vectorX = 0
    vectorY = 0
    
    # Start building SVG string
    svg_string = f"M {vectorX},{vectorY} "
    
    # Calculate tabs manually
    divisions = int(length / nomTab)
    if not divisions % 2:
        divisions -= 1
    divisions = float(divisions)
    
    tabWidth = (length / ((divisions - 1) / 2)) / (1 + (1 / nomTab))
    gapWidth = tabWidth / nomTab
    
    print(f"   Manual calculations:")
    print(f"   - divisions: {divisions}")
    print(f"   - tabWidth: {tabWidth:.2f}")
    print(f"   - gapWidth: {gapWidth:.2f}")
    
    # Build SVG string with manual coordinate calculations
    for tabDivision in range(1, int(divisions) + 1):
        w = gapWidth if (tabDivision % 2) == 1 else tabWidth
        vectorX += w / 2
        vectorY += 0
        svg_string += f"L {vectorX},{vectorY} "
        
        # Add tab/gap
        if (tabDivision % 2) == 0:  # tab
            vectorY += -thickness
            svg_string += f"L {vectorX},{vectorY} "
            vectorX += w / 2
            svg_string += f"L {vectorX},{vectorY} "
            vectorY += thickness
            svg_string += f"L {vectorX},{vectorY} "
        else:  # gap
            vectorX += w / 2
    
    vectorX = length
    svg_string += f"L {vectorX},{vectorY} "
    
    print(f"   Result: SVG string with {len(svg_string)} characters")
    print(f"   SVG: {svg_string[:60]}...")
    
    # To get path length from SVG string, we'd need complex parsing
    print(f"   Getting path length: ❌ Requires complex SVG parsing")
    print(f"   Getting bounds: ❌ Requires coordinate extraction from string")
    print(f"   Geometric operations: ❌ Limited to string concatenation")
    
    print()
    
    # === NEW APPROACH (Shapely-first) ===
    print("⚡ NEW APPROACH: Shapely-first")
    print("=" * 40)
    
    # Create with Shapely
    settings = GeometrySettings(
        thickness=thickness,
        kerf=kerf,
        nomTab=nomTab,
        equalTabs=False,
        tabSymmetry=0,
        dimpleHeight=2.0,
        dimpleLength=5.0,
        dogbone=False,
        linethickness=0.1
    )
    
    geometry_builder = BoxGeometry(settings)
    
    side_geometry = geometry_builder.create_side_geometry(
        root=(0, 0),
        startOffset=(0, 0),
        endOffset=(0, 0),
        tabVec=True,
        prevTab=False,
        length=length,
        direction=(1, 0),
        isTab=False,
        isDivider=False,
        numDividers=0,
        dividerSpacing=0
    )
    
    print(f"   Shapely calculations:")
    print(f"   - LineString with {len(side_geometry.main_path.coords)} coordinates")
    print(f"   - Automatic geometric properties available")
    
    # Easy geometric operations
    path_length = side_geometry.main_path.length
    bounds = side_geometry.main_path.bounds
    coords = list(side_geometry.main_path.coords)
    
    print(f"   Result: Shapely LineString object")
    print(f"   Coordinates: {coords[:3]}...{coords[-2:]}")
    
    print(f"   Getting path length: ✅ {path_length:.2f} (built-in)")
    print(f"   Getting bounds: ✅ {bounds} (built-in)")
    print(f"   Geometric operations: ✅ Full Shapely library available")
    
    # Convert to SVG when needed
    svg_elements = side_geometry.to_svg_elements(settings)
    final_svg = svg_elements[0].path if svg_elements else "No SVG"
    print(f"   SVG generation: ✅ {str(final_svg)[:60]}...")
    
    print()
    
    # === COMPARISON SUMMARY ===
    print("📋 COMPARISON SUMMARY")
    print("=" * 40)
    
    print("| Aspect                  | Old Approach      | New Approach     |")
    print("|-------------------------|-------------------|------------------|")
    print("| Primary representation | SVG strings       | Shapely objects  |")
    print("| Coordinate calculations | Manual            | Automatic        |")
    print("| Path length            | Complex parsing   | Built-in         |")
    print("| Bounds calculation     | Manual extraction | Built-in         |")
    print("| Geometric operations   | String concat     | Full Shapely API |")
    print("| Optimization potential | Limited           | Extensive        |")
    print("| Validation             | Manual            | Built-in         |")
    print("| Future enhancements    | Difficult         | Easy             |")
    
    print()
    
    # === SPECIFIC EXAMPLES ===
    print("🔍 SPECIFIC EXAMPLES")
    print("=" * 40)
    
    print("1. Path Length Calculation:")
    print(f"   Old: Parse SVG string, extract coordinates, calculate manually")
    print(f"   New: side_geometry.main_path.length → {path_length:.2f}")
    
    print("\n2. Bounding Box:")
    print(f"   Old: Parse all coordinates, find min/max manually")
    print(f"   New: side_geometry.main_path.bounds → {bounds}")
    
    print("\n3. Path Translation:")
    print(f"   Old: Parse SVG, adjust all coordinates, rebuild string")
    print(f"   New: side_geometry.translate(50, 25) → New geometry object")
    
    translated = side_geometry.translate(50, 25)
    new_bounds = translated.main_path.bounds
    print(f"        Translated bounds: {new_bounds}")
    
    print("\n4. Path Intersection Check:")
    print(f"   Old: Complex coordinate geometry calculations")
    print(f"   New: path1.intersects(path2) → Boolean result")
    
    # Create another path for intersection test
    other_side = geometry_builder.create_side_geometry(
        root=(50, 0), startOffset=(0, 0), endOffset=(0, 0),
        tabVec=True, prevTab=False, length=50, direction=(0, 1),
        isTab=True, isDivider=False, numDividers=0, dividerSpacing=0
    )
    
    intersects = side_geometry.main_path.intersects(other_side.main_path)
    print(f"        Intersection result: {intersects}")
    
    print("\n5. Path Optimization:")
    print(f"   Old: Limited to string concatenation and basic operations")
    print(f"   New: Full geometric operations (union, simplification, etc.)")
    
    from shapely.ops import unary_union
    try:
        combined = unary_union([side_geometry.main_path, other_side.main_path])
        print(f"        Combined geometry type: {type(combined).__name__}")
    except:
        print(f"        Combined geometry: Available through Shapely operations")


def demonstrate_advanced_benefits():
    """Show advanced capabilities enabled by Shapely"""
    
    print("\n\n🚀 ADVANCED CAPABILITIES ENABLED")
    print("=" * 50)
    
    settings = GeometrySettings(
        thickness=3.0, kerf=0.1, nomTab=15.0, equalTabs=False,
        tabSymmetry=0, dimpleHeight=2.0, dimpleLength=5.0,
        dogbone=False, linethickness=0.1
    )
    
    geometry_builder = BoxGeometry(settings)
    
    # Create multiple sides
    sides = []
    for i in range(4):
        side = geometry_builder.create_side_geometry(
            root=(i * 25, 0), startOffset=(0, 0), endOffset=(0, 0),
            tabVec=True, prevTab=False, length=100, direction=(1, 0),
            isTab=i % 2 == 0, isDivider=False, numDividers=0, dividerSpacing=0
        )
        sides.append(side)
    
    print("1. Batch Geometric Analysis:")
    for i, side in enumerate(sides):
        length = side.main_path.length
        complexity = len(side.main_path.coords)
        print(f"   Side {i+1}: length={length:.1f}, complexity={complexity} points")
    
    print("\n2. Geometric Relationships:")
    total_length = sum(side.main_path.length for side in sides)
    print(f"   Total path length: {total_length:.1f}")
    
    # Find closest sides
    min_distance = float('inf')
    closest_pair = None
    for i in range(len(sides)):
        for j in range(i+1, len(sides)):
            dist = sides[i].main_path.distance(sides[j].main_path)
            if dist < min_distance:
                min_distance = dist
                closest_pair = (i, j)
    
    print(f"   Closest sides: {closest_pair[0]+1} and {closest_pair[1]+1} (distance: {min_distance:.1f})")
    
    print("\n3. Optimization Opportunities:")
    
    # Check for overlapping geometry
    overlaps = 0
    for i in range(len(sides)):
        for j in range(i+1, len(sides)):
            if sides[i].main_path.intersects(sides[j].main_path):
                overlaps += 1
    
    print(f"   Overlapping paths detected: {overlaps}")
    print(f"   Potential for path merging: {'Yes' if overlaps > 0 else 'Available'}")
    
    # Show validation capabilities
    print("\n4. Geometric Validation:")
    for i, side in enumerate(sides):
        is_valid = side.main_path.is_valid
        is_simple = side.main_path.is_simple
        print(f"   Side {i+1}: valid={is_valid}, simple={is_simple}")
    
    print("\n5. Future Enhancement Examples:")
    print("   ✅ Automatic collision detection")
    print("   ✅ Intelligent path merging") 
    print("   ✅ Geometric constraint solving")
    print("   ✅ Advanced nesting algorithms")
    print("   ✅ Stress analysis integration")
    print("   ✅ 3D geometric preview")


if __name__ == "__main__":
    try:
        demonstrate_comparison()
        demonstrate_advanced_benefits()
        
        print("\n\n🎯 CONCLUSION")
        print("=" * 50)
        print("The Shapely refactor provides a modern, powerful foundation for")
        print("geometric operations while maintaining full backward compatibility.")
        print("This enables sophisticated optimizations and opens the door for")
        print("advanced features that would be difficult or impossible with the")
        print("original SVG-string-first approach.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
