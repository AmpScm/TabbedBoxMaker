# SPDX-FileCopyrightText: 2025-present Bert Huijben
#
# SPDX-License-Identifier: GPL-3.0
"""
Changelog:
Original Tabbed Box Maker Copyright (C) 2011 Elliot White

19/12/2014 Paul Hutchison:
 - Ability to generate 6, 5, 4, 3 or 2-panel cutouts
 - Ability to also generate evenly spaced dividers within the box
   including tabbed joints to box sides and slots to slot into each other

23/06/2015 by Paul Hutchison:
 - Updated for Inkscape's 0.91 breaking change (unittouu)

v0.93 - 15/8/2016 by Paul Hutchison:
 - Added Hairline option and fixed open box height bug

v0.94 - 05/01/2017 by Paul Hutchison:
 - Added option for keying dividers into walls/floor/none

v0.95 - 2017-04-20 by Jim McBeath
 - Added optional dimples

v0.96 - 2017-04-24 by Jim McBeath
 - Refactored to make box type, tab style, and layout all orthogonal
 - Added Tab Style option to allow creating waffle-block-style tabs
 - Made open box size correct based on inner or outer dimension choice
 - Fixed a few tab bugs

v0.99 - 2020-06-01 by Paul Hutchison
 - Preparatory release with Inkscape 1.0 compatibility upgrades (further fixes to come!)
 - Removed Antisymmetric option as it's broken, kinda pointless and looks weird
 - Fixed divider issues with Rotate Symmetric
 - Made individual panels and their keyholes/slots grouped

v1.0 - 2020-06-17 by Paul Hutchison
 - Removed clearance parameter, as this was just subtracted from kerf - pointless?
 - Corrected kerf adjustments for overall box size and divider keyholes
 - Added dogbone cuts: CNC mills now supported!
 - Fix for floor/ceiling divider key issue (#17)
 - Increased max dividers to 20 (#35)

v1.1 - 2021-08-09 by Paul Hutchison
 - Fixed for current Inkscape release version 1.1 - thanks to PR from https://github.com/roastedneutrons

v1.2 - 2023-12-04 contributed by [@mausmaux](https://github.com/mausmaux) - See [PR59](https://github.com/paulh-rnd/TabbedBoxMaker/pull/59)
 - Fixed bug with unit conversion for the kerf parameter.
 - Fixed bug with dimple unit conversion.
 - Fixed boxes which have omitted sides are incorrectly drawn when using the rotationally symmetric mode.

14/05/2024 Brad Goodman:
 - Created Cardboard Box Maker from Tabbed Box Maker

v1.4 - 2025-09 (WIP) by Bert Huijben
 - Moved project to AmpScm. Updated sourcecode to be a proper python package. Added result cleanup
   from previous PRs in a cleaner way. Integrated tests from other open PRs.

"""

__version__ = "2.0.0"
