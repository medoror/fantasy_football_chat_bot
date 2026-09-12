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
        # Sleeper returns "settings": null for uninitialized/newly-joined rosters.
        settings = roster.get('settings') or {}
        wins = settings.get('wins', 0)
        losses = settings.get('losses', 0)
        ties = settings.get('ties', 0)
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

    grouped = {}
    for m in matchups:
        grouped.setdefault(m['matchup_id'], []).append(m)

    closest_diff = None
    close_winner = close_loser = None
    biggest_diff = -1
    blowout_winner = blowout_loser = None
    weekly_scores = {}

    for entries in grouped.values():
        if len(entries) != 2:
            # Malformed matchup group (not exactly 2 rosters): no head-to-head result to compare.
            continue

        a, b = entries
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
