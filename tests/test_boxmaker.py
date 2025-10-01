import io
import os
import pytest
import re
from inkex.paths import Path

import xml.dom.minidom
from tabbedboxmaker.InkexShapely import path_to_polygon
from collections.abc import Iterable

from tabbedboxmaker import TabbedBoxMaker


from shapely.affinity import translate
from shapely.geometry import Polygon


def mask_unstable(svgin: str) -> str:
    """Mask out unstable parts of SVG output that may vary between runs."""

    def round_points(m):
        x = round(float(m.group(2)), 3)
        y = round(float(m.group(4)), 3)
        return f'{m.group(1)} {x} {y}'

    regexes = [
        (r'<!--.*?-->', '<!-- MASKED -->'),
        (r' inkscape:version="[^"]*"', ''),
        (r' inkscape:groupmode="layer"', ''),
        (r' inkscape:label="[^"]*"', ''),
        (r' id="[^"]*"', ''),
        (r'<metadata[^>]*?/>', '<metadata />'),
        (r'<sodipodi:namedview[^>]*?/>', '<sodipodi:namedview />'),
        (r'([ML]) (-?\d+(\.\d+)?) (-?\d+(\.\d+)?)', round_points),
    ]

    for pattern, replacement in regexes:
        svgin = re.sub(pattern, replacement, svgin, flags=re.DOTALL)

    return svgin.replace('\r', '')


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
        "label": "fully_enclosed",
        "args": [
            "--unit=mm",
            "--inside=1",
            "--length=80",
            "--width=100",
            "--depth=40",
            "--equal=0",
            "--tab=6",
            "--tabtype=0",
            "--tabsymmetry=0",
            "--dimpleheight=0",
            "--dimplelength=0",
            "--hairline=1",
            "--thickness=3",
            "--kerf=0",
            "--style=1",
            "--boxtype=1",
            "--div-l=0",
            "--div-w=0",
            "--keydiv=1",
            "--spacing=1",
        ],
    },
    {
        "label": "open_top",
        "args": [
            "--unit=mm",
            "--inside=1",
            "--length=80",
            "--width=100",
            "--depth=43",
            "--equal=0",
            "--tab=6",
            "--tabtype=0",
            "--tabsymmetry=0",
            "--dimpleheight=0",
            "--dimplelength=0",
            "--hairline=1",
            "--thickness=3",
            "--kerf=0",
            "--style=1",
            "--boxtype=2",
            "--div-l=0",
            "--div-w=0",
            "--keydiv=1",
            "--spacing=1",
        ],
    },
    {
        "label": "two_sides_open",
        "args": [
            "--unit=mm",
            "--inside=1",
            "--length=80",
            "--width=103",
            "--depth=43",
            "--equal=0",
            "--tab=6",
            "--tabtype=0",
            "--tabsymmetry=0",
            "--dimpleheight=0",
            "--dimplelength=0",
            "--hairline=1",
            "--thickness=3",
            "--kerf=0",
            "--style=1",
            "--boxtype=3",
            "--div-l=0",
            "--div-w=0",
            "--keydiv=1",
            "--spacing=1",
        ],
    },
    {
        "label": "three_sides_open",
        "args": [
            "--unit=mm",
            "--inside=1",
            "--length=83",
            "--width=103",
            "--depth=43",
            "--equal=0",
            "--tab=6",
            "--tabtype=0",
            "--tabsymmetry=0",
            "--dimpleheight=0",
            "--dimplelength=0",
            "--hairline=1",
            "--thickness=3",
            "--kerf=0",
            "--style=1",
            "--boxtype=4",
            "--div-l=0",
            "--div-w=0",
            "--keydiv=1",
            "--spacing=1",
        ],
    },
    {
        "label": "opposite_ends_open",
        "args": [
            "--unit=mm",
            "--inside=1",
            "--length=80",
            "--width=100",
            "--depth=46",
            "--equal=0",
            "--tab=6",
            "--tabtype=0",
            "--tabsymmetry=0",
            "--dimpleheight=0",
            "--dimplelength=0",
            "--hairline=1",
            "--thickness=3",
            "--kerf=0",
            "--style=1",
            "--boxtype=5",
            "--div-l=0",
            "--div-w=0",
            "--keydiv=1",
            "--spacing=1",
        ],
    },
    {
        "label": "two_panels_only",
        "args": [
            "--unit=mm",
            "--inside=1",
            "--length=83",
            "--width=106",
            "--depth=43",
            "--equal=0",
            "--tab=6",
            "--tabtype=0",
            "--tabsymmetry=0",
            "--dimpleheight=0",
            "--dimplelength=0",
            "--hairline=1",
            "--thickness=3",
            "--kerf=0",
            "--style=1",
            "--boxtype=6",
            "--div-l=0",
            "--div-w=0",
            "--keydiv=1",
            "--spacing=1",
        ],
    },
    {
        "label": "outside_measurement",
        "args": [
            "--unit=mm",
            "--inside=0",
            "--length=80",
            "--width=100",
            "--depth=40",
            "--equal=0",
            "--tab=6",
            "--tabtype=0",
            "--tabsymmetry=0",
            "--dimpleheight=0",
            "--dimplelength=0",
            "--hairline=1",
            "--thickness=3",
            "--kerf=0",
            "--style=1",
            "--boxtype=2",
            "--div-l=0",
            "--div-w=0",
            "--keydiv=1",
            "--spacing=1",
        ],
    },
    {
        "label": "outside_measurement_kerf_nonzero",
        "args": [
            "--unit=mm",
            "--inside=0",
            "--length=80",
            "--width=100",
            "--depth=40",
            "--equal=0",
            "--tab=6",
            "--tabtype=0",
            "--tabsymmetry=0",
            "--dimpleheight=0",
            "--dimplelength=0",
            "--hairline=1",
            "--thickness=3",
            "--kerf=0.5",
            "--style=1",
            "--boxtype=2",
            "--div-l=0",
            "--div-w=0",
            "--keydiv=1",
            "--spacing=1",
        ],
    },
    {
        "label": "with_dogbone",
        "args": [
            "--unit=mm",
            "--inside=1",
            "--length=80",
            "--width=100",
            "--depth=43",
            "--equal=0",
            "--tab=6",
            "--tabtype=1",
            "--tabsymmetry=0",
            "--dimpleheight=0",
            "--dimplelength=0",
            "--hairline=1",
            "--thickness=3",
            "--kerf=0",
            "--style=1",
            "--boxtype=2",
            "--div-l=0",
            "--div-w=0",
            "--keydiv=1",
            "--spacing=1",
        ],
    },
    {
        "label": "with_dimple",
        "args": [
            "--unit=mm",
            "--inside=1",
            "--length=80",
            "--width=100",
            "--depth=43",
            "--equal=0",
            "--tab=6",
            "--tabtype=0",
            "--tabsymmetry=0",
            "--dimpleheight=0.2",
            "--dimplelength=0.2",
            "--hairline=1",
            "--thickness=3",
            "--kerf=0",
            "--style=1",
            "--boxtype=2",
            "--div-l=0",
            "--div-w=0",
            "--keydiv=1",
            "--spacing=1",
        ],
    },
    {
        "label": "with_rotate_symmetry_tabs",
        "args": [
            "--unit=mm",
            "--inside=1",
            "--length=80",
            "--width=100",
            "--depth=43",
            "--equal=0",
            "--tab=6",
            "--tabtype=0",
            "--tabsymmetry=1",
            "--dimpleheight=0",
            "--dimplelength=0",
            "--hairline=1",
            "--thickness=3",
            "--kerf=0",
            "--style=1",
            "--boxtype=2",
            "--div-l=0",
            "--div-w=0",
            "--keydiv=1",
            "--spacing=1",
        ],
    },
    {
        "label": "with_thick_lines",
        "args": [
            "--unit=mm",
            "--inside=1",
            "--length=80",
            "--width=100",
            "--depth=43",
            "--equal=0",
            "--tab=6",
            "--tabtype=0",
            "--tabsymmetry=0",
            "--dimpleheight=0",
            "--dimplelength=0",
            "--hairline=0",
            "--line-thickness=1",
            "--thickness=3",
            "--kerf=0",
            "--style=1",
            "--boxtype=2",
            "--div-l=0",
            "--div-w=0",
            "--keydiv=1",
            "--spacing=1",
        ],
    },
    {
        "label": "with_nonzero_kerf",
        "args": [
            "--unit=mm",
            "--inside=1",
            "--length=80",
            "--width=100",
            "--depth=43",
            "--equal=0",
            "--tab=6",
            "--tabtype=0",
            "--tabsymmetry=0",
            "--dimpleheight=0",
            "--dimplelength=0",
            "--hairline=1",
            "--thickness=3",
            "--kerf=0.1",
            "--style=1",
            "--boxtype=2",
            "--div-l=0",
            "--div-w=0",
            "--keydiv=1",
            "--spacing=1",
        ],
    },
    {
        "label": "threepiece_layout",
        "args": [
            "--unit=mm",
            "--inside=1",
            "--length=80",
            "--width=100",
            "--depth=43",
            "--equal=0",
            "--tab=6",
            "--tabtype=0",
            "--tabsymmetry=0",
            "--dimpleheight=0",
            "--dimplelength=0",
            "--hairline=1",
            "--thickness=3",
            "--kerf=0",
            "--style=2",
            "--boxtype=2",
            "--div-l=0",
            "--div-w=0",
            "--keydiv=1",
            "--spacing=1",
        ],
    },
    {
        "label": "inline_layout",
        "args": [
            "--unit=mm",
            "--inside=1",
            "--length=80",
            "--width=100",
            "--depth=43",
            "--equal=0",
            "--tab=6",
            "--tabtype=0",
            "--tabsymmetry=0",
            "--dimpleheight=0",
            "--dimplelength=0",
            "--hairline=1",
            "--thickness=3",
            "--kerf=0",
            "--style=3",
            "--boxtype=2",
            "--div-l=0",
            "--div-w=0",
            "--keydiv=1",
            "--spacing=1",
        ],
    },
    {
        "label": "with_dividers_keyed_all",
        "args": [
            "--unit=mm",
            "--inside=1",
            "--length=80",
            "--width=100",
            "--depth=43",
            "--equal=0",
            "--tab=6",
            "--tabtype=0",
            "--tabsymmetry=0",
            "--dimpleheight=0",
            "--dimplelength=0",
            "--hairline=1",
            "--thickness=3",
            "--kerf=0",
            "--style=1",
            "--boxtype=2",
            "--div-l=1",
            "--div-w=1",
            "--keydiv=0",
            "--spacing=1",
        ],
    },
    {
        "label": "with_dividers_keyed_floor",
        "args": [
            "--unit=mm",
            "--inside=1",
            "--length=80",
            "--width=100",
            "--depth=43",
            "--equal=0",
            "--tab=6",
            "--tabtype=0",
            "--tabsymmetry=0",
            "--dimpleheight=0",
            "--dimplelength=0",
            "--hairline=1",
            "--thickness=3",
            "--kerf=0",
            "--style=1",
            "--boxtype=2",
            "--div-l=1",
            "--div-w=1",
            "--keydiv=1",
            "--spacing=1",
        ],
    },
    {
        "label": "with_dividers_keyed_walls",
        "args": [
            "--unit=mm",
            "--inside=1",
            "--length=80",
            "--width=100",
            "--depth=43",
            "--equal=0",
            "--tab=6",
            "--tabtype=0",
            "--tabsymmetry=0",
            "--dimpleheight=0",
            "--dimplelength=0",
            "--hairline=1",
            "--thickness=3",
            "--kerf=0",
            "--style=1",
            "--boxtype=2",
            "--div-l=1",
            "--div-w=1",
            "--keydiv=2",
            "--spacing=1",
        ],
    },
    {
        "label": "with_dividers_keyed_none",
        "args": [
            "--unit=mm",
            "--inside=1",
            "--length=80",
            "--width=100",
            "--depth=43",
            "--equal=0",
            "--tab=6",
            "--tabtype=0",
            "--tabsymmetry=0",
            "--dimpleheight=0",
            "--dimplelength=0",
            "--hairline=1",
            "--thickness=3",
            "--kerf=0",
            "--style=1",
            "--boxtype=2",
            "--div-l=1",
            "--div-w=1",
            "--keydiv=3",
            "--spacing=1",
        ],
    },
    {
        "label": "with_many_dividers_keyed_all",
        "args": [
            "--unit=mm",
            "--inside=1",
            "--length=180",
            "--width=240",
            "--depth=50",
            "--equal=0",
            "--tab=6",
            "--tabtype=0",
            "--tabsymmetry=0",
            "--dimpleheight=0",
            "--dimplelength=0",
            "--hairline=1",
            "--thickness=3",
            "--kerf=0.1",
            "--style=1",
            "--boxtype=1",
            "--div-l=2",
            "--div-w=3",
            "--keydiv=0",
            "--spacing=1",
        ],
    },
    {
        "label": "custom_divider_spacing",
        "args": [
            "--unit=mm",
            "--inside=1",
            "--length=75",
            "--width=75",
            "--depth=20",
            "--thickness=2",
            "--style=1",
            "--boxtype=2",
            "--tab=3",
            "--div-l=3",
            "--div-w=4",
            "--div-l-spacing=10;5;10",
            "--div-w-spacing=10;5",
            "--spacing=1",
            "--keydiv=0",
            "--hairline=1",
            "--kerf=0.1",
        ]
    },
]

expected_output_dir = os.path.join(os.path.dirname(__file__), "..", "expected")
actual_output_dir = os.path.join(os.path.dirname(__file__), "..", "actual")


def make_box(args, make_relative=False, optimize=False, mask=True, no_subtract=False) -> str:
    """Run one test case and return (output, expected) strings."""

    outfh = io.BytesIO()

    boxmaker = TabbedBoxMaker(cli=True)
    boxmaker.parse_arguments(args)

    boxmaker.options.output = outfh
    boxmaker.options.combine = optimize
    boxmaker.options.cutout = not no_subtract and optimize
    boxmaker.version = None
    boxmaker.raw_hairline_thickness = -1
    boxmaker.hairline_thickness = 0.0508

    boxmaker.load_raw()
    boxmaker.save_raw(boxmaker.effect())

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

    output = make_box(args, make_relative=make_relative, optimize=optimize, mask=False, no_subtract=not optimize)

    if make_relative:
        def make_path_relative(m):
            v = m.group(0)
            v = Path(v)
            return str(v.to_relative())

        output = re.sub(r'(?<=\bd=")M [^"]*(?=")', make_path_relative, output, flags=re.DOTALL)
        expected = re.sub(r'(?<=\bd=")M [^"]*(?=")', make_path_relative, output, flags=re.DOTALL)

        if len(expected) and not os.path.exists(expected_file):
            with open(expected_file, "w", encoding="utf-8") as f:
                f.write(expected)

    if not os.path.exists(expected_file):
        with open(expected_file, "w", encoding="utf-8") as f:
            f.write(output)

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


gen_args = [
    ('unit', ["mm", "in"]),
    ('inside', [1, 0]),
    ('length', [80, 100]),
    ('width', [100, 80]),
    ('depth', [40, 60]),
    ('equal', [0, 1]),
    ('tab', [6, 10]),
    ('tabtype', [0, 1]),  # regular, dogbone
    ('tabsymmetry', [0, 1, 2]),  # mirror, rotate, antisymmetric
    (['dimpleheight', 'dimplelength'], [[0, 0], [0.1, 0.2]]),
    ('hairline', [1, 0]),
    ('thickness', [3, 6]),
    ('kerf', [0, 0.1, 0.5]),
    ('style', [1, 2, 3]),  # diagrammatic, three-piece, inline
    ('boxtype', [1, 2, 3, 4, 5, 6]),  # fully enclosed, open top, two sides open, three sides open, opposite ends open, two panels only
    (['div-l', 'div-w'], [[1, 1], [0, 0], [0, 1], [1, 0], [2, 3]]),
    ('keydiv', [0, 1, 2, 3]),  # all sides, floor/ceiling only, walls only, none
    ('spacing', [2, 1, 3]),
]

arg_cases : list[list[str]] = []
for i in range(len(gen_args)):

    n = 0
    s = ''
    for k, v in gen_args:
        n += 1
        if i == n-1:
            continue

        if not isinstance(k, Iterable) or isinstance(k, str):
            k = [k]
            v = [[v] for v in v]

        for kk in range(len(k)):
            s += f'--{k[kk]}={v[0][kk]} '

    k, v = gen_args[i]

    if not isinstance(k, Iterable) or isinstance(k, str):
        k = [k]
        v = [[v] for v in v]

    for vv in range(1, len(v)):
        sa = ''
        na = ''

        for kk in range(len(k)):
            sa += f'--{k[kk]}={v[vv][kk]} '
            if na != '':
                na += '&'
            na += f'{k[kk]}={v[vv][kk]}'

        arg_cases.append([s, sa, na])


@pytest.mark.parametrize("cp", arg_cases, ids=[c[2] for c in arg_cases])
def test_params(cp):
    prefix, suffix, name = cp

    name = suffix.replace('--', '').replace('-', '_').replace(' ', '')

    output, expected = run_one(os.path.join('p', name + '.n'), list((prefix + '  ' + suffix).split()))

    # Compare outputs
    assert (
        output == expected
    ), f"Test case {name} failed - output doesn't match expected"


@pytest.mark.parametrize("cp", arg_cases, ids=[c[2] for c in arg_cases])
def test_params_relative(cp):
    prefix, suffix, name = cp

    name = suffix.replace('--', '').replace('-', '_').replace(' ', '')

    output, expected = run_one(os.path.join('p', name + '.r'), list((prefix + '  ' + suffix).split()), make_relative=True)

    # Compare outputs
    assert (
        output == expected
    ), f"Test case {name} failed - output doesn't match expected"


@pytest.mark.parametrize("cp", arg_cases, ids=[c[2] for c in arg_cases])
def test_params_optimized(cp):
    prefix, suffix, name = cp

    name = suffix.replace('--', '').replace('-', '_').replace(' ', '')

    output, expected = run_one(os.path.join('p', name + '.o'), list((prefix + '  ' + suffix).split()), optimize=True)

    # Compare outputs
    assert (
        output == expected
    ), f"Test case {name} failed - output doesn't match expected"


def test_inside_sizes_no_kerf():
    output, expected = run_one(os.path.join('v', 'sizes-20-30-40'), [
            "--unit=mm",
            "--inside=1",
            "--length=20",
            "--width=30",
            "--depth=40",
            "--tab=5",
            "--tabtype=0",
            "--kerf=0",
            "--thickness=2"], optimize=True)

    sizes = []

    for i in re.findall(r'(?<=\bd=")M [^"]*(?=")', output):
        bbox = Path(i).bounding_box()
        w = bbox.width - 4
        h = bbox.height - 4

        sizes.append((round(min(w, h), 3), round(max(w, h), 3)))

    sizes.sort(key=lambda p: p[0]*p[1], reverse=True)
    assert sizes == [(30, 40), (30, 40) , (20, 40), (20, 40), (20, 30), (20, 30)], f"Sizes incorrect: {sizes}"


def test_inside_sizes_kerf():
    output, expected = run_one(os.path.join('v', 'sizes-20-30-40-kerf'), [
            "--unit=mm",
            "--inside=1",
            "--length=20",
            "--width=30",
            "--depth=40",
            "--tab=5",
            "--tabtype=0",
            "--kerf=0.5",
            "--thickness=2"], optimize=True)

    sizes = []

    for i in re.findall(r'(?<=\bd=")M [^"]*(?=")', output):
        bbox = Path(i).bounding_box()
        w = bbox.width - 4 - 0.5
        h = bbox.height - 4 - 0.5

        sizes.append((round(min(w, h), 3), round(max(w, h), 3)))

    sizes.sort(key=lambda p: p[0]*p[1], reverse=True)
    assert sizes == [(30, 40), (30, 40) , (20, 40), (20, 40), (20, 30), (20, 30)], f"Sizes incorrect: {sizes}"


def test_outside_sizes_no_kerf():
    output, expected = run_one(os.path.join('v', 'sizes-20-30-40-outside'), [
            "--unit=mm",
            "--inside=0",
            "--length=20",
            "--width=30",
            "--depth=40",
            "--tab=5",
            "--tabtype=0",
            "--kerf=0",
            "--thickness=2"], optimize=True)

    sizes = []

    for i in re.findall(r'(?<=\bd=")M [^"]*(?=")', output):
        bbox = Path(i).bounding_box()
        w = bbox.width
        h = bbox.height

        sizes.append((round(min(w, h), 3), round(max(w, h), 3)))

    sizes.sort(key=lambda p: p[0]*p[1], reverse=True)
    assert sizes == [(30, 40), (30, 40) , (20, 40), (20, 40), (20, 30), (20, 30)], f"Sizes incorrect: {sizes}"


def test_outside_sizes_kerf():
    output, expected = run_one(os.path.join('v', 'sizes-20-30-40-outside-kerf'), [
            "--unit=mm",
            "--inside=0",
            "--length=20",
            "--width=30",
            "--depth=40",
            "--tab=5",
            "--tabtype=0",
            "--kerf=0.5",
            "--thickness=2"], optimize=True)

    sizes = []

    for i in re.findall(r'(?<=\bd=")M [^"]*(?=")', output):
        bbox = Path(i).bounding_box()
        w = bbox.width - 0.5
        h = bbox.height - 0.5

        sizes.append((round(min(w, h), 3), round(max(w, h), 3)))

    sizes.sort(key=lambda p: p[0]*p[1], reverse=True)
    assert sizes == [(30, 40), (30, 40) , (20, 40), (20, 40), (20, 30), (20, 30)], f"Sizes incorrect: {sizes}"


def test_output_kerf():
    kerf = 0.5
    args = [
            "--unit=mm",
            "--inside=0",
            "--length=20",
            "--width=30",
            "--depth=40",
            "--tab=5",
            "--tabtype=0",
            "--thickness=2"]

    map = make_box_polygons(args, args + ['--kerf=0'])
    map_kerf = make_box_polygons(args + [f'--kerf={kerf}'], optimize=True)

    for k in map.keys():
        if k not in map_kerf:
            assert 0 == 1, f"Missing kerf output for {k}"

        poly = map[k]
        poly_kerf = map_kerf[k]

        poly_bb = poly.bounds
        poly_kerf_bb = poly_kerf.bounds

        width = poly_bb[2] - poly_bb[0]
        kerf_width = poly_kerf_bb[2] - poly_kerf_bb[0]
        assert width == kerf_width - 0.5, f"Kerf output for {k} has different width ({width} vs {kerf_width})"

        height = poly_bb[3] - poly_bb[1]
        kerf_height = poly_kerf_bb[3] - poly_kerf_bb[1]
        assert height == kerf_height - 0.5, f"Kerf output for {k} has different height ({height} vs {kerf_height})"

        poly = translate(poly, xoff=-poly_bb[0], yoff=-poly_bb[1])
        poly_kerf = translate(poly_kerf, xoff=-poly_kerf_bb[0], yoff=-poly_kerf_bb[1])

        shapely_kerf = poly.buffer(0.25, cap_style='square', join_style='mitre')
        shapely_kerf = translate(shapely_kerf, xoff=0.25, yoff=0.25)

        poly = poly.normalize()
        poly_kerf = poly_kerf.normalize()
        shapely_kerf = shapely_kerf.normalize()  # Somehow needed

        print(f'Piece:{k}')
        print(f'Original:\n{poly}')
        print(f'Kerf Generated:\n{poly_kerf}')
        print(f'Kerf Shapely:\n{shapely_kerf}')

        if not shapely_kerf.equals(poly_kerf):
            assert shapely_kerf.exterior == poly_kerf.exterior, f"Kerf output for {k} does not match expected (shell)"
            assert len(shapely_kerf.interiors) == len(poly_kerf.interiors), f"Kerf output for {k} does not match expected (holes count)"
            for h in range(len(shapely_kerf.interiors)):
                assert shapely_kerf.interiors[h] == poly_kerf.interiors[h], f"Kerf output for {k} does not match expected (interior {h})"


def test_output_kerf_dividers():
    kerf = 0.5
    args = [
            "--unit=mm",
            "--inside=0",
            "--length=20",
            "--width=30",
            "--depth=40",
            "--tab=5",
            "--tabtype=0",
            "--div-l=1",
            "--div-w=2",
            "--thickness=2"]

    map = make_box_polygons(args, args + ['--kerf=0'])
    map_kerf = make_box_polygons(args + [f'--kerf={kerf}'], optimize=True)

    for k in map.keys():
        if k not in map_kerf:
            assert 0 == 1, f"Missing kerf output for {k}"

        poly = map[k]
        poly_kerf = map_kerf[k]

        poly_bb = poly.bounds
        poly_kerf_bb = poly_kerf.bounds

        width = poly_bb[2] - poly_bb[0]
        kerf_width = poly_kerf_bb[2] - poly_kerf_bb[0]
        assert width == kerf_width - 0.5, f"Kerf output for {k} has different width ({width} vs {kerf_width})"

        height = poly_bb[3] - poly_bb[1]
        kerf_height = poly_kerf_bb[3] - poly_kerf_bb[1]
        assert height == kerf_height - 0.5, f"Kerf output for {k} has different height ({height} vs {kerf_height})"

        poly = translate(poly, xoff=-poly_bb[0], yoff=-poly_bb[1])
        poly_kerf = translate(poly_kerf, xoff=-poly_kerf_bb[0], yoff=-poly_kerf_bb[1])

        shapely_kerf = poly.buffer(0.25, cap_style='square', join_style='mitre')
        shapely_kerf = translate(shapely_kerf, xoff=0.25, yoff=0.25)

        poly = poly.normalize()
        poly_kerf = poly_kerf.normalize()
        shapely_kerf = shapely_kerf.normalize()  # Somehow needed

        print(f'Piece:{k}')
        print(f'Original:\n{poly}')
        print(f'Kerf Generated:\n{poly_kerf}')
        print(f'Kerf Shapely:\n{shapely_kerf}')

        if not shapely_kerf.equals(poly_kerf):
            assert shapely_kerf.exterior == poly_kerf.exterior, f"Kerf output for {k} does not match expected (shell)"
            assert len(shapely_kerf.interiors) == len(poly_kerf.interiors), f"Kerf output for {k} does not match expected (holes count)"
            for h in range(len(shapely_kerf.interiors)):
                assert shapely_kerf.interiors[h] == poly_kerf.interiors[h], f"Kerf output for {k} does not match expected (interior {h})"


def test_output_kerf_divider_holes():
    kerf = 0.5
    args = [
            "--unit=mm",
            "--inside=0",
            "--length=20",
            "--width=30",
            "--depth=40",
            "--tab=5",
            "--tabtype=0",
            "--div-l=1",
            "--div-w=2",
            "--keydiv=0",
            "--thickness=2"]

    map = make_box_polygons(args, args + ['--kerf=0'])
    map_kerf = make_box_polygons(args + [f'--kerf={kerf}'], optimize=True)

    for k in map.keys():
        if k not in map_kerf:
            assert 0 == 1, f"Missing kerf output for {k}"

        poly = map[k]
        poly_kerf = map_kerf[k]

        poly_bb = poly.bounds
        poly_kerf_bb = poly_kerf.bounds

        width = poly_bb[2] - poly_bb[0]
        kerf_width = poly_kerf_bb[2] - poly_kerf_bb[0]
        assert width == kerf_width - 0.5, f"Kerf output for {k} has different width ({width} vs {kerf_width})"

        height = poly_bb[3] - poly_bb[1]
        kerf_height = poly_kerf_bb[3] - poly_kerf_bb[1]
        assert height == kerf_height - 0.5, f"Kerf output for {k} has different height ({height} vs {kerf_height})"

        poly = translate(poly, xoff=-poly_bb[0], yoff=-poly_bb[1])
        poly_kerf = translate(poly_kerf, xoff=-poly_kerf_bb[0], yoff=-poly_kerf_bb[1])

        shapely_kerf = poly.buffer(0.25, cap_style='square', join_style='mitre')
        shapely_kerf = translate(shapely_kerf, xoff=0.25, yoff=0.25)

        poly = poly.normalize()
        poly_kerf = poly_kerf.normalize()
        shapely_kerf = shapely_kerf.normalize()  # Somehow needed

        print(f'Piece:{k}')
        print(f'Original:\n{poly}')
        print(f'Kerf Generated:\n{poly_kerf}')
        print(f'Kerf Shapely:\n{shapely_kerf}')

        if not shapely_kerf.equals(poly_kerf):
            assert shapely_kerf.exterior == poly_kerf.exterior, f"Kerf output for {k} does not match expected (shell)"
            assert len(shapely_kerf.interiors) == len(poly_kerf.interiors), f"Kerf output for {k} does not match expected (holes count)"
            for h in range(len(shapely_kerf.interiors)):
                assert shapely_kerf.interiors[h] == poly_kerf.interiors[h], f"Kerf output for {k} does not match expected (interior {h})"


def test_output_area():
    thickness = 2
    arg_base = [
            "--unit=mm",
            "--inside=0",
            "--length=20",
            "--width=30",
            "--depth=40",
            "--tab=5",
            "--tabtype=0",
            f"--thickness={thickness}"]

    for boxtype in [1, 2, 3, 4, 5, 6]:
        b_args = arg_base.copy()
        b_args.append(f'--boxtype={boxtype % 100}')

        # We assume the total area of the box polygons * thickness is the volume of material needed to make the box
        expected_area = {
            1: (20.0*30.0*40.0 - 16.0*26.0*36.0) / 2.0,  # 4512.0, #FULLY_ENCLOSED
            2: 4096.0,  # ONE_SIDE_OPEN
            3: 3488.0,  # TWO_SIDES_OPEN
            4: 2424.0,  # THREE_SIDES_OPEN
            5: 3680.0,  # OPPOSITE_ENDS_OPEN
            6: 1740.0,  # TWO_PANELS_ONLY
        }.get(boxtype, 0)

        for sym in [0, 1, 2]:
            args = b_args + [f'--tabsymmetry={sym}']

            polies = make_box_polygons(args, optimize=True)
            area = 0.0

            for k, p in polies.items():
                if p.area == 0:
                    print(f"Warning: zero area polygon for ({boxtype, sym}: {" " .join(args)}")
                area += p.area

            area = round(area, 3)
            expected_area = round(expected_area, 3)

            assert area == expected_area, f"Area mismatch for ({boxtype, sym}: {" " .join(args)}: {area} != {expected_area}"


def test_output_area_dividers():
    thickness = 2
    arg_base = [
            "--unit=mm",
            "--inside=0",
            "--length=20",
            "--width=30",
            "--depth=40",
            "--tab=5",
            "--tabtype=0",
            f"--thickness={thickness}"]

    for boxtype in [101, 102, 103, 104, 105, 106, 201, 202, 203, 204, 205, 206]:
        b_args = arg_base.copy()
        b_args.append(f'--boxtype={boxtype % 100}')

        if boxtype > 200:
            b_args += ['--div-w=1', '--keydiv=1']
        elif boxtype > 100:
            b_args += ['--div-l=2', '--keydiv=1']

        # We assume the total area of the box polygons * thickness is the volume of material needed to make the box
        base_expected_area = {
            101: (20.0*30.0*40.0 - 16.0*26.0*36.0 + 2*16.0*36.0*thickness) / 2.0,  # 5664.0, #FULLY_ENCLOSED with dividers
            102: 5312.0,  # ONE_SIDE_OPEN with dividers
            103: 4704.0,  # TWO_SIDES_OPEN with dividers
            104: 3792.0,  # THREE_SIDES_OPEN with dividers
            105: 4960.0,  # OPPOSITE_ENDS_OPEN with dividers
            106: 3108.0,  # TWO_PANELS_ONLY with dividers

            201: (20.0*30.0*40.0 - 16.0*26.0*36.0 + 26.0*36.0*thickness) / 2.0,  # 5448.0, #FULLY_ENCLOSED with dividers
            202: 5084.0,  # ONE_SIDE_OPEN with dividers
            203: 4554.0,  # TWO_SIDES_OPEN with dividers
            204: 3488.0,  # THREE_SIDES_OPEN with dividers
            205: 4720.0,  # OPPOSITE_ENDS_OPEN with dividers
            206: 2880.0,  # TWO_PANELS_ONLY with dividers
        }.get(boxtype, 0)

        for sym in [0, 1, 2]:
            args = b_args + [f'--tabsymmetry={sym}']

            polies = make_box_polygons(args, optimize=True)
            area = 0.0

            offset = {
                (104, 1): 4,
                (104, 2): 8,
                (202, 2): -12,
                (201, 2): -16,
                (203, 0): -2,
                (203, 2): -14,
                (204, 1): 2,
                (206, 1): +4,
            }.get((boxtype, sym), 0)

            expected_area = base_expected_area + offset

            for k, p in polies.items():
                if p.area == 0:
                    print(f"Warning: zero area polygon for ({boxtype, sym}: {" " .join(args)}")
                area += p.area

            area = round(area, 3)
            expected_area = round(expected_area, 3)

            assert area == expected_area, f"Area mismatch for ({boxtype, sym}: {" " .join(args)}: {area} != {expected_area}"
