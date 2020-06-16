import re
import json
import sys
import os.path
from os import path

import numpy as np
import pandas as pd
import requests
import fpl_trans

# from pyquery import PyQuery as pq
# from bs4 import BeautifulSoup

teams = fpl_trans.teams
# teams = ['Fulham', 'Huddersfield', 'Cardiff']
# teams = ['Manchester United', 'Bournemouth', 'Brighton', 'Leicester']
# teams = ['Arsenal', 'Burnley', 'Everton', 'Chelsea']
# teams = ['Tottenham', 'Watford', 'West Ham', 'Wolverhampton Wanderers']
# teams = ['Liverpool']
saved_match_ids = []

if path.exists("match_data_raw.xlsx"):
    df_match_data_saved = pd.read_excel('match_data_raw.xlsx')
    saved_match_ids = df_match_data_saved['match_id'].unique().tolist()


# print(saved_match_ids)
# sys.exit()


def get_match_ids():
    match_ids = []
    for team in teams:
        raw_html = requests.get(f"https://understat.com/team/{team}/2019").text
        # print(raw_html)

        # Only works if datesData is first on page. Note sure why
        dates_data_text = re.search(r"JSON\.parse\(\'(.*)\'\)", raw_html, re.MULTILINE).group(1)
        dates_data_json = bytes(dates_data_text, "utf-8").decode('unicode_escape')
        dates_data = json.loads(dates_data_json)
        df_matches = pd.DataFrame(dates_data)
        df_matches = df_matches.apply(pd.to_numeric, errors='ignore')
        df_matches = df_matches[(df_matches['isResult'] == True) & (df_matches['side'] == 'h')]
        match_ids = match_ids + df_matches['id'].tolist()

    # filter out saved match_ids so only fetch new ones
    # print(match_ids)
    match_ids = [x for x in match_ids if x not in saved_match_ids]
    print(F"Fetching {len(match_ids)} matches")
    return match_ids


def get_match_data(match_ids):
    match_data = []
    for match_id in match_ids:

        game_html = requests.get(f"https://understat.com/match/{match_id}").text
        roster_data_text = re.search(r"rostersData.+= JSON\.parse\(\'(.*)\'\)", game_html, re.MULTILINE).group(1)
        roster_data_json = bytes(roster_data_text, "utf-8").decode('unicode_escape')
        roster_data = json.loads(roster_data_json)

        for k, v in roster_data['h'].items():
            v['match_id'] = match_id
            match_data.append(v)

        for k, v in roster_data['a'].items():
            v['match_id'] = match_id
            match_data.append(v)

    return match_data


# match_ids = []
match_ids = get_match_ids()
match_data = get_match_data(match_ids)
df_match_data = pd.DataFrame(match_data)
df_match_data = df_match_data.apply(pd.to_numeric, errors='ignore')
if path.exists("match_data_raw.xlsx"):
    #  Todo: Is this adding an extra index column?
    df_match_data = df_match_data_saved.append(df_match_data)
df_match_data.to_excel('match_data_raw.xlsx')

# Drop players that aren't in a current premier league team
# todo: not necessary as this gets dropped in the merge in fpl
df_match_data = df_match_data[df_match_data['team_id'].isin(fpl_trans.team_ids.keys())]

#  translate team_ids to team names
# todo: not necessary as this gets dropped in the merge in fpl
df_match_data['team'] = df_match_data['team_id'].apply(lambda team_id: fpl_trans.team_ids[team_id])

#  Filter games where players have played less than 45 minutes
df_match_data = df_match_data[df_match_data['time'] >= 45]

df_match_data.sort_values(by=['player', 'match_id'], ascending=[True, False], inplace=True)
df_match_data['cumulative_count'] = df_match_data.groupby('player').cumcount()

# Only include players last 10 games (count start from 0)
df_match_data = df_match_data[df_match_data['cumulative_count'] < 8]

df_match_data.to_excel('match_data_processed.xlsx')

df_out = pd.pivot_table(df_match_data, values=['xG', 'xA', 'time'],
                        index=['player'],
                        fill_value=0, aggfunc=np.sum, dropna=True, )
# print(df_out)
# df_out = df_out.merge(df_match_data[['player', 'team']], on='player', how='left')
# print(df_out)
# print(df_out.info())

df_out.index.names = ['player_name']
# df_out.rename(index={"player": "player_name"}, inplace=True, errors='raise')

df_out.to_excel('match_data_aggregated.xlsx')
print('Done')
