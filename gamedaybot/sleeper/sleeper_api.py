import json
import os
import time

import requests

BASE_URL = 'https://api.sleeper.app/v1'

# Per Sleeper's API docs, /players/nfl returns a ~5MB payload that rarely
# changes and should be fetched at most once per day.
PLAYERS_CACHE_TTL_SECONDS = 24 * 60 * 60

DEFAULT_PLAYERS_CACHE_PATH = os.path.join(os.path.dirname(__file__), '.players_cache.json')


class SleeperAPI:
    """
    A small REST client for the unauthenticated Sleeper fantasy football API
    (https://api.sleeper.app/v1). Unlike ESPN, Sleeper requires no year or
    cookie based auth; a league is identified solely by its league_id.

    Parameters
    ----------
    league_id : str
        The Sleeper league id to query.
    cache_path : str, optional
        Path to the on-disk cache file used for /players/nfl. Defaults to a
        file alongside this module.
    """

    def __init__(self, league_id, cache_path=None):
        self.league_id = league_id
        self.cache_path = cache_path or DEFAULT_PLAYERS_CACHE_PATH

    def _get(self, path):
        response = requests.get(f'{BASE_URL}{path}')
        response.raise_for_status()
        return response.json()

    def get_league(self):
        """Retrieve league metadata (name, season, settings, roster_positions, etc.)."""

        return self._get(f'/league/{self.league_id}')

    def get_rosters(self):
        """Retrieve all rosters in the league, including wins/losses/ties/points."""

        return self._get(f'/league/{self.league_id}/rosters')

    def get_users(self):
        """Retrieve all users (team owners) in the league."""

        return self._get(f'/league/{self.league_id}/users')

    def get_matchups(self, week):
        """Retrieve each roster's matchup and points for a given week."""

        return self._get(f'/league/{self.league_id}/matchups/{week}')

    def get_nfl_state(self):
        """Retrieve the current NFL state (used to determine the current week/season)."""

        return self._get('/state/nfl')

    def get_transactions(self, week):
        """Retrieve waiver/free-agent/trade transactions for a given week (round)."""

        return self._get(f'/league/{self.league_id}/transactions/{week}')

    def get_players(self):
        """
        Retrieve NFL player metadata, cached to disk for at most one day.

        Returns
        -------
        dict
            A mapping of player_id to player metadata.
        """

        cached = self._read_players_cache()
        if cached is not None:
            return cached

        players = self._get('/players/nfl')
        self._write_players_cache(players)
        return players

    def _read_players_cache(self):
        if not os.path.exists(self.cache_path):
            return None

        try:
            with open(self.cache_path, 'r') as f:
                cache = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

        if time.time() - cache.get('fetched_at', 0) >= PLAYERS_CACHE_TTL_SECONDS:
            return None

        return cache.get('players')

    def _write_players_cache(self, players):
        cache = {'fetched_at': time.time(), 'players': players}
        with open(self.cache_path, 'w') as f:
            json.dump(cache, f)
