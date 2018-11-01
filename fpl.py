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

    def calc_x_points_17(row):
        if row.minutes == 0:
            return 0
        if row.element_type == 1:
            return row.xA90_17 * 3 + row.xCS * 4
        if row.element_type == 2:
            return row.npxG90_17 * 6 + row.xA90_17 * 3 + row.xCS * 4
        if row.element_type == 3:
            return row.npxG90_17 * 5 + row.xA90_17 * 3 + row.xCS * 1
        if row.element_type == 4:
            return row.npxG90_17 * 4 + row.xA90_17 * 3
        return 0

    # understats data
    under_html = requests.get('https://understat.com/league/EPL').text
    #  player data
    player_data_text = re.search(r"playersData	= JSON\.parse\(\'(.*)\'\)", under_html, re.MULTILINE).group(1)
    player_data_json = bytes(player_data_text, "utf-8").decode('unicode_escape')
    player_data = json.loads(player_data_json)
    df_master = pd.DataFrame(player_data)
    df_master = df_master.apply(pd.to_numeric, errors='ignore')
    # print(df_master.info())
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
    df_cs = pd.read_csv('clean_sheets.csv')
    #  api data
    response_ = requests.get('https://fantasy.premierleague.com/drf/bootstrap-static')
    data = response_.json()['elements']
    df_api = pd.DataFrame(data)
    df_api['player_name'] = df_api['first_name'] + ' ' + df_api['second_name']
    df_api['team'] = df_api['team'].apply(lambda x: ft.teams_trans[x])
    df_api['now_cost'] = df_api['now_cost'] / 10
    df_api = df_api[['player_name', 'total_points', 'element_type', 'now_cost', 'minutes']]
    df_api['player_name'].replace(ft.player_trans, inplace=True)
    # print(df_api.head())
    # 2017 data
    # df_csv17 = pd.read_json('playersdata17_18.json', encoding='utf-8')
    # df_csv17 = df_csv17[['player', 'npxG90', 'xA90', 'min']]
    # df_csv17.rename(index=str, columns={"npxG90": "npxG90_17", "xA90": "xA90_17", 'min': 'min_17'}, inplace=True)
    #  merges
    # df_master = df_master.merge(df_csv17, on='player')
    df_master = df_master.merge(df_cs[['team', 'xCS']], on='team', how='left')
    df_master = df_master.merge(df_api, on='player_name', how='left')
    df_master = df_master.merge(df_xga, left_on='team', right_index=True, how='left')
    #  calculated fields
    df_master['xG90'] = df_master['xG'] / df_master['minutes'] * 90
    df_master['npxG90'] = df_master['npxG'] / df_master['minutes'] * 90
    df_master['xA90'] = df_master['xA'] / df_master['minutes'] * 90
    #  data processing
    df_master.set_index('player_name', inplace=True)
    # print(df_master.info())
    #  xP
    df_master['xPoints'] = df_master.apply(calc_x_points, type='xG', axis=1)
    df_master['xPoints'] = df_master['xPoints'] + (2 * df_master['team_played'])
    df_master['xPoints_per_mil'] = df_master['xPoints'] / df_master['now_cost']
    df_master['xNPPoints'] = df_master.apply(calc_x_points, type='npxG', axis=1)
    df_master['xNPPoints'] = df_master['xNPPoints'] + (2 * df_master['team_played'])
    df_master['xNPPoints_per_mil'] = df_master['xNPPoints'] / df_master['now_cost']
    #  xPP90
    # df_master['xPoints_17'] = df_master.apply(calc_x_points_17, axis=1)
    # df_master['xPoints_per_mil_17'] = df_master['xPoints_17'] / df_master['now_cost']
    df_master['xPointsP90'] = df_master.apply(calc_x_points_90, type='xG90', axis=1)
    df_master['xPointsP90'] = df_master['xPointsP90'] + 2  # Appearance points
    df_master['xPointsP90_per_mil'] = df_master['xPointsP90'] / df_master['now_cost']
    df_master['xNPPointsP90'] = df_master.apply(calc_x_points_90, type='npxG90', axis=1)
    df_master['xNPPointsP90'] = df_master['xNPPointsP90'] + 2
    df_master['xNPPointsP90_per_mil'] = df_master['xPointsP90'] / df_master['now_cost']
    df_master['actualP_per_mil'] = df_master['total_points'] / df_master['now_cost']
    df_master['actualP_P90_per_mil'] = (df_master['total_points'] / df_master['minutes'] * 90) / df_master['now_cost']
    df_master.sort_values(by=['xPointsP90_per_mil'], ascending=False, inplace=True)
    # df_api.to_excel('apiout.xlsx', encoding='utf-8')
    df_master.drop(['id', 'xGBuildup', 'xGChain', 'key_passes', 'time', 'shots'], axis=1, inplace=True)
    # df_master = df_master[df_master['minutes']]
    df_master = df_master[['team', 'now_cost', 'total_points', 'games', 'minutes', 'position', 'element_type',
                           'yellow_cards', 'red_cards', 'goals', 'npg', 'xG', 'xG90', 'npg', 'npxG', 'npxG90',
                           'assists', 'xA', 'xA90',
                           'xPoints', 'xPoints_per_mil', 'xPointsP90', 'xPointsP90_per_mil',
                           'actualP_per_mil', 'actualP_P90_per_mil'
                           ]]
    df_bargains = df_master[(df_master['now_cost'] <= 4.5) & (df_master['minutes'] < 360)]  # cheapest options for subs
    df_bargains['xPointsP90'] = df_bargains['xPointsP90'] * 0.01  # de-weight them
    df_master = df_master[df_master['minutes'] >= 450]
    df_master = df_master.append(df_bargains)
    df_master.to_excel('out.xlsx', encoding='utf-8')
    return df_master
    # pc.df.to_sql(con=database_connection, name='1fpl', if_exists='replace') # , index_label='entity_id'


def read_player_list():
    df_master = pd.read_excel('out.xlsx')
    df_master.set_index('player_name', inplace=True)
    return df_master


class Optimiser:

    def __init__(self, df: pd.DataFrame, team_size: int, shortlist_num: int, budget: float, max_players_per_pos: list):
        self.budget = budget
        self.best_team = None
        self.player_list = df
        self.player_points = {}
        self.player_costs = {}
        self.player_teams = {}
        self.team_size = team_size
        self._shortlist_num = shortlist_num
        self.possible_teams = []
        self.max_players_per_pos = max_players_per_pos
        self.num_gks = self.num_defs = self.num_mids = self.num_forwards = 0

        self.weight_players()
        self.update_custom_prices()
        self.player_list.sort_values(by='element_type', inplace=True)
        self.player_list.reset_index(inplace=True)
        # self.exclude_dominated()
        # self.filter_to_shortlist()
        self._num_players = len(self.player_list.index)
        print("Number of players to choose from = {}".format(self._num_players))

    def exclude_dominated(self):
        self.player_list['remove'] = self.player_list.apply(self.filter_dominated, axis=1)
        self.player_list = self.player_list[self.player_list['remove'] == False]
        print(len(self.player_list.index))

    def update_custom_prices(self):
        price_update = {'Benjamin Mendy': 6, 'Andrew Robertson': 6, 'Richarlison': 6.7,
                        'Aaron Wan-Bissaka': 4, 'Callum Wilson': 6.3,
                        'Raheem Sterling': 11.1, 'Eden Hazard': 11.3, 'Raúl Jiménez': 5.6,
                        'Danny Ings': 5.6, 'Matt Doherty': 4.6}
        self.player_list.update(pd.Series(price_update, name="now_cost"))
        print(self.player_list[self.player_list.index.isin(price_update.keys())]['now_cost'])

    def weight_players(self):
        player_weights = {'David Silva': 0.80,
                          'James Milner': 0.7,
                          'Paul Pogba': 0.9,
                          'Sergio Agüero': 0.85,
                          'Jamie Vardy': 0.85,
                          'Josh Murphy': 0.80,
                          'David Brooks': 0.80,
                          'Davinson Sánchez': 0.8,
                          'Callum Paterson': 0.8
                        }
        for k, v in player_weights.items():
            self.player_list.loc[k, 'xPointsP90'] = self.player_list.loc[k, 'xPointsP90'] * v

    def filter_dominated(self, row):
        if(len(self.player_list[(row.xPointsP90 < self.player_list['xPointsP90']) &
                                (row.now_cost > self.player_list['now_cost']) &
                                (row.element_type == self.player_list['element_type'])
                                ].index) >= self.max_players_per_pos[int(row.element_type) - 1]):
            return True
        else:
            return False

    # @staticmethod
    # def print_team():
    #     print(team.players["player_name"].values)
    #     print("Your team costs: £{}m".format(team.players['now_cost'].sum()))
    #     print("Goalkeepers: {}, Defenders: {}, Midfielders: {}, Forwards: {} ".format(
    #         len(team.players[team.players['element_type'] == 1].index),
    #         len(team.players[team.players['element_type'] == 2].index),
    #         len(team.players[team.players['element_type'] == 3].index),
    #         len(team.players[team.players['element_type'] == 4].index))
    #     )

    #  TODO: Convert to loop
    def filter_to_shortlist(self):
        num = self._shortlist_num

        self.player_list.sort_values('xPointsP90', ascending=False, inplace=True)
        # Efficiency
        goalkeepers = list(self.player_list[self.player_list.element_type == 1].iloc[:5, :]['player_name'])
        defenders = list(self.player_list[self.player_list.element_type == 2].iloc[:num, :]['player_name'])
        midfielders = list(self.player_list[self.player_list.element_type == 3].iloc[:num, :]['player_name'])
        forwards = list(self.player_list[self.player_list.element_type == 4].iloc[:num, :]['player_name'])

        # Total Points
        self.player_list.sort_values('xPoints', ascending=False, inplace=True)
        goalkeepers += list(self.player_list[self.player_list.element_type == 1].iloc[:5, :]['player_name'])
        defenders += list(self.player_list[self.player_list.element_type == 2].iloc[:num, :]['player_name'])
        midfielders += list(self.player_list[self.player_list.element_type == 3].iloc[:num, :]['player_name'])
        forwards += list(self.player_list[self.player_list.element_type == 4].iloc[:num, :]['player_name'])

        goalkeepers = list(set(goalkeepers))
        defenders = list(set(defenders))
        midfielders = list(set(midfielders))
        forwards = list(set(forwards))

        #  TODO move this out as makes this dependant on shortlisting
        self.num_gks = len(goalkeepers)
        self.num_defs = len(defenders)
        self.num_mids = len(midfielders)
        self.num_forwards = len(forwards)

        players = goalkeepers + defenders + midfielders + forwards
        self.player_list = self.player_list[self.player_list.player_name.isin(players)]

    def prepare_optimise(self):
        max_gks, max_defs, max_mids, max_fws = self.max_players_per_pos
        self.k_mins = [0] * self.team_size
        self.k_mins[1:6] = [self.num_gks] * 5
        self.k_mins[6:10] = [self.num_gks + self.num_defs] * 5
        self.k_mins[10] = self.num_gks + self.num_defs + self.num_mids
        # self.k_mins[max_gks: max_gks + max_defs] = [self.num_gks] * max_defs
        # self.k_mins[max_gks + max_defs:max_gks + max_defs + max_mids] = [self.num_gks + self.num_defs] * max_mids
        # self.k_mins[max_gks + max_defs + max_mids + max_fws] = [self.num_gks + self.num_defs + self.num_mids] * max_fws
        self.k_maxs = [0] * self.team_size
        self.k_maxs[0] = self.num_gks - 1
        self.k_maxs[1:4] = [self.num_gks + self.num_defs - 1] * 3
        self.k_maxs[3:8] = [self.num_gks + self.num_defs + self.num_mids - 1] * 5
        self.k_maxs[8:11] = [self.num_gks + self.num_defs + self.num_mids + self.num_forwards - 1] * 3
        # self.k_maxs[0] = num_gks - 1
        # self.k_maxs[self.team_size - max_fws - max_mids - max_defs: self.team_size - max_fws - max_mids + 1] = [num_gks + num_defs - 1] * 3
        # self.k_maxs[4:8] = [num_gks + num_defs + num_mids - 1] * 4
        # self.k_maxs[max_gks + max_defs + max_mids:max_gks + max_defs + max_mids + max_fws] = [num_gks + num_defs + num_mids + num_forwards - 1] * max_fws
        # print(self.player_list['player_name'])
        self.player_costs = self.player_list['now_cost'].to_dict()
        self.player_points = self.player_list['xPointsP90'].to_dict()
        self.player_teams = self.player_list['team'].to_dict()


        data_for_combs = {
            'player_costs': self.player_costs,
            'player_points': self.player_points,
            'player_teams': self.player_teams,
            'k_mins': self.k_mins,
            'k_maxs': self.k_maxs,
            'budget': self.budget,
            'n': self._num_players,
            'k': self.team_size,
            'player_positions': self.player_list['element_type'].to_dict(),
            'names': self.player_list['player_name'].to_dict()
        }
        save_obj(data_for_combs, "data")

    def find_best_team(self):
        max_score = 0
        for team in self.possible_teams:
            # value, count = Counter([self.player_teams[player] for player in team]).most_common(1)[0]
            # if count > 3:  # only allowed 3 per team
            #     continue

            total_score = sum([self.player_points[x] for x in team])
            if total_score > max_score:
                max_score = total_score
                self.best_team = team

        print(self.best_team)
        print("Total Score: {}".format(max_score))
        print("Total Cost: {}".format(sum([self.player_costs[x] for x in self.best_team])))
        print(self.player_list[self.player_list.index.isin(self.best_team)]['player_name'])

    def optimise(self):
        n = self._num_players
        k = self.team_size
        # c = combinations.Combinations(n, k, self.k_mins, self.k_maxs, self.player_costs, self.player_teams, self.budget).get_combs()
        c = combinations.Combinations().get_combs()
        for r in c:
            # if sum([self.player_costs[x] for x in r]) < self.budget:
            self.possible_teams.append(r)


if True:
    build_player_list()
    df_player_list = read_player_list()
    optimiser = Optimiser(df_player_list, team_size=11, shortlist_num=11, budget=82.5, max_players_per_pos=[1, 5, 5, 3])
    optimiser.prepare_optimise()

    # print("Starting Optimize...")
    # t1 = timeit.timeit(lambda: optimiser.optimise(), number=1)
    # print("Optimization Time: {:.2f}".format(t1))
    # print("Possible Teams: {}".format(len(optimiser.possible_teams)))
    #
    # t2 = timeit.timeit(lambda: optimiser.find_best_team(), number=1)
    # print("Team Find Time: {:.2f}".format(t2))
    # print("Total Time: {:.2f}".format(t1+t2))


