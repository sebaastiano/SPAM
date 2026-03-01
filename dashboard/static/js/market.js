/*  SPAM! Dashboard — Market Intelligence  */

async function loadMarket() {
  const data = await fetchJSON('/api/market_intel');
  if (!data) return;

  const summary = data.summary || {};

  // KPI cards
  setText('mkt-sells', summary.open_sells ?? '—');
  setText('mkt-buys', summary.open_buys ?? '—');
  setText('mkt-trades', summary.completed_trades ?? '—');
  setText('mkt-arb', summary.arbitrage_opportunities ?? '—');

  // ── Arbitrage section ──
  const arbs = data.arbitrage || [];
  const arbSection = el('arb-section');
  if (arbs.length > 0) {
    arbSection.style.display = '';
    let html = '';
    for (const a of arbs) {
      html += `<tr>
        <td>${a.ingredient}</td>
        <td class="text-end text-success">${fmtMoney(a.buy_price)}</td>
        <td class="text-end text-warning">${fmtMoney(a.sell_price)}</td>
        <td class="text-end text-danger fw-bold">+${fmtMoney(a.spread)}</td>
        <td>${a.seller}</td>
        <td>${a.buyer}</td>
      </tr>`;
    }
    setHTML('arb-body', html);
  } else {
    arbSection.style.display = 'none';
  }

  // ── Sell Listings ──
  const sells = data.sells || [];
  let sellHtml = '';
  for (const s of sells) {
    const statusCls = s.status === 'open' ? 'text-success' : 'text-muted';
    sellHtml += `<tr>
      <td>${s.ingredient_name || '?'}</td>
      <td class="text-end">${s.quantity ?? '—'}</td>
      <td class="text-end">${fmtMoney(s.unit_price)}</td>
      <td class="text-end">${fmtMoney(s.total_price)}</td>
      <td>${s.seller_name || '?'}</td>
      <td class="${statusCls}">${s.status || 'open'}</td>
    </tr>`;
  }
  setHTML('sell-body', sellHtml || '<tr><td colspan="6" class="text-muted">No sell listings</td></tr>');

  // ── Buy Listings ──
  const buys = data.buys || [];
  let buyHtml = '';
  for (const b of buys) {
    const statusCls = b.status === 'open' ? 'text-warning' : 'text-muted';
    buyHtml += `<tr>
      <td>${b.ingredient_name || '?'}</td>
      <td class="text-end">${b.quantity ?? '—'}</td>
      <td class="text-end">${fmtMoney(b.unit_price)}</td>
      <td class="text-end">${fmtMoney(b.total_price)}</td>
      <td>${b.buyer_name || b.seller_name || '?'}</td>
      <td class="${statusCls}">${b.status || 'open'}</td>
    </tr>`;
  }
  setHTML('buy-body', buyHtml || '<tr><td colspan="6" class="text-muted">No buy listings</td></tr>');

  // ── Completed Trades ──
  const trades = data.trades || [];
  let tradeHtml = '';
  for (const t of trades) {
    tradeHtml += `<tr>
      <td>${t.ingredient_name || '?'}</td>
      <td class="text-end">${t.quantity ?? '—'}</td>
      <td class="text-end">${fmtMoney(t.unit_price)}</td>
      <td class="text-end">${fmtMoney(t.total_price)}</td>
      <td>${t.seller_name || '?'}</td>
      <td>${t.buyer_name || '?'}</td>
    </tr>`;
  }
  setHTML('trades-body', tradeHtml || '<tr><td colspan="6" class="text-muted">No completed trades</td></tr>');
}

startRefresh(loadMarket);
