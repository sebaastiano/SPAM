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

def api_get(path: str, params: dict = None):
    try:
        r = requests.get(f"{BASE_URL}{path}", headers=HEADERS, params=params, timeout=10)
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

def polling_thread():
    time.sleep(1)  # small delay so SSE thread connects first
    while True:
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
    if not turn_id:
        return
    data = api_get("/meals", params={"turn_id": turn_id, "restaurant_id": TEAM_ID})
    if not data:
        return
    meals = data if isinstance(data, list) else data.get("meals", [])
    with state_lock:
        for m in meals:
            mid = m.get("id") or m.get("client_id")
            key = (turn_id, mid)
            flat_new = {
                "client_id": m.get("client_id"),
                "order": m.get("orderText") or m.get("order"),
                "executed": m.get("executed"),
                "dish": m.get("dish_name") or m.get("dish"),
            }
            flat_old = state["meals"].get(key)
            if flat_old is None:
                state["meals"][key] = flat_new
                push_event("meal_new", {"turn": turn_id, "meal": flat_new})
            else:
                changes = diff_dict(flat_old, flat_new, f"meal#{mid}")
                if changes:
                    state["meals"][key] = flat_new
                    push_event("meal_changed", {"turn": turn_id, "changes": changes, "meal": flat_new})


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
      <div class="panel-header">🍽️ OUR MEALS (this turn) <span class="badge" id="meal-count">0</span></div>
      <div class="table-scroll">
        <table id="meal-table">
          <thead>
            <tr><th>CLIENT</th><th>ORDER</th><th>DISH</th><th>SERVED</th></tr>
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
  else if (type === 'meal_new' || type === 'meal_changed') updateMeal(data.meal);
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
      return `New client — ${data.meal.order||'?'} (id:${data.meal.client_id})`;
    case 'meal_changed':
      return `Meal updated: ${data.changes.map(c=>`${c.field}: ${c.old}→${c.new}`).join(', ')}`;
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
function updateMeal(meal) {
  meals[meal.client_id] = meal;
  const tbody = document.getElementById('meal-tbody');
  let row = document.getElementById(`meal-${meal.client_id}`);
  const srvCls = meal.executed ? 'up' : 'muted';
  const srvTxt = meal.executed ? '✅ YES' : '⏳ NO';
  const inner = `
    <td style="max-width:100px;overflow:hidden;text-overflow:ellipsis">${escHtml(String(meal.client_id||''))}</td>
    <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:normal">${escHtml(meal.order||'')}</td>
    <td>${escHtml(meal.dish||'—')}</td>
    <td class="${srvCls}">${srvTxt}</td>
  `;
  if (!row) {
    row = document.createElement('tr');
    row.id = `meal-${meal.client_id}`;
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

@app.route("/api/restaurant/<rid>")
def api_restaurant_detail(rid):
    """Return full live detail for a restaurant (raw + change log + meals)."""
    # Fetch fresh data directly from the game server
    raw = api_get(f"/restaurant/{rid}")
    menu_data = api_get(f"/restaurant/{rid}/menu")
    with state_lock:
        change_log = list(state["restaurants_changes"].get(rid, []))
        turn_id = state.get("turn_id")

    # Meals for this restaurant this turn (only works for our own team or public endpoint)
    meals = []
    if turn_id:
        meal_data = api_get("/meals", params={"turn_id": turn_id, "restaurant_id": int(rid)})
        if isinstance(meal_data, list):
            meals = meal_data
        elif isinstance(meal_data, dict):
            meals = meal_data.get("meals", [])

    return jsonify({
        "raw": raw,
        "menu": menu_data,
        "meals": meals,
        "change_log": change_log,
        "turn_id": turn_id,
    })


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
    t1 = threading.Thread(target=sse_relay_thread, daemon=True, name="sse-relay")
    t2 = threading.Thread(target=polling_thread, daemon=True, name="poller")
    t1.start()
    t2.start()

    print("=" * 55)
    print("  🍕  SPAM! Server Tracker")
    print("  Open browser at  http://localhost:5555")
    print("  Press Ctrl+C to stop")
    print("=" * 55)
    app.run(host="0.0.0.0", port=5555, threaded=True, use_reloader=False)
