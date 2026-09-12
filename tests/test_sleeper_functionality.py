import sys
import os
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
