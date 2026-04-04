# EoA: ParsingStats

ParsingStats is an overlay for [Echoes of Angmar](https://www.echoesofangmar.com/) (vanilla Version of Lord of the Rings online - Shadows of Angmar) that analyse your combat log in real-time and thus track your stats of damaging skills, healing (including power) and damage taken. So far the parser works for english and german clients only. French clients are not supported at the moment, but french integration might be added soon. Russian and chinese will be to much work and there are no further plans to add thise location as well.
Note: **the EoAparsingOverlay.exe does not access any illegal server stats, it just a real-time analyzing of your combat log output** 

## Installation:

- Download the [EoAparsingOverlay.exe](https://github.com/MaSchm1983/eoa_dps_parser/releases/download/beta-v0.9.9/EoAparsingOverlay.exe) 
- Start the **EoAparsingOverlay.exe**
- Press **Settings** and select the folder where EoA saves your chat logs (typically it is in users ==> documents ==> the lord of the rings online)
- Optional: Most of the default names of pets, even all names of Captain pets renamed by using certain armaments should be covered. However, if you have some specific pet names (renamed ingame with /pet rename <name>), you need to add the names using the **Settings** menu. You can manage your pet names here. **Otherwise stats from custom pet names cannot be tracked!!**
- Ingame: Right click the combat chat and press "Start logging" otherwise there will be no update to any logs and thus no tracking.
- Parsing should start automatically now
- by default, checkbox "auto stop combat after 30s" is marked. This will stop the current fight if after 30s no event like hitting an enemy or taking damage occurs. Once the fight stopped, the next event will automatically restart a new fight and thus next parsing event. You can toggle that checkbox off, parsing will than run until you press the stop button by yourself.
- **_Note:_** The overlay will only work as an overlay, if you play EoA in any kind of windowed mode. If you play full screen it also works but not as overlay, it will run in the background. Working on windows layering overtaken by game GUI would need some .dll coding and I want to keep it simple and not using any data from your computer for that tool.

## License

This project is licensed under the MIT License – see the [LICENSE](https://github.com/MaSchm1983/EoAparsingOverlay/blob/main/LICENSE) file for details.









