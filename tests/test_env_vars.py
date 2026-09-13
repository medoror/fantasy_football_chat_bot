import sys
import os
sys.path.insert(1, os.path.abspath('.'))
import pytest
import gamedaybot.espn.env_vars as espn_env_vars
import gamedaybot.sleeper.env_vars as sleeper_env_vars


COMMON_ENV = {
    'BOT_ID': '123456',
    'START_DATE': '2024-09-05',
    'END_DATE': '2025-01-05',
    'TIMEZONE': 'America/Chicago',
    'INIT_MSG': 'Bot is live!',
}


class TestEspnEnvVars:
    '''Test gamedaybot/espn/env_vars.py against the shared get_common_env_vars() extraction'''

    def test_happy_path_matches_pre_refactor_behavior(self, monkeypatch):
        env = dict(COMMON_ENV)
        env.update({
            'LEAGUE_ID': '999888',
            'LEAGUE_YEAR': '2023',
            'SWID': 'ABCD-1234',
            'ESPN_S2': 'somelongcookievalue',
            'TOP_HALF_SCORING': 'true',
            'RANDOM_PHRASE': 'yes',
            'WAIVER_REPORT': 'true',
            'DAILY_WAIVER': 'true',
            'MONITOR_REPORT': 'false',
        })
        for key, value in env.items():
            monkeypatch.setenv(key, value)

        data = espn_env_vars.get_env_vars()

        assert data['ff_start_date'] == '2024-09-05'
        assert data['ff_end_date'] == '2025-01-05'
        assert data['my_timezone'] == 'America/Chicago'
        assert data['str_limit'] == 1000  # BOT_ID set, no DISCORD_WEBHOOK_URL override
        assert data['bot_id'] == '123456'
        assert data['slack_webhook_url'] == 1
        assert data['discord_webhook_url'] == 1
        assert data['init_msg'] == 'Bot is live!'
        assert data['daily_waiver'] is True
        assert data['monitor_report'] is False
        assert data['league_id'] == '999888'
        assert data['year'] == 2023
        assert data['swid'] == '{ABCD-1234}'
        assert data['espn_s2'] == 'somelongcookievalue'
        assert data['test'] is False
        assert data['top_half_scoring'] is True
        assert data['random_phrase'] is True
        assert data['waiver_report'] is True

    def test_defaults_when_optional_vars_unset(self, monkeypatch):
        monkeypatch.setenv('BOT_ID', '123456')
        monkeypatch.setenv('LEAGUE_ID', '1')
        for key in ('START_DATE', 'END_DATE', 'TIMEZONE', 'INIT_MSG', 'LEAGUE_YEAR', 'SWID',
                    'ESPN_S2', 'DAILY_WAIVER', 'MONITOR_REPORT', 'TOP_HALF_SCORING',
                    'RANDOM_PHRASE', 'WAIVER_REPORT', 'TEST'):
            monkeypatch.delenv(key, raising=False)

        data = espn_env_vars.get_env_vars()

        assert data['ff_start_date'] == '2024-09-05'
        assert data['ff_end_date'] == '2025-01-05'
        assert data['my_timezone'] == 'America/New_York'
        assert 'init_msg' not in data
        assert data['daily_waiver'] is False
        assert data['monitor_report'] is True
        assert data['year'] == 2024
        assert data['swid'] == '{1}'
        assert data['espn_s2'] == '1'
        assert data['test'] is False
        assert data['top_half_scoring'] is False
        assert data['random_phrase'] is False
        assert data['waiver_report'] is False

    def test_no_messaging_platform_raises_exception(self, monkeypatch):
        monkeypatch.setenv('LEAGUE_ID', '1')
        for key in ('BOT_ID', 'SLACK_WEBHOOK_URL', 'DISCORD_WEBHOOK_URL'):
            monkeypatch.delenv(key, raising=False)

        with pytest.raises(Exception) as exc_info:
            espn_env_vars.get_env_vars()

        assert 'No messaging platform info provided' in str(exc_info.value)


class TestSleeperEnvVars:
    '''Test gamedaybot/sleeper/env_vars.py against the shared get_common_env_vars() extraction'''

    def test_happy_path_matches_pre_refactor_behavior(self, monkeypatch):
        env = dict(COMMON_ENV)
        env['SLEEPER_LEAGUE_ID'] = '445566'
        for key, value in env.items():
            monkeypatch.setenv(key, value)

        data = sleeper_env_vars.get_env_vars()

        assert data['ff_start_date'] == '2024-09-05'
        assert data['ff_end_date'] == '2025-01-05'
        assert data['my_timezone'] == 'America/Chicago'
        assert data['str_limit'] == 1000
        assert data['bot_id'] == '123456'
        assert data['slack_webhook_url'] == 1
        assert data['discord_webhook_url'] == 1
        assert data['init_msg'] == 'Bot is live!'
        assert data['sleeper_league_id'] == '445566'

    def test_defaults_when_optional_vars_unset(self, monkeypatch):
        monkeypatch.setenv('BOT_ID', '123456')
        monkeypatch.setenv('SLEEPER_LEAGUE_ID', '1')
        for key in ('START_DATE', 'END_DATE', 'TIMEZONE', 'INIT_MSG'):
            monkeypatch.delenv(key, raising=False)

        data = sleeper_env_vars.get_env_vars()

        assert data['ff_start_date'] == '2024-09-05'
        assert data['ff_end_date'] == '2025-01-05'
        assert data['my_timezone'] == 'America/New_York'
        assert 'init_msg' not in data

    def test_no_messaging_platform_raises_same_exception_as_espn(self, monkeypatch):
        monkeypatch.setenv('SLEEPER_LEAGUE_ID', '1')
        for key in ('BOT_ID', 'SLACK_WEBHOOK_URL', 'DISCORD_WEBHOOK_URL'):
            monkeypatch.delenv(key, raising=False)

        with pytest.raises(Exception) as exc_info:
            sleeper_env_vars.get_env_vars()

        assert 'No messaging platform info provided' in str(exc_info.value)
