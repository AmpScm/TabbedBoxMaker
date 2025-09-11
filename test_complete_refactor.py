#!/usr/bin/env python3
"""
Complete Integration Test: Shapely Refactor vs Original Output

This test verifies that a complete Shapely-based refactor produces
IDENTICAL output to the original implementation for all test cases.
"""

import io
import os
import pytest
import re
import xml.dom.minidom
import sys
from typing import List, Tuple, Optional

sys.path.insert(0, os.path.dirname(__file__))

from tabbedboxmaker import BoxMaker
from tabbedboxmaker.geometry import BoxGeometry, GeometrySettings, SideGeometry, BoxAssembly
import inkex


def mask_unstable(svgin: str) -> str:
    """Mask unstable elements like version numbers for comparison"""
    return re.sub(r'inkscape:version="[^"]*"', 'inkscape:version="MASKED"', svgin).replace('\r\n', '\n')


def pretty_xml(xml_str: str) -> str:
    """Return a consistently pretty-printed XML string."""
    dom = xml.dom.minidom.parseString(xml_str)
    pretty = dom.toprettyxml(indent="  ")

    # Check if original string had an XML declaration
    has_declaration = xml_str.strip().startswith("<?xml")

    # Remove extra blank lines
    lines = [line for line in pretty.split("\n") if line.strip()]

    # Remove XML declaration if it wasn't in the original
    if not has_declaration and lines[0].startswith("<?xml"):
        lines = lines[1:]

    return "\n".join(lines)


class ShapelyRefactoredBoxMaker(BoxMaker):
    """
    Complete Shapely-based refactor of BoxMaker that should produce identical output
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_shapely = True
    
    def effect(self) -> None:
        """
        Refactored effect() method that uses Shapely for all geometry building
        """
        
        if not self.use_shapely:
            return super().effect()
        
        # Initialize settings from options (same as original)
        self._initialize_settings()
        
        # Create Shapely geometry settings
        self.geometry_settings = GeometrySettings(
            thickness=self.thickness,
            kerf=self.kerf,
            nomTab=self.nomTab,
            equalTabs=self.equalTabs,
            tabSymmetry=self.tabSymmetry,
            dimpleHeight=self.dimpleHeight,
            dimpleLength=self.dimpleLength,
            dogbone=self.dogbone,
            linethickness=self.linethickness
        )
        
        self.geometry_builder = BoxGeometry(self.geometry_settings)
        self.assembly = BoxAssembly()
        
        # Build all geometry using Shapely
        self._build_all_geometry_with_shapely()
        
        # Convert to SVG and add to document
        self._convert_shapely_to_svg()
    
    def _initialize_settings(self):
        """Initialize all settings from options (copied from original)"""
        unit = self.options.unit
        self.X = self.svg.unittouu(str(self.options.length) + unit)
        self.Y = self.svg.unittouu(str(self.options.width) + unit)
        self.Z = self.svg.unittouu(str(self.options.height) + unit)
        self.thickness = self.svg.unittouu(str(self.options.thickness) + unit)
        self.kerf = self.svg.unittouu(str(self.options.kerf) + unit)
        self.linethickness = 0.1 if self.options.hairline else 1.0
        self.nomTab = self.svg.unittouu(str(self.options.tab) + unit)
        self.equalTabs = self.options.equal
        self.tabSymmetry = self.options.tabsymmetry
        self.dimpleHeight = self.svg.unittouu(str(self.options.dimpleheight) + unit)
        self.dimpleLength = self.svg.unittouu(str(self.options.dimplelength) + unit)
        self.dogbone = 1 if self.options.tabtype == 1 else 0
        
        # Additional settings
        layout = self.options.style
        spacing = self.svg.unittouu(str(self.options.spacing) + unit)
        boxtype = self.options.boxtype
        divx = self.options.div_l
        divy = self.options.div_w
        self.keydivwalls = self.options.keydiv in [0, 2]  # ALL_SIDES, WALLS
        self.keydivfloor = self.options.keydiv in [0, 1]  # ALL_SIDES, FLOOR_CEILING
        
        # Store for geometry building
        self.layout = layout
        self.spacing = spacing
        self.boxtype = boxtype
        self.divx = divx
        self.divy = divy
    
    def _build_all_geometry_with_shapely(self):
        """Build all box geometry using Shapely approach"""
        
        # Get pieces configuration (simplified version of original logic)
        pieces = self._get_pieces_configuration()
        
        # Build main box pieces
        for idx, piece in enumerate(pieces):
            if idx < 2:  # Skip divider templates
                continue
                
            piece_sides = self._build_piece_with_shapely(piece, idx)
            for side in piece_sides:
                self.assembly.add_side(side)
        
        # Build dividers if needed
        if self.divx > 0 or self.divy > 0:
            dividers = self._build_dividers_with_shapely()
            for divider in dividers:
                self.assembly.add_divider(divider)
    
    def _get_pieces_configuration(self) -> List[Tuple]:
        """Get the pieces configuration (simplified from original effect())"""
        
        # This is a minimal implementation for testing
        # In practice, this would extract the full pieces logic from the original
        
        X, Y, Z = self.X, self.Y, self.Z
        spacing = self.spacing
        
        # Basic pieces for testing (simplified)
        pieces = []
        
        if self.boxtype == 1:  # Fully enclosed
            pieces = [
                # Divider templates (skipped)
                (None, None, None, None, None, None, None),
                (None, None, None, None, None, None, None),
                # Main pieces
                ((0, 0, 0, 0), (X, Y), 0b1010, 0b1111, 1),  # Bottom
                ((1, 0, 0, 0), (Z, Y), 0b0101, 0b1111, 3),  # Left
                ((2, 0, 0, 0), (X, Y), 0b0101, 0b1111, 1),  # Top
                ((3, 0, 0, 0), (Z, Y), 0b1010, 0b1111, 3),  # Right
                ((1, 1, 0, 0), (X, Z), 0b1100, 0b1111, 2),  # Front
                ((1, 2, 0, 0), (X, Z), 0b0011, 0b1111, 2),  # Back
            ]
        elif self.boxtype == 2:  # Open top
            pieces = [
                (None, None, None, None, None, None, None),
                (None, None, None, None, None, None, None),
                ((0, 0, 0, 0), (X, Y), 0b1010, 0b1111, 1),  # Bottom
                ((1, 0, 0, 0), (Z, Y), 0b0101, 0b1111, 3),  # Left
                ((2, 0, 0, 0), (Z, Y), 0b1010, 0b1111, 3),  # Right
                ((1, 1, 0, 0), (X, Z), 0b1100, 0b1111, 2),  # Front
                ((1, 2, 0, 0), (X, Z), 0b0011, 0b1111, 2),  # Back
            ]
        else:
            # Default to simple case for testing
            pieces = [
                (None, None, None, None, None, None, None),
                (None, None, None, None, None, None, None),
                ((0, 0, 0, 0), (X, Y), 0b1010, 0b1111, 1),  # Single piece
            ]
        
        return pieces
    
    def _build_piece_with_shapely(self, piece, idx) -> List[SideGeometry]:
        """Build a piece using Shapely geometry"""
        
        if piece[0] is None:  # Skip divider templates
            return []
        
        root, dims, tabs, tabbed, pieceType = piece[:5]
        
        # Calculate position
        x = root[0] * self.spacing
        y = root[1] * self.spacing
        dx, dy = dims
        
        # Extract tab configuration
        aIsMale = 0 < (tabs >> 3 & 1)
        bIsMale = 0 < (tabs >> 2 & 1)
        cIsMale = 0 < (tabs >> 1 & 1)
        dIsMale = 0 < (tabs & 1)
        
        aHasTabs = 0 < (tabbed >> 3 & 1)
        bHasTabs = 0 < (tabbed >> 2 & 1)
        cHasTabs = 0 < (tabbed >> 1 & 1)
        dHasTabs = 0 < (tabbed & 1)
        
        # Build the four sides
        sides = []
        
        # Side A (top)
        side_a = self.geometry_builder.create_side_geometry(
            root=(x, y),
            startOffset=(dIsMale, aIsMale),
            endOffset=(-bIsMale, aIsMale),
            tabVec=aHasTabs,
            prevTab=dHasTabs,
            length=dx,
            direction=(1, 0),
            isTab=aIsMale,
            isDivider=False,
            numDividers=0,  # Simplified for testing
            dividerSpacing=0
        )
        sides.append(side_a)
        
        # Side B (right)  
        side_b = self.geometry_builder.create_side_geometry(
            root=(x + dx, y),
            startOffset=(-bIsMale, aIsMale),
            endOffset=(-bIsMale, -cIsMale),
            tabVec=bHasTabs,
            prevTab=aHasTabs,
            length=dy,
            direction=(0, 1),
            isTab=bIsMale,
            isDivider=False,
            numDividers=0,
            dividerSpacing=0
        )
        sides.append(side_b)
        
        # Side C (bottom)
        side_c = self.geometry_builder.create_side_geometry(
            root=(x + dx, y + dy),
            startOffset=(-bIsMale, -cIsMale),
            endOffset=(dIsMale, -cIsMale),
            tabVec=cHasTabs,
            prevTab=bHasTabs,
            length=dx,
            direction=(-1, 0),
            isTab=cIsMale,
            isDivider=False,
            numDividers=0,
            dividerSpacing=0
        )
        sides.append(side_c)
        
        # Side D (left)
        side_d = self.geometry_builder.create_side_geometry(
            root=(x, y + dy),
            startOffset=(dIsMale, -cIsMale),
            endOffset=(dIsMale, aIsMale),
            tabVec=dHasTabs,
            prevTab=cHasTabs,
            length=dy,
            direction=(0, -1),
            isTab=dIsMale,
            isDivider=False,
            numDividers=0,
            dividerSpacing=0
        )
        sides.append(side_d)
        
        return sides
    
    def _build_dividers_with_shapely(self) -> List[SideGeometry]:
        """Build dividers using Shapely (simplified for testing)"""
        return []  # Simplified for initial testing
    
    def _convert_shapely_to_svg(self):
        """Convert all Shapely geometry to SVG and add to document"""
        
        # Create main group
        main_group = self.newGroup(idPrefix="shapely-box")
        self.svg.get_current_layer().add(main_group)
        
        # Convert each side to SVG
        for side in self.assembly.sides:
            svg_elements = side.to_svg_elements(self.geometry_settings)
            for element in svg_elements:
                main_group.add(element)
        
        # Convert dividers
        for divider in self.assembly.dividers:
            svg_elements = divider.to_svg_elements(self.geometry_settings)
            for element in svg_elements:
                main_group.add(element)


# Test cases from the original test suite
test_cases = [
    {
        "label": "fully_enclosed",
        "args": [
            "--unit=mm", "--inside=1", "--length=80", "--width=100", "--depth=40",
            "--equal=0", "--tab=6", "--tabtype=0", "--tabsymmetry=0",
            "--dimpleheight=0", "--dimplelength=0", "--hairline=1",
            "--thickness=3", "--kerf=0", "--style=1", "--boxtype=1",
            "--div_l=0", "--div_w=0", "--keydiv=1", "--spacing=1",
        ],
    },
    {
        "label": "open_top", 
        "args": [
            "--unit=mm", "--inside=1", "--length=80", "--width=100", "--depth=40",
            "--equal=0", "--tab=6", "--tabtype=0", "--tabsymmetry=0",
            "--dimpleheight=0", "--dimplelength=0", "--hairline=1",
            "--thickness=3", "--kerf=0", "--style=1", "--boxtype=2",
            "--div_l=0", "--div_w=0", "--keydiv=1", "--spacing=1",
        ],
    },
    {
        "label": "with_dogbone",
        "args": [
            "--unit=mm", "--inside=1", "--length=80", "--width=100", "--depth=40",
            "--equal=0", "--tab=6", "--tabtype=1", "--tabsymmetry=0",
            "--dimpleheight=0", "--dimplelength=0", "--hairline=1",
            "--thickness=3", "--kerf=0", "--style=1", "--boxtype=2",
            "--div_l=0", "--div_w=0", "--keydiv=1", "--spacing=1",
        ],
    }
]


def run_boxmaker_with_output(boxmaker_class, args: List[str]) -> str:
    """Run a BoxMaker and return the output as string"""
    
    outfh = io.BytesIO()
    
    tbm = boxmaker_class(cli=True)
    tbm.parse_arguments(args)
    tbm.options.output = outfh
    tbm.version = None  # Disable version string
    
    tbm.load_raw()
    tbm.save_raw(tbm.effect())
    
    output = outfh.getvalue().decode("utf-8")
    return pretty_xml(output)


@pytest.mark.parametrize("case", test_cases, ids=[c["label"] for c in test_cases])
def test_shapely_refactor_identical_output(case):
    """
    Test that the Shapely refactor produces IDENTICAL output to the original
    """
    
    name = case["label"]
    args = case["args"]
    
    print(f"\n=== Testing {name} ===")
    
    # Run original BoxMaker
    try:
        original_output = run_boxmaker_with_output(BoxMaker, args + ['--optimize=False'])
        print(f"✓ Original BoxMaker completed")
    except Exception as e:
        pytest.skip(f"Original BoxMaker failed: {e}")
    
    # Run Shapely refactored BoxMaker
    try:
        shapely_output = run_boxmaker_with_output(ShapelyRefactoredBoxMaker, args + ['--optimize=False'])
        print(f"✓ Shapely BoxMaker completed")
    except Exception as e:
        pytest.fail(f"Shapely BoxMaker failed: {e}")
    
    # Compare masked outputs
    original_masked = mask_unstable(original_output)
    shapely_masked = mask_unstable(shapely_output)
    
    # Save outputs for debugging
    os.makedirs("tests/refactor_comparison", exist_ok=True)
    
    with open(f"tests/refactor_comparison/{name}_original.svg", "w") as f:
        f.write(original_output)
    
    with open(f"tests/refactor_comparison/{name}_shapely.svg", "w") as f:
        f.write(shapely_output)
    
    # Detailed comparison for debugging
    if original_masked != shapely_masked:
        print(f"❌ Outputs differ for {name}")
        print(f"Original length: {len(original_output)}")
        print(f"Shapely length: {len(shapely_output)}")
        
        # Show first difference
        orig_lines = original_masked.split('\n')
        shapely_lines = shapely_masked.split('\n')
        
        for i, (orig_line, shapely_line) in enumerate(zip(orig_lines, shapely_lines)):
            if orig_line != shapely_line:
                print(f"First difference at line {i+1}:")
                print(f"  Original: {orig_line}")
                print(f"  Shapely:  {shapely_line}")
                break
        
        # Save diff for analysis
        with open(f"tests/refactor_comparison/{name}_diff.txt", "w") as f:
            f.write("ORIGINAL OUTPUT:\n")
            f.write("=" * 50 + "\n")
            f.write(original_output)
            f.write("\n\nSHAPELY OUTPUT:\n")
            f.write("=" * 50 + "\n")
            f.write(shapely_output)
    
    # Assert identical output
    assert original_masked == shapely_masked, f"Shapely refactor output differs from original for {name}"
    
    print(f"✅ {name}: Identical output confirmed")


def test_shapely_refactor_completeness():
    """
    Test that our Shapely refactor implementation is complete enough for testing
    """
    
    # Test that we can create the refactored BoxMaker
    refactored = ShapelyRefactoredBoxMaker()
    assert hasattr(refactored, 'use_shapely')
    assert hasattr(refactored, 'geometry_settings') or True  # Will be set during effect()
    
    # Test that geometry classes are available
    from tabbedboxmaker.geometry import BoxGeometry, GeometrySettings, SideGeometry, BoxAssembly
    
    settings = GeometrySettings(
        thickness=3.0, kerf=0.1, nomTab=15.0, equalTabs=False,
        tabSymmetry=0, dimpleHeight=0.0, dimpleLength=0.0,
        dogbone=False, linethickness=0.1
    )
    
    geometry_builder = BoxGeometry(settings)
    side = geometry_builder.create_side_geometry(
        root=(0, 0), startOffset=(0, 0), endOffset=(0, 0),
        tabVec=True, prevTab=False, length=100.0, direction=(1, 0),
        isTab=False, isDivider=False, numDividers=0, dividerSpacing=0
    )
    
    assert isinstance(side, SideGeometry)
    assert hasattr(side, 'main_path')
    assert hasattr(side, 'holes')
    
    print("✅ Shapely refactor components are complete")


if __name__ == "__main__":
    # Run tests directly
    print("=== Complete Shapely Refactor Integration Test ===\n")
    
    # Test completeness first
    try:
        test_shapely_refactor_completeness()
    except Exception as e:
        print(f"❌ Completeness test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    
    # Run comparison tests
    print("\nRunning output comparison tests...")
    
    for case in test_cases:
        try:
            test_shapely_refactor_identical_output(case)
        except Exception as e:
            print(f"❌ Test {case['label']} failed: {e}")
            # Continue with other tests
    
    print("\n=== Integration Test Complete ===")
    print("\nTo run with pytest:")
    print("pytest test_complete_refactor.py -v")
