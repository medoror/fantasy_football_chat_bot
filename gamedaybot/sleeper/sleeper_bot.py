import os
if os.environ.get("AWS_EXECUTION_ENV") is not None:
    # For use in lambda function
    import utils.util as util
    from chat.groupme import GroupMe
    from chat.slack import Slack
    from chat.discord import Discord
else:
    # For local use
    import sys
    sys.path.insert(1, os.path.abspath('.'))
    import gamedaybot.utils.util as util
    from gamedaybot.chat.groupme import GroupMe
    from gamedaybot.chat.slack import Slack
    from gamedaybot.chat.discord import Discord
    from gamedaybot.sleeper.env_vars import get_env_vars
    import gamedaybot.sleeper.functionality as sleeper
    from gamedaybot.sleeper.sleeper_api import SleeperAPI


import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def sleeper_bot(function):
    """
    This function is used to send messages to a messaging platform (e.g. Slack, Discord, or GroupMe) with information
    about a Sleeper fantasy football league.

    Parameters
    ----------
    function: str
        A string that specifies which type of information to send.

    Returns
    -------
    None

    Notes
    -----
    Sleeper v1 supports a reduced feature set compared to the ESPN bot, since
    Sleeper's API exposes no projected-points data. See
    gamedaybot/sleeper/functionality.py.

    Possible function values:

    get_standings: sends a message with the standings for the league.
    get_trophies: sends a message with the trophies for the league.
    get_scoreboard_short: sends a short version of the current week's scores.
    get_matchups: sends the current week's matchups and records.
    get_waiver_report: sends a message with today's waiver/free-agent transactions.
    get_final: sends the final scores and trophies for the previous week.
    get_power_rankings: sends a message with the power rankings for the league.
    broadcast: sends a custom broadcast message.
    init: sends a message to confirm that the bot has been set up.
    """

    data = get_env_vars()
    str_limit = data['str_limit']  # slack char limit

    try:
        bot_id = data['bot_id']
    except KeyError:
        bot_id = 1

    try:
        slack_webhook_url = data['slack_webhook_url']
    except KeyError:
        slack_webhook_url = 1

    try:
        discord_webhook_url = data['discord_webhook_url']
    except KeyError:
        discord_webhook_url = 1

    groupme_bot = GroupMe(bot_id)
    slack_bot = Slack(slack_webhook_url)
    discord_bot = Discord(discord_webhook_url)

    client = SleeperAPI(data['sleeper_league_id'])

    try:
        broadcast_message = data['broadcast_message']
    except KeyError:
        broadcast_message = None

    text = ''
    logger.info("Function: " + function)

    if function == "get_standings":
        text = sleeper.get_standings(client)
    elif function == "get_trophies":
        text = sleeper.get_trophies(client)
    elif function == "get_scoreboard_short":
        text = sleeper.get_scoreboard_short(client)
    elif function == "get_matchups":
        text = sleeper.get_matchups(client)
    elif function == "get_waiver_report":
        text = sleeper.get_waiver_report(client)
    elif function == "get_final":
        text = sleeper.get_final(client)
    elif function == "get_power_rankings":
        text = sleeper.get_power_rankings(client)
    elif function == "broadcast":
        try:
            text = broadcast_message
        except KeyError:
            # do nothing here, empty broadcast message
            pass
    elif function == "init":
        try:
            text = data["init_msg"]
        except KeyError:
            # do nothing here, empty init message
            pass
    else:
        text = "Something bad happened. HALP"

    logger.debug(data)
    if text != '':
        logger.debug(text)
        messages = util.str_limit_check(text, str_limit)
        for message in messages:
            groupme_bot.send_message(message)
            slack_bot.send_message(message)
            discord_bot.send_message(message)


if __name__ == '__main__':
    from gamedaybot.sleeper.scheduler import scheduler

    sleeper_bot("init")
    scheduler()
