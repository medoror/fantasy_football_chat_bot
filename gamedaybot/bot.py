import os
import sys

sys.path.insert(1, os.path.abspath('.'))


def _espn_dispatch():
    """Lazily import and return the ESPN bot/scheduler callables."""

    from gamedaybot.espn.espn_bot import espn_bot
    from gamedaybot.espn.scheduler import scheduler
    return espn_bot, scheduler


def _sleeper_dispatch():
    """Lazily import and return the Sleeper bot/scheduler callables."""

    from gamedaybot.sleeper.sleeper_bot import sleeper_bot
    from gamedaybot.sleeper.scheduler import scheduler
    return sleeper_bot, scheduler


# Maps a normalized PLATFORM value to a callable returning
# (bot_callable, scheduler_callable) for that platform. Each entry imports
# only its own platform's modules, and only when actually dispatched to -
# adding a new provider is one more entry here, not another elif branch.
PLATFORMS = {
    'espn': _espn_dispatch,
    'sleeper': _sleeper_dispatch,
}


def get_platform_dispatch(platform):
    """
    Resolve a normalized platform name to its (bot_callable, scheduler_callable)
    pair, lazily importing only that platform's modules.

    Parameters
    ----------
    platform : str
        The platform name, expected to already be normalized (lowercased and
        stripped) by the caller.

    Returns
    -------
    tuple
        (bot_callable, scheduler_callable) for the requested platform.

    Raises
    ------
    ValueError
        If platform is not a recognized key in PLATFORMS.
    """

    try:
        dispatch = PLATFORMS[platform]
    except KeyError:
        raise ValueError(
            f"Unrecognized PLATFORM '{platform}'. Must be one of: {sorted(PLATFORMS)}")

    return dispatch()


if __name__ == '__main__':
    platform = os.environ.get('PLATFORM', 'espn').strip().lower()
    bot_fn, scheduler_fn = get_platform_dispatch(platform)

    bot_fn("init")
    scheduler_fn()
