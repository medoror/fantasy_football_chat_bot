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
python3 gamedaybot/bot.py

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
- `gamedaybot/bot.py` - The platform-neutral process entry point (`python3 gamedaybot/bot.py`). Its `__main__` block reads `PLATFORM` (defaulting to `espn` only when the env var is unset), validates it against the `PLATFORMS` registry, and raises `ValueError` for anything unrecognized rather than silently falling back to ESPN. `PLATFORMS` maps a platform name to a function that lazily imports and returns that platform's `(bot_callable, scheduler_callable)` pair - only the selected platform's modules are ever imported, and adding a third provider is one registry entry, not another branch. `gamedaybot/espn/espn_bot.py` itself has zero awareness of Sleeper: its own `__main__` block is ESPN-only (kept for direct/local invocation of that module specifically), same as `gamedaybot/sleeper/sleeper_bot.py`'s.

**ESPN Components (PLATFORM=espn, the default):**
- `gamedaybot/espn/functionality.py` - Core ESPN fantasy football functions (scores, standings, matchups, power rankings, etc.)
- `gamedaybot/espn/scheduler.py` - APScheduler-based job scheduling for automated messages
- `gamedaybot/espn/env_vars.py` - ESPN-specific env vars (LEAGUE_ID/LEAGUE_YEAR/SWID/ESPN_S2/TEST/TOP_HALF_SCORING/RANDOM_PHRASE/WAIVER_REPORT/DAILY_WAIVER/MONITOR_REPORT), layered on top of `get_common_env_vars()`
- `gamedaybot/chat/` - Platform-specific messaging clients (GroupMe, Slack, Discord), shared with Sleeper
- `gamedaybot/utils/util.py` - Utility functions including string manipulation and message splitting
- `gamedaybot/utils/env.py` - `get_common_env_vars()`, the platform-agnostic env var block (schedule window, messaging platform config/str_limit, INIT_MSG) shared by both `gamedaybot/espn/env_vars.py` and `gamedaybot/sleeper/env_vars.py`

**Sleeper Components (PLATFORM=sleeper):**
Sleeper (`api.sleeper.app/v1`) is unauthenticated and needs no year/cookie auth - a league is
identified solely by `SLEEPER_LEAGUE_ID`. It is implemented as a parallel package (not a
shared-interface refactor of the ESPN side), with a **reduced feature set**: standings, trophies
(high/low score, closest score/biggest blowout, lucky/unlucky), a scoreboard, matchups (no
projections), a waiver report, a final recap, and power rankings. Power rankings are a faithful port
of ESPN's own two-step-dominance / 80-15-5 algorithm (see `_two_step_dominance`/`_power_points` in
functionality.py, ported line-for-line from the installed espn_api package's
`espn_api/football/utils.py` and `espn_api/football/league.py`), computed cumulatively from
Sleeper's weekly matchup data instead of espn_api's Team objects; the playoff-percentage column is
omitted since Sleeper has no equivalent field. Player monitor and every projection-based feature
(projected scoreboard, projection-based close scores, achiever/underachiever trophies) are
intentionally **not implemented** for Sleeper, because Sleeper's REST API exposes no
projected-points field.
- `gamedaybot/sleeper/sleeper_api.py` - Thin REST client for `/league/{id}`, `/league/{id}/rosters`,
  `/league/{id}/users`, `/league/{id}/matchups/{week}`, `/league/{id}/transactions/{week}`,
  `/state/nfl`, and `/players/nfl`. `/players/nfl` returns a ~5MB payload; per Sleeper's docs it is
  cached to disk and fetched at most once per day.
- `gamedaybot/sleeper/functionality.py` - `get_standings`, `get_trophies`, `get_scoreboard_short`,
  `get_matchups`, `get_waiver_report`, `get_final`, and `get_power_rankings` for Sleeper leagues.
  Sleeper's API is unauthenticated, so `get_waiver_report` is always available (no ESPN_S2/SWID-style
  credential gate). `get_power_rankings` issues one `/matchups/{week}` request per historical week
  (1..week), for both the current and previous snapshots it diffs - acceptable given Sleeper's
  generous rate limits, but worth knowing before calling it deep into a long season.
- `gamedaybot/sleeper/scheduler.py` - Scheduling for the reduced Sleeper function set (no monitor job)
- `gamedaybot/sleeper/env_vars.py` - Sleeper-specific env vars (just `SLEEPER_LEAGUE_ID`), layered on top of `get_common_env_vars()`
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
(no projections), `get_waiver_report`, `get_final`, and `get_power_rankings`. It does not support
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

Tests use `pytest` with mocking via `requests_mock` for HTTP calls. Test files mirror the source structure in the `tests/` directory. Sleeper tests (`tests/test_sleeper_api.py`, `tests/test_sleeper_functionality.py`) mock the Sleeper REST endpoints with representative JSON payloads and include coverage of the `/players/nfl` daily disk-cache behavior. `tests/test_bot.py` covers `gamedaybot/bot.py`'s `PLATFORM` validation/dispatch, and `tests/test_env_vars.py` covers `gamedaybot/espn/env_vars.py`/`gamedaybot/sleeper/env_vars.py` (via `monkeypatch`'d env vars) to confirm the shared `get_common_env_vars()` extraction preserves each platform's original behavior.