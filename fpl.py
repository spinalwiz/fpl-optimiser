import sys
import pandas as pd
import pickle
import numpy as np
import my_team
import player_weights
import optimiser


#TODO: compare api_out xlsx with understatout xlsx to find mssing players

def save_obj(obj, name):
    with open('obj/' + name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


def read_player_list():
    df_master = pd.read_excel('out.xlsx')
    df_master.set_index('player_name', inplace=True)
    return df_master


class Optimiser:

    def __init__(self, df: pd.DataFrame, budget: float, limit_changes: bool, limit_sub_changes: bool, num_changes: int):
        self.current_team = my_team.team3
        self.budget = budget
        self.limit_changes = limit_changes
        self.limit_sub_changes = limit_sub_changes
        self.num_changes = num_changes
        self.player_list = df
        # self.player_list = self.player_list[self.player_list['minutes'] > 800]  # Remove players who havent played at least 800 minutes
        self.player_points = {}
        self.player_costs = {}
        self.player_teams = {}
        self.my_team = None

        self.weight_players()
        # self.update_custom_prices()
        self.player_list.sort_values(by='element_type', inplace=True)
        self.player_list.reset_index(inplace=True)
        self._num_players = len(self.player_list.index)

    def update_custom_prices(self):
        # If the price of players in your team has changed you can use this override the current prices
        price_update = {'Andrew Robertson': 6,
                        'Aaron Wan-Bissaka': 4, 'Callum Wilson': 6.3, 'Aymeric Laporte': 5.7,
                        'Raheem Sterling': 11.1,  'Raúl Jiménez': 5.6,
                        'Mohamed Salah': 13, 'Matt Doherty': 4.6}
        self.player_list.update(pd.Series(price_update, name="now_cost"))

    def weight_players(self):
        for k, v in player_weights.weights.items():
            self.player_list.loc[k, 'xPoints'] = self.player_list.loc[k, 'xPoints'] * v

    def prepare_optimise(self):
        self.player_list = self.player_list[self.player_list['now_cost'].notna()]  #  Remove players without a cost
        #  Set points to 0 for players without points - I think this only happens when they change teams - points are bound to the team they earned them for?
        self.player_list['xPoints'] = self.player_list['xPoints'].apply(lambda x: 0 if np.isnan(x) else x)
        self.player_costs = self.player_list['now_cost'].to_dict()
        self.player_points = self.player_list['xPoints'].to_dict()
        self.player_teams = self.player_list['team'].to_dict()
        self.player_list['my_team'] = np.where(self.player_list['player_name'].isin(self.current_team), 1, 0)
        print("Number of players in My Current Team (should be 14):")
        print(self.player_list['my_team'].sum())
        print(self.player_list.index[self.player_list['my_team'] == True].tolist())
        self.player_list['man_city_team'] = np.where(self.player_list['team'].isin(['Manchester City']), 1, 0)
        self.player_list['liverpool_team'] = np.where(self.player_list['team'].isin(['Liverpool']), 1, 0)
        self.player_list['chelsea_team'] = np.where(self.player_list['team'].isin(['Chelsea']), 1, 0)
        self.my_team = self.player_list['my_team'].to_dict()

        data_for_optimiser = {
            'player_costs': self.player_costs,
            'player_points': self.player_points,
            'budget': self.budget,
            'limit_changes': self.limit_changes,
            'limit_sub_changes': self.limit_sub_changes,
            'num_changes': self.num_changes,
            'player_positions': self.player_list['element_type'].to_dict(),
            'names': self.player_list['player_name'].to_dict(),
            'my_team': self.my_team,
            'man_city_team': self.player_list['man_city_team'].to_dict(),
            'liverpool_team': self.player_list['liverpool_team'].to_dict(),
            'chelsea_team': self.player_list['chelsea_team'].to_dict()
        }
        save_obj(data_for_optimiser, "data_for_optimiser")


if __name__ == "__main__":
    df_player_list = read_player_list()
    opt = Optimiser(df_player_list, budget=96, limit_changes=False, limit_sub_changes=False, num_changes=14)
    opt.prepare_optimise()
    optimiser.run_optimizer()




