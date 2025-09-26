import io
import os
import pytest
import re
import sys
from inkex.paths import Path

import xml.dom.minidom
from tabbedboxmaker.InkexShapely import path_to_polygon, polygon_to_path
from collections.abc import Iterable

from tabbedboxmaker import TabbedBoxMaker


from shapely.affinity import translate

def mask_unstable(svgin: str) -> str:
    """Mask out unstable parts of SVG output that may vary between runs."""
    return re.sub(
        r'<!--.*?-->', '<!-- MASKED -->', re.sub(
        r'inkscape:version="[^"]*"', 'inkscape:version="MASKED"',  re.sub(
        r'id="[^"]*"', 'id="MASKED"',  re.sub(
        r'<metadata[^>]*?/>', '<metadata />', svgin, flags=re.DOTALL),
        flags=re.DOTALL), flags=re.DOTALL), flags=re.DOTALL).replace('\r\n', '\n')

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
            "--div_l=0",
            "--div_w=0",
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
            "--div_l=0",
            "--div_w=0",
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
            "--div_l=0",
            "--div_w=0",
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
            "--div_l=0",
            "--div_w=0",
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
            "--div_l=0",
            "--div_w=0",
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
            "--div_l=0",
            "--div_w=0",
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
            "--div_l=0",
            "--div_w=0",
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
            "--div_l=0",
            "--div_w=0",
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
            "--div_l=0",
            "--div_w=0",
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
            "--div_l=0",
            "--div_w=0",
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
            "--div_l=0",
            "--div_w=0",
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
            "--thickness=3",
            "--kerf=0",
            "--style=1",
            "--boxtype=2",
            "--div_l=0",
            "--div_w=0",
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
            "--div_l=0",
            "--div_w=0",
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
            "--div_l=0",
            "--div_w=0",
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
            "--div_l=0",
            "--div_w=0",
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
            "--div_l=1",
            "--div_w=1",
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
            "--div_l=1",
            "--div_w=1",
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
            "--div_l=1",
            "--div_w=1",
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
            "--div_l=1",
            "--div_w=1",
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
            "--div_l=2",
            "--div_w=3",
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
            "--div_l=3",
            "--div_w=4",
            "--div_l_spacing=10;5;10",
            "--div_w_spacing=10;5",
            "--spacing=1",
            "--keydiv=0",
            "--hairline=1",
            "--kerf=0.1",
        ]
    },
]

expected_output_dir = os.path.join(os.path.dirname(__file__), "..","expected")
actual_output_dir = os.path.join(os.path.dirname(__file__), "..", "actual")

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

    tbm = TabbedBoxMaker()
    
    blank_svg = os.path.join(os.path.dirname(__file__), "blank.svg")

    with open(blank_svg, "r") as f:
        blank_data = f.read()

    infh = io.BytesIO(blank_data.encode("utf-8"))
    tbm.parse_arguments(args)
    tbm.options.output = outfh
    tbm.options.input_file = infh
    tbm.options.optimize = optimize
    tbm.version = None
    tbm.raw_hairline_thickness = -1
    tbm.hairline_thickness = 0.0508

    tbm.load_raw()
    tbm.save_raw(tbm.effect())

    output = outfh.getvalue().decode("utf-8")
    output = pretty_xml(output)

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

gen_args = [
    ('unit', ["mm", "in"]),
    ('inside', [1, 0]),
    ('length', [80, 100]),
    ('width', [100, 80]),
    ('depth', [40, 60]),
    ('equal', [0, 1]),
    ('tab', [6, 10]),
    ('tabtype', [0, 1]), # regular, dogbone
    ('tabsymmetry', [0, 1, 2]), # mirror, rotate, antisymmetric
    (['dimpleheight', 'dimplelength'], [[0, 0], [0.1, 0.2]]),
    ('hairline', [1, 0]),
    ('thickness', [3, 6]),
    ('kerf', [0, 0.1, 0.5]),
    ('style', [1, 2, 3]), # diagrammatic, three-piece, inline
    ('boxtype', [1, 2, 3, 4, 5, 6]), # fully enclosed, open top, two sides open, three sides open, opposite ends open, two panels only
    (['div_l', 'div_w'], [[1, 1], [0, 0], [0, 1], [1, 0], [2, 3]]),
    ('keydiv', [0, 1, 2, 3]), # all sides, floor/ceiling only, walls only, none
    ('spacing', [2, 1, 3]),
]

arg_cases : list[list[str]]= []
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

    name = suffix.replace('-', '').replace(' ','')

    output, expected = run_one(os.path.join('p', name + '.n'), list((prefix + '  ' + suffix).split()))

    # Compare outputs
    assert (
        output == expected
    ), f"Test case {name} failed - output doesn't match expected"

@pytest.mark.parametrize("cp", arg_cases, ids=[c[2] for c in arg_cases])
def test_params_relative(cp):
    prefix, suffix, name = cp

    name = suffix.replace('-', '').replace(' ','')

    output, expected = run_one(os.path.join('p', name + '.r'), list((prefix + '  ' + suffix).split()), make_relative=True)

    # Compare outputs
    assert (
        output == expected
    ), f"Test case {name} failed - output doesn't match expected"


@pytest.mark.parametrize("cp", arg_cases, ids=[c[2] for c in arg_cases])
def test_params_optimized(cp):
    prefix, suffix, name = cp

    name = suffix.replace('-', '').replace(' ','')

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

    sizes=[]

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

    sizes=[]

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

    sizes=[]

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

    sizes=[]

    for i in re.findall(r'(?<=\bd=")M [^"]*(?=")', output):
        bbox = Path(i).bounding_box()
        w = bbox.width - 0.5
        h = bbox.height - 0.5

        sizes.append((round(min(w, h), 3), round(max(w, h), 3)))
    
    sizes.sort(key=lambda p: p[0]*p[1], reverse=True)
    assert sizes == [(30, 40), (30, 40) , (20, 40), (20, 40), (20, 30), (20, 30)], f"Sizes incorrect: {sizes}"


def test_output_kerf():
    output, _ = run_one(os.path.join('v', 'sizes-20-30-40-outside'), [
            "--unit=mm",
            "--inside=0",
            "--length=20",
            "--width=30",
            "--depth=40",
            "--tab=5",
            "--tabtype=0",
            "--kerf=0",
            "--thickness=2"], optimize=True, mask=False)
    
    output_kerf, _ = run_one(os.path.join('v', 'sizes-20-30-40-outside-kerf'), [
            "--unit=mm",
            "--inside=0",
            "--length=20",
            "--width=30",
            "--depth=40",
            "--tab=5",
            "--tabtype=0",
            "--kerf=0.5",
            "--thickness=2"], optimize=True, mask=False)
    
    map = {}
    for i in re.findall(r'id="((piece|[xy]divider)[^"]+)".*d="(M [^"]*(?="))', output):
        map[i[0]] = i[2]

    map_kerf = {}
    for i in re.findall(r'id="((piece|[xy]divider)[^"]+)".*d="(M [^"]*(?="))', output_kerf):
        map_kerf[i[0]] = i[2]


    for k in map.keys():
        if k not in map_kerf:
            assert 0 == 1, f"Missing kerf output for {k}"

        p = Path(map[k])
        p_kerf = Path(map_kerf[k])

        bb = p.bounding_box()
        bb_kerf = p_kerf.bounding_box()

        assert bb.width == bb_kerf.width - 0.5, f"Kerf output for {k} has different width ({bb.width} vs {bb_kerf.width})"

        poly = path_to_polygon(p)
        poly_kerf = path_to_polygon(p_kerf)

        poly = translate(poly, xoff=-bb.left, yoff=-bb.top)
        poly_kerf = translate(poly_kerf, xoff=-bb_kerf.left, yoff=-bb_kerf.top)

        pp = poly.buffer(0.25, cap_style='square', join_style='mitre')
        pp = translate(pp, xoff=0.25, yoff=0.25)

        poly.normalize()
        poly_kerf.normalize()
        pp = pp.reverse() # Somehow needed

        print(k)
        print(poly)
        print(poly_kerf)
        print(pp)
        assert pp == poly_kerf, f"Kerf output for {k} does not match expected"


def test_output_kerf_dividers():
    output, _ = run_one(os.path.join('v', 'sizes-20-30-40-outside-d'), [
            "--unit=mm",
            "--inside=0",
            "--length=20",
            "--width=30",
            "--depth=40",
            "--tab=5",
            "--tabtype=0",
            "--kerf=0",
            "--div_l=1",
            "--div_w=2",
            "--thickness=2"], optimize=True, mask=False)
    
    output_kerf, _ = run_one(os.path.join('v', 'sizes-20-30-40-outside-d-kerf'), [
            "--unit=mm",
            "--inside=0",
            "--length=20",
            "--width=30",
            "--depth=40",
            "--tab=5",
            "--tabtype=0",
            "--kerf=0.5",
            "--div_l=1",
            "--div_w=2",
            "--thickness=2"], optimize=True, mask=False)
    
    map = {}
    for i in re.findall(r'id="((piece|[xy]divider)[^"]+)".*d="(M [^"]*(?="))', output):
        map[i[0]] = i[2]

    map_kerf = {}
    for i in re.findall(r'id="((piece|[xy]divider)[^"]+)".*d="(M [^"]*(?="))', output_kerf):
        map_kerf[i[0]] = i[2]


    for k in map.keys():
        if k not in map_kerf:
            assert 0 == 1, f"Missing kerf output for {k}"

        p = Path(map[k])
        p_kerf = Path(map_kerf[k])

        bb = p.bounding_box()
        bb_kerf = p_kerf.bounding_box()

        assert bb.width == bb_kerf.width - 0.5, f"Kerf output for {k} has different width ({bb.width} vs {bb_kerf.width})"

        poly = path_to_polygon(p)
        poly_kerf = path_to_polygon(p_kerf)

        poly = translate(poly, xoff=-bb.left, yoff=-bb.top)
        poly_kerf = translate(poly_kerf, xoff=-bb_kerf.left, yoff=-bb_kerf.top)

        pp = poly.buffer(0.25, cap_style='square', join_style='mitre')
        pp = translate(pp, xoff=0.25, yoff=0.25)

        poly.normalize()
        poly_kerf.normalize()
        pp = pp.reverse() # Somehow needed

        print(k)
        print(poly)
        print(poly_kerf)
        print(pp)

        #with open('/tmp.svg', "w", encoding="utf-8") as f:
        #    f.write('<svg xmlns="http://www.w3.org/2000/svg">\n' +
        #            '<path d="' + str(polygon_to_path(poly_kerf)) + '" fill="none" stroke="blue"/>\n' +
        #            '</svg>\n')
        #    
        #with open('/tmp-pp.svg', "w", encoding="utf-8") as f:
        #    f.write('<svg xmlns="http://www.w3.org/2000/svg">\n' +
        #            '<path d="' + str(polygon_to_path(pp)) + '" fill="none" stroke="blue"/>\n' +
        #            '</svg>\n')

        assert pp == poly_kerf or pp.reverse() == poly_kerf, f"Kerf output for {k} does not match expected"


def test_output_kerf_divider_holes():
    kerf = 0.5
    name = 'sizes-20-30-40-outside-dh'
    args = [
            "--unit=mm",
            "--inside=0",
            "--length=20",
            "--width=30",
            "--depth=40",
            "--tab=5",
            "--tabtype=0",
            "--div_l=1",
            "--div_w=2",
            "--keydiv=0",
            "--thickness=2"]
    
    output, _ = run_one(os.path.join('v', name), 
                        args + ['--kerf=0'], optimize=True, mask=False)
    output_kerf, _ = run_one(os.path.join('v', name + '-kerf'),
                             args + [f'--kerf={kerf}'], optimize=True, mask=False)
    
    map = {}
    for i in re.findall(r'id="((piece|[xy]divider)[^"]+)".*d="(M [^"]*(?="))', output):
        map[i[0]] = i[2]

    map_kerf = {}
    for i in re.findall(r'id="((piece|[xy]divider)[^"]+)".*d="(M [^"]*(?="))', output_kerf):
        map_kerf[i[0]] = i[2]


    for k in map.keys():
        if k not in map_kerf:
            assert 0 == 1, f"Missing kerf output for {k}"

        p = Path(map[k])
        p_kerf = Path(map_kerf[k])

        bb = p.bounding_box()
        bb_kerf = p_kerf.bounding_box()

        assert bb.width == bb_kerf.width - 0.5, f"Kerf output for {k} has different width ({bb.width} vs {bb_kerf.width})"

        half_kerf = kerf / 2.0
        poly = path_to_polygon(p)
        poly_kerf = path_to_polygon(p_kerf)
        poly = translate(poly, xoff=-bb.left, yoff=-bb.top)
        poly_kerf = translate(poly_kerf, xoff=-bb_kerf.left, yoff=-bb_kerf.top)

        pp = poly.buffer(half_kerf, cap_style='square', join_style='mitre')
        pp = translate(pp, xoff=half_kerf, yoff=half_kerf)

        poly = poly.normalize()
        poly_kerf = poly_kerf.normalize()
        pp = pp.normalize() # Somehow needed

        print(f'Piece: {k}')
        print(f'Original: {poly}')
        print(f'Kerf Generated: {poly_kerf}')
        print(f'Kerf Shapely: {pp}')

        with open('/tmp.svg', "w", encoding="utf-8") as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg">\n' +
                    '<path d="' + str(polygon_to_path(poly_kerf)) + '" fill="none" stroke="blue"/>\n' +
                    '</svg>\n')
            
        with open('/tmp-pp.svg', "w", encoding="utf-8") as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg">\n' +
                    '<path d="' + str(polygon_to_path(pp)) + '" fill="none" stroke="blue"/>\n' +
                    '</svg>\n')

        assert pp == poly_kerf or pp.reverse() == poly_kerf, f"Kerf output for {k} does not match expected"
