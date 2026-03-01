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
  for (const m of allMessages) {
    const sender = m.sender || m.from || m.restaurant_id || m.restaurantId || '?';
    senders.add(sender);
    // Check if message mentions us (team 17)
    const text = (m.text || m.message || m.content || '').toLowerCase();
    if (text.includes('17') || text.includes('spam')) {
      directedAtUs++;
    }
  }
  setText('msg-senders', senders.size);
  setText('msg-us', directedAtUs);

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
    const sender = m.sender || m.from || m.restaurant_id || m.restaurantId || 'Unknown';
    const time = m.timestamp || m.ts || m.time || '';
    const text = m.text || m.message || m.content || JSON.stringify(m);
    const turn = m.turn_id || m.turnId || '';

    html += `
    <div class="msg-item">
      <div class="d-flex justify-content-between">
        <span class="msg-sender">${escapeHtml(String(sender))}</span>
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
