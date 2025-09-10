import io, os, re, xml.dom.minidom
from tabbedboxmaker import BoxMaker

def mask_id_attributes(svgin: str) -> str:
    return re.sub(r'id="[-a-z0-9A-Z_]+"', 'id="TEST"', svgin)

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


class TestTabbedBox:

    def test_tabbed(self):
        # See boxmaker.inx for arg descriptions
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
                "label": "two_sides_open",
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
                "label": "with_dogbone",
                "args": [
                    "--unit=mm",
                    "--inside=1",
                    "--length=80",
                    "--width=100",
                    "--depth=40",
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
                    "--depth=40",
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
                    "--depth=40",
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
                    "--depth=40",
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
                    "--depth=40",
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



            # {
            #    'label': 'default_tabs',
            #    'args': [
            #        '--unit=mm', '--inside=1', '--length=80', '--width=100',
            #        '--depth=40', '--equal=0', '--tabtype=0',
            #        '--tabsymmetry=0', '--dimpleheight=0', '--dimplelength=0',
            #        '--hairline=1', '--thickness=3', '--kerf=0', '--style=1',
            #        '--boxtype=1', '--div_l=0', '--div_w=0', '--keydiv=1',
            #        '--spacing=1' ],
            # },
        ]

        expected_output_dir = os.path.join(os.path.dirname(__file__), "expected")
        actual_output_dir = os.path.join(os.path.dirname(__file__), "actual")

        os.makedirs(actual_output_dir, exist_ok=True)
        os.makedirs(os.path.join(actual_output_dir, 'o'), exist_ok=True)

        for case in cases:
            name = case["label"]
            args = case["args"]
            print(name)

            outfh = io.BytesIO()
            expected_file = os.path.join(expected_output_dir, name + ".svg")
            expected = ""
            actual_file = os.path.join(actual_output_dir, name + ".svg")
            with open(expected_file, "r") as f:
                expected = f.read()

            tbm = BoxMaker(cli=True)

            tbm.parse_arguments(args + ['--optimize=False'])
            tbm.options.output = outfh

            tbm.load_raw()
            tbm.save_raw(tbm.effect())

            output = outfh.getvalue().decode("utf-8")
            output = pretty_xml(output)

            with open(actual_file, "w", encoding="utf-8") as f:
                f.write(output)

            output = output

            # Compare outputs
            assert (
                output == expected
            ), f"Test case {name} failed - output doesn't match expected"


            # Now do it again with optimization enabled
            outfh = io.BytesIO()
            expected_file = os.path.join(expected_output_dir, 'o', name + ".svg")
            expected = ""
            actual_file = os.path.join(actual_output_dir, 'o', name + ".svg")
            with open(expected_file, "r") as f:
                expected = f.read()

            tbm = BoxMaker(cli=True)

            tbm.parse_arguments(args + ['--optimize=True'])
            tbm.options.output = outfh

            tbm.load_raw()
            tbm.save_raw(tbm.effect())

            output = outfh.getvalue().decode("utf-8")
            output = pretty_xml(output)

            with open(actual_file, "w", encoding="utf-8") as f:
                f.write(output)

            # Compare outputs
            assert (
                output == expected
            ), f"Test case {name} failed - optimized output doesn't match expected"
