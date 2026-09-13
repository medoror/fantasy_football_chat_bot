import json
import sys
import os
import time
sys.path.insert(1, os.path.abspath('.'))
import pytest
from gamedaybot.sleeper.sleeper_api import SleeperAPI, PLAYERS_CACHE_TTL_SECONDS


@pytest.mark.usefixtures("mock_requests")
class TestSleeperAPI:
    '''Test SleeperAPI REST client'''

    def setup_method(self):
        self.league_id = '12345'

    def test_get_league(self, mock_requests):
        mock_requests.get(
            'https://api.sleeper.app/v1/league/12345',
            json={'league_id': '12345', 'name': 'Test League', 'season': '2024'}
        )
        client = SleeperAPI(self.league_id)
        league = client.get_league()
        assert league['name'] == 'Test League'

    def test_get_rosters(self, mock_requests):
        mock_requests.get(
            'https://api.sleeper.app/v1/league/12345/rosters',
            json=[{'roster_id': 1, 'owner_id': '1', 'settings': {'wins': 5, 'losses': 2}}]
        )
        client = SleeperAPI(self.league_id)
        rosters = client.get_rosters()
        assert rosters[0]['settings']['wins'] == 5

    def test_get_users(self, mock_requests):
        mock_requests.get(
            'https://api.sleeper.app/v1/league/12345/users',
            json=[{'user_id': '1', 'display_name': 'Alice'}]
        )
        client = SleeperAPI(self.league_id)
        users = client.get_users()
        assert users[0]['display_name'] == 'Alice'

    def test_get_matchups(self, mock_requests):
        mock_requests.get(
            'https://api.sleeper.app/v1/league/12345/matchups/5',
            json=[{'roster_id': 1, 'matchup_id': 1, 'points': 100.5}]
        )
        client = SleeperAPI(self.league_id)
        matchups = client.get_matchups(5)
        assert matchups[0]['points'] == 100.5

    def test_get_nfl_state(self, mock_requests):
        mock_requests.get(
            'https://api.sleeper.app/v1/state/nfl',
            json={'week': 6, 'season': '2024'}
        )
        client = SleeperAPI(self.league_id)
        state = client.get_nfl_state()
        assert state['week'] == 6

    def test_get_transactions(self, mock_requests):
        mock_requests.get(
            'https://api.sleeper.app/v1/league/12345/transactions/5',
            json=[{'transaction_id': 't1', 'type': 'waiver', 'status': 'complete'}]
        )
        client = SleeperAPI(self.league_id)
        transactions = client.get_transactions(5)
        assert transactions[0]['type'] == 'waiver'


@pytest.mark.usefixtures("mock_requests")
class TestSleeperAPIPlayersCache:
    '''Test the daily disk cache for the /players/nfl endpoint'''

    def test_get_players_fetches_and_caches(self, mock_requests, tmp_path):
        cache_path = tmp_path / 'players_cache.json'
        mock_requests.get(
            'https://api.sleeper.app/v1/players/nfl',
            json={'1': {'first_name': 'Test', 'last_name': 'Player'}}
        )
        client = SleeperAPI('12345', cache_path=str(cache_path))

        players = client.get_players()

        assert players == {'1': {'first_name': 'Test', 'last_name': 'Player'}}
        assert cache_path.exists()
        assert mock_requests.call_count == 1

    def test_get_players_does_not_refetch_within_ttl(self, mock_requests, tmp_path):
        cache_path = tmp_path / 'players_cache.json'
        mock_requests.get(
            'https://api.sleeper.app/v1/players/nfl',
            json={'1': {'first_name': 'Test'}}
        )
        client = SleeperAPI('12345', cache_path=str(cache_path))

        first = client.get_players()
        second = client.get_players()

        assert first == second
        # The endpoint must only be hit once; the second call should be served from disk.
        assert mock_requests.call_count == 1

    def test_get_players_refetches_after_ttl_expires(self, mock_requests, tmp_path):
        cache_path = tmp_path / 'players_cache.json'
        stale_fetch_time = time.time() - (PLAYERS_CACHE_TTL_SECONDS + 60)
        cache_path.write_text(json.dumps({'fetched_at': stale_fetch_time, 'players': {'stale': True}}))
        mock_requests.get(
            'https://api.sleeper.app/v1/players/nfl',
            json={'fresh': True}
        )
        client = SleeperAPI('12345', cache_path=str(cache_path))

        players = client.get_players()

        assert players == {'fresh': True}
        assert mock_requests.call_count == 1
