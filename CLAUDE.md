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

This is a Fantasy Football chat bot that sends automated messages to GroupMe, Slack, or Discord channels. It supports two fantasy platforms, selected via the `PLATFORM` env var: ESPN (default) and Sleeper. The bot runs on a scheduled basis and provides league updates, scores, standings, and other fantasy football information.

### Core Structure

**Main Entry Point:**
- `gamedaybot/espn/espn_bot.py` - Contains the main `espn_bot()` function that orchestrates ESPN bot functionality. Its `__main__` block also reads `PLATFORM` and dispatches to the Sleeper bot/scheduler instead when `PLATFORM=sleeper`.

**ESPN Components (PLATFORM=espn, the default):**
- `gamedaybot/espn/functionality.py` - Core ESPN fantasy football functions (scores, standings, matchups, power rankings, etc.)
- `gamedaybot/espn/scheduler.py` - APScheduler-based job scheduling for automated messages
- `gamedaybot/espn/env_vars.py` - Environment variable management and defaults
- `gamedaybot/chat/` - Platform-specific messaging clients (GroupMe, Slack, Discord), shared with Sleeper
- `gamedaybot/utils/util.py` - Utility functions including string manipulation and message splitting

**Sleeper Components (PLATFORM=sleeper):**
Sleeper (`api.sleeper.app/v1`) is unauthenticated and needs no year/cookie auth - a league is
identified solely by `SLEEPER_LEAGUE_ID`. It is implemented as a parallel package (not a
shared-interface refactor of the ESPN side), with a **reduced feature set**: standings, trophies
(high/low score, closest score/biggest blowout, lucky/unlucky), a scoreboard, matchups (no
projections), a waiver report, and a final recap. Power rankings, player monitor, and every
projection-based feature (projected scoreboard, projection-based close scores, achiever/
underachiever trophies) are intentionally **not implemented** for Sleeper, because Sleeper's REST
API exposes no projected-points field and computing power rankings would require lineup/roster data
out of scope for this version.
- `gamedaybot/sleeper/sleeper_api.py` - Thin REST client for `/league/{id}`, `/league/{id}/rosters`,
  `/league/{id}/users`, `/league/{id}/matchups/{week}`, `/league/{id}/transactions/{week}`,
  `/state/nfl`, and `/players/nfl`. `/players/nfl` returns a ~5MB payload; per Sleeper's docs it is
  cached to disk and fetched at most once per day.
- `gamedaybot/sleeper/functionality.py` - `get_standings`, `get_trophies`, `get_scoreboard_short`,
  `get_matchups`, `get_waiver_report`, and `get_final` for Sleeper leagues. Sleeper's API is
  unauthenticated, so `get_waiver_report` is always available (no ESPN_S2/SWID-style credential gate).
- `gamedaybot/sleeper/scheduler.py` - Scheduling for the reduced Sleeper function set (no power
  rankings or monitor job)
- `gamedaybot/sleeper/env_vars.py` - Environment variable management for Sleeper
- `gamedaybot/sleeper/sleeper_bot.py` - Thin entry point mirroring `espn_bot.py` for Sleeper

**Message Functions:**
The ESPN bot supports these scheduled message types:
- `get_matchups` - Weekly matchups with projections
- `get_scoreboard_short` - Current scores
- `get_power_rankings` - League power rankings
- `get_trophies` - Weekly awards (high score, low score, etc.)
- `get_standings` - League standings
- `get_waiver_report` - Add/drop transactions (requires ESPN_S2/SWID)
- `get_monitor` - Player status alerts
- `get_close_scores` - Games within scoring threshold

The Sleeper bot supports `get_standings`, `get_trophies`, `get_scoreboard_short`, `get_matchups`
(no projections), `get_waiver_report`, and `get_final`. It does not support `get_power_rankings`,
`get_monitor`, `get_close_scores`, or `get_projected_scoreboard` (see above for why).

### Dependencies

- `espn_api` - ESPN Fantasy API wrapper for league data
- `apscheduler` - Job scheduling for automated messages
- `requests` - HTTP requests for webhook messaging and the Sleeper REST client

### Environment Configuration

The bot requires these key environment variables:
- `PLATFORM` - `espn` (default) or `sleeper`. Unset or `espn` preserves all existing ESPN behavior byte-for-byte.
- `LEAGUE_ID` - ESPN league identifier (ESPN only)
- `LEAGUE_YEAR` - Fantasy season year (ESPN only)
- `SLEEPER_LEAGUE_ID` - Sleeper league identifier (Sleeper only)
- `START_DATE/END_DATE` - Bot active period
- One of: `BOT_ID` (GroupMe), `SLACK_WEBHOOK_URL`, or `DISCORD_WEBHOOK_URL`
- `ESPN_S2/SWID` - Required for private ESPN leagues and waiver reports

### Testing Strategy

Tests use `pytest` with mocking via `requests_mock` for HTTP calls. Test files mirror the source structure in the `tests/` directory. Sleeper tests (`tests/test_sleeper_api.py`, `tests/test_sleeper_functionality.py`) mock the Sleeper REST endpoints with representative JSON payloads and include coverage of the `/players/nfl` daily disk-cache behavior.