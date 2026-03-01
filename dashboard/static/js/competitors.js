/*  SPAM! Dashboard — Competitor Intelligence  */

let currentFilter = 'ALL';
let cachedProfiles = {};

function filterThreat(btn) {
  // Update active button
  document.querySelectorAll('[data-filter]').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentFilter = btn.dataset.filter;
  renderCards(cachedProfiles);
}

function renderCards(profiles) {
  const container = el('competitor-cards');
  if (!container) return;

  const arr = Object.entries(profiles)
    .map(([rid, p]) => ({ rid: Number(rid), ...p }))
    .filter(p => currentFilter === 'ALL' || p.threat_level === currentFilter)
    .sort((a, b) => b.balance - a.balance);

  if (arr.length === 0) {
    container.innerHTML = '<div class="col-12 text-muted">No competitors match this filter.</div>';
    return;
  }

  let html = '';
  for (const p of arr) {
    const threatCls = `threat-${p.threat_level}`;
    const statusDot = p.is_open
      ? '<span class="text-success"><i class="bi bi-circle-fill"></i> Open</span>'
      : '<span class="text-danger"><i class="bi bi-circle-fill"></i> Closed</span>';

    // Top ingredients list
    let ingHtml = '';
    if (p.top_ingredients && p.top_ingredients.length > 0) {
      ingHtml = '<div class="mt-2"><small class="text-muted">Top Ingredients:</small><ul class="mb-0 ps-3">';
      for (const ig of p.top_ingredients) {
        ingHtml += `<li><small>${ig.name}: $${fmtMoney(ig.spend)} (${ig.qty} units)</small></li>`;
      }
      ingHtml += '</ul></div>';
    }

    html += `
    <div class="col-md-6 col-lg-4 competitor-row" data-threat="${p.threat_level}">
      <div class="card bg-dark border-secondary competitor-card h-100">
        <div class="card-header">
          <span>${p.name}</span>
          ${threatBadge(p.threat_level)}
        </div>
        <div class="card-body">
          <div class="d-flex justify-content-between mb-2">
            ${statusDot}
            <span class="text-muted small">ID: ${p.rid}</span>
          </div>
          <div class="stat-row"><span class="stat-label">Balance</span><span class="stat-value text-warning">${fmtMoney(p.balance)}</span></div>
          <div class="stat-row"><span class="stat-label">Reputation</span><span class="stat-value">${fmt(p.reputation)}</span></div>
          <div class="stat-row"><span class="stat-label">Menu Items</span><span class="stat-value">${p.menu_count}</span></div>
          <div class="stat-row"><span class="stat-label">Avg Price</span><span class="stat-value">${fmtMoney(p.avg_price)}</span></div>
          <div class="stat-row"><span class="stat-label">Price Range</span><span class="stat-value">${fmtMoney(p.min_price)} – ${fmtMoney(p.max_price)}</span></div>
          <div class="stat-row"><span class="stat-label">Bid Spend</span><span class="stat-value">${fmtMoney(p.total_bid_spend)}</span></div>
          <div class="stat-row"><span class="stat-label">Total Bids</span><span class="stat-value">${fmt(p.bid_count)}</span></div>
          <div class="stat-row"><span class="stat-label">Market Sells</span><span class="stat-value">${p.market_sells}</span></div>
          <div class="stat-row"><span class="stat-label">Market Buys</span><span class="stat-value">${p.market_buys}</span></div>
          ${ingHtml}
        </div>
      </div>
    </div>`;
  }

  container.innerHTML = html;
}

async function loadCompetitors() {
  const data = await fetchJSON('/api/competitors');
  if (!data) return;
  cachedProfiles = data;
  renderCards(data);
}

startRefresh(loadCompetitors);
