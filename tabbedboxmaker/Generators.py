import sys
import re

from tabbedboxmaker.InkexShapely import adjust_canvas
from inkex import GenerateExtension, Transform


class CliEnabledGenerator(GenerateExtension):
    """An Inkscape extension that can be run from the command line to generate SVG output."""
    hairline_thickness: float = None
    raw_hairline_thickness: float = None
    cli: bool = True
    cli_args: list[str] = []
    nextId: dict[str, int] = {}
    container_no_transform = False
    doument_unit: str = None

    def __init__(self, cli=True, inkscape=False):
        self.cli = cli
        self.inkscape = inkscape

        super().__init__()

        self.cli_args = sys.argv[1:]  # Store command-line arguments for later use
        self.nextId = {}

    def container_transform(self):
        """Get the transform attribute of the container layer, if any."""

        # In cli mode, or if the document is empty, return identity transform
        if self.cli or self.container_no_transform or len(self.svg.get_current_layer()) == 0:
            return Transform()
        else:
            return super().container_transform()

    def effect(self):
        if not self.hairline_thickness:
            self.raw_hairline_thickness = self.hairline_thickness = round(self.svg.unittouu("1px"), 6)
        elif self.hairline_thickness is None:
            self.hairline_thickness = 0.1

        super().effect()

        if not self.inkscape:
            container = self.svg.get_current_layer()
            container[-1].set_id(self.makeId(re.sub(r'[^a-zA-Z]', '', str(self.container_label).lower())))


        if not self.inkscape:
            adjust_canvas(self.svg, unit=self.document_unit)


    def makeId(self, prefix: str | None) -> str:
        """Generate a new unique ID with the given prefix."""

        prefix = prefix if prefix is not None else "id"
        if prefix not in self.nextId:
            id = self.nextId[prefix] = 0

        self.nextId[prefix] = id = self.nextId[prefix] + 1

        return f"{prefix}_{id:03d}"
