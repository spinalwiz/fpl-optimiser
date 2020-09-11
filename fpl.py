import sys

import pandas as pd
import json
import requests
import re
import fpl_trans as ft
import combinations
from collections import Counter
import timeit
import pickle
import numpy as np



def save_obj(obj, name):
    with open('obj/' + name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

def build_player_list():

    def calc_x_points_90(row, **kwargs):
        type = kwargs['type']
        if row.minutes == 0:
            return 0
        if row.element_type == 1:
            return row.xA90 * 3 + row.xCS * 4 - (row.xgAp90 / 3) + (row.xgAp90 / 2)
        if row.element_type == 2:
            return row[type] * 6 + row.xA90 * 3 + row.xCS * 4 - (row.xgAp90 / 3)
        if row.element_type == 3:
            return row[type] * 5 + row.xA90 * 3 + row.xCS * 1
        if row.element_type == 4:
            return row[type] * 4 + row.xA90 * 3
        return 0

    def calc_x_points(row, **kwargs):
        type = kwargs['type']
        if row.element_type == 1:
            return row.xA * 3 + row.xCS * 4 * row.team_played - (row.xgA / 3) + (row.xgA / 2)
        if row.element_type == 2:
            return row[type] * 6 + row.xA * 3 + row.xCS * 4 * row.team_played - (row.xgA / 3)
        if row.element_type == 3:
            return row[type] * 5 + row.xA * 3 + row.xCS * 1 * row.team_played
        if row.element_type == 4:
            return row[type] * 4 + row.xA * 3
        return 0

    # understats data
    under_html = requests.get('https://understat.com/league/EPL/').text
    #  player data from understat
    player_data_text = re.search(r"playersData	= JSON\.parse\(\'(.*)\'\)", under_html, re.MULTILINE).group(1)
    player_data_json = bytes(player_data_text, "utf-8").decode('unicode_escape')
    player_data = json.loads(player_data_json)

    # Swapping for new data
    df_understat = pd.DataFrame(player_data)
    df_master = pd.read_excel('match_data_aggregated.xlsx')

    df_master = df_master.merge(df_understat[['player_name', 'team_title', 'red_cards', 'games', 'position', 'yellow_cards', 'npg', 'assists', 'goals']], on='player_name', how='right')

    df_master = df_master.apply(pd.to_numeric, errors='ignore')
    # df_master.to_excel('understatout.xlsx', encoding='utf-8')

    df_master.rename(columns={"team_title": "team"}, inplace=True)
    # goals conceded data
    team_data_text = re.search(r"teamsData = JSON\.parse\(\'(.*)\'\)", under_html, re.MULTILINE).group(1)
    team_data_json = bytes(team_data_text, "utf-8").decode('unicode_escape')
    team_data_raw = json.loads(team_data_json)
    xga_data = {}
    for k, team in team_data_raw.items():
        xgA = sum(v['xGA'] for v in team['history'])
        xgAp90 = xgA / len(team['history'])
        xga_data[team['title']] = {'xgA': xgA,
                                   'xgAp90': xgAp90,
                                   'team_played': len(team['history'])}
    # df_xga = pd.DataFrame(list(xga_data.values()), index=xga_data.keys(), columns=['team_xga'])
    df_xga = pd.DataFrame(xga_data).transpose()
    #  clean sheets data
    df_cs = pd.read_excel('clean_sheets.xlsx')
    #  api data
    response_ = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
    data = response_.json()['elements']
    df_api = pd.DataFrame(data)
    df_api['player_name'] = df_api['first_name'] + ' ' + df_api['second_name']
    # df_api['team'] = df_api['team'].apply(lambda x: ft.teams_trans[x])
    df_api['now_cost'] = df_api['now_cost'] / 10
    df_api = df_api[['player_name', 'total_points', 'element_type', 'now_cost', 'minutes', 'web_name']]
    # df_api.to_excel('api_out_nov_19.xlsx')
    df_api['player_name'].replace(ft.player_trans, inplace=True)

    df_master = df_master.merge(df_cs[['team', 'xCS']], on='team', how='left')
    df_master = df_master.merge(df_api, on='player_name', how='left')
    df_master = df_master.merge(df_xga, left_on='team', right_index=True, how='left')
    #  calculated fields
    df_master['xG90'] = df_master['xG'] / df_master['minutes'] * 90
    # df_master['npxG90'] = df_master['npxG'] / df_master['minutes'] * 90
    df_master['xA90'] = df_master['xA'] / df_master['minutes'] * 90
    #  data processing
    df_master.set_index('player_name', inplace=True)
    # print(df_master.info())
    #  xP
    df_master['xPoints'] = df_master.apply(calc_x_points, type='xG', axis=1)
    df_master['xPoints'] = df_master['xPoints'] + (2 * df_master['team_played'])
    df_master['xPoints_per_mil'] = df_master['xPoints'] / df_master['now_cost']
    # df_master['xNPPoints'] = df_master.apply(calc_x_points, type='npxG', axis=1)
    # df_master['xNPPoints'] = df_master['xNPPoints'] + (2 * df_master['team_played'])
    # df_master['xNPPoints_per_mil'] = df_master['xNPPoints'] / df_master['now_cost']
    #  xPP90
    # df_master['xPoints_17'] = df_master.apply(calc_x_points_17, axis=1)
    # df_master['xPoints_per_mil_17'] = df_master['xPoints_17'] / df_master['now_cost']
    df_master['xPointsP90'] = df_master.apply(calc_x_points_90, type='xG90', axis=1)
    df_master['xPointsP90'] = df_master['xPointsP90'] + 2  # Appearance points
    df_master['xPointsP90_per_mil'] = df_master['xPointsP90'] / df_master['now_cost']
    # df_master['xNPPointsP90'] = df_master.apply(calc_x_points_90, type='npxG90', axis=1)
    # df_master['xNPPointsP90'] = df_master['xNPPointsP90'] + 2
    # df_master['xNPPointsP90_per_mil'] = df_master['xNPPointsP90'] / df_master['now_cost']
    df_master['actualP_per_mil'] = df_master['total_points'] / df_master['now_cost']
    df_master['actualP_P90_per_mil'] = (df_master['total_points'] / df_master['minutes'] * 90) / df_master['now_cost']
    df_master.sort_values(by=['xPointsP90_per_mil'], ascending=False, inplace=True)
    # df_api.to_excel('apiout.xlsx', encoding='utf-8')
    # df_master.drop(['id', 'xGBuildup', 'xGChain', 'key_passes', 'time', 'shots'], axis=1, inplace=True)
    # df_master = df_master[df_master['minutes']]
    df_master = df_master[['team', 'now_cost', 'total_points', 'games', 'minutes', 'position', 'element_type',
                           'yellow_cards', 'red_cards', 'goals', 'npg', 'xG', 'xG90', 'npg',
                           'assists', 'xA', 'xA90',
                           'xPoints', 'xPoints_per_mil', 'xPointsP90', 'xPointsP90_per_mil',
                           'actualP_per_mil', 'actualP_P90_per_mil'
                           ]]
    #Todo: can take this out now?
    # df_bargains = df_master[(df_master['now_cost'] <= 4.5) & (df_master['minutes'] < 360)]  # cheapest options for subs
    #Todo: can take this out now?
    # df_bargains['xPointsP90'] = df_bargains['xPointsP90'] * 0.01  # de-weight them
    #Todo: can take this out now?
    # df_master = df_master[df_master['minutes'] >= 360]
    # df_master = df_master.append(df_bargains) #  Taking this out temporarily to avoid duplicates. The minutes filters need to not overlap
    df_master.to_excel('out.xlsx', encoding='utf-8')
    return df_master
    # pc.df.to_sql(con=database_connection, name='1fpl', if_exists='replace') # , index_label='entity_id'

def read_player_list():
    df_master = pd.read_excel('out.xlsx')
    df_master.set_index('player_name', inplace=True)
    return df_master


class Optimiser:

    def __init__(self, df: pd.DataFrame, team_size: int, shortlist_num: int, budget: float, max_players_per_pos: list):

        # self.current_team = ['Nick Pope', 'Trent Alexander-Arnold', 'Virgil van Dijk', 'Matt Doherty', 'Aymeric Laporte',
        #         'Ismaila Sarr', 'César Azpilicueta', 'Sadio Mané', 'Richarlison', 'Andreas Pereira', 'Son Heung-Min', 'Gabriel Martinelli',
        #         'Mason Greenwood', 'Raúl Jiménez']
        self.current_team = ['Nick Pope', 'Trent Alexander-Arnold', 'Andrew Robertson', 'Romain Saiss',
                'Kevin De Bruyne', 'Mason Holgate', 'Mohamed Salah', 'Anwar El Ghazi', 'Anthony Martial', 'Mason Mount', 'Tammy Abraham',
                'Neal Maupay', 'Mason Greenwood', 'John Lundstram']
        self.budget = budget
        self.best_team = None
        self.player_list = df
        self.player_points = {}
        self.player_costs = {}
        self.player_teams = {}
        self.my_team = None
        self.team_size = team_size
        self._shortlist_num = shortlist_num
        self.possible_teams = []
        self.max_players_per_pos = max_players_per_pos
        self.num_gks = self.num_defs = self.num_mids = self.num_forwards = 0

        self.weight_players()
        # self.update_custom_prices()
        self.player_list.sort_values(by='element_type', inplace=True)
        self.player_list.reset_index(inplace=True)
        self._num_players = len(self.player_list.index)

    def update_custom_prices(self):
        price_update = {'Andrew Robertson': 6,
                        'Aaron Wan-Bissaka': 4, 'Callum Wilson': 6.3, 'Aymeric Laporte': 5.7,
                        'Raheem Sterling': 11.1,  'Raúl Jiménez': 5.6,
                        'Mohamed Salah': 13, 'Matt Doherty': 4.6}
        self.player_list.update(pd.Series(price_update, name="now_cost"))
        # print(self.player_list[self.player_list.index.isin(price_update.keys())]['now_cost'])

    def weight_players(self):
        player_weights = {'David Silva': 0.8,
                          'Ashley Young': 0.1,
                          'James Milner': 0.7,
                          'Paul Pogba': 1,
                          'Sergio Agüero': 0.9,
                          'Jamie Vardy': 1,
                          'Davinson Sánchez': 1,
                          'Joshua King': 1,
                          'Ryan Fraser': 1,
                          'Andrew Robertson': 1,
                          'Paulo Gazzaniga': 1,
                          'Willy Caballero': 1,
                          'Ederson': 0.8,
                          'Trent Alexander-Arnold': 1,
                          'Leander Dendoncker': 1,
                          'Nicolás Otamendi': 0.9,
                          'Erik Lamela': 1,
                          # 'Xherdan Shaqiri': 0.7,
                          'Gabriel Jesus': 0.5,
                          # 'Chicharito': 0.5,
                          # 'Harvey Barnes': 0.5,
                          'Dejan Lovren': 0.5,

                          # 'Leroy Sané': 0.5,
                          'Che Adams': 0.8,
                          'Emerson': 0.8,
                          'Paul Pogba': 1,
                          'Kevin De Bruyne': 1,
                          'Raheem Sterling': 0.9,
                          'Bernardo Silva': 0.8,
                          "Oleksandr Zinchenko": 0.1,
                          'Adrián': 0.1,
                          'Kurt Zouma': 0.7,
                          'Christian Pulisic': 0.9,
                          'Riyad Mahrez': 0.7,
                          'Seamus Coleman': 1,
                          'Marcos Alonso': 0.8,
                          'Shane Long': 0.2,
                          'Henrikh Mkhitaryan': 0.1,
                          'João Cancelo': 0.8,
                          'Chris Wood': 0.8,
                          'Aymeric Laporte': 1,
                          'Wes Morgan': 0.1,
                          'Isaac Success': 0.1,
                          'Kyle Walker': 0.7,
                          'Luke Shaw': 1,
                          'Eric Garcia': 0.1,
                          'Phil Jones': 0.1,
                          # 'Alex Iwobi': 0.9,
                          'Harry Maguire': 1,
                          'Diogo Dalot': 0.1,
                          'Todd Cantwell': 1,
                          'Xherdan Shaqiri': 0.1,
                          'Ilkay Gündogan': 0.9,
                          'Demarai Gray': 0.8,
                          'Wesley': 1,
                          'Mohamed Salah': 1,
                          'Callum Hudson-Odoi': 0.8,
                          'Andriy Yarmolenko': 1,
                          'Bukayo Saka': 0.85,
                          'Glenn Murray': 0.7,
                          'John Lundstram': 1,
                          'Matt Doherty': 1,
                          'Angelino': 0.1,
                          'Tammy Abraham': 1,
                          'John Stones': 0.7,
                          'Ayoze Pérez': 0.8,
                          'Willian': 0.9,
                          'Claudio Bravo': 0.1,
                          # 'Lys Mousset': 1.1,
                          'Fikayo Tomori': 0.8,
                          'Brandon Williams': 0.1,
                          'Phil Foden': 0.1,
                          'Ross Barkley': 0.9,
                          'Harvey Barnes': 0.9,
                          'Sadio Mané': 1,
                          'Nick Pope': 1.3,
                          'Christian Fuchs': 0.2,
                          'Benjamin Mendy': 0.9,
                          'Aaron Connolly': 0.5,
                          'Rúben Vinagre': 0.1,
                          'Son Heung-Min': 1,
                          'Dele Alli': 0.9,
                          'Max Kilman': 0.1

                        }
        for k, v in player_weights.items():
            self.player_list.loc[k, 'xPoints'] = self.player_list.loc[k, 'xPoints'] * v

    def prepare_optimise(self):
        # print(self.player_list['player_name'])
        # TODO: Remove or fix this properly
        self.player_list = self.player_list.drop([491, 492, 493, 494, 495, 496, 497, 498])
        # self.player_list = self.player_list[pd.notnull(self.player_list['xPoints'])]
        self.player_list['xPoints'] = self.player_list['xPoints'].apply(lambda x: 0 if np.isnan(x) else x)
        # self.player_list.to_excel("player_list.xlsx")
        self.player_costs = self.player_list['now_cost'].to_dict()
        self.player_points = self.player_list['xPoints'].to_dict()
        self.player_teams = self.player_list['team'].to_dict()
        self.player_list['my_team'] = np.where(self.player_list['player_name'].isin(self.current_team), 1, 0)
        print("Number of players in My Current Team (should be 14):")
        print(self.player_list['my_team'].sum())
        print(self.player_list.index[self.player_list['my_team'] == True].tolist())
        self.player_list['man_city_team'] = np.where(self.player_list['team'].isin(['Manchester City']), 1, 0)
        self.player_list['liverpool_team'] = np.where(self.player_list['team'].isin(['Liverpool']), 1, 0)
        self.my_team = self.player_list['my_team'].to_dict()


        # print(self.player_list[self.player_list['player_name'].isin(self.current_team)].index)
        # print(self.my_team)
        # print(self.player_list['element_type'].to_dict())
        data_for_combs = {
            'player_costs': self.player_costs,
            'player_points': self.player_points,
            'player_teams': self.player_teams,
            'budget': self.budget,
            'player_positions': self.player_list['element_type'].to_dict(),
            'names': self.player_list['player_name'].to_dict(),
            'my_team': self.my_team,
            'man_city_team': self.player_list['man_city_team'].to_dict(),
            'liverpool_team': self.player_list['liverpool_team'].to_dict()
        }
        save_obj(data_for_combs, "data")


if True:
    build_player_list()
    df_player_list = read_player_list()
    # TODO: None of these parameters are being used
    optimiser = Optimiser(df_player_list, team_size=11, shortlist_num=11, budget=82.5, max_players_per_pos=[1, 5, 5, 3])
    optimiser.prepare_optimise()

    import integer



