# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Modern Python packaging with pyproject.toml
- Command-line interface for standalone usage
- Comprehensive test suite with pytest
- Code quality tools (black, flake8, mypy)
- Pre-commit hooks for development
- GitHub Actions CI with multi-Python version testing
- Development documentation and contributing guidelines

### Changed
- Modernized project structure following Python best practices
- Improved CI/CD pipeline with better caching and multi-version support
- Enhanced README with installation and development instructions

### Developer Notes
- This version maintains full backward compatibility
- All existing Inkscape extension functionality preserved
- Legacy test runner still available alongside modern pytest

## [1.2.0] - 2023-12-04

### Fixed
- Bug with unit conversion for the kerf parameter
- Bug with dimple unit conversion  
- Boxes which have omitted sides are incorrectly drawn when using the rotationally symmetric mode

### Contributors
- [@mausmaux](https://github.com/mausmaux) - [PR59](https://github.com/paulh-rnd/TabbedBoxMaker/pull/59)

## [1.1.0] - 2021-08-09

### Fixed
- Compatibility with Inkscape version 1.1

### Contributors
- [@roastedneutrons](https://github.com/roastedneutrons)

## [1.0.0] - 2020-06-17

### Added
- Dogbone cuts support for CNC mills
- Full Inkscape 1.0 compatibility

### Changed
- Removed clearance parameter (was just subtracted from kerf)
- Corrected kerf adjustments for overall box size and divider keyholes

### Fixed
- Floor/ceiling divider key issue (#17)
- Increased max dividers to 20 (#35)

## [0.99.0] - 2020-06-01

### Added
- Inkscape 1.0 compatibility upgrades
- Individual panels and their keyholes/slots are now grouped

### Removed
- Antisymmetric option (was broken and pointless)

### Fixed
- Divider issues with Rotate Symmetric

## [0.96.0] - 2017-04-24

### Added
- Tab Style option for waffle-block-style tabs
- Orthogonal box type, tab style, and layout options

### Changed
- Open box size correct based on inner or outer dimension choice

### Fixed
- Various tab bugs

### Contributors
- Jim McBeath

## [0.95.0] - 2017-04-20

### Added
- Optional dimples on tabs

### Contributors
- Jim McBeath

## [0.94.0] - 2017-01-04

### Added
- Divider keying options

### Contributors
- Paul Hutchison

## [0.93a] - 2015-06-23

### Added
- Hairline line thickness option for Epilog lasers

## [0.93.0] - 2015-09-21

### Changed
- Updated versioning to match original author's v0.91 plus additions

## [0.87.0] - 2015-07-28

### Added
- Schroff enclosure add-on

### Contributors
- John Slee

## [0.86a] - 2015-06-23

### Fixed
- Compatibility with Inkscape 0.91

## [0.86.0] - 2014-12-19

### Added
- Different box types (6, 5, 4, 3, or 2-panel cutouts)
- Evenly spaced dividers within the box
- Tabbed joints to box sides and slots for dividers

### Contributors
- Paul Hutchison

## [0.8.0] - 2011-10-26

### Added
- Basic input checking

## [0.7.0] - 2011-10-24

### Added
- First public release

## [0.5.0] - 2011-10-09

### Added
- Initial beta version

### Contributors
- Elliot White (original author)
