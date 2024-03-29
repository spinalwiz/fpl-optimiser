import pickle
from pulp import *


def run_optimizer():
    def load_obj(name):
        with open('obj/' + name + '.pkl', 'rb') as f:
            return pickle.load(f)

    def save_obj(obj, name):
        with open('obj/' + name + '.pkl', 'wb') as f:
            pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


    # prepare data
    data = load_obj('data_for_optimiser')
    costs = {k: int(v * 10) for (k, v) in data['player_costs'].items()}
    budget = data['budget'] * 10
    # variables
    limit_changes = data['limit_changes']
    limit_sub_changes = data['limit_sub_changes']
    changes = data['num_changes']  # 11 means everyone is different
    my_team = data['my_team']
    man_city_team = data['man_city_team']
    liverpool_team = data['liverpool_team']
    chelsea_team = data['chelsea_team']
    points = {k: int(v * 10) for (k, v) in data['player_points'].items()}
    players = [i for i in range(len(costs))]
    sub1 = players[:]
    sub2 = players[:]
    sub3 = players[:]
    gks = {k: 1 if v == 1 else 0 for (k, v) in data['player_positions'].items()}
    defs = {k: 1 if v == 2 else 0 for (k, v) in data['player_positions'].items()}
    mids = {k: 1 if v == 3 else 0 for (k, v) in data['player_positions'].items()}
    fws = {k: 1 if v == 4 else 0 for (k, v) in data['player_positions'].items()}

    # Setup Optimizer
    prob = LpProblem("Fantasy Football", LpMaximize)

    player_vars = LpVariable.dicts("Players", players, 0, 1, LpBinary)
    sub1_vars = LpVariable.dicts("Sub1", sub1, 0, 1, LpBinary)
    sub2_vars = LpVariable.dicts("Sub2", sub2, 0, 1, LpBinary)
    sub3_vars = LpVariable.dicts("Sub3", sub3, 0, 1, LpBinary)

    prob += lpSum([points[i]*player_vars[i] for i in players] +
                  [0.7 * points[i] * sub1_vars[i] for i in sub1] +
                  [0.4 * points[i] * sub2_vars[i] for i in sub2] +
                  [0.1 * points[i] * sub3_vars[i] for i in sub3]), "Total Points"

    prob += lpSum([player_vars[i] for i in players]) == 11, "Total 11 Players"
    prob += lpSum([sub1_vars[i] for i in sub1]) == 1, "1 x sub 1"
    prob += lpSum([sub2_vars[i] for i in sub2]) == 1, "1 x sub 2"
    prob += lpSum([sub3_vars[i] for i in sub3]) == 1, "1 x sub 3"

    if limit_changes:
        prob += lpSum([my_team[i] * player_vars[i] for i in players] +
                      [my_team[i] * sub1_vars[i] for i in players] +
                      [my_team[i] * sub2_vars[i] for i in players] +
                      [my_team[i] * sub3_vars[i] for i in players]
                      ) >= (14 - changes), "No More than x changes"

    # Should this be = 1 to avoid changes to subs?
    if limit_sub_changes:
        prob += lpSum([my_team[i] * sub1_vars[i] for i in players]) <= 1, "Don't make changes to sub 1"
        prob += lpSum([my_team[i] * sub2_vars[i] for i in players]) <= 1, "Don't make changes to sub 2"
        prob += lpSum([my_team[i] * sub3_vars[i] for i in players]) <= 1, "Don't make changes to sub 3"

    prob += lpSum([man_city_team[i] * player_vars[i] for i in players] +
                  [man_city_team[i] * sub1_vars[i] for i in players] +
                  [man_city_team[i] * sub2_vars[i] for i in players] +
                  [man_city_team[i] * sub3_vars[i] for i in players]) <= 3, "No more than 3 Man City player"

    prob += lpSum([liverpool_team[i] * player_vars[i] for i in players] +
                  [liverpool_team[i] * sub1_vars[i] for i in players] +
                  [liverpool_team[i] * sub2_vars[i] for i in players] +
                  [liverpool_team[i] * sub3_vars[i] for i in players]) <= 3, "No more than 3 Liverpool player"

    prob += lpSum([chelsea_team[i] * player_vars[i] for i in players] +
                  [chelsea_team[i] * sub1_vars[i] for i in players] +
                  [chelsea_team[i] * sub2_vars[i] for i in players] +
                  [chelsea_team[i] * sub3_vars[i] for i in players]) <= 3, "No more than 3 Chelsea player"

    prob += lpSum([costs[i] * player_vars[i] for i in players] +
                  [costs[i] * sub1_vars[i] for i in sub1] +
                  [costs[i] * sub2_vars[i] for i in sub2] +
                  [costs[i] * sub3_vars[i] for i in sub3]) <= budget, "Total Cost"
    prob += lpSum([gks[i] * player_vars[i] for i in players]) == 1, "Only 1 GK"
    prob += lpSum([gks[i] * sub1_vars[i] for i in sub1] +
                  [gks[i] * sub2_vars[i] for i in sub2] +
                  [gks[i] * sub3_vars[i] for i in sub3]) == 0, "No sub GKs"
    prob += lpSum([defs[i] * player_vars[i] for i in players] +
                  [defs[i] * sub1_vars[i] for i in sub1] +
                  [defs[i] * sub2_vars[i] for i in sub2] +
                  [defs[i] * sub3_vars[i] for i in sub3]) == 5, "5 DEFs"
    prob += lpSum([mids[i] * player_vars[i] for i in players] +
                  [mids[i] * sub1_vars[i] for i in sub1] +
                  [mids[i] * sub2_vars[i] for i in sub2] +
                  [mids[i] * sub3_vars[i] for i in sub3]) == 5, "5 Mids"
    prob += lpSum([fws[i] * player_vars[i] for i in players] +
                  [fws[i] * sub1_vars[i] for i in sub1] +
                  [fws[i] * sub2_vars[i] for i in sub2] +
                  [fws[i] * sub3_vars[i] for i in sub3]) == 3, "3 FWs"
    for i in players:
        prob += lpSum(player_vars[i] + sub1_vars[i] + sub2_vars[i] + sub3_vars[i]) <= 1, "Only 1 of id:{} player".format(i)

    # Run Optimizer
    status = prob.solve()
    print("Status:", LpStatus[prob.status])

    selection = {}
    # print(prob)
    for v in prob.variables():
        # print(v.name)
        # print(v.varValue)
        if v.varValue > 0:
            index = int(v.name.split("_")[1])
            selection[index] = 1

    # Output
    team = {k: data['names'][k] for (k, v) in selection.items() if v == 1}
    team_points = {k: {'name': data['names'][k], 'points': data['player_points'][k]} for (k, v) in selection.items() if v == 1}
    print(team)
    # print(team_points)
    # print(my_team)
    print()
    print("Players Out:")
    for k, v in my_team.items():
        if my_team[k] == 1 and k not in team.keys():
            print(k, data['names'][k])
    print()
    print("Players In:")
    for k, v in team.items():
        if my_team[k] != 1:
            print(k, data['names'][k])

    maxPoints = 0
    captain = {}
    for k, v in team_points.items():
        if v['points'] > maxPoints:
            captain = v
            maxPoints = v['points']

    print()
    print("Captain: ")
    print(captain)
