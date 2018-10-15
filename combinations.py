import pickle
from collections import Counter
import timeit


def load_obj(name):
    with open('obj/' + name + '.pkl', 'rb') as f:
        return pickle.load(f)


class Combinations:

    # def __init__(self, n, k, k_mins: list, k_maxs: list, player_costs: dict, player_teams: dict, budget: float):
    def __init__(self):
        data = load_obj('data_for_combs')
        self.n = data['n']
        self.k = data['k']
        self.k_mins = data['k_mins']
        self.k_maxs = data['k_maxs']
        self.player_costs = data['player_costs']
        self.player_teams = data['player_teams']
        self.budget = data['budget']

    def get_combs(self):

        """
        Generates all n choose k combinations of the n natural numbers
        """
        # comb = [i for i in range(k)]
        comb = [0]
        for i in range(1, self.k):
            comb.append(max(self.k_mins[i], comb[i - 1] + 1))

        while comb is not None:
            # print(comb)
            yield comb
            comb = self.get_next_combination(comb)

    def get_pos_to_change(self, comb):
        """
        Finds the rightmost position in the comb list such that its value can
        can be increased. Returns -1 if there's no such position.
        """
        k = len(comb)
        pos_to_change = k - 1
        max_possible_value = self.n - 1

        # for idx in range(k - 1, 0, -1):
        #     max_possible_value = max(k_maxs[idx] - (k - 1 - idx), k_maxs[idx])
        #     if comb[pos_to_change] == max_possible_value:
        #         pos_to_change -= 1
        #         continue
        #     return pos_to_change

        while pos_to_change >= 0 and comb[pos_to_change] == max_possible_value:
            pos_to_change -= 1
            max_possible_value = min(max_possible_value - 1, self.k_maxs[pos_to_change])
        return pos_to_change

    def players_per_team(self, comb):
        value, count = Counter([self.player_teams[player] for player in comb]).most_common(1)[0]
        if count <= 3:  # only allowed 3 per team
            return True
        else:
            return False

    def in_budget(self, comb):
        if sum([self.player_costs[x] for x in comb]) <= self.budget:
            return True

    def validate_team(self, comb):
        if self.in_budget(comb) and self.players_per_team(comb):
            return True
        else:
            return False

    def inc_value_at_pos(self, comb, pos):
        """
        Increments the value at the given position and generates the
        lexicographically smallest suffix after this position.
        """
        new_comb = comb[:]
        new_comb[pos] += 1
        if self.validate_team(new_comb[:pos + 1]):
            for idx in range(pos + 1, len(comb)):
                new_comb[idx] = max(new_comb[idx - 1] + 1, self.k_mins[idx])
        return new_comb

    def get_next_combination(self, comb):
        """
        Returns the lexicographically next combination or None if it doesn't
        exist.
        """
        pos_to_change = self.get_pos_to_change(comb)
        if pos_to_change < 0:
            return None
        return self.inc_value_at_pos(comb, pos_to_change)


if __name__ == '__main__':
    # print(list(combinations(20, 10, [0, 1, 1, 1, 6, 6, 6, 6, 12, 12], [1, 4, 4, 4, 10, 10, 10, 10, 18, 18])))
    # c = Combinations(10, 3, [0, 3, 7], [1, 5, 9]).get_combs()
    def run():
        c = Combinations().get_combs()
        print(len(list(c)))

    t1 = timeit.timeit(run, number=1)
    print("total time: {:.2f}".format(t1))
