#Fantasy Premier League: Team Selector and Optimizer

##What is This?
FPL Optimizer selects the best possible fantasy football team by using an expected points model to generate expected points (xP) for every player in [Fantasy Premier League (FPL)](https://fantasy.premierleague.com/) and then using a Linear Programming model to select the best possible combination of players given a limited budget (and other constraints). 
 
 ### How Does it Work?
 To generate expected points it uses:
 * Expected Points
 * Expected Assists
 * Expected Clean Sheets
 * Expected Goals Conceded
 * Appearance Points
 
 It doesn't take into account:
 * Bonus Points (but let me know if you know of a good way to model this)
 * Fixture Difficulty (coming soon)
 
 From this, it can generate an expected points value per player per match and from there expected value.
 
 The Liner Programming Model is then able to select a team (or changes to a team) based on the FPL constraints for player positions (e.g. no more than 3 Forwards) and a budget (e.g. 100 million).
 
 ###Features
 * Updates player data after every match
 * Pick a brand new team or optimise a current team
 * Restrict the number of changes (e.g. find the best two changes to my current team)
 * Store multiple teams (in case you play in multiple leagues)
 * Will only pick valid FPL teams
 * Record player purchase prices so that it optimises based on the price you paid, not the current price 
 * Can toggle whether to allow changes to subs or not (who wants to waste transfers on subs)
 * Add weightings to individual players allowing you to exclude (or preference) certain players
 * Recommends who to captain
 * Recommends subs
 
 ##Requirements
 Requires Python 3.5 or above. 
 
 In Ubuntu, Mint and Debian you can install Python 3 like this:

`$ sudo apt-get install python3 python3-pip`

For other Linux flavors, macOS and Windows, packages are available at

https://www.python.org/getit/

##Quick Start
Clone the repository 

`git clone https://github.com/spinalwiz/fpl-optimiser.git`

From within the directory, install the project requirements. 
 
`pip install -r requirements.txt`

Update data and build the player list. The first run will take a LONG time as it needs to download data for every match 
(This needs to be run once after every round of matches)

`python builder_player_list.py`

Then run the optimiser with:
`python fpl.py`




##Notes
fpl.py contains settings, defaults are:
`budget=96, limit_changes=False, limit_sub_changes=False, num_changes=2`

(The budget is set to 96 assuming you will select a 4m sub-keeper). Limit_changes = False means it will pick a brand new team. 

player_weights.py allows you to weight certain players based on their likelihood to play/get minutes. E.g. you could set Raheem Sterling to 0.9 if you think he has a chance of not playing/getting full minutes. You can set this to 0 to exclude players completely (or a large number to ensure they get picked)

my_team.py lets you store your current team (the team selection needs to be updated in fpl.py)

fpl_trans.py is for translating player's full names to their FPL short names (e.g. Bruno Miguel Borges Fernandes to Bruno Fernandes)

in get_understat_data.py you can edit the lookback period

##To Do
* Make all settings adjustable through command line arguments (instead of needing to edit the source files)
* Make loading previous season data more user friendly
* Add match difficulty and bonus points model
* Add 3 players per team constraint to all teams (currently only added for Liverpool and Man City which has been sufficient so far...)

##Technology
Python
Pandas and Numpy
Pulp




 