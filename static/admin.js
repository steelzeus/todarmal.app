let ADMIN_PW = sessionStorage.getItem('todarmal_admin_pw') || '';
let REF = null;

function fmt(n){ return (Math.round(n * 100) / 100).toLocaleString('en-IN'); }

async function api(path, opts = {}) {
  opts.headers = Object.assign({'Content-Type': 'application/json', 'X-Admin-Password': ADMIN_PW}, opts.headers || {});
  const res = await fetch(path, opts);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || res.statusText);
  return body;
}

function itemLabel(itemId) {
  const [kind, id] = itemId.split(':');
  if (kind === 'res') return REF.resources[id] ? REF.resources[id].name : id;
  return REF.products[id] ? REF.products[id].name : id;
}

async function doLogin() {
  ADMIN_PW = document.getElementById('pwInput').value;
  try {
    await api('/api/admin/teams');
    sessionStorage.setItem('todarmal_admin_pw', ADMIN_PW);
    document.getElementById('login').style.display = 'none';
    document.getElementById('app').style.display = 'block';
    await boot();
  } catch (e) {
    document.getElementById('loginMsg').innerHTML = `<div class="msg err">${e.message}</div>`;
  }
}

async function boot() {
  REF = await fetch('/api/reference').then(r => r.json());
  populateResourceCrisisSelects();
  await refreshAll();
  await ensureCrisisOptions();
  setInterval(refreshAll, 5000);
}

function populateResourceCrisisSelects() {
  ['assignRes1', 'assignRes2', 'assignRes3'].forEach(id => {
    const sel = document.getElementById(id);
    sel.innerHTML = Object.entries(REF.resources).map(([k, v]) => `<option value="${k}">${v.name}</option>`).join('');
  });
}

async function refreshAll() {
  const teams = await api('/api/admin/teams');
  const state = await fetch('/api/leaderboard').then(r => r.json());
  document.getElementById('roundNow').textContent = state.round + (state.frozen ? ' (FROZEN)' : '');
  document.getElementById('frozenBanner').style.display = state.frozen ? 'block' : 'none';

  document.getElementById('teamsTable').querySelector('tbody').innerHTML = teams.map(t => `
    <tr><td>${t.name}</td><td>${t.access_code}</td><td>${fmt(t.treasury)}</td><td>${fmt(t.round1_estimate)}</td>
    <td>${fmt(t.production_used)}/${fmt(t.capacity_total)}</td>
    <td>${fmt(t.trade_units_used)}/${fmt(t.trade_capacity)}</td>
    <td>${t.crisis_id}</td>
    <td>${t.active_sessions} <button class="ghost" onclick="releaseSessions(${t.id})">Release</button></td>
    <td><button class="ghost" onclick="pickTeamFor(${t.id})">Select</button></td></tr>`).join('');

  ['assignTeam', 'editTeam', 'auditTeam'].forEach(id => {
    const sel = document.getElementById(id);
    const prev = sel.value;
    sel.innerHTML = teams.map(t => `<option value="${t.id}">${t.name}</option>`).join('');
    if ([...sel.options].some(o => o.value === prev)) sel.value = prev;
  });

  const crisisSel = document.getElementById('assignCrisis');
  if (!crisisSel.dataset.filled) {
    const crisisIds = [...new Set(teams.map(t => t.crisis_id))];
    // build from reference isn't available for crises via /api/reference, so pull from a known team's list via export
  }

  window._teamsCache = teams;

  const trades = await fetch('/api/trades').then(r => r.json());
  document.getElementById('tradesTable').querySelector('tbody').innerHTML = trades.length ? trades.map(t =>
    `<tr><td>${t.buyer_name}</td><td>${t.seller_name}</td><td>${itemLabel(t.item_id)}</td><td>${fmt(t.qty)}</td><td>${fmt(t.price_total)}</td></tr>`
  ).join('') : '<tr><td colspan="5" class="small">No trades yet.</td></tr>';
}

function pickTeamFor(teamId) {
  const t = window._teamsCache.find(x => x.id === teamId);
  if (!t) return;
  document.getElementById('assignTeam').value = teamId;
  document.getElementById('assignRes1').value = t.resources[0] || '';
  document.getElementById('assignRes2').value = t.resources[1] || '';
  document.getElementById('assignRes3').value = t.resources[2] || '';
  document.getElementById('editTeam').value = teamId;
  document.getElementById('editTreasury').value = t.treasury;
  document.getElementById('auditTeam').value = teamId;
}

async function releaseSessions(teamId) {
  try {
    await api('/api/admin/release_sessions', {method: 'POST', body: JSON.stringify({team_id: teamId})});
    await refreshAll();
  } catch (e) { alert(e.message); }
}

async function ensureCrisisOptions() {
  const sel = document.getElementById('assignCrisis');
  if (sel.options.length) return;
  const audit = await api('/api/admin/export');
  const seen = {};
  audit.forEach(t => { if (t.crisis && t.crisis.id) seen[t.crisis.id] = t.crisis.name; });
  sel.innerHTML = Object.entries(seen).map(([k, v]) => `<option value="${k}">${v}</option>`).join('');
}

async function saveAssign() {
  await ensureCrisisOptions();
  const team_id = parseInt(document.getElementById('assignTeam').value);
  const resources = [document.getElementById('assignRes1').value, document.getElementById('assignRes2').value, document.getElementById('assignRes3').value];
  const crisis_id = document.getElementById('assignCrisis').value;
  try {
    await api('/api/admin/assign', {method: 'POST', body: JSON.stringify({team_id, resources, crisis_id})});
    document.getElementById('assignMsg').innerHTML = '<div class="msg ok">Saved.</div>';
    await refreshAll();
  } catch (e) { document.getElementById('assignMsg').innerHTML = `<div class="msg err">${e.message}</div>`; }
}

async function saveTreasury() {
  const team_id = parseInt(document.getElementById('editTeam').value);
  const treasury = parseFloat(document.getElementById('editTreasury').value);
  try {
    await api('/api/admin/team/edit', {method: 'POST', body: JSON.stringify({team_id, treasury})});
    document.getElementById('editMsg').innerHTML = '<div class="msg ok">Saved.</div>';
    await refreshAll();
  } catch (e) { document.getElementById('editMsg').innerHTML = `<div class="msg err">${e.message}</div>`; }
}

async function loadAudit() {
  const id = document.getElementById('auditTeam').value;
  const audit = await api('/api/admin/audit/' + id);
  document.getElementById('auditBox').textContent = JSON.stringify(audit, null, 2);
}

async function downloadExport() {
  const data = await api('/api/admin/export');
  const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'todarmal_export.json';
  a.click();
}

async function setRound(r) {
  await api('/api/admin/round', {method: 'POST', body: JSON.stringify({round: r})});
  await refreshAll();
}
async function freezeGame() { await api('/api/admin/freeze', {method: 'POST'}); await refreshAll(); }
async function unfreezeGame() { await api('/api/admin/unfreeze', {method: 'POST'}); await refreshAll(); }
async function resetAll() { await api('/api/admin/reset', {method: 'POST'}); await refreshAll(); }

if (ADMIN_PW) {
  api('/api/admin/teams').then(() => {
    document.getElementById('login').style.display = 'none';
    document.getElementById('app').style.display = 'block';
    boot();
  }).catch(() => {});
}
