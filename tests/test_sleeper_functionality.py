import sys
import os
import time
from datetime import date
sys.path.insert(1, os.path.abspath('.'))
import pytest
import gamedaybot.sleeper.functionality as sleeper
from gamedaybot.sleeper.sleeper_api import SleeperAPI


USERS = [
    {'user_id': '1', 'display_name': 'Alice', 'metadata': {'team_name': 'Dynasty Warriors'}},
    {'user_id': '2', 'display_name': 'Bob', 'metadata': {'team_name': 'Gridiron Gang'}},
    {'user_id': '3', 'display_name': 'Carol', 'metadata': {'team_name': 'End Zone Elite'}},
    {'user_id': '4', 'display_name': 'Dave', 'metadata': {}},
]

ROSTERS = [
    {'roster_id': 1, 'owner_id': '1', 'settings': {'wins': 5, 'losses': 2, 'ties': 0, 'fpts': 650, 'fpts_decimal': 25}},
    {'roster_id': 2, 'owner_id': '2', 'settings': {'wins': 4, 'losses': 3, 'ties': 0, 'fpts': 600, 'fpts_decimal': 10}},
    {'roster_id': 3, 'owner_id': '3', 'settings': {'wins': 3, 'losses': 3, 'ties': 1, 'fpts': 590, 'fpts_decimal': 0}},
    {'roster_id': 4, 'owner_id': '4', 'settings': {'wins': 2, 'losses': 5, 'ties': 0, 'fpts': 500, 'fpts_decimal': 50}},
]

MATCHUPS_WEEK_5 = [
    {'roster_id': 1, 'matchup_id': 1, 'points': 120.5},
    {'roster_id': 2, 'matchup_id': 1, 'points': 110.0},
    {'roster_id': 3, 'matchup_id': 2, 'points': 95.0},
    {'roster_id': 4, 'matchup_id': 2, 'points': 60.0},
]


def _mock_league_endpoints(mock_requests, league_id='12345', rosters=ROSTERS, users=USERS):
    mock_requests.get(f'https://api.sleeper.app/v1/league/{league_id}/rosters', json=rosters)
    mock_requests.get(f'https://api.sleeper.app/v1/league/{league_id}/users', json=users)


@pytest.mark.usefixtures("mock_requests")
class TestGetStandings:
    '''Test get_standings against mocked Sleeper roster/user endpoints'''

    def test_get_standings(self, mock_requests):
        _mock_league_endpoints(mock_requests)
        client = SleeperAPI('12345')

        result = sleeper.get_standings(client)

        expected = '\n'.join([
            'Current Standings',
            ' 1: (5-2-0) Dynasty Warriors ',
            ' 2: (4-3-0) Gridiron Gang ',
            ' 3: (3-3-1) End Zone Elite ',
            ' 4: (2-5-0) Dave ',
        ])
        assert result == expected

    def test_get_standings_without_ties_omits_tie_column(self, mock_requests):
        rosters = [
            {'roster_id': 1, 'owner_id': '1',
             'settings': {'wins': 3, 'losses': 1, 'ties': 0, 'fpts': 400, 'fpts_decimal': 0}},
            {'roster_id': 2, 'owner_id': '2',
             'settings': {'wins': 1, 'losses': 3, 'ties': 0, 'fpts': 300, 'fpts_decimal': 0}},
        ]
        _mock_league_endpoints(mock_requests, rosters=rosters, users=USERS[:2])
        client = SleeperAPI('12345')

        result = sleeper.get_standings(client)

        expected = '\n'.join([
            'Current Standings',
            ' 1: (3-1) Dynasty Warriors ',
            ' 2: (1-3) Gridiron Gang ',
        ])
        assert result == expected

    def test_get_standings_null_settings_treated_as_zero(self, mock_requests):
        # Sleeper returns "settings": null for uninitialized/newly-joined rosters.
        rosters = [
            {'roster_id': 1, 'owner_id': '1',
             'settings': {'wins': 1, 'losses': 0, 'ties': 0, 'fpts': 100, 'fpts_decimal': 0}},
            {'roster_id': 2, 'owner_id': '2', 'settings': None},
        ]
        _mock_league_endpoints(mock_requests, rosters=rosters, users=USERS[:2])
        client = SleeperAPI('12345')

        result = sleeper.get_standings(client)

        expected = '\n'.join([
            'Current Standings',
            ' 1: (1-0) Dynasty Warriors ',
            ' 2: (0-0) Gridiron Gang ',
        ])
        assert result == expected

    def test_get_standings_ties_rank_above_equal_wins_with_more_points(self, mock_requests):
        rosters = [
            # Same win count as roster 2, but with ties and fewer points; should still rank first.
            {'roster_id': 1, 'owner_id': '1',
             'settings': {'wins': 5, 'losses': 0, 'ties': 2, 'fpts': 500, 'fpts_decimal': 0}},
            {'roster_id': 2, 'owner_id': '2',
             'settings': {'wins': 5, 'losses': 2, 'ties': 0, 'fpts': 900, 'fpts_decimal': 0}},
        ]
        _mock_league_endpoints(mock_requests, rosters=rosters, users=USERS[:2])
        client = SleeperAPI('12345')

        result = sleeper.get_standings(client)

        expected = '\n'.join([
            'Current Standings',
            ' 1: (5-0-2) Dynasty Warriors ',
            ' 2: (5-2-0) Gridiron Gang ',
        ])
        assert result == expected


@pytest.mark.usefixtures("mock_requests")
class TestGetTrophies:
    '''Test get_trophies against mocked Sleeper roster/user/matchup endpoints'''

    def test_get_trophies_explicit_week(self, mock_requests):
        _mock_league_endpoints(mock_requests)
        mock_requests.get('https://api.sleeper.app/v1/league/12345/matchups/5', json=MATCHUPS_WEEK_5)
        client = SleeperAPI('12345')

        result = sleeper.get_trophies(client, week=5)

        expected = '\n'.join([
            'Trophies of the week:',
            '👑 High score 👑',
            'Dynasty Warriors with 120.50 points',
            '💩 Low score 💩',
            'Dave with 60.00 points',
            '😱 Blow out 😱',
            'End Zone Elite blew out Dave by 35.00 points',
            '😅 Close win 😅',
            'Dynasty Warriors barely beat Gridiron Gang by 10.50 points',
            '🍀 Lucky 🍀',
            'End Zone Elite was 1-2 against the league, but still got the win',
            '😡 Unlucky 😡',
            'Gridiron Gang was 2-1 against the league, but still took an L',
        ])
        assert result == expected

    def test_get_trophies_defaults_to_prior_week(self, mock_requests):
        _mock_league_endpoints(mock_requests)
        mock_requests.get('https://api.sleeper.app/v1/state/nfl', json={'week': 6, 'season': '2024'})
        mock_requests.get('https://api.sleeper.app/v1/league/12345/matchups/5', json=MATCHUPS_WEEK_5)
        client = SleeperAPI('12345')

        result = sleeper.get_trophies(client)

        assert result.startswith('Trophies of the week:')
        assert 'Dynasty Warriors with 120.50 points' in result

    def test_get_trophies_ignores_tied_matchup_for_win_loss_trophies(self, mock_requests):
        rosters = [
            {'roster_id': 1, 'owner_id': '1',
             'settings': {'wins': 1, 'losses': 0, 'ties': 0, 'fpts': 100, 'fpts_decimal': 0}},
            {'roster_id': 2, 'owner_id': '2',
             'settings': {'wins': 0, 'losses': 1, 'ties': 0, 'fpts': 90, 'fpts_decimal': 0}},
        ]
        matchups = [
            {'roster_id': 1, 'matchup_id': 1, 'points': 100.0},
            {'roster_id': 2, 'matchup_id': 1, 'points': 100.0},
        ]
        _mock_league_endpoints(mock_requests, rosters=rosters, users=USERS[:2])
        mock_requests.get('https://api.sleeper.app/v1/league/12345/matchups/5', json=matchups)
        client = SleeperAPI('12345')

        result = sleeper.get_trophies(client, week=5)

        # No decided matchups means no close/blowout/lucky/unlucky trophies.
        assert '😱 Blow out 😱' not in result
        assert '😅 Close win 😅' not in result
        assert '🍀 Lucky 🍀' not in result
        assert '😡 Unlucky 😡' not in result
        assert 'Dynasty Warriors with 100.00 points' in result

    def test_get_trophies_excludes_bye_week_entries(self, mock_requests):
        # Two rosters on a playoff-round bye share matchup_id: null and must not be
        # paired against each other, nor corrupt the high/low score trophies.
        matchups = MATCHUPS_WEEK_5 + [
            {'roster_id': 5, 'matchup_id': None, 'points': 0.0},
            {'roster_id': 6, 'matchup_id': None, 'points': 0.0},
        ]
        users = USERS + [
            {'user_id': '5', 'display_name': 'Eve', 'metadata': {'team_name': 'Bye Week Squad'}},
            {'user_id': '6', 'display_name': 'Frank', 'metadata': {'team_name': 'Resting Roster'}},
        ]
        bye_settings = {'wins': 6, 'losses': 1, 'ties': 0, 'fpts': 700, 'fpts_decimal': 0}
        rosters = ROSTERS + [
            {'roster_id': 5, 'owner_id': '5', 'settings': bye_settings},
            {'roster_id': 6, 'owner_id': '6', 'settings': bye_settings},
        ]
        _mock_league_endpoints(mock_requests, rosters=rosters, users=users)
        mock_requests.get('https://api.sleeper.app/v1/league/12345/matchups/5', json=matchups)
        client = SleeperAPI('12345')

        result = sleeper.get_trophies(client, week=5)

        # The bye-week teams must not appear anywhere in the trophy output.
        assert 'Bye Week Squad' not in result
        assert 'Resting Roster' not in result
        # And they must not steal the low-score trophy with their 0.0 bye score.
        assert 'Low score' in result
        assert 'Dave with 60.00 points' in result

    def test_get_trophies_empty_matchups_returns_message(self, mock_requests):
        _mock_league_endpoints(mock_requests)
        mock_requests.get('https://api.sleeper.app/v1/league/12345/matchups/5', json=[])
        client = SleeperAPI('12345')

        result = sleeper.get_trophies(client, week=5)

        assert result == '\n'.join(['Trophies of the week:', 'No matchups available for this week'])


@pytest.mark.usefixtures("mock_requests")
class TestGetScoreboardShort:
    '''Test get_scoreboard_short against mocked Sleeper roster/user/matchup endpoints'''

    def test_get_scoreboard_short(self, mock_requests):
        _mock_league_endpoints(mock_requests)
        mock_requests.get('https://api.sleeper.app/v1/league/12345/matchups/5', json=MATCHUPS_WEEK_5)
        client = SleeperAPI('12345')

        result = sleeper.get_scoreboard_short(client, week=5)

        expected = '\n'.join([
            'Score Update',
            '%4s %6.2f - %6.2f %s' % ('Dynasty Warriors', 120.5, 110.0, 'Gridiron Gang'),
            '%4s %6.2f - %6.2f %s' % ('End Zone Elite', 95.0, 60.0, 'Dave'),
        ])
        assert result == expected

    def test_get_scoreboard_short_defaults_to_current_week(self, mock_requests):
        _mock_league_endpoints(mock_requests)
        mock_requests.get('https://api.sleeper.app/v1/state/nfl', json={'week': 5, 'season': '2024'})
        mock_requests.get('https://api.sleeper.app/v1/league/12345/matchups/5', json=MATCHUPS_WEEK_5)
        client = SleeperAPI('12345')

        result = sleeper.get_scoreboard_short(client)

        assert result.startswith('Score Update')
        assert 'Dynasty Warriors' in result

    def test_get_scoreboard_short_excludes_bye_week_entries(self, mock_requests):
        matchups = MATCHUPS_WEEK_5 + [
            {'roster_id': 5, 'matchup_id': None, 'points': 0.0},
            {'roster_id': 6, 'matchup_id': None, 'points': 0.0},
        ]
        users = USERS + [
            {'user_id': '5', 'display_name': 'Eve', 'metadata': {'team_name': 'Bye Week Squad'}},
            {'user_id': '6', 'display_name': 'Frank', 'metadata': {'team_name': 'Resting Roster'}},
        ]
        bye_settings = {'wins': 6, 'losses': 1, 'ties': 0, 'fpts': 700, 'fpts_decimal': 0}
        rosters = ROSTERS + [
            {'roster_id': 5, 'owner_id': '5', 'settings': bye_settings},
            {'roster_id': 6, 'owner_id': '6', 'settings': bye_settings},
        ]
        _mock_league_endpoints(mock_requests, rosters=rosters, users=users)
        mock_requests.get('https://api.sleeper.app/v1/league/12345/matchups/5', json=matchups)
        client = SleeperAPI('12345')

        result = sleeper.get_scoreboard_short(client, week=5)

        assert 'Bye Week Squad' not in result
        assert 'Resting Roster' not in result
        assert result.count('\n') == 2  # header + 2 real matchup lines only


@pytest.mark.usefixtures("mock_requests")
class TestGetMatchups:
    '''Test get_matchups against mocked Sleeper roster/user/matchup endpoints'''

    def test_get_matchups(self, mock_requests):
        _mock_league_endpoints(mock_requests)
        mock_requests.get('https://api.sleeper.app/v1/league/12345/matchups/5', json=MATCHUPS_WEEK_5)
        client = SleeperAPI('12345')

        result = sleeper.get_matchups(client, week=5)

        expected = '\n'.join([
            'Matchups',
            'Dynasty Warriors vs Gridiron Gang',
            'End Zone Elite vs Dave',
            '',
            '%4s (%s) vs (%s) %s' % ('Dynasty Warriors', '5-2', '4-3', 'Gridiron Gang'),
            '%4s (%s) vs (%s) %s' % ('End Zone Elite', '3-3-1', '2-5', 'Dave'),
        ])
        assert result == expected

    def test_get_matchups_defaults_to_current_week(self, mock_requests):
        _mock_league_endpoints(mock_requests)
        mock_requests.get('https://api.sleeper.app/v1/state/nfl', json={'week': 5, 'season': '2024'})
        mock_requests.get('https://api.sleeper.app/v1/league/12345/matchups/5', json=MATCHUPS_WEEK_5)
        client = SleeperAPI('12345')

        result = sleeper.get_matchups(client)

        assert result.startswith('Matchups')
        assert 'Dynasty Warriors vs Gridiron Gang' in result

    def test_get_matchups_excludes_bye_week_entries(self, mock_requests):
        matchups = MATCHUPS_WEEK_5 + [
            {'roster_id': 5, 'matchup_id': None, 'points': 0.0},
            {'roster_id': 6, 'matchup_id': None, 'points': 0.0},
        ]
        users = USERS + [
            {'user_id': '5', 'display_name': 'Eve', 'metadata': {'team_name': 'Bye Week Squad'}},
            {'user_id': '6', 'display_name': 'Frank', 'metadata': {'team_name': 'Resting Roster'}},
        ]
        bye_settings = {'wins': 6, 'losses': 1, 'ties': 0, 'fpts': 700, 'fpts_decimal': 0}
        rosters = ROSTERS + [
            {'roster_id': 5, 'owner_id': '5', 'settings': bye_settings},
            {'roster_id': 6, 'owner_id': '6', 'settings': bye_settings},
        ]
        _mock_league_endpoints(mock_requests, rosters=rosters, users=users)
        mock_requests.get('https://api.sleeper.app/v1/league/12345/matchups/5', json=matchups)
        client = SleeperAPI('12345')

        result = sleeper.get_matchups(client, week=5)

        assert 'Bye Week Squad' not in result
        assert 'Resting Roster' not in result


PLAYERS = {
    '9001': {'first_name': 'Josh', 'last_name': 'Allen', 'position': 'QB'},
    '9002': {'first_name': 'Cooper', 'last_name': 'Kupp', 'position': 'WR'},
}


@pytest.mark.usefixtures("mock_requests")
class TestGetWaiverReport:
    '''Test get_waiver_report against mocked Sleeper transaction/player endpoints'''

    def test_get_waiver_report_add_and_drop_with_faab(self, mock_requests, tmp_path):
        _mock_league_endpoints(mock_requests)
        mock_requests.get('https://api.sleeper.app/v1/players/nfl', json=PLAYERS)
        transactions = [
            {
                'transaction_id': 't1',
                'type': 'waiver',
                'status': 'complete',
                'created': int(time.time() * 1000),
                'adds': {'9001': 1},
                'drops': {'9002': 1},
                'settings': {'waiver_bid': 15},
            },
        ]
        mock_requests.get('https://api.sleeper.app/v1/league/12345/transactions/5', json=transactions)
        client = SleeperAPI('12345', cache_path=str(tmp_path / 'players_cache.json'))

        result = sleeper.get_waiver_report(client, week=5)

        expected = '\n'.join([
            'Waiver Report %s: ' % date.today().strftime('%Y-%m-%d'),
            'Dynasty Warriors \nADDED QB Josh Allen ($15)\nDROPPED WR Cooper Kupp\n',
        ])
        assert result == expected

    def test_get_waiver_report_free_agent_add_only_no_faab(self, mock_requests, tmp_path):
        _mock_league_endpoints(mock_requests)
        mock_requests.get('https://api.sleeper.app/v1/players/nfl', json=PLAYERS)
        transactions = [
            {
                'transaction_id': 't2',
                'type': 'free_agent',
                'status': 'complete',
                'created': int(time.time() * 1000),
                'adds': {'9001': 2},
                'drops': None,
                'settings': None,
            },
        ]
        mock_requests.get('https://api.sleeper.app/v1/league/12345/transactions/5', json=transactions)
        client = SleeperAPI('12345', cache_path=str(tmp_path / 'players_cache.json'))

        result = sleeper.get_waiver_report(client, week=5)

        expected = '\n'.join([
            'Waiver Report %s: ' % date.today().strftime('%Y-%m-%d'),
            'Gridiron Gang \nADDED QB Josh Allen\n',
        ])
        assert result == expected

    def test_get_waiver_report_ignores_failed_and_non_today_transactions(self, mock_requests, tmp_path):
        _mock_league_endpoints(mock_requests)
        mock_requests.get('https://api.sleeper.app/v1/players/nfl', json=PLAYERS)
        old_created_ms = int((time.time() - 3 * 24 * 60 * 60) * 1000)
        transactions = [
            {
                'transaction_id': 't3',
                'type': 'waiver',
                'status': 'failed',
                'created': int(time.time() * 1000),
                'adds': {'9001': 1},
                'drops': None,
                'settings': {'waiver_bid': 5},
            },
            {
                'transaction_id': 't4',
                'type': 'waiver',
                'status': 'complete',
                'created': old_created_ms,
                'adds': {'9002': 2},
                'drops': None,
                'settings': {'waiver_bid': 5},
            },
            {
                'transaction_id': 't5',
                'type': 'trade',
                'status': 'complete',
                'created': int(time.time() * 1000),
                'adds': {'9001': 1},
                'drops': None,
                'settings': None,
            },
        ]
        mock_requests.get('https://api.sleeper.app/v1/league/12345/transactions/5', json=transactions)
        client = SleeperAPI('12345', cache_path=str(tmp_path / 'players_cache.json'))

        result = sleeper.get_waiver_report(client, week=5)

        assert result == 'No waiver transactions'

    def test_get_waiver_report_empty_transactions_returns_message(self, mock_requests, tmp_path):
        _mock_league_endpoints(mock_requests)
        mock_requests.get('https://api.sleeper.app/v1/players/nfl', json=PLAYERS)
        mock_requests.get('https://api.sleeper.app/v1/league/12345/transactions/5', json=[])
        client = SleeperAPI('12345', cache_path=str(tmp_path / 'players_cache.json'))

        result = sleeper.get_waiver_report(client, week=5)

        assert result == 'No waiver transactions'

    def test_get_waiver_report_defaults_to_current_week(self, mock_requests, tmp_path):
        _mock_league_endpoints(mock_requests)
        mock_requests.get('https://api.sleeper.app/v1/state/nfl', json={'week': 5, 'season': '2024'})
        mock_requests.get('https://api.sleeper.app/v1/players/nfl', json=PLAYERS)
        mock_requests.get('https://api.sleeper.app/v1/league/12345/transactions/5', json=[])
        client = SleeperAPI('12345', cache_path=str(tmp_path / 'players_cache.json'))

        result = sleeper.get_waiver_report(client)

        assert result == 'No waiver transactions'


@pytest.mark.usefixtures("mock_requests")
class TestGetFinal:
    '''Test get_final against mocked Sleeper roster/user/matchup endpoints'''

    def test_get_final_composes_scoreboard_and_trophies(self, mock_requests):
        _mock_league_endpoints(mock_requests)
        mock_requests.get('https://api.sleeper.app/v1/league/12345/matchups/5', json=MATCHUPS_WEEK_5)
        client = SleeperAPI('12345')

        result = sleeper.get_final(client, week=5)

        expected_scoreboard = sleeper.get_scoreboard_short(client, week=5)
        expected_trophies = sleeper.get_trophies(client, week=5)
        expected = "Final " + expected_scoreboard + "\n\n" + expected_trophies
        assert result == expected
        assert result.startswith("Final Score Update")

    def test_get_final_defaults_to_prior_week(self, mock_requests):
        _mock_league_endpoints(mock_requests)
        mock_requests.get('https://api.sleeper.app/v1/state/nfl', json={'week': 6, 'season': '2024'})
        mock_requests.get('https://api.sleeper.app/v1/league/12345/matchups/5', json=MATCHUPS_WEEK_5)
        client = SleeperAPI('12345')

        result = sleeper.get_final(client)

        assert result.startswith('Final Score Update')
        assert 'Trophies of the week:' in result


# Hand-derived 4-team, 2-week scenario used by TestPowerRankingsMath and
# TestGetPowerRankings below.
#
# Week 1: roster 1 beats roster 2 (120.5 - 110.0); roster 3 beats roster 4 (95.0 - 60.0)
# Week 2: roster 1 beats roster 3 (130.0 - 100.0); roster 2 beats roster 4 (105.0 - 95.0)
#
# Win matrix through week 2 (rows/cols in roster_id order 1,2,3,4):
#   1: [0,1,1,0]   (beat 2 and 3)
#   2: [0,0,0,1]   (beat 4)
#   3: [0,0,0,1]   (beat 4)
#   4: [0,0,0,0]   (no wins)
#
# X^2 (matrix multiplication, NOT elementwise): only row 1 is non-zero, since
# rosters 2 and 3 both beat 4 and roster 1 beat both 2 and 3:
#   X^2[1] = [0,0,0,2]  (roster 1 gets credit for 2 (2->4) and 3 (3->4)'s indirect win over 4)
#   X^2[2] = X^2[3] = X^2[4] = [0,0,0,0]
#
# two_step_dominance (row sums of X^2 + X): roster 1 = 4, roster 2 = 1, roster 3 = 1, roster 4 = 0.
#
# Final power (dominance*0.8 + avg_score*0.15 + avg_mov*0.05, each int-truncated
# first), averaged over both weeks: roster 1 = 22.95, roster 2 = 16.85,
# roster 3 = 15.45, roster 4 = 10.45. Rosters 2 and 3 tie on dominance (1 each),
# but roster 2's higher average score/margin (avg_score 107.5 vs 97.5, avg_mov
# -0.25 vs 2.5, both truncated before weighting: int(107.5)=107 * 0.15 = 16.05
# beats int(97.5)=97 * 0.15 = 14.55 by more than the margin term can close)
# gives it the higher final power score.
POWER_MATCHUPS_WEEK_1 = [
    {'roster_id': 1, 'matchup_id': 1, 'points': 120.5},
    {'roster_id': 2, 'matchup_id': 1, 'points': 110.0},
    {'roster_id': 3, 'matchup_id': 2, 'points': 95.0},
    {'roster_id': 4, 'matchup_id': 2, 'points': 60.0},
]
POWER_MATCHUPS_WEEK_2 = [
    {'roster_id': 1, 'matchup_id': 1, 'points': 130.0},
    {'roster_id': 3, 'matchup_id': 1, 'points': 100.0},
    {'roster_id': 2, 'matchup_id': 2, 'points': 105.0},
    {'roster_id': 4, 'matchup_id': 2, 'points': 95.0},
]


def _mock_power_ranking_weeks(mock_requests, league_id='12345'):
    mock_requests.get(f'https://api.sleeper.app/v1/league/{league_id}/matchups/1', json=POWER_MATCHUPS_WEEK_1)
    mock_requests.get(f'https://api.sleeper.app/v1/league/{league_id}/matchups/2', json=POWER_MATCHUPS_WEEK_2)


class TestPowerRankingsMath:
    '''Test the two-step-dominance matrix math directly against a hand-derived win matrix'''

    def test_square_matrix_is_real_matrix_multiplication(self):
        # See espn_api/football/utils.py:23-37 (square_matrix): despite the name,
        # this is X @ X, not an elementwise square - confirmed by reading the
        # actual installed espn_api 0.46.0 source.
        x = [
            [0, 1, 1, 0],
            [0, 0, 0, 1],
            [0, 0, 0, 1],
            [0, 0, 0, 0],
        ]

        squared = sleeper._square_matrix(x)

        assert squared == [
            [0.0, 0.0, 0.0, 2.0],
            [0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0],
        ]

    def test_two_step_dominance_matches_hand_derived_win_matrix(self):
        x = [
            [0, 1, 1, 0],
            [0, 0, 0, 1],
            [0, 0, 0, 1],
            [0, 0, 0, 0],
        ]

        dominance = sleeper._two_step_dominance(x)

        assert dominance == [4.0, 1.0, 1.0, 0.0]

    def test_two_step_dominance_tied_matchup_yields_no_wins(self):
        # A 2x2 win matrix with no recorded wins (as would result from every
        # matchup being tied) has zero dominance for both teams.
        x = [
            [0, 0],
            [0, 0],
        ]

        dominance = sleeper._two_step_dominance(x)

        assert dominance == [0.0, 0.0]


@pytest.mark.usefixtures("mock_requests")
class TestPowerRankingsHistory:
    '''Test _power_rankings end-to-end against mocked multi-week Sleeper matchup data'''

    def test_power_rankings_ranking_order_matches_hand_derived_dominance(self, mock_requests):
        _mock_league_endpoints(mock_requests)
        _mock_power_ranking_weeks(mock_requests)
        client = SleeperAPI('12345')

        result = sleeper._power_rankings(client, week=2, current_week=2)

        # Hand-derived expected order: roster 1 (dominance 4) way out front,
        # then roster 2 ahead of roster 3 (equal dominance of 1, but roster 2's
        # higher average score/margin gives it the edge), then roster 4
        # (dominance 0) last. See the comment above POWER_MATCHUPS_WEEK_1/2.
        ranked_roster_ids = [roster_id for _, roster_id in result]
        assert ranked_roster_ids == [1, 2, 3, 4]

        scores = {roster_id: float(score) for score, roster_id in result}
        assert scores[1] == pytest.approx(22.95)
        assert scores[2] == pytest.approx(16.85)
        assert scores[3] == pytest.approx(15.45)
        assert scores[4] == pytest.approx(10.45)

    def test_power_rankings_tied_matchup_credits_no_wins_to_either_team(self, mock_requests):
        tied_settings = {'wins': 0, 'losses': 0, 'ties': 2, 'fpts': 200, 'fpts_decimal': 0}
        rosters = [
            {'roster_id': 1, 'owner_id': '1', 'settings': tied_settings},
            {'roster_id': 2, 'owner_id': '2', 'settings': tied_settings},
        ]
        _mock_league_endpoints(mock_requests, rosters=rosters, users=USERS[:2])
        tied_week = [
            {'roster_id': 1, 'matchup_id': 1, 'points': 100.0},
            {'roster_id': 2, 'matchup_id': 1, 'points': 100.0},
        ]
        mock_requests.get('https://api.sleeper.app/v1/league/12345/matchups/1', json=tied_week)
        mock_requests.get('https://api.sleeper.app/v1/league/12345/matchups/2', json=tied_week)
        client = SleeperAPI('12345')

        result = sleeper._power_rankings(client, week=2, current_week=2)

        # Neither roster ever wins a matchup (every week is a tie), so dominance
        # is zero for both and the only contribution to power is average score.
        assert sorted(result) == [('15.00', 1), ('15.00', 2)]


@pytest.mark.usefixtures("mock_requests")
class TestGetPowerRankings:
    '''Test get_power_rankings against mocked Sleeper roster/user/matchup endpoints'''

    def test_get_power_rankings_explicit_week(self, mock_requests):
        _mock_league_endpoints(mock_requests)
        _mock_power_ranking_weeks(mock_requests)
        mock_requests.get('https://api.sleeper.app/v1/state/nfl', json={'week': 3, 'season': '2024'})
        client = SleeperAPI('12345')

        result = sleeper.get_power_rankings(client, week=2)

        lines = result.split('\n')
        assert lines[0] == 'Power Rankings'
        # Top team's own snapshot always normalizes to exactly 99.99.
        assert lines[1].startswith('99.99')
        assert 'Dynasty Warriors' in lines[1]
        # Hand-derived order: Dynasty Warriors (1), Gridiron Gang (2), End Zone Elite (3), Dave (4).
        team_order = [line.split(' - ')[-1] for line in lines[1:]]
        assert team_order == ['Dynasty Warriors', 'Gridiron Gang', 'End Zone Elite', 'Dave']
        # No playoff-percentage parenthetical - Sleeper has no such field.
        assert '(' not in result

    def test_get_power_rankings_defaults_to_prior_week(self, mock_requests):
        _mock_league_endpoints(mock_requests)
        _mock_power_ranking_weeks(mock_requests)
        mock_requests.get('https://api.sleeper.app/v1/state/nfl', json={'week': 3, 'season': '2024'})
        client = SleeperAPI('12345')

        result = sleeper.get_power_rankings(client)

        assert result.startswith('Power Rankings')
        assert 'Dynasty Warriors' in result

    def test_get_power_rankings_week_one_has_no_previous_snapshot(self, mock_requests):
        # At current_week=1, week defaults to 0, which _power_rankings clamps
        # back up to current_week=1 - only one week of history exists, so
        # there's no previous snapshot to diff against and no crash.
        _mock_league_endpoints(mock_requests)
        mock_requests.get('https://api.sleeper.app/v1/state/nfl', json={'week': 1, 'season': '2024'})
        mock_requests.get('https://api.sleeper.app/v1/league/12345/matchups/1', json=POWER_MATCHUPS_WEEK_1)
        client = SleeperAPI('12345')

        result = sleeper.get_power_rankings(client)

        assert result.startswith('Power Rankings')
        for team_name in ('Dynasty Warriors', 'Gridiron Gang', 'End Zone Elite', 'Dave'):
            assert team_name in result
        # No previous snapshot means no movement indicator brackets for anyone.
        assert '[' not in result
