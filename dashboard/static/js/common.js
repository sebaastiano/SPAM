/*  SPAM! Dashboard — Common JS utilities  */

const REFRESH_MS = 6000; // fetch updated data every 6s

// ── Fetch helper ──────────────────────────

async function fetchJSON(url) {
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  } catch (e) {
    console.warn(`fetchJSON(${url}) failed:`, e);
    return null;
  }
}

// ── Number formatting ─────────────────────

function fmt(n, decimals = 0) {
  if (n == null || isNaN(n)) return '—';
  return Number(n).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function fmtMoney(n) {
  if (n == null || isNaN(n)) return '—';
  const v = Number(n);
  if (Math.abs(v) >= 1000) return fmt(v);
  return fmt(v, 1);
}

function fmtPct(n) {
  if (n == null || isNaN(n)) return '—';
  return Number(n).toFixed(1) + '%';
}

// ── DOM helpers ───────────────────────────

function el(id) { return document.getElementById(id); }

function setText(id, text) {
  const e = el(id);
  if (e && e.textContent !== String(text)) {
    e.textContent = text;
    e.classList.remove('flash');
    void e.offsetWidth;  // trigger reflow
    e.classList.add('flash');
  }
}

function setHTML(id, html) {
  const e = el(id);
  if (e) e.innerHTML = html;
}

// ── Heatmap color ─────────────────────────

function heatColor(value, max) {
  if (!value || !max) return 'transparent';
  const ratio = Math.min(value / max, 1);
  const r = Math.round(255 * ratio);
  const g = Math.round(193 * ratio);
  const b = Math.round(7 * ratio);
  return `rgba(${r}, ${g}, ${b}, ${0.1 + ratio * 0.6})`;
}

// ── Threat badge ──────────────────────────

function threatBadge(level) {
  const cls = `badge badge-threat-${level}`;
  return `<span class="${cls}">${level}</span>`;
}

// ── Game state updater (shared across pages) ──

async function updateGameBadges() {
  const gs = await fetchJSON('/api/raw/api/game_state');
  if (!gs) {
    el('tracker-status')?.classList.remove('online');
    el('tracker-status')?.classList.add('offline');
    return;
  }
  el('tracker-status')?.classList.remove('offline');
  el('tracker-status')?.classList.add('online');

  const phase = gs.phase || '—';
  const turn = gs.turn_id ?? '—';

  const phBadge = el('badge-phase');
  if (phBadge) {
    phBadge.textContent = `Phase: ${phase}`;
    phBadge.className = `badge phase-${phase}`;
  }
  setText('badge-turn', `Turn: ${turn}`);
}

// ── Periodic refresh engine ───────────────

function startRefresh(loadFn, intervalMs = REFRESH_MS) {
  // Initial load
  loadFn();
  updateGameBadges();

  // Periodic
  setInterval(() => {
    loadFn();
    updateGameBadges();
  }, intervalMs);
}
