import json
import requests
import re
import fpl_trans as ft
import urls
import pandas as pd


def build():
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
    under_html = requests.get(urls.understat_current_season).text

    #  player data from understat
    player_data_text = re.search(r"playersData	= JSON\.parse\(\'(.*)\'\)", under_html, re.MULTILINE).group(1)
    player_data_json = bytes(player_data_text, "utf-8").decode('unicode_escape')
    player_data = json.loads(player_data_json)

    # Merge in aggregated data
    df_understat = pd.DataFrame(player_data)
    df_master = pd.read_excel('match_data_aggregated.xlsx')
    df_master = df_master.merge(df_understat[
                                    ['player_name', 'team_title', 'red_cards', 'games', 'position', 'yellow_cards',
                                     'npg', 'assists', 'goals']], on='player_name', how='right')
    df_master = df_master.apply(pd.to_numeric, errors='ignore')
    df_master.rename(columns={"team_title": "team"}, inplace=True)

    # Goals conceded data
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
    df_xga = pd.DataFrame(xga_data).transpose()

    #  clean sheets data
    df_cs = pd.read_excel('clean_sheets.xlsx')

    #  FPL api data
    response_ = requests.get(urls.fpl_api)
    data = response_.json()['elements']
    df_api = pd.DataFrame(data)
    df_api['player_name'] = df_api['first_name'] + ' ' + df_api['second_name']
    # df_api['team'] = df_api['team'].apply(lambda x: ft.teams_trans[x])
    df_api['now_cost'] = df_api['now_cost'] / 10
    df_api = df_api[['player_name', 'total_points', 'element_type', 'now_cost', 'minutes', 'web_name']]
    df_api['player_name'].replace(ft.player_trans, inplace=True)

    # Merge all data together
    df_master = df_master.merge(df_cs[['team', 'xCS']], on='team', how='left')
    df_master = df_master.merge(df_api, on='player_name', how='left')
    df_master = df_master.merge(df_xga, left_on='team', right_index=True, how='left')

    #  calculated fields
    df_master['xG90'] = df_master['xG'] / df_master['minutes'] * 90
    # If want to use non-penalty goals
    # df_master['npxG90'] = df_master['npxG'] / df_master['minutes'] * 90
    df_master['xA90'] = df_master['xA'] / df_master['minutes'] * 90

    #  data processing
    df_master.set_index('player_name', inplace=True)

    #  xP
    df_master['xPoints'] = df_master.apply(calc_x_points, type='xG', axis=1)
    df_master['xPoints'] = df_master['xPoints'] + (2 * df_master['team_played'])
    df_master['xPoints_per_mil'] = df_master['xPoints'] / df_master['now_cost']

    # Non-penalty xP
    # df_master['xNPPoints'] = df_master.apply(calc_x_points, type='npxG', axis=1)
    # df_master['xNPPoints'] = df_master['xNPPoints'] + (2 * df_master['team_played'])
    # df_master['xNPPoints_per_mil'] = df_master['xNPPoints'] / df_master['now_cost']

    #  xPP90
    df_master['xPointsP90'] = df_master.apply(calc_x_points_90, type='xG90', axis=1)
    df_master['xPointsP90'] = df_master['xPointsP90'] + 2  # Appearance points
    df_master['xPointsP90_per_mil'] = df_master['xPointsP90'] / df_master['now_cost']

    # Non-penalty xPP90
    # df_master['xNPPointsP90'] = df_master.apply(calc_x_points_90, type='npxG90', axis=1)
    # df_master['xNPPointsP90'] = df_master['xNPPointsP90'] + 2
    # df_master['xNPPointsP90_per_mil'] = df_master['xNPPointsP90'] / df_master['now_cost']

    # Actual Points
    df_master['actualP_per_mil'] = df_master['total_points'] / df_master['now_cost']
    df_master['actualP_P90_per_mil'] = (df_master['total_points'] / df_master['minutes'] * 90) / df_master['now_cost']

    # Output final data
    df_master.sort_values(by=['xPointsP90_per_mil'], ascending=False, inplace=True)
    df_master = df_master[['team', 'now_cost', 'total_points', 'games', 'minutes', 'position', 'element_type',
                           'yellow_cards', 'red_cards', 'goals', 'npg', 'xG', 'xG90', 'npg',
                           'assists', 'xA', 'xA90',
                           'xPoints', 'xPoints_per_mil', 'xPointsP90', 'xPointsP90_per_mil',
                           'actualP_per_mil', 'actualP_P90_per_mil'
                           ]]
    df_master.to_excel('out.xlsx', encoding='utf-8')


if __name__ == "__main__":
    build()
