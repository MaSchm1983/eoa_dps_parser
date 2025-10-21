# EoA: ParsingStats

ParsingStats is an overlay for [Echoes of Angmar](https://www.echoesofangmar.com/) (vanilla Version of Lord of the Rings online - Shadows of Angmar) that analyse your combat log in real-time and thus track your stats of damaging skills, healing (including power) and damage taken. So far the parser only works for english clients only. Note: **the parsingStats.exe does not access any illegal server stats, it justs load the textfile, where your ingame chat output of the combat chat is logged** 

## Installation:

- Download the [EoA-parsingStats.exe](https://github.com/MaSchm1983/eoa_dps_parser/releases/tag/beta-v0.9.8.0) 
- Download the [config.ini](https://github.com/MaSchm1983/eoa_dps_parser/blob/main/config.ini)
- Edit <CMBT_LOG_DIR> in **config.ini**
- (Optional: edit the  <NAMES> of your pets or add the names of your pets if you rename them ingame, otherwise pet damage/heal cannot not be tracked) 
- The **config.ini** needs to be in the same folder as your **EoA-parsingStats.exe** 
- Start **EoA-parsingStats.exe**, tab to EoA, rightclick the "Combat Chat" and "Start Chatlogging". 
- Press the start button on the parsingStats overlay. Parsing will start once an event happens
- For now, you need to stop the fight by pressing the stop button. And restart it again (will trying to get some Qol here in release version)
- up to 10 fights should be stored in the "select combat" dropdown menu. 

## to do / future plans:

- analyzing German combat logs
- add an "analyse combat" window with details about all attacks and their distribution to the total damage
- some setting options as Qol and get rid of the config.ini
- Qol options for starting and stopping a fight.



