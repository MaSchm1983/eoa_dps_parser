# EoA_DPS_meter

First approach for a DPS meter for [Echoes of Angmar](https://www.echoesofangmar.com/) (vanilla Version of Lord of the Rings online - Shadows of Angmar). So far the dps parser only works for english clients only and AoE damage might cause curious output since no AoE logic has been implemented yet. Since vanilla SoA and thus EoA do not give a lot of combat logging output its hard to deal with a few things. On the other hand, it should work for group play as well since combat end is not depending on defeat messages. Thus, the combat time runs 3.5 seconds after combat but the parser safe the time of last hit and thus use this for calculation. You will notice, that when the timer stops, it set back the dps value on last hit time.


## Discription

What does dpsOverlay.exe do? Basically only show what you can see already ingame in your combat chat window, but as you know, so many numbers pass and you cannot find what you're searching for. The dpsOverlay.exe just reads this file and analysing anything about damage for you and present it in a more handy form in real-time. Its for all who are interested in maybe figure out what skills are useable and which not. Even in vanilla lotro some kind of "rotation" make sense to speed up things. You don't have enough time for a 3h carn dum run? Well our kin does it in about 1h30min since everyone does just a good amount of damage :-)

#### How does dpsOverlay.exe work?

dpsOverlay.exe is a standalone version of a coded analysing overlay tool with PyQt5. Once you started the .exe you'll get a partwise transparent little window you can move whereever you want on your screen. Per default you can just start damaging and will see automatic DPS values, total damage, biggest hit and biggest hitting skill (all for current) fight. You can also review past fight within the "select combat" dropdown menu. (**Don't forget to start chat logging in LoTro!!** No combat log, no combat, it's that easy ;-) ). It started cause by default your in the "Parse on hit" logic. The other option is the "Parse on start/stop", you can easy switch between both parsing methods between fights by clicking the button. 

Difference between both parsing methods:

- Parse on hit (suggested for singleplayer usage, non-aoe situations for just chill parsing): 
  - DPS parsing starts as the name may suggest on the first hit. You'll see now the name of the enemy, DPS, total damage, duration and biggist hit.
  - DPS parsing stops automatically when no new entry in combat_log occurs for 3.5 seconds.
  - You'll notice the timer continues although the fight is over, but it will stop after this 3.5 seconds and set back to the real time, the fight ended. It also shows the DPS 3.5. seconds before the timer stops that you have the right duration of the fight. (The 3.5 seconds were a first guess for a good time for the logic to not stop random between fights and not go on on pulling next enemy, can be adapted due to testing and experiencing)
  - You may no ask "why not use the "you defated xyz...." trigger? Because of two reasons this runs fast into few problems
    - First, sometime you hit the enemy even if he is already dead (think on hunter's swift bow second hit or champ's brutal strike hitting three time)
    - Second, if you're playing in group, you won't get any defeated triggers when you don't land the killing blow yourself and thus the timer will run....and run ... and run....
  - Of timer stops, you can just start to hit next enemy and timer will store the current fight to the "select fight" history and restart. 
  - Problems with this routine:
    - Heartseeker: Heartseeker seem the only skill which has a way too long induction time, that the timer may stop during heartseekers induction
    - Getting stunned. If you're getting stunned, the timer will most likley also stop since most stuns lock your attacks for more than 3.5 seconds. 

To solve the issues, I added a new parsing logic called "Parsing on start/stop"

- Parse on start/stop (suggested for group content, boss encounters and aoe situations)
  - Once you've clicked the button to switch to this logic, you'll notice a "start" button. 
  - DPS starting starts on first hit after you started the parsing manually. So e.g. before you do the Thorog encounter, you idealy press the start button bevor Drugoth gets active and parsing starts on your first hit on Drugoth. As long as the button is green, all combat is parsed.
  - For now you need to end the parsing manually. Idealy you press the start button again (which will transfer into a "stop" button after you started the fight)
  - After pressing stop, the parser will also "jump a bit back in time" to the last hit (internal timer will store the exact time when this happens). I did this to at least border the fight on the actual fight and not on like wasting time while eating buffood at start or if you forget to instantly stop the fight after the boss/enemy is dead.
  - You can now see the dps on the total combat and you can see the dps on all enemys you've fought during the combat. So you can see your DPS in e.g. Thorog as well. Since the parser stores the exakt time on hitting certain enemies, you will get the pure DPS you did on Thorog not influenced by phases like the phases he periodically fly's to the top to greet the burglars. 
  - You can also see any aoe dmg here. However it is not possible to differentiate between dps on enemys with same names. So e.g. at Zaudru you just can see the dps on all spiderlings (as burglar, it is basically the same as on spiderling xD). But I think thats even better since that is the more interested thing.

If you just wanna track some damage during questing etc. I recommend the first "parse on hit" since its more chill. For any other things I suggest the "parse on start/stop" especially during group conents.

## Usage (short for lazy dudes):

- Download dpsOverlay.exe and config.ini
- Edit path to combat log files in config.ini (Windows paths: make sure "\\" is changed to "/" like "C:\\users\\" to "C:/users/"  and so on) 
- .exe and config.ini need to be in the same folder
- start the exe
- Ingame: right click on combat log chat window and select "Chat logging" ==> "start logging"


## to do / future plans:

- analyzing German combat logs
- show dps by skills, thus add classes to the code
- parsing heal and taken damage
- if no config.ini is found create a config.ini with most accurate path prediction 
- Add dps per skill to see where most dps came from
- Add dps over time small diagram
- Add all aoe skills to differ between single target and aoe (need to be thought about a bit in depth)
- cleaning code

## bugs:

- hunters heartseaker cause a stop of parsing due to long induction time. if after 3.5s no hit occurs in log, the fight is currently seen as ended. (Hard to fix, but dealt with new start/stop parsing logic)
- fill bar filling does not scale correct to peak DPS as max (should now work)
- selecting an old combat log again might cause a crash of the parser (should now work)
- some struggleson special characters like in Tarkrîp need to be fixed with unicodedata or anything else
- loremaster wizard fire doesn't count ==> You hit the Snow-lurker for 51 points of Light damage to Morale. But routine tracks for skill name before "for" and this dosen't occur here. Thus I need to set group3 (DMG) fix on searching between "for" and "points"
- LM and cappy pets: Tracking of their damage does currently not work. 

