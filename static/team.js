let TEAM_CODE = localStorage.getItem('todarmal_code') || '';
let REF = null;      // static reference data (resources/products)
let STATE = null;    // this team's live state
let currentTab = 'build';

function fmt(n){ return (Math.round(n * 100) / 100).toLocaleString('en-IN'); }

async function api(path, opts = {}) {
  opts.headers = Object.assign({'Content-Type': 'application/json', 'X-Team-Code': TEAM_CODE}, opts.headers || {});
  const res = await fetch(path, opts);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || res.statusText);
  return body;
}

function flash(elId, text, ok) {
  const el = document.getElementById(elId);
  el.innerHTML = `<div class="msg ${ok ? 'ok' : 'err'}">${text}</div>`;
  setTimeout(() => { if (el.firstChild) el.innerHTML = ''; }, 5000);
}

async function doLogin() {
  const code = document.getElementById('codeInput').value.trim().toUpperCase();
  if (!code) return;
  TEAM_CODE = code;
  try {
    await api('/api/state');
    localStorage.setItem('todarmal_code', code);
    document.getElementById('login').style.display = 'none';
    document.getElementById('app').style.display = 'block';
    await boot();
  } catch (e) {
    document.getElementById('loginMsg').innerHTML = `<div class="msg err">${e.message}</div>`;
  }
}

function doLogout() {
  localStorage.removeItem('todarmal_code');
  TEAM_CODE = '';
  location.reload();
}

async function boot() {
  REF = await api('/api/reference');
  await refresh();
  populateSelects();
  setInterval(refresh, 4000);
}

function itemLabel(itemId) {
  const [kind, id] = itemId.split(':');
  if (kind === 'res') return REF.resources[id] ? REF.resources[id].name : id;
  return REF.products[id] ? REF.products[id].name : id;
}

function populateSelects() {
  const extractSel = document.getElementById('extractResource');
  extractSel.innerHTML = '';
  (STATE.resources || []).forEach(rid => {
    const opt = document.createElement('option');
    opt.value = rid; opt.textContent = `${REF.resources[rid].name} (${REF.resources[rid].extraction_cost}/unit)`;
    extractSel.appendChild(opt);
  });
  extractSel.onchange = renderExtractHint;

  const prodSel = document.getElementById('produceProduct');
  prodSel.innerHTML = '';
  Object.keys(REF.products).sort((a, b) => REF.products[a].name.localeCompare(REF.products[b].name)).forEach(pid => {
    const opt = document.createElement('option');
    opt.value = pid; opt.textContent = `${REF.products[pid].name} [${REF.products[pid].category}]`;
    prodSel.appendChild(opt);
  });

  document.getElementById('newFactoryCost').textContent = REF.new_factory_cost;
}

function renderExtractHint() {
  const rid = document.getElementById('extractResource').value;
  if (!rid) return;
  document.getElementById('extractCostHint').textContent =
    `Costs ${REF.resources[rid].extraction_cost} mohurs per unit.`;
}

function renderRecipeHint() {
  const pid = document.getElementById('produceProduct').value;
  const p = REF.products[pid];
  if (!p) return;
  const inputs = p.inputs.map(([iid, qty]) => `${qty} ${itemLabel(iid)}`).join(' + ');
  const energy = p.energy_yield ? ` — yields ${p.energy_yield} energy per unit made` : '';
  document.getElementById('recipeHint').textContent =
    `1 unit of ${p.name} needs: ${inputs}. Sells for roughly ${p.sell_low}–${p.sell_high}.${energy}`;
}

function showTab(name) {
  currentTab = name;
  ['build', 'trade', 'board', 'crisis'].forEach(t => {
    document.getElementById('tab-' + t).style.display = t === name ? 'block' : 'none';
    document.getElementById('tab' + t.charAt(0).toUpperCase() + t.slice(1) + 'Btn').classList.toggle('active', t === name);
  });
  if (name === 'board') refreshLeaderboard();
  if (name === 'trade') refreshMarket();
}

async function refresh() {
  try {
    STATE = await api('/api/state');
  } catch (e) { return; }
  document.getElementById('countryName').textContent = STATE.name;
  document.getElementById('roundLabel').textContent = `Round ${STATE.round}${STATE.frozen ? ' — FROZEN' : ''}`;
  document.getElementById('treasuryTop').textContent = fmt(STATE.treasury);
  document.getElementById('frozenBanner').style.display = STATE.frozen ? 'block' : 'none';

  document.getElementById('resourceList').innerHTML = (STATE.resources || [])
    .map(r => `<div class="pill gold" style="margin:2px">${REF.resources[r].name}</div>`).join(' ');

  const capPct = Math.min(100, (STATE.production_used / Math.max(STATE.capacity_total, 1)) * 100);
  document.getElementById('capacityBox').innerHTML = `
    <div>${fmt(STATE.production_used)} / ${fmt(STATE.capacity_total)} units used</div>
    <div class="bar"><i style="width:${capPct}%"></i></div>`;
  document.getElementById('factoryList').innerHTML = STATE.factories.map(f =>
    `<div class="row" style="justify-content:space-between">
       <span class="small">Factory #${f.id} — Level ${f.level} (${f.capacity} cap)</span>
       ${f.level < 3 ? `<button class="ghost" onclick="upgradeFactory(${f.id})">Upgrade (${REF.factory_level_cost[f.level + 1]})</button>` : '<span class="small">Max</span>'}
     </div>`).join('');

  document.getElementById('tradeCapBox').innerHTML = `
    <div>${fmt(STATE.trade_units_used)} / ${fmt(STATE.trade_capacity)} units used (tier ${STATE.trade_tier})</div>
    <div class="bar"><i style="width:${Math.min(100, STATE.trade_units_used / Math.max(STATE.trade_capacity, 1) * 100)}%"></i></div>`;

  populateItemSelectsFromInventory();

  const invRows = Object.entries(STATE.inventory || {}).sort();
  document.getElementById('invTable').querySelector('tbody').innerHTML =
    invRows.length ? invRows.map(([k, v]) => `<tr><td>${itemLabel(k)}</td><td>${fmt(v)}</td></tr>`).join('')
                  : '<tr><td colspan="2" class="small">Nothing yet.</td></tr>';

  document.getElementById('crisisBox').innerHTML = STATE.crisis ? `
    <h3 style="margin-bottom:6px">${STATE.crisis.name}</h3>
    <p>${STATE.crisis.requirement_text || ''}</p>` : '';

  if (currentTab === 'trade') refreshMarket();
}

function populateItemSelectsFromInventory() {
  const sel = document.getElementById('listItem');
  const prev = sel.value;
  sel.innerHTML = '';
  Object.entries(STATE.inventory || {}).forEach(([itemId, qty]) => {
    if (qty <= 0) return;
    const opt = document.createElement('option');
    opt.value = itemId; opt.textContent = `${itemLabel(itemId)} (have ${fmt(qty)})`;
    sel.appendChild(opt);
  });
  if ([...sel.options].some(o => o.value === prev)) sel.value = prev;
}

async function doExtract() {
  const resource_id = document.getElementById('extractResource').value;
  const qty = parseFloat(document.getElementById('extractQty').value);
  try {
    const r = await api('/api/extract', {method: 'POST', body: JSON.stringify({resource_id, qty})});
    flash('extractMsg', `Extracted ${qty} for ${fmt(r.cost)} mohurs.`, true);
    await refresh();
  } catch (e) { flash('extractMsg', e.message, false); }
}

async function doProduce() {
  const product_id = document.getElementById('produceProduct').value;
  const qty = parseFloat(document.getElementById('produceQty').value);
  try {
    await api('/api/produce', {method: 'POST', body: JSON.stringify({product_id, qty})});
    flash('produceMsg', `Manufactured ${qty}.`, true);
    await refresh();
  } catch (e) { flash('produceMsg', e.message, false); }
}

async function buildFactory() {
  try {
    await api('/api/factory/build', {method: 'POST'});
    await refresh();
  } catch (e) { alert(e.message); }
}

async function upgradeFactory(id) {
  try {
    await api('/api/factory/upgrade', {method: 'POST', body: JSON.stringify({factory_id: id})});
    await refresh();
  } catch (e) { alert(e.message); }
}

async function upgradeTradeCapacity() {
  try {
    await api('/api/trade_capacity/upgrade', {method: 'POST'});
    flash('tradeCapMsg', 'Trade capacity upgraded.', true);
    await refresh();
  } catch (e) { flash('tradeCapMsg', e.message, false); }
}

async function doList() {
  const item_id = document.getElementById('listItem').value;
  const qty = parseFloat(document.getElementById('listQty').value);
  const ask_price = parseFloat(document.getElementById('listPrice').value);
  try {
    await api('/api/market/list', {method: 'POST', body: JSON.stringify({item_id, qty, ask_price})});
    flash('listMsg', 'Listed on the market.', true);
    await refresh(); await refreshMarket();
  } catch (e) { flash('listMsg', e.message, false); }
}

async function doDelist(id) {
  try { await api('/api/market/delist/' + id, {method: 'POST'}); await refresh(); await refreshMarket(); }
  catch (e) { alert(e.message); }
}

async function doBuy(listingId, askPrice) {
  const qtyStr = prompt('How many units are you buying?', '1');
  if (!qtyStr) return;
  const priceStr = prompt('Agreed price per unit (after your in-person negotiation):', askPrice);
  if (priceStr === null) return;
  try {
    await api('/api/market/buy', {method: 'POST', body: JSON.stringify({
      listing_id: listingId, qty: parseFloat(qtyStr), price: parseFloat(priceStr)})});
    await refresh(); await refreshMarket();
  } catch (e) { alert(e.message); }
}

async function refreshMarket() {
  const market = await api('/api/market');
  const mine = market.filter(m => STATE && m.team_id === STATE.id);
  const others = market.filter(m => !STATE || m.team_id !== STATE.id);
  document.getElementById('marketTable').querySelector('tbody').innerHTML = others.length ?
    others.map(m => `<tr><td>${m.team_name}</td><td>${itemLabel(m.item_id)}</td><td>${fmt(m.qty)}</td>
      <td>${fmt(m.ask_price)}</td><td><button class="ghost" onclick="doBuy(${m.id}, ${m.ask_price})">Buy</button></td></tr>`).join('')
    : '<tr><td colspan="5" class="small">Nothing listed yet.</td></tr>';
  document.getElementById('myListingsTable').querySelector('tbody').innerHTML = mine.length ?
    mine.map(m => `<tr><td>${itemLabel(m.item_id)}</td><td>${fmt(m.qty)}</td><td>${fmt(m.ask_price)}</td>
      <td><button class="ghost" onclick="doDelist(${m.id})">Delist</button></td></tr>`).join('')
    : '<tr><td colspan="4" class="small">You have nothing listed.</td></tr>';

  const trades = await api('/api/trades');
  document.getElementById('tradesTable').querySelector('tbody').innerHTML = trades.length ?
    trades.slice(0, 20).map(t => `<tr><td>${t.buyer_name}</td><td>${t.seller_name}</td>
      <td>${itemLabel(t.item_id)}</td><td>${fmt(t.qty)}</td><td>${fmt(t.price_total)}</td></tr>`).join('')
    : '<tr><td colspan="5" class="small">No trades yet.</td></tr>';
}

async function refreshLeaderboard() {
  const lb = await api('/api/leaderboard');
  document.getElementById('boardNote').textContent = lb.frozen ? 'Frozen — final standings.' :
    (lb.round === 1 ? 'Live estimate of production value. Not the official score.' : 'Live treasury. Not the official score.');
  document.getElementById('boardTable').querySelector('tbody').innerHTML = lb.teams.map((t, i) =>
    `<tr><td>${i + 1}</td><td>${t.name}</td><td>${fmt(t.round1_estimate)}</td><td>${fmt(t.treasury)}</td></tr>`).join('');
}

if (TEAM_CODE) {
  api('/api/state').then(() => {
    document.getElementById('login').style.display = 'none';
    document.getElementById('app').style.display = 'block';
    boot();
  }).catch(() => {});
}
