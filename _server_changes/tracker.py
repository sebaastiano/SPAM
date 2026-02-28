"""
Hackapizza Server Tracker
=========================
Tracks ALL server changes in real-time:
  - SSE events from the game stream (/events/17)
  - REST polling: restaurants, market, meals, bid history
Serves a minimal live web UI at http://localhost:5555
"""

import json
import threading
import time
import copy
import queue
import requests
from flask import Flask, Response, render_template_string
from datetime import datetime

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────
API_KEY   = "dTpZhKpZ02-4ac2be8821b52df78bf06070"
BASE_URL  = "https://hackapizza.datapizza.tech"
TEAM_ID   = 17
HEADERS   = {"x-api-key": API_KEY}
SSE_HEADERS = {**HEADERS, "Accept": "text/event-stream"}
POLL_INTERVAL = 5  # seconds between REST polls

# Set to False when the SPAM bot is running (it owns the SSE connection).
# The tracker will still get all data via REST polling.
USE_SSE = False

app = Flask(__name__)

# Shared state
state = {
    "phase": "unknown",
    "turn_id": None,
    "restaurants": {},      # id -> flattened dict
    "restaurants_raw": {},  # id -> full raw dict from API
    "restaurants_names": {},# id -> name string
    "restaurants_changes": {},  # id -> list of change events (last 50)
    "market": {},           # entry_id -> dict
    "meals": {},            # (turn_id, restaurant_id, meal_id) -> dict
    "bid_history": {},      # (turn_id, entry_id) -> dict
    "messages": [],         # recent broadcast messages
}
state_lock = threading.Lock()

# Queue of change events to push to all browser SSE clients
# Each item: {"type": str, "ts": str, "data": dict}
event_queues: list[queue.Queue] = []
event_queues_lock = threading.Lock()


def now_ts():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def push_event(evt_type: str, data: dict):
    """Push an event to all connected browser clients."""
    payload = {
        "type": evt_type,
        "ts": now_ts(),
        "data": data,
    }
    with event_queues_lock:
        for q in event_queues:
            try:
                q.put_nowait(payload)
            except queue.Full:
                pass


# ──────────────────────────────────────────────
# SSE relay thread  (game server → our clients)
# ──────────────────────────────────────────────

def sse_relay_thread():
    url = f"{BASE_URL}/events/{TEAM_ID}"
    while True:
        try:
            print(f"[SSE] Connecting to {url} …")
            push_event("system", {"msg": "Connecting to game SSE stream…"})
            with requests.get(url, headers=SSE_HEADERS, stream=True, timeout=60) as resp:
                push_event("system", {"msg": f"SSE connected (HTTP {resp.status_code})"})
                event_name = "message"
                data_buf = []
                for raw_line in resp.iter_lines(decode_unicode=True):
                    if raw_line.startswith("event:"):
                        event_name = raw_line[6:].strip()
                    elif raw_line.startswith("data:"):
                        data_buf.append(raw_line[5:].strip())
                    elif raw_line == "":  # blank line = end of event
                        raw_data = " ".join(data_buf)
                        data_buf = []
                        try:
                            parsed = json.loads(raw_data) if raw_data else {}
                        except Exception:
                            parsed = {"raw": raw_data}

                        # Update shared state for important events
                        with state_lock:
                            if event_name == "game_phase_changed":
                                state["phase"] = parsed.get("phase", state["phase"])
                            elif event_name == "game_started":
                                state["turn_id"] = parsed.get("turn_id", state["turn_id"])
                                state["phase"] = "speaking"
                            elif event_name == "game_reset":
                                state["phase"] = "reset"
                                state["turn_id"] = None
                            elif event_name == "new_message":
                                msg_entry = {
                                    "ts": now_ts(),
                                    "sender_id": parsed.get("sender_id"),
                                    "sender_name": parsed.get("sender_name", "?"),
                                    "recipient_id": parsed.get("recipient_id"),
                                    "recipient_name": parsed.get("recipient_name", "?"),
                                    "text": parsed.get("text") or parsed.get("content") or str(parsed),
                                    "turn_id": state.get("turn_id"),
                                }
                                state["messages"].append(msg_entry)
                                if len(state["messages"]) > 200:
                                    state["messages"].pop(0)

                        push_event("sse_event", {
                            "event": event_name,
                            "payload": parsed,
                        })
                        event_name = "message"
        except Exception as e:
            push_event("system", {"msg": f"SSE disconnected: {e} — reconnecting in 5s"})
            time.sleep(5)


# ──────────────────────────────────────────────
# Helper: safe GET
# ──────────────────────────────────────────────

def api_get(path: str, params: dict = None, silent_404: bool = False):
    try:
        r = requests.get(f"{BASE_URL}{path}", headers=HEADERS, params=params, timeout=10)
        if r.status_code == 404 and silent_404:
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        push_event("system", {"msg": f"GET {path} failed: {e}"})
        return None


# ──────────────────────────────────────────────
# Diff helpers
# ──────────────────────────────────────────────

def diff_dict(old: dict, new: dict, label: str):
    """Return list of human-readable change strings for changed keys."""
    changes = []
    for k in set(list(old.keys()) + list(new.keys())):
        ov = old.get(k)
        nv = new.get(k)
        if ov != nv:
            changes.append({"field": k, "old": ov, "new": nv})
    return changes


def flatten_restaurant(r: dict) -> dict:
    """Extract the fields we want to track for diffing."""
    # menu can be {"items": [...]} or a list directly
    raw_menu = r.get("menu") or {}
    if isinstance(raw_menu, dict):
        menu_items = raw_menu.get("items") or []
    elif isinstance(raw_menu, list):
        menu_items = raw_menu
    else:
        menu_items = []
    menu = {item.get("name"): item.get("price") for item in menu_items if isinstance(item, dict)}

    inventory = r.get("inventory") or {}
    if not isinstance(inventory, dict):
        inventory = {}

    # kitchen may be a list or dict
    raw_kitchen = r.get("kitchen") or []
    if isinstance(raw_kitchen, list):
        kitchen = len(raw_kitchen)
    elif isinstance(raw_kitchen, dict):
        kitchen = len(raw_kitchen)
    else:
        kitchen = 0

    # receivedMessages may be a list or int
    recv = r.get("receivedMessages")
    if isinstance(recv, list):
        recv = len(recv)
    elif recv is None:
        recv = 0

    return {
        "balance": r.get("balance"),
        "reputation": r.get("reputation"),
        "isOpen": r.get("isOpen"),
        "menu": menu,
        "menu_count": len(menu),
        "inventory": inventory,
        "inventory_count": len(inventory),
        "kitchen": kitchen,
        "receivedMessages": recv,
    }


def flatten_market_entry(e: dict) -> dict:
    return {
        "side": e.get("side"),
        "ingredient_name": e.get("ingredient_name") or e.get("ingredientName"),
        "quantity": e.get("quantity"),
        "price": e.get("price"),
        "status": e.get("status"),
        "seller_id": e.get("seller_id") or e.get("sellerId"),
        "buyer_id": e.get("buyer_id") or e.get("buyerId"),
    }


# ──────────────────────────────────────────────
# Polling thread
# ──────────────────────────────────────────────

def _poll_game_state():
    """Infer turn_id from our own restaurant data (no dedicated game-state endpoint)."""
    # Try /restaurant/{TEAM_ID} — our own record often contains turnId / currentTurn
    data = api_get(f"/restaurant/{TEAM_ID}", silent_404=True)
    if data:
        turn = (data.get("turn_id") or data.get("turnId") or
                data.get("currentTurn") or data.get("current_turn"))
        if turn:
            with state_lock:
                if state["turn_id"] != turn:
                    state["turn_id"] = turn
                    push_event("system", {"msg": f"turn_id detected from restaurant data: {turn}"})
            return

    # Fallback: scan the last polled raw restaurant snapshots for any turnId field
    with state_lock:
        for r in state["restaurants_raw"].values():
            turn = (r.get("turn_id") or r.get("turnId") or
                    r.get("currentTurn") or r.get("current_turn"))
            if turn:
                if state["turn_id"] != turn:
                    state["turn_id"] = turn
                    push_event("system", {"msg": f"turn_id inferred from restaurants: {turn}"})
                break


def polling_thread():
    time.sleep(1)  # small delay so SSE thread connects first
    while True:
        if not USE_SSE:
            try:
                _poll_game_state()
            except Exception as e:
                push_event("system", {"msg": f"Poll game state error: {e}"})
        try:
            _poll_restaurants()
        except Exception as e:
            push_event("system", {"msg": f"Poll restaurants error: {e}"})
        try:
            _poll_market()
        except Exception as e:
            push_event("system", {"msg": f"Poll market error: {e}"})
        try:
            _poll_meals()
        except Exception as e:
            push_event("system", {"msg": f"Poll meals error: {e}"})
        try:
            _poll_bid_history()
        except Exception as e:
            push_event("system", {"msg": f"Poll bids error: {e}"})
        time.sleep(POLL_INTERVAL)


def _poll_restaurants():
    data = api_get("/restaurants")
    if not data:
        return
    restaurants = data if isinstance(data, list) else data.get("restaurants", [])
    with state_lock:
        for r in restaurants:
            rid = r.get("id")
            name = r.get("name", f"team {rid}")
            flat_new = flatten_restaurant(r)
            flat_old = state["restaurants"].get(rid)
            state["restaurants_raw"][rid] = r
            state["restaurants_names"][rid] = name
            if flat_old is None:
                # First time we see this restaurant
                state["restaurants"][rid] = flat_new
                state["restaurants_changes"].setdefault(rid, [])
                push_event("restaurant_snapshot", {
                    "id": rid,
                    "name": name,
                    "state": flat_new,
                })
            else:
                changes = diff_dict(flat_old, flat_new, name)
                if changes:
                    state["restaurants"][rid] = flat_new
                    change_entry = {"ts": now_ts(), "changes": changes}
                    log = state["restaurants_changes"].setdefault(rid, [])
                    log.append(change_entry)
                    if len(log) > 50:
                        log.pop(0)
                    push_event("restaurant_changed", {
                        "id": rid,
                        "name": name,
                        "changes": changes,
                        "state": flat_new,
                    })


def _poll_market():
    data = api_get("/market/entries")
    if not data:
        return
    entries = data if isinstance(data, list) else data.get("entries", [])
    with state_lock:
        seen_ids = set()
        for e in entries:
            eid = e.get("id")
            if eid is None:
                continue
            seen_ids.add(eid)
            flat_new = flatten_market_entry(e)
            flat_old = state["market"].get(eid)
            if flat_old is None:
                state["market"][eid] = flat_new
                push_event("market_new_entry", {
                    "id": eid,
                    "entry": flat_new,
                })
            else:
                changes = diff_dict(flat_old, flat_new, f"market#{eid}")
                if changes:
                    state["market"][eid] = flat_new
                    push_event("market_changed", {
                        "id": eid,
                        "changes": changes,
                        "entry": flat_new,
                    })
        # Detect removed entries
        for eid in list(state["market"].keys()):
            if eid not in seen_ids:
                old = state["market"].pop(eid)
                push_event("market_removed", {"id": eid, "entry": old})


def _poll_meals():
    with state_lock:
        turn_id = state.get("turn_id")
        restaurant_ids = list(state["restaurants"].keys())
    if not turn_id or not restaurant_ids:
        return
    for rid in restaurant_ids:
        data = api_get("/meals", params={"turn_id": turn_id, "restaurant_id": rid})
        if not data:
            continue
        meals = data if isinstance(data, list) else data.get("meals", [])
        with state_lock:
            rname = state["restaurants_names"].get(rid, f"team {rid}")
            for m in meals:
                mid = m.get("id") or m.get("client_id")
                key = (turn_id, rid, mid)
                flat_new = {
                    "restaurant_id": rid,
                    "restaurant_name": rname,
                    "client_id": m.get("client_id"),
                    "order": m.get("orderText") or m.get("order"),
                    "executed": m.get("executed"),
                    "dish": m.get("dish_name") or m.get("dish"),
                }
                flat_old = state["meals"].get(key)
                if flat_old is None:
                    state["meals"][key] = flat_new
                    push_event("meal_new", {"turn": turn_id, "restaurant_id": rid, "restaurant_name": rname, "meal": flat_new})
                else:
                    changes = diff_dict(flat_old, flat_new, f"meal#{mid}")
                    if changes:
                        state["meals"][key] = flat_new
                        push_event("meal_changed", {"turn": turn_id, "restaurant_id": rid, "restaurant_name": rname, "changes": changes, "meal": flat_new})


def _poll_bid_history():
    with state_lock:
        turn_id = state.get("turn_id")
    if not turn_id:
        return
    data = api_get("/bid_history", params={"turn_id": turn_id})
    if not data:
        return
    bids = data if isinstance(data, list) else data.get("bids", [])
    with state_lock:
        for b in bids:
            bid_id = b.get("id") or id(b)
            key = (turn_id, bid_id)
            if key not in state["bid_history"]:
                state["bid_history"][key] = b
                push_event("bid_history", {"turn": turn_id, "bid": b})


# ──────────────────────────────────────────────
# Flask routes
# ──────────────────────────────────────────────

SOCIAL_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>🍕 Agent Social — SPAM!</title>
<style>
  :root {
    --bg: #0a0a0f;
    --panel: #12121a;
    --border: #1e1e30;
    --accent: #e85d04;
    --accent2: #ff9f1c;
    --green: #2ecc71;
    --red: #e74c3c;
    --yellow: #f39c12;
    --blue: #3d9eff;
    --purple: #a855f7;
    --pink: #ec4899;
    --text: #e0e0e0;
    --muted: #666;
    --font: 'Segoe UI', system-ui, sans-serif;
    --mono: 'Courier New', monospace;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; overflow: hidden; background: var(--bg); color: var(--text); font-family: var(--font); font-size: 14px; }

  /* ── Header ── */
  header {
    height: 52px;
    background: var(--panel);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    padding: 0 20px;
    gap: 14px;
    flex-shrink: 0;
    z-index: 10;
  }
  header .logo { font-size: 20px; color: var(--accent); font-weight: 700; letter-spacing: 1px; }
  header .logo span { color: var(--accent2); }
  .badge {
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: .5px;
    border: 1px solid;
  }
  #phase-badge { border-color: var(--yellow); color: var(--yellow); background: rgba(243,156,18,.1); }
  #turn-badge  { border-color: var(--blue);   color: var(--blue);   background: rgba(61,158,255,.1); }
  #conn-badge  { border-color: var(--green);  color: var(--green);  background: rgba(46,204,113,.1); }
  #conn-badge.off { border-color: var(--red); color: var(--red); background: rgba(231,76,60,.1); }
  .spacer { flex: 1; }
  #agent-count { color: var(--muted); font-size: 12px; }

  /* ── Layout ── */
  .layout {
    display: grid;
    grid-template-columns: 320px 1fr;
    height: calc(100vh - 52px);
    overflow: hidden;
  }

  /* ── Left: Agent Roster ── */
  .roster {
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .roster-header {
    padding: 12px 16px;
    background: var(--panel);
    border-bottom: 1px solid var(--border);
    font-size: 11px;
    letter-spacing: 1px;
    color: var(--muted);
    text-transform: uppercase;
    flex-shrink: 0;
  }
  .roster-list {
    overflow-y: auto;
    flex: 1;
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .agent-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    transition: border-color .2s, background .2s;
    position: relative;
  }
  .agent-card:hover { border-color: #333; background: #16161f; }
  .agent-card.active { border-color: var(--accent); background: rgba(232,93,4,.06); }
  .agent-card.our-team { border-color: var(--purple) !important; }
  .agent-avatar {
    width: 40px; height: 40px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 16px; flex-shrink: 0;
    color: #fff;
  }
  .agent-info { flex: 1; min-width: 0; }
  .agent-name { font-weight: 600; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .agent-sub { font-size: 11px; color: var(--muted); display: flex; gap: 8px; margin-top: 2px; flex-wrap: wrap; }
  .agent-sub .val { color: var(--text); font-family: var(--mono); }
  .status-dot {
    width: 9px; height: 9px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .status-dot.open { background: var(--green); box-shadow: 0 0 5px var(--green); }
  .status-dot.closed { background: #333; }
  .agent-badge {
    position: absolute;
    top: 6px; right: 8px;
    font-size: 9px;
    padding: 1px 5px;
    border-radius: 3px;
    background: var(--purple);
    color: #fff;
    font-weight: 600;
  }
  .our-badge { background: var(--purple); }

  /* ── Right: Social Feed ── */
  .feed-col {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .feed-header {
    padding: 12px 16px;
    background: var(--panel);
    border-bottom: 1px solid var(--border);
    font-size: 11px;
    letter-spacing: 1px;
    color: var(--muted);
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }
  #msg-count {
    background: var(--accent);
    color: #fff;
    border-radius: 20px;
    padding: 1px 8px;
    font-size: 10px;
    font-weight: 600;
  }
  .feed-filter {
    padding: 8px 14px;
    border-bottom: 1px solid var(--border);
    display: flex;
    gap: 6px;
    flex-shrink: 0;
    background: #0d0d14;
  }
  .filt-btn {
    padding: 3px 10px;
    border-radius: 20px;
    border: 1px solid var(--border);
    background: transparent;
    color: var(--muted);
    cursor: pointer;
    font-size: 11px;
    font-family: var(--font);
    transition: all .15s;
  }
  .filt-btn.on { border-color: var(--accent); color: var(--accent); background: rgba(232,93,4,.12); }
  .feed-stream {
    flex: 1;
    overflow-y: auto;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  /* ── Post Card ── */
  .post {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px 14px;
    animation: slideIn .25s ease;
    position: relative;
  }
  @keyframes slideIn {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: none; }
  }
  .post.new-msg   { border-left: 3px solid var(--purple); }
  .post.sys-msg   { border-left: 3px solid var(--blue); opacity: .8; }
  .post.phase-evt { border-left: 3px solid var(--yellow); }
  .post.rest-evt  { border-left: 3px solid var(--green); }
  .post.meal-evt  { border-left: 3px solid var(--accent); }
  .post-head {
    display: flex;
    align-items: center;
    gap: 9px;
    margin-bottom: 7px;
  }
  .mini-avatar {
    width: 32px; height: 32px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 13px; flex-shrink: 0;
    color: #fff;
  }
  .post-meta { flex: 1; min-width: 0; }
  .post-author { font-weight: 600; font-size: 13px; }
  .post-to { font-size: 11px; color: var(--muted); margin-top: 1px; }
  .post-ts { font-size: 10px; color: var(--muted); font-family: var(--mono); flex-shrink: 0; }
  .post-body { font-size: 13px; line-height: 1.5; color: var(--text); word-break: break-word; }
  .post-body.mono { font-family: var(--mono); font-size: 12px; white-space: pre-wrap; }
  .tag-chip {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: .5px;
    margin-right: 4px;
    vertical-align: middle;
  }
  .tag-chip.msg   { background: var(--purple); color: #fff; }
  .tag-chip.sys   { background: var(--blue);   color: #fff; }
  .tag-chip.phase { background: var(--yellow); color: #000; }
  .tag-chip.rest  { background: var(--green);  color: #000; }
  .tag-chip.meal  { background: var(--accent); color: #fff; }
  .tag-chip.bid   { background: var(--pink);   color: #fff; }

  /* ── Scrollbar ── */
  ::-webkit-scrollbar { width: 5px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: #2a2a3a; border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: #3a3a5a; }

  /* ── Empty state ── */
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--muted);
    gap: 10px;
  }
  .empty-state .icon { font-size: 40px; opacity: .3; }
  .empty-state p { font-size: 13px; }
</style>
</head>
<body>

<header>
  <div class="logo">🍕 Agent<span>Social</span></div>
  <div id="phase-badge" class="badge">—</div>
  <div id="turn-badge"  class="badge">Turn —</div>
  <div class="spacer"></div>
  <span id="agent-count">Loading agents…</span>
  <div id="conn-badge" class="badge off">● CONNECTING</div>
</header>

<div class="layout">
  <!-- ── Roster ── -->
  <div class="roster">
    <div class="roster-header">🤖 Agents Online</div>
    <div class="roster-list" id="roster"></div>
  </div>

  <!-- ── Feed ── -->
  <div class="feed-col">
    <div class="feed-header">
      📡 Live Feed
      <span id="msg-count">0</span>
    </div>
    <div class="feed-filter">
      <button class="filt-btn on" data-f="all">All</button>
      <button class="filt-btn" data-f="new-msg">💬 Messages</button>
      <button class="filt-btn" data-f="phase-evt">⚡ Phase</button>
      <button class="filt-btn" data-f="rest-evt">🏪 Restaurants</button>
      <button class="filt-btn" data-f="meal-evt">🍽️ Meals</button>
      <button class="filt-btn" data-f="sys-msg">⚙️ System</button>
    </div>
    <div class="feed-stream" id="feed">
      <div class="empty-state">
        <div class="icon">📡</div>
        <p>Waiting for game events…</p>
      </div>
    </div>
  </div>
</div>

<script>
// ═══════════════════════════════════════════════════
// Config
// ═══════════════════════════════════════════════════
const TEAM_ID = 17;
const MAX_POSTS = 200;

// ═══════════════════════════════════════════════════
// State
// ═══════════════════════════════════════════════════
let restaurants = {};   // id → raw + flat
let posts = [];         // all post objects {id,type,html}
let postCount = 0;
let activeFilter = 'all';
let emptyCleared = false;

// ═══════════════════════════════════════════════════
// Avatar colors (deterministic by ID)
// ═══════════════════════════════════════════════════
const COLORS = [
  '#e85d04','#ff9f1c','#2ecc71','#3d9eff','#a855f7',
  '#ec4899','#06b6d4','#84cc16','#f59e0b','#8b5cf6',
  '#10b981','#ef4444','#6366f1','#14b8a6','#f97316',
];
function avatarColor(id) {
  return COLORS[Math.abs(parseInt(id) || 0) % COLORS.length];
}
function avatarLetter(name) {
  return (name || '?')[0].toUpperCase();
}
function miniAvatar(id, name, size=32) {
  const c = avatarColor(id);
  const l = avatarLetter(name);
  return `<div class="mini-avatar" style="width:${size}px;height:${size}px;background:${c}">${l}</div>`;
}

// ═══════════════════════════════════════════════════
// Roster rendering
// ═══════════════════════════════════════════════════
function renderRoster() {
  const roster = document.getElementById('roster');
  const sorted = Object.values(restaurants).sort((a,b) => {
    // Our team first, then by reputation desc
    if (a.id == TEAM_ID) return -1;
    if (b.id == TEAM_ID) return 1;
    const ra = a._flat?.reputation ?? 0;
    const rb = b._flat?.reputation ?? 0;
    return rb - ra;
  });

  document.getElementById('agent-count').textContent =
    `${sorted.length} agent${sorted.length !== 1 ? 's' : ''}`;

  roster.innerHTML = sorted.map(r => {
    const f = r._flat || {};
    const isUs = r.id == TEAM_ID;
    const isOpen = f.is_open;
    const rep = f.reputation ?? '—';
    const bal = f.balance != null ? '€' + Math.round(f.balance).toLocaleString() : '—';
    const zone = f.zone ?? '—';
    const menuN = Array.isArray(r.menu) ? r.menu.length : (f.menu_count ?? '—');
    const c = avatarColor(r.id);
    const letter = avatarLetter(r.name);
    return `
      <div class="agent-card${isUs ? ' our-team' : ''}" data-id="${r.id}" onclick="filterByAgent(${r.id})">
        ${isUs ? '<div class="agent-badge our-badge">US</div>' : ''}
        <div class="agent-avatar" style="background:${c}">${letter}</div>
        <div class="agent-info">
          <div class="agent-name">${r.name || 'Team ' + r.id}</div>
          <div class="agent-sub">
            <span>Rep <span class="val">${rep}</span></span>
            <span>Bal <span class="val">${bal}</span></span>
            <span>Zone <span class="val">${zone}</span></span>
            <span>Menu <span class="val">${menuN}</span></span>
          </div>
        </div>
        <div class="status-dot ${isOpen ? 'open' : 'closed'}"></div>
      </div>`;
  }).join('');
}

// ═══════════════════════════════════════════════════
// Feed: creating posts
// ═══════════════════════════════════════════════════
function clearEmpty() {
  if (!emptyCleared) {
    document.getElementById('feed').innerHTML = '';
    emptyCleared = true;
  }
}

function addPost(type, html, anchorId) {
  clearEmpty();
  const feed = document.getElementById('feed');
  const id = 'p' + (++postCount);
  const div = document.createElement('div');
  div.className = `post ${type}`;
  div.dataset.type = type;
  div.dataset.agent = anchorId || '';
  div.id = id;
  div.innerHTML = html;

  // Apply filter visibility
  if (activeFilter !== 'all' && !type.includes(activeFilter)) {
    div.style.display = 'none';
  }

  feed.appendChild(div);
  // Trim to max
  const all = feed.querySelectorAll('.post');
  if (all.length > MAX_POSTS) all[0].remove();
  // Scroll to bottom
  feed.scrollTop = feed.scrollHeight;

  document.getElementById('msg-count').textContent =
    feed.querySelectorAll('.post').length;

  return id;
}

// ── Agent message (new_message SSE event) ──
function postAgentMessage(payload) {
  const sid  = payload.sender_id    || null;
  const sname = payload.sender_name  || (sid ? 'Agent ' + sid : 'Unknown');
  const rid  = payload.recipient_id  || null;
  const rname = payload.recipient_name || (rid ? 'Agent ' + rid : 'broadcast');
  const text  = payload.text || payload.content || JSON.stringify(payload);
  const ts    = new Date().toLocaleTimeString();

  const html = `
    <div class="post-head">
      ${miniAvatar(sid, sname)}
      <div class="post-meta">
        <div class="post-author"><span class="tag-chip msg">MSG</span>${sname}</div>
        <div class="post-to">→ ${rname}</div>
      </div>
      <div class="post-ts">${ts}</div>
    </div>
    <div class="post-body">${escHtml(text)}</div>`;
  addPost('new-msg', html, sid);
}

// ── System / server message ──
function postSystem(msg) {
  const ts = new Date().toLocaleTimeString();
  const html = `
    <div class="post-head">
      ${miniAvatar('0', '⚙')}
      <div class="post-meta"><div class="post-author"><span class="tag-chip sys">SYS</span>Server</div></div>
      <div class="post-ts">${ts}</div>
    </div>
    <div class="post-body">${escHtml(msg)}</div>`;
  addPost('sys-msg', html, null);
}

// ── Phase change ──
function postPhase(phase, turnId) {
  const ts = new Date().toLocaleTimeString();
  const phaseEmoji = {speaking:'🗣️',closed_bid:'🔒',waiting:'⏳',serving:'🍽️',stopped:'🛑'}[phase] || '⚡';
  const html = `
    <div class="post-head">
      ${miniAvatar('sys', phaseEmoji, 32)}
      <div class="post-meta">
        <div class="post-author"><span class="tag-chip phase">PHASE</span>Game Phase Changed</div>
        <div class="post-to">Turn ${turnId ?? '—'}</div>
      </div>
      <div class="post-ts">${ts}</div>
    </div>
    <div class="post-body">Phase: <strong>${phase}</strong></div>`;
  addPost('phase-evt', html, null);
}

// ── Restaurant change ──
function postRestaurant(name, id, changes) {
  const ts = new Date().toLocaleTimeString();
  const changesText = changes.map(c => `${c.key}: ${c.old} → ${c.new}`).join(', ');
  const html = `
    <div class="post-head">
      ${miniAvatar(id, name)}
      <div class="post-meta">
        <div class="post-author"><span class="tag-chip rest">AGENT</span>${name}</div>
        <div class="post-to">State updated</div>
      </div>
      <div class="post-ts">${ts}</div>
    </div>
    <div class="post-body">${escHtml(changesText)}</div>`;
  addPost('rest-evt', html, id);
}

// ── Meal event ──
function postMeal(restaurantName, rid, meal, isNew) {
  const ts = new Date().toLocaleTimeString();
  const label = isNew ? 'New order' : 'Order updated';
  const dish = meal?.dish || meal?.dish_name || '?';
  const client = meal?.client_id || '?';
  const executed = meal?.executed;
  const html = `
    <div class="post-head">
      ${miniAvatar(rid, restaurantName)}
      <div class="post-meta">
        <div class="post-author"><span class="tag-chip meal">MEAL</span>${restaurantName}</div>
        <div class="post-to">${label} — Client #${client}</div>
      </div>
      <div class="post-ts">${ts}</div>
    </div>
    <div class="post-body">🍽️ ${escHtml(dish)} ${executed === true ? '✅' : executed === false ? '❌' : ''}</div>`;
  addPost('meal-evt', html, rid);
}

// ═══════════════════════════════════════════════════
// Filter
// ═══════════════════════════════════════════════════
document.querySelectorAll('.filt-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filt-btn').forEach(b => b.classList.remove('on'));
    btn.classList.add('on');
    activeFilter = btn.dataset.f;
    document.querySelectorAll('.post').forEach(p => {
      if (activeFilter === 'all') {
        p.style.display = '';
      } else {
        p.style.display = p.dataset.type === activeFilter ? '' : 'none';
      }
    });
  });
});

function filterByAgent(id) {
  // Toggle: if already filtering this agent, clear
  document.querySelectorAll('.post').forEach(p => {
    if (activeFilter === 'agent-' + id) {
      p.style.display = '';
    } else {
      p.style.display = (p.dataset.agent == id) ? '' : 'none';
    }
  });
  activeFilter = activeFilter === 'agent-' + id ? 'all' : 'agent-' + id;
  // Reset filter buttons
  document.querySelectorAll('.filt-btn').forEach(b => b.classList.remove('on'));
  if (activeFilter === 'all') document.querySelector('.filt-btn[data-f=all]').classList.add('on');
  // Highlight active card
  document.querySelectorAll('.agent-card').forEach(c => {
    c.classList.toggle('active', c.dataset.id == id && activeFilter === 'agent-' + id);
  });
}

// ═══════════════════════════════════════════════════
// Helper
// ═══════════════════════════════════════════════════
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ═══════════════════════════════════════════════════
// Phase badge update
// ═══════════════════════════════════════════════════
const PHASE_COLORS = {
  speaking: '#f39c12', closed_bid: '#e85d04', waiting: '#3d9eff',
  serving: '#2ecc71', stopped: '#e74c3c', reset: '#9b59b6'
};
function updateHeader(phase, turnId) {
  const pb = document.getElementById('phase-badge');
  const tb = document.getElementById('turn-badge');
  pb.textContent = (phase || '—').toUpperCase();
  const c = PHASE_COLORS[phase] || '#aaa';
  pb.style.borderColor = c;
  pb.style.color = c;
  pb.style.background = c + '19';
  if (turnId) tb.textContent = 'Turn ' + turnId;
}

// ═══════════════════════════════════════════════════
// Initial data load
// ═══════════════════════════════════════════════════
async function loadInitial() {
  try {
    const [restResp, stateResp, msgResp] = await Promise.all([
      fetch('/api/all_restaurants'),
      fetch('/api/game_state'),
      fetch('/api/messages'),
    ]);
    if (restResp.ok) {
      const data = await restResp.json();
      Object.assign(restaurants, data);
      renderRoster();
    }
    if (stateResp.ok) {
      const gs = await stateResp.json();
      updateHeader(gs.phase, gs.turn_id);
    }
    if (msgResp.ok) {
      const msgs = await msgResp.json();
      msgs.forEach(m => postAgentMessage(m));
    }
  } catch(e) {
    console.warn('Initial load failed:', e);
  }
}

// ═══════════════════════════════════════════════════
// SSE — only connects to our OWN tracker (port 5555)
// NO direct calls to the game server ever!
// ═══════════════════════════════════════════════════
function connectSSE() {
  const connBadge = document.getElementById('conn-badge');
  const es = new EventSource('/stream');

  es.onopen = () => {
    connBadge.textContent = '● LIVE';
    connBadge.className = 'badge';
    connBadge.style.borderColor = 'var(--green)';
    connBadge.style.color = 'var(--green)';
    connBadge.style.background = 'rgba(46,204,113,.1)';
  };
  es.onerror = () => {
    connBadge.textContent = '● RECONNECTING';
    connBadge.className = 'badge off';
    connBadge.style.borderColor = '';
    connBadge.style.color = '';
    connBadge.style.background = '';
  };

  es.onmessage = (ev) => {
    let evt;
    try { evt = JSON.parse(ev.data); } catch { return; }
    const { type, data: d } = evt;

    if (type === 'sse_event') {
      const gameEvt = d.event;
      const payload = d.payload || {};

      if (gameEvt === 'new_message') {
        postAgentMessage(payload);
      } else if (gameEvt === 'game_phase_changed' || gameEvt === 'game_started') {
        const phase = payload.phase || (gameEvt === 'game_started' ? 'speaking' : null);
        const turn  = payload.turn_id;
        updateHeader(phase, turn);
        postPhase(phase, turn);
      } else if (gameEvt === 'game_reset') {
        updateHeader('reset', null);
        postSystem('Game has been reset.');
      }

    } else if (type === 'restaurant_changed') {
      // Update our local restaurant cache
      const rid = d.id;
      if (restaurants[rid]) {
        if (d.state) restaurants[rid]._flat = d.state;
      } else {
        restaurants[rid] = { id: rid, name: d.name, _flat: d.state || {} };
      }
      renderRoster();
      if (d.changes && d.changes.length) {
        postRestaurant(d.name, rid, d.changes);
      }

    } else if (type === 'restaurant_snapshot') {
      const rid = d.id;
      if (!restaurants[rid]) {
        restaurants[rid] = { id: rid, name: d.name, _flat: d.state || {} };
        renderRoster();
      }

    } else if (type === 'meal_new') {
      postMeal(d.restaurant_name, d.restaurant_id, d.meal, true);

    } else if (type === 'meal_changed') {
      postMeal(d.restaurant_name, d.restaurant_id, d.meal, false);

    } else if (type === 'system') {
      postSystem(d.msg || JSON.stringify(d));
    }
  };
}

// ═══════════════════════════════════════════════════
// Boot
// ═══════════════════════════════════════════════════
loadInitial();
connectSSE();

// Refresh roster every 10 s (tracker already polls, no game API calls)
setInterval(async () => {
  try {
    const r = await fetch('/api/all_restaurants');
    if (r.ok) { Object.assign(restaurants, await r.json()); renderRoster(); }
  } catch {}
}, 10000);
</script>
</body>
</html>
"""  # end SOCIAL_TEMPLATE


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>🍕 SPAM! Server Tracker</title>
<style>
  :root {
    --bg: #0e0e0e;
    --panel: #161616;
    --border: #2a2a2a;
    --accent: #e85d04;
    --green: #2ecc71;
    --red: #e74c3c;
    --yellow: #f39c12;
    --blue: #3498db;
    --purple: #9b59b6;
    --text: #e0e0e0;
    --muted: #777;
    --font: 'Courier New', monospace;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html { height: 100%; overflow: hidden; }
  body { background: var(--bg); color: var(--text); font-family: var(--font); font-size: 13px; height: 100%; overflow: hidden; }
  header { background: var(--panel); border-bottom: 1px solid var(--border); padding: 10px 20px; display: flex; align-items: center; gap: 16px; position: sticky; top: 0; z-index: 100; }
  header h1 { font-size: 16px; color: var(--accent); letter-spacing: 2px; }
  #phase-badge { padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; background: #333; color: var(--yellow); border: 1px solid var(--yellow); }
  #turn-badge { padding: 3px 10px; border-radius: 4px; font-size: 12px; background: #1a1a2e; color: var(--blue); border: 1px solid var(--blue); }
  #conn-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--red); margin-left: auto; }
  #conn-dot.ok { background: var(--green); box-shadow: 0 0 6px var(--green); }
  #conn-label { font-size: 11px; color: var(--muted); }
  .layout { display: grid; grid-template-columns: 1fr 420px; gap: 0; height: calc(100vh - 45px); overflow: hidden; }
  .main-col { overflow-y: auto; overflow-x: hidden; padding: 14px; display: flex; flex-direction: column; gap: 14px; min-height: 0; }
  .side-col { border-left: 1px solid var(--border); overflow: hidden; display: flex; flex-direction: column; min-height: 0; }
  .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }
  .panel-header { padding: 8px 12px; background: #1a1a1a; border-bottom: 1px solid var(--border); font-size: 11px; letter-spacing: 1px; color: var(--muted); display: flex; justify-content: space-between; align-items: center; }
  .panel-header span.badge { background: var(--accent); color: #fff; border-radius: 3px; padding: 1px 6px; font-size: 10px; }
  table { width: 100%; border-collapse: collapse; }
  th { padding: 6px 8px; text-align: left; color: var(--muted); font-size: 10px; letter-spacing: 1px; border-bottom: 1px solid var(--border); background: #111; }
  td { padding: 5px 8px; border-bottom: 1px solid #1a1a1a; vertical-align: top; white-space: nowrap; }
  tr:hover td { background: #1c1c1c; }
  td.num { text-align: right; font-feature-settings: "tnum"; }
  .up { color: var(--green); }
  .dn { color: var(--red); }
  .warn { color: var(--yellow); }
  .info { color: var(--blue); }
  .open-true  { color: var(--green); }
  .open-false { color: var(--red); }
  /* Event feed */
  #feed { flex: 1; overflow-y: auto; overflow-x: hidden; display: flex; flex-direction: column-reverse; padding: 8px; gap: 4px; min-height: 0; }
  .evt { border-left: 3px solid var(--border); padding: 5px 8px; background: #111; border-radius: 0 4px 4px 0; animation: fadein .3s ease; }
  .evt:hover { background: #1a1a1a; }
  @keyframes fadein { from { opacity:0; transform: translateX(6px); } to { opacity:1; transform: none; } }
  .evt .ts { color: var(--muted); font-size: 10px; margin-right: 6px; }
  .evt .tag { font-size: 10px; padding: 1px 5px; border-radius: 3px; margin-right: 4px; }
  .evt .body { color: var(--text); word-break: break-word; white-space: pre-wrap; }
  /* event type colors */
  .evt.sse_event { border-color: var(--blue); }
  .evt.restaurant_changed { border-color: var(--green); }
  .evt.restaurant_snapshot { border-color: #333; }
  .evt.market_new_entry { border-color: var(--purple); }
  .evt.market_changed { border-color: var(--yellow); }
  .evt.market_removed { border-color: var(--red); }
  .evt.meal_new { border-color: var(--accent); }
  .evt.meal_changed { border-color: var(--yellow); }
  .evt.bid_history { border-color: var(--purple); }
  .evt.system { border-color: #444; }
  .tag.sse_event { background: var(--blue); color: #fff; }
  .tag.restaurant_changed { background: var(--green); color: #000; }
  .tag.restaurant_snapshot { background: #333; color: #fff; }
  .tag.market_new_entry { background: var(--purple); color: #fff; }
  .tag.market_changed { background: var(--yellow); color: #000; }
  .tag.market_removed { background: var(--red); color: #fff; }
  .tag.meal_new { background: var(--accent); color: #fff; }
  .tag.meal_changed { background: var(--yellow); color: #000; }
  .tag.bid_history { background: var(--purple); color: #fff; }
  .tag.system { background: #333; color: #aaa; }
  .feed-header { padding: 8px 12px; background: #1a1a1a; border-bottom: 1px solid var(--border); font-size: 11px; letter-spacing: 1px; color: var(--muted); display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
  #feed-count { background: var(--accent); color: #fff; border-radius: 3px; padding: 1px 6px; font-size: 10px; }
  .market-row td { max-width: 200px; overflow: hidden; text-overflow: ellipsis; }
  .table-scroll { overflow-x: auto; overflow-y: auto; max-height: 400px; }
  #filter-bar { padding: 6px 12px; background: #111; border-bottom: 1px solid var(--border); display: flex; gap: 6px; flex-shrink: 0; flex-wrap: wrap; }
  .filter-btn { padding: 2px 8px; border-radius: 3px; border: 1px solid var(--border); background: transparent; color: var(--muted); cursor: pointer; font-family: var(--font); font-size: 11px; }
  .filter-btn.active { color: #fff; }
  .filter-btn.all.active { border-color: var(--text); color: var(--text); }
  .filter-btn.sse_event.active { border-color: var(--blue); color: var(--blue); }
  .filter-btn.restaurant_changed.active { border-color: var(--green); color: var(--green); }
  .filter-btn.market_new_entry.active { border-color: var(--purple); color: var(--purple); }
  .filter-btn.market_changed.active { border-color: var(--yellow); color: var(--yellow); }
  .filter-btn.meal_new.active { border-color: var(--accent); color: var(--accent); }
  .filter-btn.system.active { border-color: #555; color: #aaa; }
  .highlight { animation: hl 1.5s ease; }
  @keyframes hl { 0%,100% { background: transparent; } 20% { background: rgba(232,93,4,.18); } }
  .delta-up::after { content: ' ▲'; color: var(--green); font-size: 10px; }
  .delta-dn::after { content: ' ▼'; color: var(--red); font-size: 10px; }
  /* Modal */
  #modal-overlay { display:none; position:fixed; inset:0; background:rgba(0,0,0,.75); z-index:999; align-items:center; justify-content:center; }
  #modal-overlay.open { display:flex; }
  #modal { background:var(--panel); border:1px solid var(--border); border-radius:8px; width:min(860px,95vw); max-height:92vh; height:92vh; display:flex; flex-direction:column; overflow:hidden; }
  #modal-header { padding:12px 16px; background:#1a1a1a; border-bottom:1px solid var(--border); display:flex; align-items:center; gap:12px; flex-shrink:0; }
  #modal-title { font-size:15px; color:var(--accent); flex:1; }
  #modal-close { background:transparent; border:1px solid #444; color:#aaa; cursor:pointer; font-size:16px; padding:2px 10px; border-radius:4px; font-family:var(--font); }
  #modal-close:hover { border-color:var(--accent); color:var(--accent); }
  #modal-refresh { background:transparent; border:1px solid #444; color:#aaa; cursor:pointer; font-size:11px; padding:4px 10px; border-radius:4px; font-family:var(--font); }
  #modal-refresh:hover { border-color:var(--blue); color:var(--blue); }
  #modal-body { overflow-y:auto; overflow-x:hidden; padding:16px; display:flex; flex-direction:column; gap:16px; flex:1; min-height:0; }
  .detail-section { border:1px solid var(--border); border-radius:6px; overflow-y:auto; overflow-x:hidden; max-height:480px; flex-shrink:0; }
  .detail-section-header { padding:7px 12px; background:#111; font-size:10px; letter-spacing:1.5px; color:var(--muted); border-bottom:1px solid var(--border); display:flex; justify-content:space-between; position:sticky; top:0; z-index:2; }
  .detail-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(160px,1fr)); gap:0; }
  .detail-kv { padding:8px 12px; border-right:1px solid #1a1a1a; border-bottom:1px solid #1a1a1a; }
  .detail-kv .dk { font-size:10px; color:var(--muted); margin-bottom:3px; letter-spacing:.5px; }
  .detail-kv .dv { font-size:13px; }
  .modal-table { width:100%; border-collapse:collapse; }
  .modal-table th { padding:6px 10px; text-align:left; font-size:10px; color:var(--muted); letter-spacing:1px; border-bottom:1px solid var(--border); background:#111; }
  .modal-table td { padding:5px 10px; border-bottom:1px solid #1a1a1a; font-size:12px; }
  .modal-table tr:hover td { background:#1c1c1c; }
  .change-entry { padding:6px 10px; border-bottom:1px solid #1a1a1a; display:flex; gap:8px; align-items:flex-start; font-size:12px; }
  .change-entry:last-child { border:none; }
  .change-ts { color:var(--muted); font-size:10px; white-space:nowrap; min-width:80px; padding-top:2px; }
  .change-list { display:flex; flex-wrap:wrap; gap:4px; }
  .change-pill { padding:2px 7px; border-radius:3px; background:#1e1e1e; border:1px solid var(--border); font-size:11px; }
  .change-pill .old { color:var(--red); }
  .change-pill .new { color:var(--green); }
  #modal-loading { text-align:center; padding:40px; color:var(--muted); }
  tr.clickable { cursor:pointer; }
  tr.clickable:hover td { background:#1f1f1f !important; }
  .team-17 td:first-child { color:var(--accent); font-weight:bold; }
</style>
</head>
<body>
<header>
  <h1>🍕 SPAM! TRACKER</h1>
  <div id="phase-badge">PHASE: —</div>
  <div id="turn-badge">TURN: —</div>
  <div style="margin-left:auto;display:flex;align-items:center;gap:6px;">
    <span id="conn-label">disconnected</span>
    <div id="conn-dot"></div>
  </div>
</header>
<div class="layout">
  <!-- Main area -->
  <div class="main-col">
    <!-- Restaurants table -->
    <div class="panel">
      <div class="panel-header">🏪 ALL RESTAURANTS <span class="badge" id="rest-count">0</span> <span style="color:var(--muted);font-size:10px;font-weight:normal">click a row to inspect</span></div>
      <div class="table-scroll">
        <table id="rest-table">
          <thead>
            <tr>
              <th>ID</th><th>NAME</th><th>BALANCE</th><th>REPUTATION</th>
              <th>OPEN</th><th>MENU ITEMS</th><th>INVENTORY</th><th>KITCHEN</th><th>MESSAGES</th>
            </tr>
          </thead>
          <tbody id="rest-tbody"></tbody>
        </table>
      </div>
    </div>
    <!-- Market table -->
    <div class="panel">
      <div class="panel-header">📈 MARKET ENTRIES <span class="badge" id="mkt-count">0</span></div>
      <div class="table-scroll">
        <table id="mkt-table">
          <thead>
            <tr>
              <th>ID</th><th>SIDE</th><th>INGREDIENT</th><th>QTY</th>
              <th>PRICE</th><th>STATUS</th><th>SELLER</th><th>BUYER</th>
            </tr>
          </thead>
          <tbody id="mkt-tbody"></tbody>
        </table>
      </div>
    </div>
    <!-- Meals table -->
    <div class="panel">
      <div class="panel-header">🍽️ ALL TEAMS' MEALS (this turn) <span class="badge" id="meal-count">0</span></div>
      <div class="table-scroll">
        <table id="meal-table">
          <thead>
            <tr><th>TEAM</th><th>CLIENT</th><th>ORDER</th><th>DISH</th><th>SERVED</th></tr>
          </thead>
          <tbody id="meal-tbody"></tbody>
        </table>
      </div>
    </div>
  </div>
  <!-- Side feed -->
  <div class="side-col">
    <div class="feed-header">
      ⚡ LIVE EVENT FEED
      <span id="feed-count">0</span>
      <button onclick="clearFeed()" style="margin-left:auto;background:transparent;border:1px solid #333;color:#555;cursor:pointer;font-family:var(--font);font-size:10px;padding:2px 6px;border-radius:3px;">CLEAR</button>
    </div>
    <div id="filter-bar">
      <button class="filter-btn all active" onclick="setFilter('all')">ALL</button>
      <button class="filter-btn sse_event" onclick="setFilter('sse_event')">SSE</button>
      <button class="filter-btn restaurant_changed" onclick="setFilter('restaurant_changed')">RESTAURANT</button>
      <button class="filter-btn market_new_entry" onclick="setFilter('market_new_entry')">MARKET</button>
      <button class="filter-btn meal_new" onclick="setFilter('meal_new')">MEALS</button>
      <button class="filter-btn system" onclick="setFilter('system')">SYSTEM</button>
    </div>
    <div id="feed"></div>
  </div>
</div>

<!-- Team Detail Modal -->
<div id="modal-overlay" onclick="closeModal(event)">
  <div id="modal">
    <div id="modal-header">
      <div id="modal-title">Team</div>
      <button id="modal-refresh" onclick="refreshModal()">⟳ REFRESH</button>
      <button id="modal-close" onclick="closeModalDirect()">✕</button>
    </div>
    <div id="modal-body"><div id="modal-loading">Loading…</div></div>
  </div>
</div>

<script>
// ── State ──────────────────────────────────────
const restaurants = {};
const market = {};
const meals = {};
let feedCount = 0;
let activeFilter = 'all';
const allEvents = [];
let modalOpenId = null;

// ── SSE connection ─────────────────────────────
let evtSource;
function connect() {
  evtSource = new EventSource('/stream');
  evtSource.onopen = () => {
    document.getElementById('conn-dot').className = 'ok';
    document.getElementById('conn-label').textContent = 'live';
  };
  evtSource.onerror = () => {
    document.getElementById('conn-dot').className = '';
    document.getElementById('conn-label').textContent = 'reconnecting…';
  };
  evtSource.onmessage = (e) => {
    const evt = JSON.parse(e.data);
    handleEvent(evt);
  };
}

// ── Event dispatcher ───────────────────────────
function handleEvent(evt) {
  const {type, ts, data} = evt;
  addFeedEntry(type, ts, formatEvent(type, data));

  if (type === 'restaurant_snapshot') updateRestaurant(data.id, data.name, data.state, false);
  else if (type === 'restaurant_changed') updateRestaurant(data.id, data.name, data.state, true);
  else if (type === 'market_new_entry') updateMarket(data.id, data.entry, false);
  else if (type === 'market_changed') updateMarket(data.id, data.entry, true);
  else if (type === 'market_removed') removeMarket(data.id);
  else if (type === 'meal_new' || type === 'meal_changed') updateMeal(data);
  else if (type === 'sse_event') {
    if (data.event === 'game_phase_changed') {
      setPhase(data.payload.phase);
    } else if (data.event === 'game_started') {
      setPhase('speaking');
      setTurn(data.payload.turn_id);
    } else if (data.event === 'game_reset') {
      setPhase('reset');
    } else if (data.event === 'heartbeat') {
      // skip heartbeats in feed (too noisy)
      allEvents.shift(); // remove just-added heartbeat
      feedCount--;
      return;
    }
  }
}

function setPhase(p) {
  const el = document.getElementById('phase-badge');
  el.textContent = 'PHASE: ' + (p||'?').toUpperCase();
}
function setTurn(t) {
  if (t) document.getElementById('turn-badge').textContent = 'TURN: ' + t;
}

// ── Format event text ──────────────────────────
function formatEvent(type, data) {
  switch(type) {
    case 'sse_event':
      return `[${data.event}] ${JSON.stringify(data.payload)}`;
    case 'restaurant_snapshot':
      return `${data.name} (id:${data.id}) — snapshot: bal=${data.state.balance} rep=${data.state.reputation}`;
    case 'restaurant_changed': {
      const ch = data.changes.map(c => {
        if (typeof c.old === 'object' || typeof c.new === 'object') {
          return `${c.field}: changed`;
        }
        return `${c.field}: ${c.old} → ${c.new}`;
      }).join(', ');
      return `${data.name} (id:${data.id}) — ${ch}`;
    }
    case 'market_new_entry':
      return `NEW ${data.entry.side} — ${data.entry.ingredient_name} x${data.entry.quantity} @ ${data.entry.price} (id:${data.id})`;
    case 'market_changed':
      return `Market #${data.id} changed: ${data.changes.map(c=>`${c.field}: ${c.old}→${c.new}`).join(', ')}`;
    case 'market_removed':
      return `Market #${data.id} removed (${data.entry.ingredient_name})`;
    case 'meal_new':
      return `[${data.restaurant_name||'team '+data.restaurant_id}] New client — ${data.meal.order||'?'} (id:${data.meal.client_id})`;
    case 'meal_changed':
      return `[${data.restaurant_name||'team '+data.restaurant_id}] Meal updated: ${data.changes.map(c=>`${c.field}: ${c.old}→${c.new}`).join(', ')}`;
    case 'bid_history':
      return `Bid: ${JSON.stringify(data.bid)}`;
    case 'system':
      return data.msg;
    default:
      return JSON.stringify(data);
  }
}

// ── Feed ───────────────────────────────────────
function addFeedEntry(type, ts, text) {
  feedCount++;
  document.getElementById('feed-count').textContent = feedCount;

  const entry = {type, ts, text};
  allEvents.unshift(entry);
  if (allEvents.length > 500) allEvents.pop();

  if (activeFilter === 'all' || activeFilter === type ||
      (activeFilter === 'restaurant_changed' && (type === 'restaurant_changed' || type === 'restaurant_snapshot')) ||
      (activeFilter === 'market_new_entry' && (type === 'market_new_entry' || type === 'market_changed' || type === 'market_removed')) ||
      (activeFilter === 'meal_new' && (type === 'meal_new' || type === 'meal_changed' || type === 'bid_history'))) {
    prependFeedDOM(entry);
  }
}

function prependFeedDOM(entry) {
  const feed = document.getElementById('feed');
  const div = document.createElement('div');
  div.className = `evt ${entry.type}`;
  div.innerHTML = `<span class="ts">${entry.ts}</span><span class="tag ${entry.type}">${entry.type.replace('_',' ').toUpperCase()}</span><span class="body">${escHtml(entry.text)}</span>`;
  feed.prepend(div);
  // Limit DOM nodes
  while (feed.children.length > 200) feed.lastChild.remove();
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function clearFeed() {
  document.getElementById('feed').innerHTML = '';
}

function setFilter(f) {
  activeFilter = f;
  document.querySelectorAll('.filter-btn').forEach(b => {
    b.classList.toggle('active', b.classList.contains(f) || (f==='all' && b.classList.contains('all')));
  });
  // Re-render
  const feed = document.getElementById('feed');
  feed.innerHTML = '';
  allEvents.forEach(entry => {
    if (activeFilter === 'all' || activeFilter === entry.type ||
        (activeFilter === 'restaurant_changed' && (entry.type === 'restaurant_changed' || entry.type === 'restaurant_snapshot')) ||
        (activeFilter === 'market_new_entry' && (entry.type === 'market_new_entry' || entry.type === 'market_changed' || entry.type === 'market_removed')) ||
        (activeFilter === 'meal_new' && (entry.type === 'meal_new' || entry.type === 'meal_changed' || entry.type === 'bid_history'))) {
      prependFeedDOM(entry);
    }
  });
}

// ── Restaurants table ──────────────────────────
function updateRestaurant(id, name, s, highlight) {
  restaurants[id] = {name, ...s};
  const tbody = document.getElementById('rest-tbody');
  let row = document.getElementById(`rest-${id}`);
  const menuCount = s.menu ? Object.keys(s.menu).length : 0;
  const invCount = s.inventory ? Object.keys(s.inventory).length : 0;
  const msgs = s.receivedMessages ?? 0;
  const openCls = s.isOpen ? 'open-true' : 'open-false';
  const openTxt = s.isOpen ? '🟢 YES' : '🔴 NO';
  const isUs = String(id) === '17';
  const idCell = isUs ? `<td class="num" style="color:var(--accent);font-weight:bold">★ ${id}</td>` : `<td class="num">${id}</td>`;
  const inner = `
    ${idCell}
    <td>${escHtml(name)}</td>
    <td class="num">${s.balance ?? '—'}</td>
    <td class="num">${s.reputation ?? '—'}</td>
    <td class="${openCls}">${openTxt}</td>
    <td class="num">${s.menu_count ?? menuCount}</td>
    <td class="num">${s.inventory_count ?? invCount}</td>
    <td class="num">${s.kitchen ?? '—'}</td>
    <td class="num ${msgs>0?'warn':''}">${msgs}</td>
  `;
  if (!row) {
    row = document.createElement('tr');
    row.id = `rest-${id}`;
    row.className = 'clickable';
    row.addEventListener('click', () => openModal(id, name));
    tbody.appendChild(row);
    const rows = Array.from(tbody.querySelectorAll('tr')).sort((a,b) => +a.id.split('-')[1] - +b.id.split('-')[1]);
    rows.forEach(r => tbody.appendChild(r));
  }
  row.innerHTML = inner;
  if (highlight) {
    row.classList.remove('highlight');
    void row.offsetWidth;
    row.classList.add('highlight');
  }
  document.getElementById('rest-count').textContent = Object.keys(restaurants).length;
  // if this team's modal is open, refresh it live
  if (modalOpenId !== null && String(modalOpenId) === String(id)) refreshModal();
}

// ── Team Detail Modal ──────────────────────────
function openModal(id, name) {
  modalOpenId = id;
  document.getElementById('modal-title').textContent = `🏪 Team Inspector — ${name} (id: ${id})`;
  document.getElementById('modal-body').innerHTML = '<div id="modal-loading">Loading…</div>';
  document.getElementById('modal-overlay').classList.add('open');
  fetchModalData(id);
}

function refreshModal() {
  if (modalOpenId === null) return;
  const name = (restaurants[modalOpenId] || {}).name || `#${modalOpenId}`;
  fetchModalData(modalOpenId);
}

function closeModal(e) {
  if (e.target === document.getElementById('modal-overlay')) closeModalDirect();
}
function closeModalDirect() {
  document.getElementById('modal-overlay').classList.remove('open');
  modalOpenId = null;
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModalDirect(); });

async function fetchModalData(id) {
  try {
    const res = await fetch(`/api/restaurant/${id}`);
    const d = await res.json();
    renderModal(id, d);
  } catch(e) {
    document.getElementById('modal-body').innerHTML =
      `<div id="modal-loading" style="color:var(--red)">Error: ${e}</div>`;
  }
}

function renderModal(id, d) {
  const r = d.raw || {};
  const menuData = d.menu || {};
  const menuItems = menuData.items || (Array.isArray(menuData) ? menuData : []);
  const changeLog = d.change_log || [];
  const mealsList = d.meals || [];

  const inv = r.inventory || {};
  const invEntries = Object.entries(inv);

  const kitchen = r.kitchen || [];
  const kitchenList = Array.isArray(kitchen) ? kitchen : Object.entries(kitchen);

  const msgs = r.receivedMessages || [];
  const msgList = Array.isArray(msgs) ? msgs : [];

  const isOpenHtml = r.isOpen
    ? '<span class="open-true">🟢 OPEN</span>'
    : '<span class="open-false">🔴 CLOSED</span>';

  let html = '';

  // ── Overview stats
  html += `<div class="detail-section">
    <div class="detail-section-header"><span>📊 OVERVIEW</span><span style="color:var(--muted);font-size:10px">turn: ${d.turn_id ?? '—'}</span></div>
    <div class="detail-grid">
      <div class="detail-kv"><div class="dk">BALANCE</div><div class="dv" style="color:var(--green);font-size:18px;font-weight:bold">${r.balance ?? '—'}</div></div>
      <div class="detail-kv"><div class="dk">REPUTATION</div><div class="dv" style="font-size:18px">${r.reputation ?? '—'}</div></div>
      <div class="detail-kv"><div class="dk">STATUS</div><div class="dv">${isOpenHtml}</div></div>
      <div class="detail-kv"><div class="dk">MENU ITEMS</div><div class="dv">${menuItems.length}</div></div>
      <div class="detail-kv"><div class="dk">INVENTORY SLOTS</div><div class="dv">${invEntries.length}</div></div>
      <div class="detail-kv"><div class="dk">KITCHEN ACTIVE</div><div class="dv">${kitchenList.length}</div></div>
      <div class="detail-kv"><div class="dk">MESSAGES</div><div class="dv ${msgList.length>0?'warn':''}">${msgList.length}</div></div>
      <div class="detail-kv"><div class="dk">CHANGES LOGGED</div><div class="dv">${changeLog.length}</div></div>
    </div>
  </div>`;

  // ── Menu
  html += `<div class="detail-section">
    <div class="detail-section-header"><span>🍽️ MENU</span><span>${menuItems.length} items</span></div>`;
  if (menuItems.length === 0) {
    html += `<div style="padding:12px;color:var(--muted);font-size:12px">No menu items set</div>`;
  } else {
    html += `<table class="modal-table"><thead><tr><th>#</th><th>DISH NAME</th><th style="text-align:right">PRICE</th></tr></thead><tbody>`;
    menuItems.forEach((item, i) => {
      const nm = item.name || item.Name || JSON.stringify(item);
      const pr = item.price ?? item.Price ?? '—';
      html += `<tr><td class="num" style="color:var(--muted)">${i+1}</td><td>${escHtml(String(nm))}</td><td class="num" style="color:var(--green)">${pr}</td></tr>`;
    });
    html += `</tbody></table>`;
  }
  html += `</div>`;

  // ── Inventory
  html += `<div class="detail-section">
    <div class="detail-section-header"><span>📦 INVENTORY</span><span>${invEntries.length} ingredients</span></div>`;
  if (invEntries.length === 0) {
    html += `<div style="padding:12px;color:var(--muted);font-size:12px">Empty</div>`;
  } else {
    html += `<table class="modal-table"><thead><tr><th>INGREDIENT</th><th style="text-align:right">QTY</th></tr></thead><tbody>`;
    invEntries.sort((a,b) => b[1]-a[1]).forEach(([ing, qty]) => {
      html += `<tr><td>${escHtml(ing)}</td><td class="num">${qty}</td></tr>`;
    });
    html += `</tbody></table>`;
  }
  html += `</div>`;

  // ── Kitchen
  html += `<div class="detail-section">
    <div class="detail-section-header"><span>👨‍🍳 KITCHEN (cooking now)</span><span>${kitchenList.length}</span></div>`;
  if (kitchenList.length === 0) {
    html += `<div style="padding:12px;color:var(--muted);font-size:12px">Nothing cooking</div>`;
  } else {
    html += `<table class="modal-table"><thead><tr><th>ITEM</th><th>DETAIL</th></tr></thead><tbody>`;
    kitchenList.forEach(entry => {
      const [k, v] = Array.isArray(entry) ? entry : [JSON.stringify(entry), ''];
      html += `<tr><td>${escHtml(String(k))}</td><td>${escHtml(String(v))}</td></tr>`;
    });
    html += `</tbody></table>`;
  }
  html += `</div>`;

  // ── Meals (only populated for our own team)
  if (mealsList.length > 0) {
    html += `<div class="detail-section">
      <div class="detail-section-header"><span>🍽️ MEALS THIS TURN</span><span>${mealsList.length}</span></div>
      <table class="modal-table"><thead><tr><th>CLIENT</th><th>ORDER</th><th>DISH</th><th>SERVED</th></tr></thead><tbody>`;
    mealsList.forEach(m => {
      const served = m.executed ? '<span class="open-true">✅</span>' : '<span style="color:var(--muted)">⏳</span>';
      html += `<tr>
        <td style="font-size:10px;max-width:80px;overflow:hidden;text-overflow:ellipsis">${escHtml(String(m.client_id||''))}</td>
        <td style="white-space:normal;max-width:220px">${escHtml(m.orderText||m.order||'')}</td>
        <td>${escHtml(m.dish_name||m.dish||'—')}</td>
        <td>${served}</td></tr>`;
    });
    html += `</tbody></table></div>`;
  }

  // ── Received messages
  if (msgList.length > 0) {
    html += `<div class="detail-section">
      <div class="detail-section-header"><span>✉️ RECEIVED MESSAGES</span><span>${msgList.length}</span></div>
      <table class="modal-table"><thead><tr><th>FROM</th><th>TEXT</th><th>TIME</th></tr></thead><tbody>`;
    msgList.forEach(m => {
      const sender = m.senderName || m.sender_name || m.senderId || '?';
      const text = m.text || m.body || JSON.stringify(m);
      const dt = m.datetime || m.ts || '';
      html += `<tr><td>${escHtml(String(sender))}</td><td style="white-space:normal">${escHtml(String(text))}</td><td style="color:var(--muted);font-size:10px">${escHtml(String(dt))}</td></tr>`;
    });
    html += `</tbody></table></div>`;
  }

  // ── Change history
  html += `<div class="detail-section">
    <div class="detail-section-header"><span>📝 CHANGE LOG</span><span>last ${changeLog.length} events</span></div>`;
  if (changeLog.length === 0) {
    html += `<div style="padding:12px;color:var(--muted);font-size:12px">No changes recorded yet — tracker started after last change or game hasn't started</div>`;
  } else {
    [...changeLog].reverse().forEach(entry => {
      const pills = entry.changes.map(c => {
        if (typeof c.old === 'object' || typeof c.new === 'object') {
          return `<span class="change-pill">${escHtml(c.field)}: <em style="color:var(--yellow)">changed</em></span>`;
        }
        return `<span class="change-pill">${escHtml(c.field)}: <span class="old">${escHtml(String(c.old))}</span> → <span class="new">${escHtml(String(c.new))}</span></span>`;
      }).join('');
      html += `<div class="change-entry"><span class="change-ts">${entry.ts}</span><div class="change-list">${pills}</div></div>`;
    });
  }
  html += `</div>`;

  document.getElementById('modal-body').innerHTML = html;
}

// ── Market table ───────────────────────────────
function updateMarket(id, entry, highlight) {
  market[id] = entry;
  const tbody = document.getElementById('mkt-tbody');
  let row = document.getElementById(`mkt-${id}`);
  const sideCls = entry.side === 'BUY' ? 'up' : 'dn';
  const stCls = entry.status === 'open' ? 'up' : entry.status === 'closed' ? 'dn' : '';
  const inner = `
    <td class="num">${id}</td>
    <td class="${sideCls}">${entry.side||'—'}</td>
    <td style="max-width:160px;overflow:hidden;text-overflow:ellipsis">${escHtml(entry.ingredient_name||'')}</td>
    <td class="num">${entry.quantity??'—'}</td>
    <td class="num">${entry.price??'—'}</td>
    <td class="${stCls}">${entry.status||'—'}</td>
    <td class="num">${entry.seller_id??'—'}</td>
    <td class="num">${entry.buyer_id??'—'}</td>
  `;
  if (!row) {
    row = document.createElement('tr');
    row.id = `mkt-${id}`;
    row.className = 'market-row';
    tbody.insertBefore(row, tbody.firstChild);
  }
  row.innerHTML = inner;
  if (highlight) {
    row.classList.remove('highlight');
    void row.offsetWidth;
    row.classList.add('highlight');
  }
  document.getElementById('mkt-count').textContent = Object.keys(market).length;
}

function removeMarket(id) {
  const row = document.getElementById(`mkt-${id}`);
  if (row) row.style.opacity = '0.3';
  delete market[id];
  document.getElementById('mkt-count').textContent = Object.keys(market).length;
}

// ── Meals table ────────────────────────────────
function updateMeal(data) {
  const meal = data.meal || data;
  const rid = data.restaurant_id || meal.restaurant_id || '?';
  const rname = data.restaurant_name || meal.restaurant_name || `team ${rid}`;
  const rowKey = `meal-${rid}-${meal.client_id}`;
  meals[rowKey] = meal;
  const tbody = document.getElementById('meal-tbody');
  let row = document.getElementById(rowKey);
  const srvCls = meal.executed ? 'up' : 'muted';
  const srvTxt = meal.executed ? '✅ YES' : '⏳ NO';
  const isUs = String(rid) === '17';
  const teamCell = isUs
    ? `<td style="color:var(--accent);font-weight:bold;white-space:nowrap">★ ${escHtml(rname)}</td>`
    : `<td style="color:var(--blue);white-space:nowrap">${escHtml(rname)}</td>`;
  const inner = `
    ${teamCell}
    <td style="max-width:90px;overflow:hidden;text-overflow:ellipsis">${escHtml(String(meal.client_id||''))}</td>
    <td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:normal">${escHtml(meal.order||'')}</td>
    <td>${escHtml(meal.dish||'—')}</td>
    <td class="${srvCls}">${srvTxt}</td>
  `;
  if (!row) {
    row = document.createElement('tr');
    row.id = rowKey;
    tbody.insertBefore(row, tbody.firstChild);
  }
  row.innerHTML = inner;
  row.classList.remove('highlight');
  void row.offsetWidth;
  row.classList.add('highlight');
  document.getElementById('meal-count').textContent = Object.keys(meals).length;
}

// ── Init ───────────────────────────────────────
connect();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


from flask import jsonify, request as flask_request


@app.route("/api/all_restaurants")
def api_all_restaurants():
    """Return all tracked restaurants (flattened + raw) indexed by id."""
    with state_lock:
        result = {}
        for rid, raw in state["restaurants_raw"].items():
            entry = dict(raw)
            entry["_flat"] = state["restaurants"].get(rid, {})
            entry["id"] = rid
            result[rid] = entry
    return jsonify(result)


@app.route("/api/bid_history")
def api_bid_history():
    """Return bid history, optionally filtered by turn_id."""
    turn_filter = flask_request.args.get("turn_id", type=int)
    with state_lock:
        bids = []
        for (turn_id, _bid_id), bid in state["bid_history"].items():
            if turn_filter is None or turn_id == turn_filter:
                bids.append(bid)
    return jsonify(bids)


@app.route("/api/market")
def api_market():
    """Return all currently tracked market entries."""
    with state_lock:
        entries = list(state["market"].values())
    return jsonify(entries)


@app.route("/api/meals")
def api_meals():
    """Return tracked meals, optionally filtered by turn_id and restaurant_id."""
    turn_filter = flask_request.args.get("turn_id", type=int)
    rid_filter = flask_request.args.get("restaurant_id", type=int)
    with state_lock:
        meals = []
        for (turn_id, r_id, _meal_id), meal in state["meals"].items():
            if turn_filter is not None and turn_id != turn_filter:
                continue
            if rid_filter is not None and r_id != rid_filter:
                continue
            meals.append(meal)
    return jsonify(meals)


@app.route("/api/game_state")
def api_game_state():
    """Return current phase, turn, and restaurant count."""
    with state_lock:
        return jsonify({
            "phase": state["phase"],
            "turn_id": state["turn_id"],
            "restaurant_count": len(state["restaurants"]),
        })


@app.route("/api/messages")
def api_messages():
    """Return recent agent messages (captured from new_message SSE events)."""
    limit = flask_request.args.get("limit", 100, type=int)
    with state_lock:
        msgs = list(state["messages"][-limit:])
    return jsonify(msgs)


@app.route("/api/restaurant/<rid>")
def api_restaurant_detail(rid):
    """Return full live detail for a restaurant (raw + change log + meals)."""
    rid_int = int(rid)
    # Only our own team returns data from /restaurant/{id} — others give 403
    raw = api_get(f"/restaurant/{rid}") if rid_int == TEAM_ID else None
    menu_data = api_get(f"/restaurant/{rid}/menu")
    with state_lock:
        change_log = list(state["restaurants_changes"].get(rid, []))
        turn_id = state.get("turn_id")
        # Serve meals from the in-memory cache (already polled for all teams)
        meals = [
            v for (t, r, _), v in state["meals"].items()
            if r == rid_int and t == turn_id
        ]
        # If not yet in cache (e.g. poller hasn't run), fall back to live fetch
        if not meals and turn_id:
            raw_meals = api_get("/meals", params={"turn_id": turn_id, "restaurant_id": rid_int})
            if isinstance(raw_meals, list):
                meals = raw_meals
            elif isinstance(raw_meals, dict):
                meals = raw_meals.get("meals", [])
        # Supplement with the cached raw restaurant data if we don't have /restaurant/{rid}
        if raw is None:
            raw = state["restaurants_raw"].get(rid_int) or state["restaurants_raw"].get(rid)

    return jsonify({
        "raw": raw,
        "menu": menu_data,
        "meals": meals,
        "change_log": change_log,
        "turn_id": turn_id,
    })


@app.route("/social")
def social():
    return render_template_string(SOCIAL_TEMPLATE)


@app.route("/stream")
def stream():
    """SSE endpoint for the browser."""
    q = queue.Queue(maxsize=500)
    with event_queues_lock:
        event_queues.append(q)

    def generate():
        try:
            while True:
                try:
                    evt = q.get(timeout=20)
                    yield f"data: {json.dumps(evt)}\n\n"
                except queue.Empty:
                    # Send a keepalive comment
                    yield ": keepalive\n\n"
        finally:
            with event_queues_lock:
                if q in event_queues:
                    event_queues.remove(q)

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
if __name__ == "__main__":
    # Start background threads
    if USE_SSE:
        t1 = threading.Thread(target=sse_relay_thread, daemon=True, name="sse-relay")
        t1.start()
        print("  ⚡  SSE relay ENABLED (tracker owns the game stream)")
    else:
        print("  ⚠️   SSE relay DISABLED (SPAM bot owns /events/17 — using REST polling only)")
    t2 = threading.Thread(target=polling_thread, daemon=True, name="poller")
    t2.start()

    print("=" * 55)
    print("  🍕  SPAM! Server Tracker")
    print("  Open browser at  http://localhost:5555")
    print("  Press Ctrl+C to stop")
    print("=" * 55)
    app.run(host="0.0.0.0", port=5555, threaded=True, use_reloader=False)
