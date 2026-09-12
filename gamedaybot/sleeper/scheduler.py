from apscheduler.schedulers.blocking import BlockingScheduler
from gamedaybot.sleeper.sleeper_bot import sleeper_bot
from gamedaybot.sleeper.env_vars import get_env_vars


def scheduler():
    """
    This function is used to schedule jobs to send messages for the Sleeper bot.

    Sleeper v1 only supports standings and trophies (see
    gamedaybot/sleeper/functionality.py for why power rankings and
    projection-based features are not implemented), so there is
    intentionally no power-rankings job here.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    data = get_env_vars()
    sched = BlockingScheduler(job_defaults={'misfire_grace_time': 15 * 60})
    ff_start_date = data['ff_start_date']
    ff_end_date = data['ff_end_date']
    my_timezone = data['my_timezone']

    # trophies:  tuesday morning at 7:30am local time.
    # standings: wednesday morning at 7:30am local time.

    sched.add_job(sleeper_bot, 'cron', ['get_trophies'], id='trophies',
                  day_of_week='tue', hour=7, minute=30, start_date=ff_start_date, end_date=ff_end_date,
                  timezone=my_timezone, replace_existing=True)
    sched.add_job(sleeper_bot, 'cron', ['get_standings'], id='standings',
                  day_of_week='wed', hour=7, minute=30, start_date=ff_start_date, end_date=ff_end_date,
                  timezone=my_timezone, replace_existing=True)

    print("Ready!")
    sched.start()
