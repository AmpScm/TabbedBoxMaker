from copy import deepcopy
import os
import re
import sys

from argparse import ArgumentParser
from tabbedboxmaker.InkexShapely import adjust_canvas
from inkex import GenerateExtension, Transform


class CliEnabledGenerator(GenerateExtension):
    """An Inkscape extension that can be run from the command line to generate SVG output."""
    hairline_thickness: float = None
    raw_hairline_thickness: float = None
    cli: bool = True
    cli_args: list[str] = []
    nextId: dict[str, int] = {}
    doument_unit: str = None

    def __init__(self, cli=True, inkscape=False):
        self.cli = cli
        self.inkscape = inkscape

        super().__init__()

        self.cli_args = sys.argv[1:]  # Store command-line arguments for later use
        self.nextId = { 'line': 0, 'rect': 0, 'circle': 0, 'path': 0, 'text': 0, 'side': 0, 'hole': 0, 'piece': 0, 'box': 0, 'slot': 0 }

        if self.cli:
            # We don"t need a required input file in CLI mode
            for action in self.arg_parser._get_positional_actions():
                self.arg_parser._remove_action(action)
                self.arg_parser._positionals._group_actions.remove(action)

    def add_arguments(self, pars : ArgumentParser) -> None:
        super().add_arguments(pars)
        self.arg_parser.add_argument(
            '--unit',
            type=str,
            dest='unit',
            default='mm',
            help='Measure Units',
            choices=["mm", "cm", "in", "ft", "px", "pt", "pc"] + (["document"] if self.inkscape else []),
        )

        if not self.cli:
            self.arg_parser.add_argument(
                '--absolute-positioning',
                type=bool,
                dest='absolute_positioning',
                default=True,
                help='Use absolute positioning',
            )


    def parse_arguments(self, args: list[str]) -> None:
        """Parse the given arguments and set 'self.options'"""

        super().parse_arguments(args)
        self.cli_args = deepcopy(args)

        if not hasattr(self.options, "input_file"):
            self.options.input_file = os.path.join(os.path.dirname(__file__), "blank.svg")


        if hasattr(self.options, "unit"):
            self.document_unit = self.options.unit
        else:
            self.document_unit = None

        if not hasattr(self.options, "absolute_positioning"):
            self.options.absolute_positioning = True

    def container_transform(self):
        """Get the transform attribute of the container layer, if any."""

        # In cli mode, or if the document is empty, return identity transform
        if self.cli or self.options.absolute_positioning or len(self.svg.get_current_layer()) == 0:
            return Transform()
        else:
            return super().container_transform()

    def effect(self):
        if not self.hairline_thickness:
            self.raw_hairline_thickness = self.hairline_thickness = round(self.svg.unittouu("1px"), 6)
        elif self.hairline_thickness is None:
            self.hairline_thickness = 0.1

        if hasattr(self.options, "unit"):
            if self.options.unit == "document":
                self.document_unit = self.options.unit = self.svg.document_unit
        elif self.document_unit == "document":
            self.document_unit = self.svg.document_unit

        super().effect()

        if not self.inkscape:
            container = self.svg.get_current_layer()
            group = container[-1]
            group.set_id(self.makeId(re.sub(r'[^a-zA-Z]', '', str(self.container_label).lower())))

        if not self.inkscape:
            adjust_canvas(self.svg, unit=self.document_unit)


    def makeId(self, prefix: str | None) -> str:
        """Generate a new unique ID with the given prefix."""

        prefix = prefix if prefix is not None else "id"
        if prefix not in self.nextId:
            id = self.nextId[prefix] = -1

        self.nextId[prefix] = id = self.nextId[prefix] + 1

        if id == 0:
            return prefix
        else:
            return f"{prefix}_{id:03d}"
