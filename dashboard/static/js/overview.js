/*  SPAM! Dashboard — Overview Page  */

async function loadOverview() {
  const data = await fetchJSON('/api/overview');
  if (!data) return;

  const perf = data.our_performance || {};
  const gs = data.game_state || {};
  const bidS = data.bid_summary || {};
  const mktS = data.market_summary || {};

  // KPI cards
  setText('kpi-balance', fmtMoney(perf.balance));
  setText('kpi-reputation', fmt(perf.reputation));
  setText('kpi-service-rate', fmtPct(perf.service_rate));

  const profit = perf.estimated_profit;
  const profitEl = el('kpi-profit');
  if (profitEl) {
    profitEl.textContent = fmtMoney(profit);
    profitEl.className = 'display-6 fw-bold ' + (profit >= 0 ? 'text-success' : 'text-danger');
  }

  // Balance badge
  setText('badge-balance', `Balance: ${fmtMoney(perf.balance)}`);

  // Our Performance stats
  const statsHTML = [
    ['Menu Items', perf.menu_items],
    ['Inventory Types', perf.inventory_types],
    ['Inventory Total', fmt(perf.inventory_total)],
    ['Total Bid Spend', fmtMoney(perf.total_bid_spend)],
    ['Served Meals', `${perf.served_meals} / ${perf.total_meals}`],
    ['Est. Revenue', fmtMoney(perf.estimated_revenue)],
    ['Est. Profit', fmtMoney(perf.estimated_profit)],
  ].map(([label, val]) =>
    `<div class="stat-row"><span class="stat-label">${label}</span><span class="stat-value">${val}</span></div>`
  ).join('');
  setHTML('our-stats', statsHTML);

  // Leaderboard
  const lb = data.leaderboard || [];
  let lbHtml = '';
  lb.forEach((r, i) => {
    const cls = r.is_us ? 'our-team' : '';
    const medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i + 1}`;
    lbHtml += `<tr class="${cls}">
      <td>${medal}</td>
      <td>${r.name}${r.is_us ? ' <small>(us)</small>' : ''}</td>
      <td class="text-end">${fmtMoney(r.balance)}</td>
      <td class="text-end">${fmt(r.reputation)}</td>
    </tr>`;
  });
  setHTML('leaderboard-body', lbHtml || '<tr><td colspan="4" class="text-muted">No data</td></tr>');

  // Market summary
  setHTML('market-summary', [
    ['Open Sells', mktS.open_sells],
    ['Open Buys', mktS.open_buys],
    ['Completed Trades', mktS.completed_trades],
    ['Trade Volume', fmtMoney(mktS.total_trade_volume)],
    ['Arbitrage Opps', mktS.arbitrage_opportunities],
  ].map(([l, v]) =>
    `<div class="stat-row"><span class="stat-label">${l}</span><span class="stat-value">${v ?? '—'}</span></div>`
  ).join(''));

  // Bid summary
  setHTML('bid-summary', [
    ['Total Market Spend', fmtMoney(bidS.total_market_spend)],
    ['Our Spend', fmtMoney(bidS.our_spend)],
    ['Our Share', fmtPct(bidS.our_share_pct)],
    ['Active Bidders', bidS.active_bidders],
    ['Ingredients Bid On', bidS.unique_ingredients_bid],
  ].map(([l, v]) =>
    `<div class="stat-row"><span class="stat-label">${l}</span><span class="stat-value">${v ?? '—'}</span></div>`
  ).join(''));

  // Inventory
  const inv = perf.inventory_detail || {};
  const invEntries = Object.entries(inv).sort((a, b) => b[1] - a[1]);
  let invHtml = '';
  if (invEntries.length === 0) {
    invHtml = '<tr><td colspan="2" class="text-muted">Empty</td></tr>';
  } else {
    for (const [name, qty] of invEntries) {
      invHtml += `<tr><td>${name}</td><td class="text-end">${qty}</td></tr>`;
    }
  }
  setHTML('inventory-body', invHtml);
}

startRefresh(loadOverview);
