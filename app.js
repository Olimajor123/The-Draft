const DATA = { rosters: null, fixtures: null, results: null, standings: null };

async function loadData() {
  const [rosters, fixtures, results, standings] = await Promise.all([
    fetch('rosters.json').then(r => r.json()),
    fetch('fixtures.json').then(r => r.json()),
    fetch('results.json').then(r => r.json()),
    fetch('standings.json').then(r => r.json()),
  ]);
  DATA.rosters = rosters;
  DATA.fixtures = fixtures;
  DATA.results = results;
  DATA.standings = standings;
}

function fmtDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

function renderUpdatedAt() {
  const t = DATA.standings.updated_at || DATA.results.updated_at;
  document.getElementById('updated-at').textContent = t ? `Last updated ${fmtDate(t)}` : '';
}

function renderStandings() {
  const body = document.getElementById('standings-body');
  body.innerHTML = '';
  DATA.standings.table.forEach(t => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${t.position}</td>
      <td class="team-col">${t.team}</td>
      <td>${t.played}</td>
      <td>${t.won}</td>
      <td>${t.drawn}</td>
      <td>${t.lost}</td>
      <td>${t.gf}</td>
      <td>${t.ga}</td>
      <td>${t.gd > 0 ? '+' + t.gd : t.gd}</td>
      <td class="pts">${t.pts}</td>`;
    body.appendChild(tr);
  });
}

function scorerLine(s) {
  const suffix = s.goals > 1 ? ` (${s.goals})` : '';
  const og = s.own_goal ? ' [OG]' : '';
  return `<div>${s.name}${suffix}${og}</div>`;
}

function renderGameweek(gwNum) {
  const key = String(gwNum);
  const gw = DATA.results.gameweeks[key];
  const list = document.getElementById('fixtures-list');
  list.innerHTML = '';
  if (!gw) return;

  gw.matches.forEach(m => {
    const played = m.home_score !== null && m.away_score !== null;
    const card = document.createElement('div');
    card.className = 'match-card';
    card.innerHTML = `
      <div class="match-row">
        <div class="match-team home">${m.home}</div>
        <div class="match-score">${played ? `${m.home_score} - ${m.away_score}` : 'vs'}</div>
        <div class="match-team away">${m.away}</div>
      </div>
      <div class="match-status ${gw.status}">${gw.status}</div>
      ${played ? `<div class="scorers">
        <div class="home-scorers">${m.home_scorers.map(scorerLine).join('')}</div>
        <div class="away-scorers">${m.away_scorers.map(scorerLine).join('')}</div>
      </div>` : ''}
    `;
    list.appendChild(card);
  });
}

function setupGameweekNav() {
  const select = document.getElementById('gw-select');
  for (let i = 1; i <= 38; i++) {
    const opt = document.createElement('option');
    opt.value = i;
    opt.textContent = `Gameweek ${i}`;
    select.appendChild(opt);
  }
  const currentGw = (DATA.results.last_gameweek_processed || 0) + 1;
  const initial = Math.min(Math.max(currentGw, 1), 38);
  select.value = initial;
  renderGameweek(initial);

  select.addEventListener('change', () => renderGameweek(Number(select.value)));
  document.getElementById('gw-prev').addEventListener('click', () => {
    const v = Math.max(1, Number(select.value) - 1);
    select.value = v;
    renderGameweek(v);
  });
  document.getElementById('gw-next').addEventListener('click', () => {
    const v = Math.min(38, Number(select.value) + 1);
    select.value = v;
    renderGameweek(v);
  });
}

function renderScorers() {
  const tally = {};
  const ownerByName = {};
  Object.entries(DATA.rosters.teams).forEach(([owner, players]) => {
    players.forEach(p => { ownerByName[`${owner}::${p.name}`] = p; });
  });

  Object.values(DATA.results.gameweeks).forEach(gw => {
    if (gw.status === 'scheduled') return;
    gw.matches.forEach(m => {
      [[m.home, m.home_scorers], [m.away, m.away_scorers]].forEach(([owner, scorers]) => {
        scorers.forEach(s => {
          if (s.own_goal) return;
          const key = `${owner}::${s.name}`;
          if (!tally[key]) {
            const meta = ownerByName[key];
            tally[key] = { name: s.name, owner, club: meta ? meta.club : '', goals: 0 };
          }
          tally[key].goals += s.goals;
        });
      });
    });
  });

  const rows = Object.values(tally).sort((a, b) => b.goals - a.goals).slice(0, 30);
  const body = document.getElementById('scorers-body');
  body.innerHTML = '';
  rows.forEach((r, i) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${i + 1}</td><td>${r.name}</td><td class="team-col">${r.club}</td><td>${r.owner}</td><td class="pts">${r.goals}</td>`;
    body.appendChild(tr);
  });
}

function renderTeams() {
  const container = document.getElementById('teams-list');
  container.innerHTML = '';
  Object.entries(DATA.rosters.teams).forEach(([owner, players]) => {
    const details = document.createElement('details');
    details.className = 'team-block';
    const order = { DEF: 0, MID: 1, FWD: 2 };
    const sorted = [...players].sort((a, b) => order[a.position] - order[b.position]);
    details.innerHTML = `
      <summary>${owner} <span>${players.length} players</span></summary>
      <ul>
        ${sorted.map(p => `<li><span><span class="pos-tag">${p.position}</span>${p.name} <span style="color:var(--text-dim)">(${p.club})</span></span><span>${p.price_paid}</span></li>`).join('')}
      </ul>`;
    container.appendChild(details);
  });
}

function setupTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
    });
  });
}

(async function init() {
  await loadData();
  renderUpdatedAt();
  renderStandings();
  setupGameweekNav();
  renderScorers();
  renderTeams();
  setupTabs();
})();
