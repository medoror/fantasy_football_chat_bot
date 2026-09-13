import sys
import os
sys.path.insert(1, os.path.abspath('.'))
import pytest
import gamedaybot.bot as bot


class TestGetPlatformDispatch:
    '''Test PLATFORM validation and lazy registry dispatch in gamedaybot/bot.py'''

    def test_espn_platform_resolves_espn_bot_and_scheduler(self):
        bot_fn, scheduler_fn = bot.get_platform_dispatch('espn')

        from gamedaybot.espn.espn_bot import espn_bot
        from gamedaybot.espn.scheduler import scheduler

        assert bot_fn is espn_bot
        assert scheduler_fn is scheduler

    def test_sleeper_platform_resolves_sleeper_bot_and_scheduler(self):
        bot_fn, scheduler_fn = bot.get_platform_dispatch('sleeper')

        from gamedaybot.sleeper.sleeper_bot import sleeper_bot
        from gamedaybot.sleeper.scheduler import scheduler

        assert bot_fn is sleeper_bot
        assert scheduler_fn is scheduler

    def test_platform_name_is_case_and_whitespace_normalized_by_caller(self):
        # get_platform_dispatch expects an already-normalized platform name -
        # the same .strip().lower() the __main__ block applies to the raw
        # PLATFORM env var. Confirm a raw value normalized that way still
        # resolves correctly, both for a mixed-case value and one with
        # incidental whitespace.
        from gamedaybot.sleeper.sleeper_bot import sleeper_bot
        from gamedaybot.espn.espn_bot import espn_bot

        bot_fn, _ = bot.get_platform_dispatch('  Sleeper  '.strip().lower())
        assert bot_fn is sleeper_bot

        bot_fn, _ = bot.get_platform_dispatch(' ESPN'.strip().lower())
        assert bot_fn is espn_bot

    def test_invalid_platform_raises_clear_actionable_error(self):
        with pytest.raises(ValueError) as exc_info:
            bot.get_platform_dispatch('yahoo')

        message = str(exc_info.value)
        # The error must name the invalid value and the allowed set, rather
        # than silently falling back to a default platform.
        assert 'yahoo' in message
        assert 'espn' in message
        assert 'sleeper' in message

    def test_platforms_registry_has_exactly_espn_and_sleeper(self):
        assert set(bot.PLATFORMS.keys()) == {'espn', 'sleeper'}
