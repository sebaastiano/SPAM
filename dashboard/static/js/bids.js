/*  SPAM! Dashboard — Bid Intelligence  */

async function loadBids() {
  const data = await fetchJSON('/api/bids');
  if (!data) return;

  const summary = data.summary || {};
  const teams = data.teams || {};
  const ingredients = data.ingredients || {};

  // Summary KPIs
  setText('bid-total-spend', fmtMoney(summary.total_market_spend));
  setText('bid-our-spend', fmtMoney(summary.our_spend));
  setText('bid-active', summary.active_bidders ?? '—');
  setText('bid-share', fmtPct(summary.our_share_pct));

  // ── Team Spending Table ──
  const teamArr = Object.entries(teams)
    .map(([rid, td]) => ({ rid: Number(rid), ...td }))
    .sort((a, b) => b.total_spent - a.total_spent);

  let teamHtml = '';
  for (const t of teamArr) {
    const isUs = t.rid === 17;
    const cls = isUs ? 'our-team' : '';
    teamHtml += `<tr class="${cls}">
      <td>${t.name || 'Team ' + t.rid}${isUs ? ' <small>(us)</small>' : ''}</td>
      <td class="text-end">${fmtMoney(t.total_spent)}</td>
      <td class="text-end">${fmt(t.bid_count)}</td>
      <td class="text-end">${fmtMoney(t.avg_bid)}</td>
      <td class="text-end">${fmtMoney(t.max_bid)}</td>
    </tr>`;
  }
  setHTML('team-spend-body', teamHtml || '<tr><td colspan="5" class="text-muted">No bid data</td></tr>');

  // ── Most Contested Ingredients ──
  const ingArr = Object.entries(ingredients)
    .map(([name, ig]) => ({ name, ...ig }))
    .sort((a, b) => b.bid_count - a.bid_count);

  let ingHtml = '';
  for (const ig of ingArr.slice(0, 20)) {
    ingHtml += `<tr>
      <td>${ig.name}</td>
      <td class="text-end">${fmt(ig.bid_count)}</td>
      <td class="text-end">${fmtMoney(ig.total_bids)}</td>
      <td class="text-end">${fmtMoney(ig.avg_price)}</td>
      <td class="text-end">${fmtMoney(ig.max_price)}</td>
      <td class="text-end">${fmtMoney(ig.min_price)}</td>
    </tr>`;
  }
  setHTML('contested-body', ingHtml || '<tr><td colspan="6" class="text-muted">No data</td></tr>');

  // ── Heatmap: Ingredient × Team ──
  buildHeatmap(ingredients, teams);
}

function buildHeatmap(ingredients, teams) {
  const teamIds = Object.keys(teams).sort((a, b) => Number(a) - Number(b));
  const ingNames = Object.keys(ingredients).sort();

  if (teamIds.length === 0 || ingNames.length === 0) {
    setHTML('heatmap-head', '<tr><th class="text-muted">No data for heatmap</th></tr>');
    setHTML('heatmap-body', '');
    return;
  }

  // Find max spend for color scaling
  let maxSpend = 0;
  for (const ig of Object.values(ingredients)) {
    for (const bid of Object.values(ig.bidders || {})) {
      maxSpend = Math.max(maxSpend, bid.total_bid || 0);
    }
  }

  // Header
  let headHtml = '<tr><th style="position:sticky;left:0;z-index:2;background:var(--spam-card)">Ingredient</th>';
  for (const tid of teamIds) {
    const name = teams[tid]?.name || `T${tid}`;
    const short = name.length > 10 ? name.substring(0, 10) + '…' : name;
    headHtml += `<th class="text-center" title="${name}">${short}</th>`;
  }
  headHtml += '</tr>';
  setHTML('heatmap-head', headHtml);

  // Body
  let bodyHtml = '';
  for (const ing of ingNames) {
    bodyHtml += `<tr><td style="position:sticky;left:0;z-index:1;background:var(--spam-card);white-space:nowrap">${ing}</td>`;
    for (const tid of teamIds) {
      const bidder = ingredients[ing]?.bidders?.[tid];
      const spend = bidder?.total_bid || 0;
      const bg = heatColor(spend, maxSpend);
      bodyHtml += `<td class="heatmap-cell" style="background:${bg}" title="${ing}: $${spend} by ${teams[tid]?.name || tid}">${spend ? fmtMoney(spend) : ''}</td>`;
    }
    bodyHtml += '</tr>';
  }
  setHTML('heatmap-body', bodyHtml);
}

startRefresh(loadBids);
