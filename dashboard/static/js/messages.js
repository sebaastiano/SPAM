/*  SPAM! Dashboard — Message Intelligence  */

let allMessages = [];

async function loadMessages() {
  const data = await fetchJSON('/api/messages_intel');
  if (!data) return;

  allMessages = Array.isArray(data) ? data : [];

  // KPIs
  setText('msg-count', allMessages.length);

  const senders = new Set();
  let directedAtUs = 0;
  let sentCount = 0;
  for (const m of allMessages) {
    const sender = m.sender_name || m.sender || m.from || m.restaurant_id || m.restaurantId || '?';
    senders.add(sender);
    if (m.direction === 'sent') {
      sentCount++;
    }
    // Check if message mentions us (team 17)
    const text = (m.text || m.message || m.content || '').toLowerCase();
    if (text.includes('17') || text.includes('spam')) {
      directedAtUs++;
    }
  }
  setText('msg-senders', senders.size);
  setText('msg-us', `${directedAtUs} in / ${sentCount} out`);

  renderMessages(allMessages);
}

function renderMessages(messages) {
  const feed = el('message-feed');
  if (!feed) return;

  if (messages.length === 0) {
    feed.innerHTML = '<div class="text-muted">No messages captured yet.</div>';
    return;
  }

  let html = '';
  // Show newest first
  const sorted = [...messages].reverse();

  for (const m of sorted) {
    const isSent = m.direction === 'sent';
    const sender = isSent
      ? ('→ ' + (m.recipient_name || 'Restaurant #' + (m.recipient_id || '?')))
      : (m.sender_name || m.sender || m.from || m.restaurant_id || m.restaurantId || 'Unknown');
    const time = m.timestamp || m.ts || m.time || '';
    const text = m.text || m.message || m.content || JSON.stringify(m);
    const turn = m.turn_id || m.turnId || '';
    const borderColor = isSent ? 'border-success' : 'border-info';
    const badge = isSent
      ? '<span class="badge bg-success ms-2">SENT</span>'
      : '<span class="badge bg-info ms-2">RECEIVED</span>';
    const armInfo = isSent && m.arm ? ` <span class="badge bg-warning text-dark ms-1">${escapeHtml(m.arm)}</span>` : '';

    html += `
    <div class="msg-item ${borderColor}" style="border-left: 3px solid; padding-left: 8px; margin-bottom: 8px;">
      <div class="d-flex justify-content-between">
        <span class="msg-sender">${escapeHtml(String(sender))}${badge}${armInfo}</span>
        <span class="msg-time">${turn ? 'Turn ' + turn + ' · ' : ''}${escapeHtml(String(time))}</span>
      </div>
      <div class="msg-text">${escapeHtml(String(text))}</div>
    </div>`;
  }

  feed.innerHTML = html;
}

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

// Filter messages on input
document.addEventListener('DOMContentLoaded', () => {
  const filterInput = el('msg-filter');
  if (filterInput) {
    filterInput.addEventListener('input', () => {
      const q = filterInput.value.toLowerCase().trim();
      if (!q) {
        renderMessages(allMessages);
        return;
      }
      const filtered = allMessages.filter(m => {
        const text = (m.text || m.message || m.content || '').toLowerCase();
        const sender = String(m.sender || m.from || m.restaurant_id || '').toLowerCase();
        return text.includes(q) || sender.includes(q);
      });
      renderMessages(filtered);
    });
  }
});

startRefresh(loadMessages);
