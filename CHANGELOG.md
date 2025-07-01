# Changelog

All notable changes to the DPS parser for Echos of Angmar will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Beta [0.9.2] - 2025-06-30

## Added
- Added a complete new combat parsing logic. You know can chose between "Parse on hit" and "Parse on Start/Stop". Explaination of the exact parsing algorithm can be found in the [README](README.md#discription).
- for new start/stop manual parsing: Added new dropdown to show "Total combat" and specific enemies. Note: vanilla lotro combat log only allows to distinguish between enemies by name. Thus you cannot see every single mob in AoE situations only all of those enemies grouped by a name. However, this logic allows to track DPS just on a boss. For more detailed information, see [README](README.md).
- added parsing of "biggest hit"
- implemented skills to DPS matrices for further plans to show DPS per skills to figure out rotation and where the damage came from.
- rebuild global variables and put them into config.py to clean up code a bit
### Fixed 
- few minor bugs, no more crashes should occur 

## Beta [0.9.1] - 2025-06-28
### Added

- rework on stop fight logic to make it independent from defeated reports and thus usabele in group play as well. However, how to deal with group play and multiple target (and thus AoE) has still to be figured out
- button to copy damage on enemy for duration and resulting dps to clipboard
- changes the standalone exe to dpsOverlay.exe
  
### Fixed

- Minor bug fixes
- cleaned few geometric dependencies

## Beta [0.9.0] - 2025-06-20
### Added
- Initial beta release
