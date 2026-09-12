import os


def get_env_vars():
    """
    Collect the environment variables needed to run the Sleeper bot.

    Sleeper's API is unauthenticated and needs no year/cookie auth, so this
    is deliberately smaller than the ESPN env_vars: only the messaging
    platform, schedule window, and SLEEPER_LEAGUE_ID are required.
    """

    data = {}

    try:
        ff_start_date = os.environ['START_DATE']
    except KeyError:
        ff_start_date = '2024-09-05'
    data['ff_start_date'] = ff_start_date

    try:
        ff_end_date = os.environ['END_DATE']
    except KeyError:
        ff_end_date = '2025-01-05'
    data['ff_end_date'] = ff_end_date

    try:
        my_timezone = os.environ['TIMEZONE']
    except KeyError:
        my_timezone = 'America/New_York'
    data['my_timezone'] = my_timezone

    str_limit = 40000  # slack char limit

    try:
        bot_id = os.environ['BOT_ID']
        str_limit = 1000
    except KeyError:
        bot_id = 1

    try:
        slack_webhook_url = os.environ['SLACK_WEBHOOK_URL']
    except KeyError:
        slack_webhook_url = 1

    try:
        discord_webhook_url = os.environ['DISCORD_WEBHOOK_URL']
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

    data['sleeper_league_id'] = os.environ['SLEEPER_LEAGUE_ID']

    try:
        data['init_msg'] = os.environ['INIT_MSG']
    except KeyError:
        # do nothing here, empty init message
        pass

    return data
