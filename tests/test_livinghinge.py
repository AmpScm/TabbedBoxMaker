import io
import os
import pytest
import re
import sys
from inkex.paths import Path

import xml.dom.minidom
from tabbedboxmaker.InkexShapely import path_to_polygon, polygon_to_path
from collections.abc import Iterable

from tabbedboxmaker import LivingHinge


from shapely.affinity import translate
from shapely.geometry import Polygon

def mask_unstable(svgin: str) -> str:
    """Mask out unstable parts of SVG output that may vary between runs."""

    def round_points(m):
        x = round(float(m.group(2)), 3)
        y = round(float(m.group(4)), 3)
        return f'{m.group(1)} {x} {y}'

    return re.sub(
        r'<!--.*?-->', '<!-- MASKED -->', re.sub(
        r'inkscape:version="[^"]*"', 'inkscape:version="MASKED"',  re.sub(
        r'id="[^"]*"', 'id="MASKED"',  re.sub(
        r'<metadata[^>]*?/>', '<metadata />', re.sub(
        r'([ML]) (-?\d+(\.\d+)?) (-?\d+(\.\d+)?)', round_points,
        svgin, flags=re.DOTALL),
        flags=re.DOTALL), flags=re.DOTALL), flags=re.DOTALL), flags=re.DOTALL
        ).replace('\r\n', '\n')

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


cases = [
    {
        "label": "hinge-basic",
        "args": [
            "--unit=mm",
            "--inside=True",
            "--length=100.00",
            "--width=100.00",
            "--depth=100.00",
            "--thickness=3.00",
            "--equal=0",
            "--tab=5.00",
            "--hingeOpt=0",
            "--hingeThick=2.00",
            "--thumbTab=15.00",
            "--hairline=True",
            "--line-thickness=0.100",
            "--line-color=black",
            "--kerf=0.100",
            "--clearance=0.010",
            "--style=0",
            "--spacing=1.00",
        ],
    },
    {
        "label": "hinge-single-spiral",
        "args": [
            "--unit=mm",
            "--inside=True",
            "--length=100.00",
            "--width=100.00",
            "--depth=100.00",
            "--thickness=3.00",
            "--equal=0",
            "--tab=5.00",
            "--hingeOpt=1",
            "--hingeThick=2.00",
            "--thumbTab=15.00",
            "--hairline=True",
            "--line-thickness=0.100",
            "--line-color=black",
            "--kerf=0.100",
            "--clearance=0.010",
            "--style=0",
            "--spacing=1.00",
        ],
    },
    {
        "label": "hinge-double-spiral",
        "args": [
            "--unit=mm",
            "--inside=True",
            "--length=100.00",
            "--width=100.00",
            "--depth=100.00",
            "--thickness=3.00",
            "--equal=0",
            "--tab=5.00",
            "--hingeOpt=2",
            "--hingeThick=2.00",
            "--thumbTab=15.00",
            "--hairline=True",
            "--line-thickness=0.100",
            "--line-color=black",
            "--kerf=0.100",
            "--clearance=0.010",
            "--style=0",
            "--spacing=1.00",
        ],
    },
    {
        "label": "hinge-parallel-snake",
        "args": [
            "--unit=mm",
            "--inside=True",
            "--length=100.00",
            "--width=100.00",
            "--depth=100.00",
            "--thickness=3.00",
            "--equal=0",
            "--tab=5.00",
            "--hingeOpt=3",
            "--hingeThick=2.00",
            "--thumbTab=15.00",
            "--hairline=True",
            "--line-thickness=0.100",
            "--line-color=black",
            "--kerf=0.100",
            "--clearance=0.010",
            "--style=0",
            "--spacing=1.00",
        ],
    },
    {
        "label": "hinge-perpendicular-snake",
        "args": [
            "--unit=mm",
            "--inside=True",
            "--length=100.00",
            "--width=100.00",
            "--depth=100.00",
            "--thickness=3.00",
            "--equal=0",
            "--tab=5.00",
            "--hingeOpt=4",
            "--hingeThick=2.00",
            "--thumbTab=15.00",
            "--hairline=True",
            "--line-thickness=0.100",
            "--line-color=black",
            "--kerf=0.100",
            "--clearance=0.010",
            "--style=0",
            "--spacing=1.00",
        ],
    },
    {
        "label": "hinge-double-perpendicular-snake",
        "args": [
            "--unit=mm",
            "--inside=True",
            "--length=100.00",
            "--width=100.00",
            "--depth=100.00",
            "--thickness=3.00",
            "--equal=0",
            "--tab=5.00",
            "--hingeOpt=5",
            "--hingeThick=2.00",
            "--thumbTab=15.00",
            "--hairline=True",
            "--line-thickness=0.100",
            "--line-color=black",
            "--kerf=0.100",
            "--clearance=0.010",
            "--style=0",
            "--spacing=1.00",
        ],
    },

]

expected_output_dir = os.path.join(os.path.dirname(__file__), "..","expected", "livinghinge")
actual_output_dir = os.path.join(os.path.dirname(__file__), "..", "actual", "livinghinge")


def make_box(args, make_relative=False, optimize=False, mask=True, no_subtract=False) -> str:
    """Run one test case and return (output, expected) strings."""

    outfh = io.BytesIO()

    ef = LivingHinge(cli=True)
    ef.parse_arguments(args)
    ef.options.output = outfh
    ef.options.combine = ef.options.cutout = optimize
    ef.raw_hairline_thickness = -1
    ef.hairline_thickness = 0.1
    ef.no_subtract = no_subtract

    ef.load_raw()
    ef.save_raw(ef.effect())

    output = outfh.getvalue().decode("utf-8")
    output = pretty_xml(output)

    if make_relative:
        def make_path_relative(m):
            v = m.group(0)
            v = Path(v)
            return str(v.to_relative())

        output = re.sub(r'(?<=\bd=")M [^"]*(?=")', make_path_relative, output, flags=re.DOTALL)


    if mask:
        output = mask_unstable(output)

    return output

def make_box_paths(args, optimize=False, no_subtract=False) -> dict[str, Path]:
    """Run one test case and return a map of id -> Path."""

    output = make_box(args, optimize=optimize, mask=False, no_subtract=no_subtract)

    map = {}
    for i in re.findall(r'path id="([^"]+)".*?d="(M [^"]*(?="))', output):
        map[i[0]] = Path(i[1])

    return map

def make_box_polygons(args, optimize=False, no_subtract=False) -> dict[str, Polygon]:
    """Run one test case and return a map of id -> Shapely Polygon."""

    paths = make_box_paths(args, optimize=optimize, no_subtract=no_subtract)

    map = {}
    for k, v in paths.items():
        map[k] = path_to_polygon(v)

    return map

def run_one(name, args, make_relative=False, optimize=False, mask=True) -> tuple[str, str]:
    """Run one test case and return (output, expected) strings."""

    outfh = io.BytesIO()

    expected_file = os.path.join(expected_output_dir, name + ".svg")
    expected_dir = os.path.dirname(expected_file)
    os.makedirs(expected_dir, exist_ok=True)

    expected = ""
    actual_file = os.path.join(actual_output_dir, name + ".svg")
    actual_dir = os.path.dirname(actual_file)
    os.makedirs(actual_dir, exist_ok=True)
    if os.path.exists(expected_file):
        with open(expected_file, "r") as f:
            expected = f.read()
    elif expected_file.endswith('.r.svg') and os.path.exists(expected_file[:-6] + '.n.svg'):
        with open(expected_file[:-6] + '.n.svg', "r") as f:
            expected = f.read()

    output = make_box(args, make_relative=make_relative, optimize=optimize, mask=False)

    if make_relative:
        def make_path_relative(m):
            v = m.group(0)
            v = Path(v)
            return str(v.to_relative())

        output = re.sub(r'(?<=\bd=")M [^"]*(?=")', make_path_relative, output, flags=re.DOTALL)
        expected = re.sub(r'(?<=\bd=")M [^"]*(?=")', make_path_relative, output, flags=re.DOTALL)

        if not os.path.exists(expected_file):
            with open(expected_file, "w", encoding="utf-8") as f:
                f.write(expected)

    with open(actual_file, "w", encoding="utf-8") as f:
        f.write(output)

    if mask:
        output, expected = mask_unstable(output), mask_unstable(expected)
    return (output, expected)

@pytest.mark.parametrize("case", cases, ids=[c["label"] for c in cases])
def test_boxmaker(case):
    name = case["label"]
    args = case["args"]

    output, expected = run_one(os.path.join(name + '.n'), args)

    # Compare outputs
    assert (
        output == expected
    ), f"Test case {name} failed - output doesn't match expected"

@pytest.mark.parametrize("case", cases, ids=[c["label"] for c in cases])
def test_boxmaker_relative(case):
    name = case["label"]
    args = case["args"]

    output, expected = run_one(os.path.join(name + '.r'), args, make_relative=True)

    # Compare outputs
    assert (
        output == expected
    ), f"Test case {name} failed - output doesn't match expected"

@pytest.mark.parametrize("case", cases, ids=[c["label"] for c in cases])
def test_boxmaker_optimized(case):
    name = case["label"]
    args = case["args"]

    output, expected = run_one(os.path.join(name + '.o'), args, optimize=True)
    assert (
        output == expected
    ), f"Test case {name} failed - optimized output doesn't match expected"

