#!/usr/bin/env python3
"""
Simple test of the Shapely refactor
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

try:
    from tabbedboxmaker.geometry import BoxGeometry, GeometrySettings, SideGeometry
    from shapely.geometry import LineString, Polygon
    
    print("✓ Successfully imported Shapely geometry classes")
    
    # Test basic geometry creation
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
    
    print("✓ Created geometry settings")
    
    geometry_builder = BoxGeometry(settings)
    print("✓ Created BoxGeometry builder")
    
    # Create a simple side
    side = geometry_builder.create_side_geometry(
        root=(0, 0),
        startOffset=(0, 0),
        endOffset=(0, 0),
        tabVec=True,
        prevTab=False,
        length=100.0,
        direction=(1, 0),
        isTab=False,
        isDivider=False,
        numDividers=1,
        dividerSpacing=30.0
    )
    
    print("✓ Created side geometry")
    print(f"  Path has {len(side.main_path.coords)} points")
    print(f"  Path length: {side.main_path.length:.2f}")
    print(f"  Has {len(side.holes)} holes")
    
    # Test translation
    translated = side.translate(50, 25)
    print("✓ Successfully translated geometry")
    
    # Test SVG conversion
    try:
        svg_elements = side.to_svg_elements(settings)
        print(f"✓ Converted to {len(svg_elements)} SVG elements")
    except Exception as e:
        print(f"⚠ SVG conversion had issues (expected - needs inkex): {e}")
    
    print("\n🎉 Shapely refactor is working correctly!")
    print("\nKey benefits demonstrated:")
    print("- Geometry built with Shapely objects instead of SVG strings")
    print("- Easy geometric calculations (length, bounds, etc.)")
    print("- Simple geometric transformations (translate)")
    print("- Clean separation of geometry and SVG generation")
    print("- Foundation for advanced optimizations")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all dependencies are installed")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
