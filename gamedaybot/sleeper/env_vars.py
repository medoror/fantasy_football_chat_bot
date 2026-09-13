import os
from gamedaybot.utils.env import get_common_env_vars


def get_env_vars():
    """
    Collect the environment variables needed to run the Sleeper bot.

    Sleeper's API is unauthenticated and needs no year/cookie auth, so this
    is deliberately smaller than the ESPN env_vars: only the messaging
    platform, schedule window, and SLEEPER_LEAGUE_ID are required.
    """

    data = get_common_env_vars()
    data['sleeper_league_id'] = os.environ['SLEEPER_LEAGUE_ID']
    return data
