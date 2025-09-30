# TabbedBoxMaker: A free Inkscape extension for generating tab-jointed box patterns

[![CI - Test and Validate BoxMaker](https://github.com/ampscm/TabbedBoxMaker/actions/workflows/ci.yaml/badge.svg)](https://github.com/ampscm/TabbedBoxMaker/actions/workflows/ci.yaml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3+](https://img.shields.io/badge/License-GPLv3+-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

_Version 2.0 - September 2025_

* Original box maker by Elliot White (formerly of twot.eu, domain name now squatted)
* Tabbed boxmaker heavily modified by [Paul Hutchison](https://github.com/paulh-rnd).
* Other modules added by their resp authors.
* Now maintained by [Bert Huijben](https://github.com/rhuijben).

## About
 This tool is designed to simplify the process of making practical boxes from sheet material using almost any kind of CNC cutter (laser, plasma, water jet or mill). The
 box edges are "tab-jointed". Depending on settings dimples may be provided to make them press-fit.

The tool creates svg files and works by generating each side of the box with the tab and edge sizes corrected to account for the kerf (width of cut) and dogbones are added if
necessary. Each box side is composed of a group of individual lines that make up each edge of the face, as well as any other cutouts for dividers. Joining adjecent lines is
optional to allow further customization.

Several users of the tabbed boxmaker and its previous versions have written extensions.
  * Schroff Box maker (=Tabbed Boxmaker customized with schroff settings and additiona holes)
  * Cardboard Box maker (Other box variant)
  * Living Hinges Box maker (Very specific kind of box)

## Release Notes
The code was completely refactored since the v1.x series. It is now a proper python package with testssuite
and supports both plugin for Inkscape and a commandline scenarios. The plugin provides 4 extension points
in Inkscape.
 * Box maker
 * Cardboard Box maker (completely separate for now)
 * Living Hinges (completely separate for now)
 * Schroff Box maker (=Tabbed Boxmaker customized with schroff settings)

The regression tests validate if output matches what is expected and if basic mathemetical constraints hold. (E.g. kerf is calculated correctly. Parts produce enough material to really create the rectangle, etc.)

The program works with Python 3 ONLY.

Note that all these extensions have moved to a single *Box Maker* submenu under extensions.

## To do
* More cleanup
* More validations
* Improve input checking to restrict values to correct solutions.
* Dogbone only works on tabbed joins, NOT divider keyholes or slots yet
* Would be great to make shapes closed and do path subtraction to get slot cutouts and keyholes from faces, and perhaps offer to add fill colour
* [Schroff] Maybe replace the somewhat obscure collection of Schroff rail input data with a dropdown box listing well-documented rail types (Vector, Z-rails, whatever it is that Elby sells, others?)
* [Schroff] Add support for multiple mounting holes per rail where possible (this would definitely make the previous todo item worthwhile)
* [Schroff] Add support for 6U row height

## Use - regular tabbed boxes
 The interface is pretty self explanatory, the three extensions are in the 'Box Maker' group in the 'Extensions' menu.

Parameters in order of appearance:

* Units - unit of measurement used for drawing

* Box Dimensions: Inside/Outside - whether the box dimensions are internal or external measurements

* Length / Width / Height - the box dimensions

* Tab Width: Fixed/Proportional - for fixed the tab width is the value given in the Tab
                                 Width, for proportional the side of a piece is divided
                                 equally into tabs and 'spaces' with the tabs size
                                 greater or equal to the Tab Width setting

* Minimum/Preferred Tab Width - the size of the tabs used to hold the pieces together

* Symmetry - there are two styles of tabs avaiable:
    * XY Symmetrix - each piece is symmetric in both the X and Y axes
    * Rotate Symmetric ("waffle block") - each piece is symmetric under a 180-degree rotation
      (and 90 degrees if that piece is square)

* Tab Dimple Height - the height of the dimple to add to the side of each tab, 0 for no dimple.
  Dimples can be added to give tabbed joints a little extra material for a tighter press fit.

* Tab Dimple Length - the length of the tip of the dimple; dimples are trapezoid shaped with
  45-degree sides; using a dimple tip length of 0 gives a triangular dimple

* Line Thickness - Leave this as _Default_ unless you need hairline thickness (Use for Epilog lasers)

* Material Thickness - as it says

* Kerf - this is the diameter/width of the cut. Typical laser cutters will be between 0.1 - 0.25mm,
  for CNC mills, this will be your end mill diameter. A larger kerf will assume more material is removed,
  hence joints will be tighter. Smaller or zero kerf will result in looser joints.

* Layout - controls how the pieces are laid out in the drawing

* Box Type - this allows you to choose how many jointed sides you want. Options are:
    * Fully enclosed (6 sides)
    * One side open (LxW) - one of the Length x Width panels will be omitted
    * Two sides open (LxW and LxH) - two adjacent panels will be omitted
    * Three sides open (LxW, LxH, HxW) - one of each panel omitted
    * Opposite ends open (LxW) - an open-ended "tube" with the LxW panels omitted
    * Two panels only (LxW and LxH) - two panels with a single joint down the Length axis

* Dividers (Length axis) - use this to create additional LxH panels that mount inside the box
  along the length axis and have finger joints into the side panels
  and slots for Width dividers to slot into

* Dividers (Width axis) - use this to create additional WxH panels that mount inside the box
                         along the width axis and have finger joints into the side panels
                         and slots for Length dividers to slot into

* Key the dividers into - this allows you to choose if/how the dividers are keyed into the sides of the box. Options are:
    * None - no keying, dividers will be free to slide in and out
    * Walls - dividers will only be keyed into the side walls of the box
    * Floor/Ceiling - dividers will only be keyed into the top/bottom of the box
    * All Sides

* Space Between Parts - how far apart the pieces are in the drawing produced

* Live Preview - you may need to turn this off when changing tab style, box type, or layout

## Use - Schroff enclosures

Much the same as for regular enclosures, except some options are removed, and some others are added. If you're using Elby rails, all you'll need to do is specify:

* Depth

* Number of 3U rows

* Row width in TE/HP units (divide rail length by 5.08mm/0.2")

* If multiple rows, inter-row spacing

## Installation

#### Installing as Inkscape Extension (Recommended)

1. Download the extension from this GitHub page using the *[Clone or download > Download ZIP](archive/refs/heads/master.zip)* link. If you are using an older version of Inkscape, you will need to download the correct version of the extension (see [Version History](#version-history) below)
2. Extract the zip file
3. Copy all files into a new subdirectory of the system or per-user Inkscape extensions directory.  On Windows that would be something like `C:\Program Files\Inkscape\share\inkscape\extensions` or `%appdata%\inkscape\extensions`. Under linux or MacOS something like `/usr/share/inkscape/extensions` or `~/.config/inkscape/extensions`. The easiest way to find the directory is to open Inkscape, go to _Edit > Preferences > System_ (Win/Linux) or _Inkscape > Preferences > System_ (Mac).
4. Inkscape *must* be restarted after copying the extension files.
5. If it has been installed correctly, you should find the extension under the _Extensions > Box Maker_ menu. Enjoy!

#### Running from the shell

You can use the files and create svg files using the tools

```bash
pip install tabbedboxmaker
```

This allows you to use it from the command line:

```bash
# Generate a basic box
$ boxmaker.py --length=100 --width=80 --depth=60 --thickness=3 --output=mybox.svg

# Generate a Schroff enclosure
$ schroff.py --hp=42 --rows=2 --depth=160 --thickness=3 --output=schroff.svg

# Generate a cardboard box
$ cardboard.py --length=100 --width=80 --depth=60 --thickness=3 --output=cardboardbox.svg

# Generate a living hinge
$  livinghinge.py  --length=100 --width=80 --depth=60 --thickness=3 --output=hinge.svg
```

### For Developers

#### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/ampscm/TabbedBoxMaker.git
   cd TabbedBoxMaker
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Unix/macOS:
   source venv/bin/activate
   ```

3. Install in development mode:
   ```bash
   pip install -e .[dev]
   ```

4. Install pre-commit hooks (optional but recommended):
   ```bash
   pre-commit install
   ```

#### Running Tests
```bash
# Run tests
python -m pytest -v
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. Before contributing:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run the test suite (python -m pytest -v`)
6. Commit your changes (`git commit -m 'Add some amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Guidelines

- Follow python sstyle guidelines (e.g. PEP 8)
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass before submitting PR

### Reporting Issues

Please use the [GitHub Issues](https://github.com/ampscm/TabbedBoxMaker/issues) page to report bugs or request features.

## License

This project is licensed under the GNU General Public License v3.0 or later - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Original Tabbed Box Maker by Elliot White
- Major contributions by Paul Hutchison, John Slee, Jim McBeath, and Brad Goodman
- All contributors who have helped improve this project

## Version History
version | Date | Notes
--------|------|--------
0.5  | ( 9 Oct 2011) | beta
0.7  | (24 Oct 2011) | first release
0.8  | (26 Oct 2011) | basic input checking implemented
0.86 | (19 Dec 2014) | updates to allow different box types and internal dividers
0.86a | (23 June 2015) | Updated for compatibility with Inkscape 0.91
0.87 | (28 July 2015) | Schroff enclosure add-on
0.93 | (21 Sept 2015) | Updated versioning to match original author's updated v0.91 plus adding my 0.02
0.93a | (21 Sept 2015) | Added hairline line thickness option for Epilog lasers
0.94 | (4 Jan 2017) | Divider keying options
0.95 | (20 Apr 2017) | Added optional dimples on tabs
0.96 | (24 Apr 2017) | Orthogonalized box type, layout, tab style; added rotate-symmetric tabs
0.99 | (4 June 2020) | Upgraded to support Inkscape v1.0, minor fixes and a tidy up of the parameters dialog layout
1.0 |  (17 June 2020) | v1.0 final released: fixes and dogbone added - Mills now supported!
1.1 |  (9 Aug 2021) | v1.1 with fixes for newer Inkscape versions - sorry for the delays
1.2 |  (4 Dec 2023) | PR merged from [@mausmaux](https://github.com/mausmaux) with thanks
1.4 | Early 2025 | Merged several PRs
2.0 | (Sep 2025) | Completely refactored to be more maintainable. Make rotational and antisymetric support generally usable with other settings.
