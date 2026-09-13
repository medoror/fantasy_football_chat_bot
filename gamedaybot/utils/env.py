import os


def get_common_env_vars():
    """
    Collect the environment variables shared by every platform bot: the
    schedule window (START_DATE/END_DATE/TIMEZONE), the messaging platform
    configuration (BOT_ID/SLACK_WEBHOOK_URL/DISCORD_WEBHOOK_URL and the
    resulting slack char limit), and the optional INIT_MSG.

    Platform-specific env_vars modules call this first, then layer their own
    league-identity vars (e.g. LEAGUE_ID for ESPN, SLEEPER_LEAGUE_ID for
    Sleeper) on top of the returned dict.

    Returns
    -------
    dict
        A dict with keys: ff_start_date, ff_end_date, my_timezone, str_limit,
        bot_id, slack_webhook_url, discord_webhook_url, and (if set) init_msg.

    Raises
    ------
    Exception
        If none of BOT_ID, SLACK_WEBHOOK_URL, or DISCORD_WEBHOOK_URL is set.
    """

    data = {}

    try:
        ff_start_date = os.environ["START_DATE"]
    except KeyError:
        ff_start_date = '2024-09-05'

    data['ff_start_date'] = ff_start_date

    try:
        ff_end_date = os.environ["END_DATE"]
    except KeyError:
        ff_end_date = '2025-01-05'

    data['ff_end_date'] = ff_end_date

    try:
        my_timezone = os.environ["TIMEZONE"]
    except KeyError:
        my_timezone = 'America/New_York'

    data['my_timezone'] = my_timezone

    str_limit = 40000  # slack char limit

    try:
        bot_id = os.environ["BOT_ID"]
        str_limit = 1000
    except KeyError:
        bot_id = 1

    try:
        slack_webhook_url = os.environ["SLACK_WEBHOOK_URL"]
    except KeyError:
        slack_webhook_url = 1

    try:
        discord_webhook_url = os.environ["DISCORD_WEBHOOK_URL"]
        str_limit = 3000
    except KeyError:
        discord_webhook_url = 1

    if (len(str(bot_id)) <= 1 and
        len(str(slack_webhook_url)) <= 1 and
            len(str(discord_webhook_url)) <= 1):
        # Ensure that there's info for at least one messaging platform,
        # use length of str in case of blank but non null env variable
        raise Exception(
            "No messaging platform info provided. Be sure one of BOT_ID, SLACK_WEBHOOK_URL, "
            "or DISCORD_WEBHOOK_URL env variables are set")

    data['str_limit'] = str_limit
    data['bot_id'] = bot_id
    data['slack_webhook_url'] = slack_webhook_url
    data['discord_webhook_url'] = discord_webhook_url

    try:
        data['init_msg'] = os.environ["INIT_MSG"]
    except KeyError:
        # do nothing here, empty init message
        pass

    return data
