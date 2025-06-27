# EoA_DPS_meter

First approach for a DPS meter for Echoes of Angmar (vanilla Version of Lord of the Rings online - Shadows of Angmar). So far the dps parser only works for english clients only and AoE damage might cause curious output since no AoE logic has been implemented yet. Since vanilla SoA and thus EoA do not give a lot of combat logging output its hard to deal with a few things. On the other hand, it should work for group play as well since combat end is not depending on defeat messages. Thus, the combat time runs 3.5 seconds after combat but the parser safe the time of last hit and thus use this for calculation. You will notice, that when the timer stops, it set back the dps value on last hit time.

Since combat in the current version end if no hit on enemy occurs of might stop during fights like thorog as well. This is planned for future releases. 

## Usage:

- Download dpsOverlay.exe and config.ini
- Edit path to combat log files in config.ini (Windows paths: make sure "\" is changed to "/" like "C:\" to "C:/") 
- .exe and config.ini need to be in the same folder
- right click on combat log chat window in lotro and select "start logging"
- use dps_parser.exe  

## actual features
- overlay live dps parsing
- window can be placed by click and hold mouse- 
- starting on hit, ending when no new hit in log occurs after 3.5seconds
- getting total damage, duration, enemy name and dps values
- storing last 4 fights selectable via dropdown
- copy button (inactive while parsing) so copy stats to clipboars. can be easy paste with ctrl + v into e.g. lotro chat window
## to do:

- analyzing German combat logs
- remove resizing of window since this only makes sense when more features are added
- show dps by skills, thus add classes to the code
- built logic to deal with aoe dmg
- parsing heal and taken damage
- if no config.ini is found create a config.ini with most accurate path prediction 
- add two parse modes.
  - starting combat on hit and ending after no further hits occur
  - starting combat per button and end combat per button. that would make e.g. thorog fight parseable
- add optional enemy parsing like "just thorog" and maybe take into account phases in which timer pauses cause thorog is not attackable

## bugs:

- hunters heartseaker cause a stop of parsing due to long induction time. if after 3.5s no hit occurs in log, the fight is currently seen as ended. 
- fill bar filling does not scale correct to peak DPS as max
- selecting an old combat log again might cause a crash of the parser

