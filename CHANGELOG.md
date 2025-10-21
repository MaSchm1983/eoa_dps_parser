# Changelog

All notable changes to the DPS parser for Echos of Angmar will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).



### Beta [0.9.8.0] - 2025-10-21
- reworked parsing logic, now can handle with dot damage, pets, spirits from FM, detection of any sorts of auto attacks
- what does the parser track?
  - damage:
    - direkt damage via skills
    - dot damage
    - pet damage
    - autoattacks
  - heal:
    - all sort of healing, including heal from fellowship manouvers
    - all sort of power gain or sharing including power gain from fellowship manouvers
  - damage taken:
    - direkt damage taken via skill damage
    - dot damage taken
    - also split damage into different damage types and set all damage into relation
- store multiple enemies for one fight (note: if there are enemies of the same name, its impossible to split them during the same fight)
- store up to 10 fights in "select combat" dropdown
- rework feedback bar to blink "on event"
- remove dps as a live tracked stat since I feel its not very impactful in vanilla SoA due to low damage and dps breaks during fights. However, copying the stats to clipboard will also give the DPS

**Not yet implemented**:
- automatic start of tracking after starting the .exe
- automatic stop options after "XX seconds" (just added the checkbox, but has no function so far)
- analyze combat button has no effect so far. will be implemented for release. plans for that:
  - add a small window below the current tracker with analyzing the stats more in detail like splitting dmg into different skills and their relative share of the total damage
  - maybe adding a small logic to detect critical hits (lvl 50 only, since that will be remote data and thus calculated from e.g. percentile values of median damage)
- information/reminder to start chat logging of combat chat ingame ;D
- setting menue to maybe add content of config.ini (path to combat log, pets etc.) into the programms settings
- support for german client

  

## Beta [0.9.2.1] - 2025-06-30

### bugfixes:
- fixed a minor back where max hit and max hitting skill does not reset properly at the "Parse on hit mode"
- Fixed a big issue with pets in general. LM and cappy pets should now get their damage tracked and added to the players damage.
- Fixed a bug with some skills not being tracked since they don't have a skill name (e.g. wizards fire or burning embers dot damage). This now counts as "no specific skill" for a first approach

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
