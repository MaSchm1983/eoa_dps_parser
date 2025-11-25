# EoA: ParsingStats

ParsingStats is an overlay for [Echoes of Angmar](https://www.echoesofangmar.com/) (vanilla Version of Lord of the Rings online - Shadows of Angmar) that analyse your combat log in real-time and thus track your stats of damaging skills, healing (including power) and damage taken. So far the parser only works for english clients only. Note: **the parsingStats.exe does not access any illegal server stats, it justs load the textfile, where your ingame chat output of the combat chat is logged** 

## Installation:

- Download the [EoAparsingOverlay.exe](https://github.com/MaSchm1983/eoa_dps_parser/releases/download/beta-v0.9.9/EoAparsingOverlay.exe) 
- Download the [config.ini](https://github.com/MaSchm1983/eoa_dps_parser/releases/download/beta-v0.9.9/config.ini)
- Edit <CMBT_LOG_DIR> in **config.ini**
- (Optional: edit the  <NAMES> of your pets or add the names of your pets if you rename them ingame, otherwise pet damage/heal cannot not be tracked) 
- The **config.ini** needs to be in the same folder as your **EoAparsingOverlay.exe** 
- Start **EoAparsingOverlay.exe**, tab to EoA, rightclick the "Combat Chat" and "Start Chatlogging". 
- Parsing will start automatically (if you entered your path to the folder with the combat logs correctly)
- by default, checkbox "stop fight after 30s" is marked. This will stop the current fight and autmatically start a new log session with next hit. you can toggle that off, parsing will than run until you press the stop button manually. 
- **_Note:_** The overlay will only work as an overlay, if you play EoA in any kind of windowed mode. If you play full screen it also works but not as overlay, it will run in the background. Working on windows layering overtaken by game GUI need .dll coding and I want to keep it simple and not using any data from your computer for that code

## License

This project is licensed under the MIT License – see the [LICENSE](https://github.com/MaSchm1983/EoAparsingOverlay/blob/main/LICENSE) file for details.









