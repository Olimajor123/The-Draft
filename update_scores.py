#!/usr/bin/env python3
"""
Pulls live Premier League goal data from the official FPL API and recomputes
this league's results and table.

Rules implemented (goals-only custom league):
  - A goal scored by one of your 10 rostered players counts for your team.
  - An own goal by one of your rostered players counts AGAINST your team
    (i.e. it's a goal for your opponent in that gameweek's match).
  - Gameweeks 1-5 are locked (manually entered history) and are never
    recomputed from the API.
  - Gameweeks 6-38 are computed from FPL's per-gameweek "live" endpoint once
    that gameweek has kicked off, and marked "final" once FPL has fully
    checked the data (bonus points / corrections settled).

Run with: python3 update_scores.py
Writes: results.json, standings.json
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = SCRIPT_DIR

BOOTSTRAP_URL = 'https://fantasy.premierleague.com/api/bootstrap-static/'
LIVE_URL = 'https://fantasy.premierleague.com/api/event/{event_id}/live/'
HEADERS = {'User-Agent': 'Mozilla/5.0 (fantasy-league-scoreboard)'}

LOCKED_GAMEWEEKS = {1, 2, 3, 4, 5}


def fetch_json(url, retries=3, delay=5):
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            last_err = e
            time.sleep(delay)
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def compute_standings(results, team_names):
    table = {t: {'team': t, 'played': 0, 'won': 0, 'drawn': 0, 'lost': 0,
                 'gf': 0, 'ga': 0, 'gd': 0, 'pts': 0} for t in team_names}

    for gw_key, gw in results['gameweeks'].items():
        if gw['status'] != 'final':
            continue
        for m in gw['matches']:
            h, a = m['home'], m['away']
            hs, asc = m['home_score'], m['away_score']
            if hs is None or asc is None:
                continue
            th, ta = table[h], table[a]
            th['played'] += 1
            ta['played'] += 1
            th['gf'] += hs
            th['ga'] += asc
            ta['gf'] += asc
            ta['ga'] += hs
            if hs > asc:
                th['won'] += 1
                th['pts'] += 3
                ta['lost'] += 1
            elif hs < asc:
                ta['won'] += 1
                ta['pts'] += 3
                th['lost'] += 1
            else:
                th['drawn'] += 1
                ta['drawn'] += 1
                th['pts'] += 1
                ta['pts'] += 1

    for t in table.values():
        t['gd'] = t['gf'] - t['ga']

    standings = sorted(table.values(), key=lambda t: (-t['pts'], -t['gd'], -t['gf'], t['team']))
    for i, t in enumerate(standings, start=1):
        t['position'] = i
    return standings


def main():
    rosters = load_json(os.path.join(DATA_DIR, 'rosters.json'))
    fixtures = load_json(os.path.join(DATA_DIR, 'fixtures.json'))
    results = load_json(os.path.join(DATA_DIR, 'results.json'))

    team_names = list(rosters['teams'].keys())

    owner_of_player = {}
    owner_player_ids = {}
    for owner, players in rosters['teams'].items():
        ids = set()
        for p in players:
            owner_of_player[p['fpl_id']] = (owner, p['name'])
            ids.add(p['fpl_id'])
        owner_player_ids[owner] = ids

    bootstrap = fetch_json(BOOTSTRAP_URL)
    events = {e['id']: e for e in bootstrap['events']}
    now = datetime.now(timezone.utc)

    changed = False

    for gw_num in range(1, 39):
        gw_key = str(gw_num)
        if gw_num in LOCKED_GAMEWEEKS:
            continue

        event = events.get(gw_num)
        if event is None:
            continue

        deadline = datetime.fromisoformat(event['deadline_time'].replace('Z', '+00:00'))
        if now < deadline:
            continue

        is_final = bool(event.get('finished')) and bool(event.get('data_checked'))

        live = fetch_json(LIVE_URL.format(event_id=gw_num))
        stats_by_id = {}
        for el in live['elements']:
            stats_by_id[el['id']] = el['stats']

        matches = fixtures[gw_key]
        new_matches = []
        for m in matches:
            home, away = m['home'], m['away']
            home_goals = 0
            away_goals = 0
            home_scorers = []
            away_scorers = []

            for pid in owner_player_ids[home]:
                st = stats_by_id.get(pid)
                if not st:
                    continue
                g = st.get('goals_scored', 0) or 0
                og = st.get('own_goals', 0) or 0
                if g:
                    home_goals += g
                    home_scorers.append({'name': owner_of_player[pid][1], 'goals': g})
                if og:
                    away_goals += og
                    away_scorers.append({'name': owner_of_player[pid][1], 'goals': og, 'own_goal': True})

            for pid in owner_player_ids[away]:
                st = stats_by_id.get(pid)
                if not st:
                    continue
                g = st.get('goals_scored', 0) or 0
                og = st.get('own_goals', 0) or 0
                if g:
                    away_goals += g
                    away_scorers.append({'name': owner_of_player[pid][1], 'goals': g})
                if og:
                    home_goals += og
                    home_scorers.append({'name': owner_of_player[pid][1], 'goals': og, 'own_goal': True})

            new_matches.append({
                'home': home, 'away': away,
                'home_score': home_goals, 'away_score': away_goals,
                'home_scorers': home_scorers, 'away_scorers': away_scorers,
            })

        new_status = 'final' if is_final else 'live'
        old_gw = results['gameweeks'].get(gw_key, {})
        if old_gw.get('status') != new_status or old_gw.get('matches') != new_matches:
            changed = True
        results['gameweeks'][gw_key] = {'status': new_status, 'matches': new_matches}

    finished_gws = [n for n in range(1, 39)
                    if results['gameweeks'].get(str(n), {}).get('status') == 'final']
    results['last_gameweek_processed'] = max(finished_gws) if finished_gws else 0
    results['updated_at'] = now.isoformat()

    standings = compute_standings(results, team_names)

    if changed or not os.path.exists(os.path.join(DATA_DIR, 'standings.json')):
        save_json(os.path.join(DATA_DIR, 'results.json'), results)
        save_json(os.path.join(DATA_DIR, 'standings.json'), {'updated_at': now.isoformat(), 'table': standings})
        print('Updated results.json and standings.json')
    else:
        print('No changes detected')


if __name__ == '__main__':
    main()
