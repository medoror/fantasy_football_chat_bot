# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Testing:**
```bash
pip install -r requirements-test.txt
pytest
```

**Linting:**
```bash
flake8
```

**Running the Bot:**
```bash
# Local development
python3 gamedaybot/espn/espn_bot.py

# With Docker
docker build -t fantasy_football_chat_bot .
docker run --rm=True \
  -e BOT_ID=$BOT_ID \
  -e LEAGUE_ID=$LEAGUE_ID \
  -e LEAGUE_YEAR=$LEAGUE_YEAR \
  fantasy_football_chat_bot
```

## Architecture Overview

This is an ESPN Fantasy Football chat bot that sends automated messages to GroupMe, Slack, or Discord channels. The bot runs on a scheduled basis and provides league updates, scores, standings, and other fantasy football information.

### Core Structure

**Main Entry Point:**
- `gamedaybot/espn/espn_bot.py` - Contains the main `espn_bot()` function that orchestrates all bot functionality

**Key Components:**
- `gamedaybot/espn/functionality.py` - Core ESPN fantasy football functions (scores, standings, matchups, power rankings, etc.)
- `gamedaybot/espn/scheduler.py` - APScheduler-based job scheduling for automated messages
- `gamedaybot/espn/env_vars.py` - Environment variable management and defaults
- `gamedaybot/chat/` - Platform-specific messaging clients (GroupMe, Slack, Discord)
- `gamedaybot/utils/util.py` - Utility functions including string manipulation and message splitting

**Message Functions:**
The bot supports these scheduled message types:
- `get_matchups` - Weekly matchups with projections
- `get_scoreboard_short` - Current scores
- `get_power_rankings` - League power rankings
- `get_trophies` - Weekly awards (high score, low score, etc.)
- `get_standings` - League standings
- `get_waiver_report` - Add/drop transactions (requires ESPN_S2/SWID)
- `get_monitor` - Player status alerts
- `get_close_scores` - Games within scoring threshold

### Dependencies

- `espn_api` - ESPN Fantasy API wrapper for league data
- `apscheduler` - Job scheduling for automated messages
- `requests` - HTTP requests for webhook messaging

### Environment Configuration

The bot requires these key environment variables:
- `LEAGUE_ID` - ESPN league identifier
- `LEAGUE_YEAR` - Fantasy season year
- `START_DATE/END_DATE` - Bot active period
- One of: `BOT_ID` (GroupMe), `SLACK_WEBHOOK_URL`, or `DISCORD_WEBHOOK_URL`
- `ESPN_S2/SWID` - Required for private leagues and waiver reports

### Testing Strategy

Tests use `pytest` with mocking via `requests_mock` for HTTP calls. Test files mirror the source structure in the `tests/` directory.