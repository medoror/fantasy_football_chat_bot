from datetime import date


def _team_names_by_roster_id(rosters, users):
    """
    Build a mapping of roster_id -> display team name, preferring the
    owner's custom team_name and falling back to their display_name.
    """

    users_by_id = {u['user_id']: u for u in users}
    team_names = {}
    for roster in rosters:
        user = users_by_id.get(roster.get('owner_id'), {})
        metadata = user.get('metadata') or {}
        team_name = metadata.get('team_name') or user.get('display_name') or f"Team {roster['roster_id']}"
        team_names[roster['roster_id']] = team_name
    return team_names


def _wins_losses_ties(roster):
    """
    Extract (wins, losses, ties) from a roster's settings, treating a
    missing or null "settings" (sent by Sleeper for uninitialized/newly-joined
    rosters) as all zeroes.
    """

    settings = roster.get('settings') or {}
    return settings.get('wins', 0), settings.get('losses', 0), settings.get('ties', 0)


def _format_record(wins, losses, ties):
    if ties:
        return f'{wins}-{losses}-{ties}'
    return f'{wins}-{losses}'


def _paired_matchups(matchups):
    """
    Group matchup entries by matchup_id into head-to-head pairs.

    Rosters on a bye have matchup_id: null and no real opponent, so they are
    excluded before grouping. Any group that doesn't end up with exactly two
    entries (a malformed payload) is skipped.

    Returns
    -------
    list of tuple
        A list of (entry_a, entry_b) pairs.
    """

    grouped = {}
    for m in matchups:
        if m.get('matchup_id') is None:
            continue
        grouped.setdefault(m['matchup_id'], []).append(m)

    return [tuple(entries) for entries in grouped.values() if len(entries) == 2]


def _player_display_name(player):
    full_name = player.get('full_name')
    if full_name:
        return full_name
    name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
    return name or 'Unknown Player'


def get_standings(client):
    """
    Retrieve the current standings for a Sleeper fantasy football league.

    Parameters
    ----------
    client : gamedaybot.sleeper.sleeper_api.SleeperAPI
        The Sleeper API client for the league to retrieve standings for.

    Returns
    -------
    str
        A string containing the current standings, formatted as a list of teams with their records and positions.
    """

    rosters = client.get_rosters()
    users = client.get_users()
    team_names = _team_names_by_roster_id(rosters, users)

    standings = []
    for roster in rosters:
        wins, losses, ties = _wins_losses_ties(roster)
        settings = roster.get('settings') or {}
        fpts = settings.get('fpts', 0) + settings.get('fpts_decimal', 0) / 100
        standings.append((wins, losses, ties, fpts, team_names[roster['roster_id']]))

    # Ties count as partial wins for ranking purposes, so a 5-0-2 record ranks
    # above a 5-2-0 record even though both have 5 wins.
    standings.sort(key=lambda row: (row[0] + 0.5 * row[2], row[3]), reverse=True)

    show_ties = any(row[2] for row in standings)
    if show_ties:
        standings_txt = [f"{pos + 1:2}: ({wins}-{losses}-{ties}) {team_name} " for
                         pos, (wins, losses, ties, fpts, team_name) in enumerate(standings)]
    else:
        standings_txt = [f"{pos + 1:2}: ({wins}-{losses}) {team_name} " for
                         pos, (wins, losses, ties, fpts, team_name) in enumerate(standings)]

    text = ['Current Standings'] + standings_txt
    return '\n'.join(text)


def _get_lucky_trophy(weekly_scores):
    """
    Determine the lucky (won despite a poor points-rank) and unlucky (lost
    despite a strong points-rank) teams for the week, based purely on where
    each team's score ranks against the rest of the league.

    Parameters
    ----------
    weekly_scores : dict
        A mapping of team_name -> [points, 'W'/'L'] for the week.

    Returns
    -------
    list of str
        The lucky/unlucky trophy lines, or an empty list if no matchups were decided.
    """

    decided = {name: result for name, result in weekly_scores.items() if result[1] in ('W', 'L')}
    if not decided:
        return []

    num_teams = len(decided) - 1

    losses = 0
    unlucky_team = None
    unlucky_record = None
    for team_name, (points, result) in sorted(decided.items(), key=lambda item: item[1][0], reverse=True):
        if result == 'L':
            unlucky_team = team_name
            unlucky_record = f'{num_teams - losses}-{losses}'
            break
        losses += 1

    wins = 0
    lucky_team = None
    lucky_record = None
    for team_name, (points, result) in sorted(decided.items(), key=lambda item: item[1][0]):
        if result == 'W':
            lucky_team = team_name
            lucky_record = f'{wins}-{num_teams - wins}'
            break
        wins += 1

    trophies = []
    if lucky_team is not None:
        trophies += ['🍀 Lucky 🍀'] + \
            ['%s was %s against the league, but still got the win' % (lucky_team, lucky_record)]
    if unlucky_team is not None:
        trophies += ['😡 Unlucky 😡'] + \
            ['%s was %s against the league, but still took an L' % (unlucky_team, unlucky_record)]
    return trophies


def get_trophies(client, week=None):
    """
    Retrieve weekly trophies for a Sleeper fantasy football league: highest score, lowest score,
    closest score, biggest blowout, and lucky/unlucky (record vs. points-rank mismatch).

    Note
    ----
    Sleeper's REST API has no projected-points field anywhere, so the
    over-achiever / under-achiever trophies (which compare actual vs.
    projected score in the ESPN implementation) cannot be computed here and
    are intentionally omitted for this platform.

    Parameters
    ----------
    client : gamedaybot.sleeper.sleeper_api.SleeperAPI
        The Sleeper API client for the league to retrieve trophies for.
    week : int, optional
        The week for which to retrieve trophies. Defaults to the prior completed week.

    Returns
    -------
    str
        A string representing the trophies of the week.
    """

    if not week:
        state = client.get_nfl_state()
        week = max(int(state['week']) - 1, 1)

    matchups = client.get_matchups(week)
    rosters = client.get_rosters()
    users = client.get_users()
    team_names = _team_names_by_roster_id(rosters, users)

    # Rosters on a bye have matchup_id: null and no real opponent to compare
    # against; exclude them from both the score pool and matchup pairing.
    matchups = [m for m in matchups if m.get('matchup_id') is not None]

    if not matchups:
        return '\n'.join(['Trophies of the week:', 'No matchups available for this week'])

    scores = [(m['points'], team_names.get(m['roster_id'], f"Team {m['roster_id']}")) for m in matchups]
    high_points, high_team = max(scores, key=lambda s: s[0])
    low_points, low_team = min(scores, key=lambda s: s[0])

    closest_diff = None
    close_winner = close_loser = None
    biggest_diff = -1
    blowout_winner = blowout_loser = None
    weekly_scores = {}

    for a, b in _paired_matchups(matchups):
        a_name = team_names.get(a['roster_id'], f"Team {a['roster_id']}")
        b_name = team_names.get(b['roster_id'], f"Team {b['roster_id']}")
        diff = abs(a['points'] - b['points'])

        if a['points'] == b['points']:
            weekly_scores[a_name] = [a['points'], 'T']
            weekly_scores[b_name] = [b['points'], 'T']
            continue

        if a['points'] > b['points']:
            winner_name, winner_points = a_name, a['points']
            loser_name, loser_points = b_name, b['points']
        else:
            winner_name, winner_points = b_name, b['points']
            loser_name, loser_points = a_name, a['points']

        weekly_scores[winner_name] = [winner_points, 'W']
        weekly_scores[loser_name] = [loser_points, 'L']

        if closest_diff is None or diff < closest_diff:
            closest_diff = diff
            close_winner, close_loser = winner_name, loser_name
        if diff > biggest_diff:
            biggest_diff = diff
            blowout_winner, blowout_loser = winner_name, loser_name

    high_score_str = ['👑 High score 👑'] + ['%s with %.2f points' % (high_team, high_points)]
    low_score_str = ['💩 Low score 💩'] + ['%s with %.2f points' % (low_team, low_points)]

    text = ['Trophies of the week:'] + high_score_str + low_score_str

    if blowout_winner is not None:
        text += ['😱 Blow out 😱'] + ['%s blew out %s by %.2f points' % (blowout_winner, blowout_loser, biggest_diff)]
    if close_winner is not None:
        text += ['😅 Close win 😅'] + ['%s barely beat %s by %.2f points' % (close_winner, close_loser, closest_diff)]

    text += _get_lucky_trophy(weekly_scores)

    return '\n'.join(text)


def get_scoreboard_short(client, week=None):
    """
    Retrieve the scoreboard for a given week of a Sleeper fantasy football league.

    Parameters
    ----------
    client : gamedaybot.sleeper.sleeper_api.SleeperAPI
        The Sleeper API client for the league to retrieve the scoreboard for.
    week : int, optional
        The week for which to retrieve the scoreboard. Defaults to the current week.

    Returns
    -------
    str
        A string containing the scoreboard for the given week, formatted as a list of matchups.
    """

    if not week:
        state = client.get_nfl_state()
        week = int(state['week'])

    matchups = client.get_matchups(week)
    rosters = client.get_rosters()
    users = client.get_users()
    team_names = _team_names_by_roster_id(rosters, users)

    score = []
    for a, b in _paired_matchups(matchups):
        a_name = team_names.get(a['roster_id'], f"Team {a['roster_id']}")
        b_name = team_names.get(b['roster_id'], f"Team {b['roster_id']}")
        score.append('%4s %6.2f - %6.2f %s' % (a_name, a['points'], b['points'], b_name))

    text = ['Score Update'] + score
    return '\n'.join(text)


def get_matchups(client, week=None):
    """
    Retrieve the matchups for a given week in a Sleeper fantasy football league.

    Note
    ----
    Sleeper has no per-player projected-points field, so unlike the ESPN
    version this does not append a projected scoreboard.

    Parameters
    ----------
    client : gamedaybot.sleeper.sleeper_api.SleeperAPI
        The Sleeper API client for the league to retrieve the matchups for.
    week : int, optional
        The week for which to retrieve the matchups. Defaults to the current week.

    Returns
    -------
    str
        A string containing the matchups for the given week, formatted as a list of team names and records.
    """

    if not week:
        state = client.get_nfl_state()
        week = int(state['week'])

    matchups = client.get_matchups(week)
    rosters = client.get_rosters()
    users = client.get_users()
    team_names = _team_names_by_roster_id(rosters, users)
    records = {roster['roster_id']: _wins_losses_ties(roster) for roster in rosters}

    full_names = []
    records_txt = []
    for a, b in _paired_matchups(matchups):
        a_name = team_names.get(a['roster_id'], f"Team {a['roster_id']}")
        b_name = team_names.get(b['roster_id'], f"Team {b['roster_id']}")
        full_names.append('%s vs %s' % (a_name, b_name))

        a_record = _format_record(*records.get(a['roster_id'], (0, 0, 0)))
        b_record = _format_record(*records.get(b['roster_id'], (0, 0, 0)))
        records_txt.append('%4s (%s) vs (%s) %s' % (a_name, a_record, b_record, b_name))

    text = ['Matchups'] + full_names + [''] + records_txt
    return '\n'.join(text)


def get_waiver_report(client, week=None):
    """
    Retrieve a waiver report of today's completed waiver/free-agent transactions for a
    Sleeper fantasy football league.

    Parameters
    ----------
    client : gamedaybot.sleeper.sleeper_api.SleeperAPI
        The Sleeper API client for the league to retrieve the waiver report for.
    week : int, optional
        The week (transaction round) for which to retrieve the waiver report. Defaults to the current week.

    Returns
    -------
    str
        A string containing the waiver report.
    """

    if not week:
        state = client.get_nfl_state()
        week = int(state['week'])

    transactions = client.get_transactions(week)
    rosters = client.get_rosters()
    users = client.get_users()
    team_names = _team_names_by_roster_id(rosters, users)
    players = client.get_players()

    today = date.today().strftime('%Y-%m-%d')
    report = []

    for txn in transactions:
        if txn.get('type') not in ('waiver', 'free_agent'):
            continue
        # A failed waiver claim never actually added or dropped anyone.
        if txn.get('status') != 'complete':
            continue

        created = txn.get('created')
        if created is None:
            continue
        txn_date = date.fromtimestamp(created / 1000).strftime('%Y-%m-%d')
        if txn_date != today:
            continue

        adds = txn.get('adds') or {}
        drops = txn.get('drops') or {}
        settings = txn.get('settings') or {}
        faab = settings.get('waiver_bid')

        by_roster = {}
        for player_id, roster_id in adds.items():
            by_roster.setdefault(roster_id, {'adds': [], 'drops': []})['adds'].append(player_id)
        for player_id, roster_id in drops.items():
            by_roster.setdefault(roster_id, {'adds': [], 'drops': []})['drops'].append(player_id)

        for roster_id, moves in by_roster.items():
            team_name = team_names.get(roster_id, f"Team {roster_id}")
            lines = []
            for player_id in moves['adds']:
                player = players.get(player_id, {})
                name = _player_display_name(player)
                position = player.get('position', '')
                if faab is not None:
                    lines.append(f'ADDED {position} {name} (${faab})')
                else:
                    lines.append(f'ADDED {position} {name}')
            for player_id in moves['drops']:
                player = players.get(player_id, {})
                name = _player_display_name(player)
                position = player.get('position', '')
                lines.append(f'DROPPED {position} {name}')

            if lines:
                s = f'{team_name} \n' + '\n'.join(lines) + '\n'
                report.append(s.lstrip())

    report.reverse()

    if not report:
        return 'No waiver transactions'

    text = [f'Waiver Report {today}: '] + report
    return '\n'.join(text)


def get_final(client, week=None):
    """
    Retrieve the final scoreboard and trophies for the prior completed week of a
    Sleeper fantasy football league.

    Parameters
    ----------
    client : gamedaybot.sleeper.sleeper_api.SleeperAPI
        The Sleeper API client for the league to retrieve the final recap for.
    week : int, optional
        The week for which to retrieve the recap. Defaults to the prior completed week.

    Returns
    -------
    str
        A string containing the final scoreboard followed by the week's trophies.
    """

    if not week:
        state = client.get_nfl_state()
        week = max(int(state['week']) - 1, 1)

    text = "Final " + get_scoreboard_short(client, week=week)
    text = text + "\n\n" + get_trophies(client, week=week)
    return text


def _square_matrix(x):
    """
    Multiply a matrix by itself (real matrix multiplication, NOT an elementwise
    square, despite the name this mirrors). Ports espn_api.football.utils.square_matrix
    verbatim (the O(n^3) row-by-column product result[i][j] += x[i][k] * x[k][j]),
    confirmed against espn_api 0.46.0's actual installed source at
    espn_api/football/utils.py:23-37.
    """

    n = len(x)
    result = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                result[i][j] += x[i][k] * x[k][j]
    return result


def _two_step_dominance(x):
    """
    Two-step dominance score per team: 2-hop indirect wins (wins racked up by the
    teams you've beaten) plus your own direct wins. Ports
    espn_api.football.utils.two_step_dominance, confirmed against espn_api 0.46.0's
    actual installed source at espn_api/football/utils.py:53-57.
    """

    squared = _square_matrix(x)
    n = len(x)
    return [sum(squared[i][j] + x[i][j] for j in range(n)) for i in range(n)]


def _build_matchup_history(client, week):
    """
    Build each roster's cumulative per-week (score, margin of victory, opponent)
    history for weeks 1..week, mirroring espn_api's Team.scores/mov/schedule.

    A roster on a bye (matchup_id: null) is treated as its own opponent for that
    week - its real score still counts toward its average, contributing a 0
    margin and no win to anyone - matching how espn_api's own Team._fetch_schedule
    handles a bye (opponent_id set to the team's own id).

    Note
    ----
    This issues one Sleeper /league/{id}/matchups/{week} request PER historical
    week from 1 through `week`, since Sleeper has no bulk multi-week endpoint.
    Acceptable given Sleeper's generous rate limits, but worth knowing before
    calling this deep into a long season.

    Returns
    -------
    tuple
        (roster_ids, scores, mov, schedule) where roster_ids is a sorted list of
        roster ids, and scores/mov/schedule are dicts of roster_id -> list, one
        entry appended per week processed.
    """

    rosters = client.get_rosters()
    roster_ids = sorted(r['roster_id'] for r in rosters)

    scores = {rid: [] for rid in roster_ids}
    mov = {rid: [] for rid in roster_ids}
    schedule = {rid: [] for rid in roster_ids}

    for w in range(1, week + 1):
        matchups = client.get_matchups(w)

        for m in matchups:
            if m.get('matchup_id') is None and m['roster_id'] in scores:
                rid = m['roster_id']
                scores[rid].append(m['points'])
                mov[rid].append(0)
                schedule[rid].append(rid)

        for a, b in _paired_matchups(matchups):
            a_id, b_id = a['roster_id'], b['roster_id']
            if a_id not in scores or b_id not in scores:
                continue
            scores[a_id].append(a['points'])
            scores[b_id].append(b['points'])
            mov[a_id].append(a['points'] - b['points'])
            mov[b_id].append(b['points'] - a['points'])
            schedule[a_id].append(b_id)
            schedule[b_id].append(a_id)

    return roster_ids, scores, mov, schedule


def _power_points(dominance, roster_ids, scores, mov, week):
    """
    Blend dominance, average score, and average margin of victory 80/15/5.
    Ports espn_api.football.utils.power_points, INCLUDING its int-truncation of
    each term before weighting, confirmed against espn_api 0.46.0's actual
    installed source at espn_api/football/utils.py:60-73.

    Returns
    -------
    list of tuple
        (power_str, roster_id) pairs sorted by power score descending.
    """

    if week <= 0:
        week = 1

    results = []
    for score, roster_id in zip(dominance, roster_ids):
        avg_score = sum(scores[roster_id][:week]) / week
        avg_mov = sum(mov[roster_id][:week]) / week
        power = (int(score) * 0.8) + (int(avg_score) * 0.15) + (int(avg_mov) * 0.05)
        results.append((f'{power:.2f}', roster_id))

    return sorted(results, key=lambda tup: float(tup[0]), reverse=True)


def _power_rankings(client, week, current_week):
    """
    Compute a single cumulative power-rankings snapshot through the given week.
    Ports espn_api.football.league.League.power_rankings, confirmed against
    espn_api 0.46.0's actual installed source at espn_api/football/league.py:337-356.

    Returns
    -------
    list of tuple
        (power_str, roster_id) pairs sorted by power score descending.
    """

    if not week or week <= 0 or week > current_week:
        week = current_week

    roster_ids, scores, mov, schedule = _build_matchup_history(client, week)

    index = {rid: i for i, rid in enumerate(roster_ids)}
    win_matrix = []
    for roster_id in roster_ids:
        wins = [0] * len(roster_ids)
        for m, opp in zip(mov[roster_id][:week], schedule[roster_id][:week]):
            if m > 0:
                wins[index[opp]] += 1
        win_matrix.append(wins)

    dominance = _two_step_dominance(win_matrix)
    return _power_points(dominance, roster_ids, scores, mov, week)


def get_power_rankings(client, week=None):
    """
    Retrieve the power rankings for a Sleeper fantasy football league, using a
    faithful port of ESPN's own two-step-dominance / 80-15-5 (dominance/average
    score/average margin of victory) algorithm, computed from Sleeper's per-week
    matchup data instead of espn_api's Team objects.

    Note
    ----
    Sleeper has no playoff-percentage field, so unlike the ESPN version this
    output omits the playoff-percentage parenthetical entirely rather than
    substituting anything in its place.

    Note
    ----
    Computing one cumulative snapshot requires one Sleeper
    /league/{id}/matchups/{week} request per historical week from 1 through
    that week, and this function computes two snapshots (current and previous)
    to show movement - acceptable given Sleeper's generous rate limits, but
    worth knowing before calling this deep into a long season.

    Parameters
    ----------
    client : gamedaybot.sleeper.sleeper_api.SleeperAPI
        The Sleeper API client for the league to retrieve power rankings for.
    week : int, optional
        The week for which to retrieve power rankings. Defaults to the prior completed week.

    Returns
    -------
    str
        A string representing the power rankings with changes from the previous week.
    """

    state = client.get_nfl_state()
    current_week = int(state['week'])

    if not week:
        week = current_week - 1

    p_rank_up_emoji = "🟢"
    p_rank_down_emoji = "🔻"
    p_rank_same_emoji = "🟰"

    current_rankings = _power_rankings(client, week, current_week)
    previous_rankings = _power_rankings(client, week - 1, current_week) if week > 1 else []

    def normalize_rankings(rankings):
        if not rankings:
            return []
        max_score = max(float(score) for score, _ in rankings)
        return [(f"{99.99 * float(score) / max_score:.2f}", roster_id) for score, roster_id in rankings]

    normalized_current_rankings = normalize_rankings(current_rankings)
    normalized_previous_rankings = normalize_rankings(previous_rankings)

    previous_rankings_dict = {roster_id: score for score, roster_id in normalized_previous_rankings}

    rosters = client.get_rosters()
    users = client.get_users()
    team_names = _team_names_by_roster_id(rosters, users)

    rankings_text = ['Power Rankings']
    for normalized_current_score, roster_id in normalized_current_rankings:
        team_name = team_names.get(roster_id, f"Team {roster_id}")
        rank_change_text = ''

        if roster_id in previous_rankings_dict:
            previous_score = previous_rankings_dict[roster_id]
            current_score_f = float(normalized_current_score)
            previous_score_f = float(previous_score)
            rank_change_percent = ((current_score_f - previous_score_f) / previous_score_f) * 100
            if rank_change_percent > 0:
                rank_change_emoji = p_rank_up_emoji
            elif rank_change_percent < 0:
                rank_change_emoji = p_rank_down_emoji
            else:
                rank_change_emoji = p_rank_same_emoji
            rank_change_text = f"[{rank_change_emoji}{abs(rank_change_percent):4.1f}%]"

        rankings_text.append(f"{normalized_current_score}{rank_change_text} - {team_name}")

    return '\n'.join(rankings_text)
