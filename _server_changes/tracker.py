"""
Hackapizza Server Tracker  (data sidecar)
==========================================
Polls the game server REST API every 5s and caches state in memory.
Exposes JSON API endpoints at localhost:5555/api/* for:
  - Intelligence pipeline (tracker_bridge.py)
  - SPAM! Dashboard (port 5556)

NO browser UI — all visualisation lives in dashboard/.
"""

import json
import os
import threading
import time
import copy
import queue
import requests
from flask import Flask, Response, jsonify
from flask import request as flask_request
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
    "_seen_message_ids": set(),  # dedup across polls
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
                                mid = parsed.get("messageId") or parsed.get("message_id") or id(parsed)
                                if mid not in state["_seen_message_ids"]:
                                    state["_seen_message_ids"].add(mid)
                                    msg_entry = {
                                        "ts": now_ts(),
                                        "sender_id": parsed.get("senderId") or parsed.get("sender_id"),
                                        "sender_name": parsed.get("senderName") or parsed.get("sender_name", "?"),
                                        "recipient_id": parsed.get("recipientId") or parsed.get("recipient_id"),
                                        "recipient_name": parsed.get("recipientName") or parsed.get("recipient_name", "?"),
                                        "text": parsed.get("text") or parsed.get("content") or str(parsed),
                                        "turn_id": state.get("turn_id"),
                                        "direction": "received",
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

def api_get(path: str, params: dict = None, silent_404: bool = False, silent_400: bool = False):
    try:
        r = requests.get(f"{BASE_URL}{path}", headers=HEADERS, params=params, timeout=10)
        if r.status_code == 404 and silent_404:
            return None
        if r.status_code == 400:
            if silent_400:
                return None
            # Return a sentinel so callers can detect 400 vs network error
            body = r.text
            push_event("system", {"msg": f"GET {path} returned 400: {body[:200]}"})
            return {"__error": 400, "body": body}
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
    # The live API uses:
    #   createdByRestaurantId  → seller
    #   ingredient.name        → ingredient name
    #   totalPrice             → total price (price × qty)
    #   No buyer field — closed entries just have status="closed"
    ing_obj = e.get("ingredient") or {}
    ing_name = (
        ing_obj.get("name")
        or e.get("ingredient_name")
        or e.get("ingredientName")
    )
    qty = e.get("quantity") or 1
    total_price = e.get("totalPrice") or e.get("total_price") or e.get("price")
    unit_price = round(total_price / qty, 2) if total_price and qty else total_price
    seller_id = (
        e.get("createdByRestaurantId")
        or e.get("seller_id")
        or e.get("sellerId")
    )
    buyer_id = (
        e.get("executedByRestaurantId")
        or e.get("buyer_id")
        or e.get("buyerId")
    )
    return {
        "side": e.get("side"),
        "ingredient_name": ing_name,
        "quantity": qty,
        "unit_price": unit_price,
        "total_price": total_price,
        "status": e.get("status"),
        "seller_id": seller_id,
        "buyer_id": buyer_id,
        "inserted_at": e.get("insertedAt"),
    }


# ──────────────────────────────────────────────
# Polling thread
# ──────────────────────────────────────────────

GAME_EVENTS_PATH = os.path.join(os.path.dirname(__file__), "..", "game_events.jsonl")

# Number of recent turns to poll for bid_history and meals
BID_HISTORY_LOOKBACK = 5
MEALS_LOOKBACK = 3


def _probe_turn_id() -> int | None:
    """Probe the server to discover the actual current turn_id.

    Like pipeline.py's _probe_correct_turn_id(): exponential search upward
    from our current guess, then binary-search for the highest valid turn_id.
    The /meals endpoint only accepts the current turn ± ~2.
    """
    with state_lock:
        current_guess = state.get("turn_id") or 1

    lo = max(1, current_guess)
    hi = lo
    found_any_valid = False

    # Phase 1: exponential search upward
    while hi <= 300:  # safety cap
        data = api_get("/meals", params={"turn_id": hi, "restaurant_id": TEAM_ID}, silent_400=True)
        if data is not None and not isinstance(data, dict) or (isinstance(data, (list, dict)) and "__error" not in (data if isinstance(data, dict) else {})):
            lo = hi
            found_any_valid = True
            hi *= 2
        else:
            if not found_any_valid:
                hi = hi + 1 if hi < 10 else hi * 2
            else:
                break

    if not found_any_valid:
        push_event("system", {"msg": f"turn_id probe: no valid turn_id found (searched up to {hi})"})
        return None

    # Phase 2: binary search for highest valid turn_id
    while lo < hi:
        mid = (lo + hi + 1) // 2
        data = api_get("/meals", params={"turn_id": mid, "restaurant_id": TEAM_ID}, silent_400=True)
        if data is not None and not isinstance(data, dict) or (isinstance(data, (list, dict)) and "__error" not in (data if isinstance(data, dict) else {})):
            lo = mid
        else:
            hi = mid - 1

    push_event("system", {"msg": f"turn_id probe result: {lo}"})
    return lo


def _validate_and_update_turn_id():
    """Validate current turn_id against the server and update if stale.

    Called once per poll cycle. If current turn_id is None or returns 400,
    probes for the correct one.
    """
    with state_lock:
        current = state.get("turn_id")

    if current is None or current <= 0:
        # No turn_id at all — probe from scratch
        probed = _probe_turn_id()
        if probed:
            with state_lock:
                state["turn_id"] = probed
            push_event("system", {"msg": f"turn_id probed from server: {probed}"})
        return

    # Quick validation: try current turn_id
    data = api_get("/meals", params={"turn_id": current, "restaurant_id": TEAM_ID}, silent_400=True)
    if data is not None and (isinstance(data, list) or (isinstance(data, dict) and "__error" not in data)):
        return  # still valid

    # Current turn_id is stale — probe for the correct one
    push_event("system", {"msg": f"turn_id {current} is stale — probing server..."})
    probed = _probe_turn_id()
    if probed and probed != current:
        with state_lock:
            state["turn_id"] = probed
        push_event("system", {"msg": f"turn_id corrected: {current} → {probed}"})


def _poll_game_state():
    """Infer turn_id, phase, and messages from game_events.jsonl written by the bot's SSE connection."""
    best_turn_id = None
    best_phase = None
    new_messages = []
    try:
        with state_lock:
            seen_ids = set(state["_seen_message_ids"])
            current_turn = state.get("turn_id")

        with open(GAME_EVENTS_PATH, "r") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    evt = json.loads(raw)
                except Exception:
                    continue
                etype = evt.get("type")
                data = evt.get("data") or {}
                ts = evt.get("ts", "")
                if etype == "game_started":
                    tid = data.get("turn_id")
                    if tid is not None:
                        best_turn_id = tid
                        best_phase = "speaking"
                        current_turn = tid
                elif etype == "game_phase_changed":
                    ph = data.get("phase")
                    if ph:
                        best_phase = ph
                elif etype == "game_reset":
                    best_turn_id = None
                    best_phase = "reset"
                    current_turn = None
                elif etype == "new_message":
                    # API sends camelCase: messageId, senderId, senderName, text, datetime
                    mid = (
                        data.get("messageId")
                        or data.get("message_id")
                        or data.get("id")
                        or f"{ts}_{data.get('senderId', data.get('sender_id', '?'))}"
                    )
                    if mid not in seen_ids:
                        seen_ids.add(mid)
                        new_messages.append({
                            "ts": ts or now_ts(),
                            "sender_id": data.get("senderId") or data.get("sender_id"),
                            "sender_name": data.get("senderName") or data.get("sender_name", "?"),
                            "recipient_id": data.get("recipientId") or data.get("recipient_id"),
                            "recipient_name": data.get("recipientName") or data.get("recipient_name", "?"),
                            "text": data.get("text") or data.get("content") or str(data),
                            "turn_id": current_turn,
                            "direction": "received",
                            "message_id": mid,
                        })
    except FileNotFoundError:
        pass
    except Exception as e:
        push_event("system", {"msg": f"game_events.jsonl read error: {e}"})

    with state_lock:
        if best_turn_id is not None and state["turn_id"] != best_turn_id:
            state["turn_id"] = best_turn_id
            push_event("system", {"msg": f"turn_id from game_events.jsonl: {best_turn_id}"})
        if best_phase is not None and state["phase"] != best_phase:
            state["phase"] = best_phase
            push_event("system", {"msg": f"phase from game_events.jsonl: {best_phase}"})
        for msg in new_messages:
            state["_seen_message_ids"].add(msg["message_id"])
            state["messages"].append(msg)
            if len(state["messages"]) > 200:
                state["messages"].pop(0)
            push_event("new_message", msg)
    if new_messages:
        push_event("system", {"msg": f"Loaded {len(new_messages)} new message(s) from game_events.jsonl"})


def polling_thread():
    time.sleep(1)  # small delay so SSE thread connects first
    while True:
        if not USE_SSE:
            try:
                _poll_game_state()
            except Exception as e:
                push_event("system", {"msg": f"Poll game state error: {e}"})
        # Validate / probe turn_id against the server each cycle
        try:
            _validate_and_update_turn_id()
        except Exception as e:
            push_event("system", {"msg": f"turn_id validation error: {e}"})
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

    # Poll current turn and a few recent ones to catch data we may have missed
    turns_to_poll = list(range(max(1, turn_id - MEALS_LOOKBACK + 1), turn_id + 1))

    for tid in turns_to_poll:
        for rid in restaurant_ids:
            data = api_get("/meals", params={"turn_id": tid, "restaurant_id": rid}, silent_400=True)
            if not data or (isinstance(data, dict) and "__error" in data):
                continue
            meals = data if isinstance(data, list) else data.get("meals", [])
            with state_lock:
                rname = state["restaurants_names"].get(rid, f"team {rid}")
                for m in meals:
                    mid = m.get("id") or m.get("customerId") or m.get("client_id")
                    key = (tid, rid, mid)
                    # Server uses 'request' for order text, customer.name for client name
                    customer = m.get("customer")
                    client_name = customer.get("name", "?") if isinstance(customer, dict) else m.get("clientName", "?")
                    flat_new = {
                        "turn_id": tid,
                        "restaurant_id": rid,
                        "restaurant_name": rname,
                        "client_id": m.get("customerId") or m.get("client_id"),
                        "client_name": client_name,
                        "order": m.get("request") or m.get("orderText") or m.get("order", ""),
                        "executed": m.get("executed"),
                        "status": m.get("status"),
                        "dish": m.get("servedDishId") or m.get("dish_name") or m.get("dish"),
                    }
                    flat_old = state["meals"].get(key)
                    if flat_old is None:
                        state["meals"][key] = flat_new
                        push_event("meal_new", {"turn": tid, "restaurant_id": rid, "restaurant_name": rname, "meal": flat_new})
                    else:
                        changes = diff_dict(flat_old, flat_new, f"meal#{mid}")
                        if changes:
                            state["meals"][key] = flat_new
                            push_event("meal_changed", {"turn": tid, "restaurant_id": rid, "restaurant_name": rname, "changes": changes, "meal": flat_new})


def _poll_bid_history():
    with state_lock:
        turn_id = state.get("turn_id")
    if not turn_id:
        return

    # Poll current turn and several recent turns for historical bid data
    turns_to_poll = list(range(max(1, turn_id - BID_HISTORY_LOOKBACK + 1), turn_id + 1))

    for tid in turns_to_poll:
        data = api_get("/bid_history", params={"turn_id": tid}, silent_400=True)
        if not data or (isinstance(data, dict) and "__error" in data):
            continue
        bids = data if isinstance(data, list) else data.get("bids", [])
        with state_lock:
            for b in bids:
                bid_id = b.get("id") or id(b)
                key = (tid, bid_id)
                if key not in state["bid_history"]:
                    # Enrich with restaurant name from nested object
                    restaurant_obj = b.get("restaurant")
                    if isinstance(restaurant_obj, dict) and "name" in restaurant_obj:
                        b["restaurant_name"] = restaurant_obj["name"]
                    # Enrich ingredient name from nested object
                    ingredient_obj = b.get("ingredient")
                    if isinstance(ingredient_obj, dict) and "name" in ingredient_obj:
                        b["ingredient_name"] = ingredient_obj["name"]
                    state["bid_history"][key] = b
                    push_event("bid_history", {"turn": tid, "bid": b})


# ──────────────────────────────────────────────
# Flask routes
# ──────────────────────────────────────────────

# NOTE: All HTML UI templates have been removed.
# The SPAM! Dashboard (port 5556) now handles all visualisation.
# This file is a pure data-gathering sidecar.

# (old WAITING_MARKET_TEMPLATE, SOCIAL_TEMPLATE, HTML_TEMPLATE removed)
# Total: ~1,730 lines of HTML/CSS/JS templates deleted.


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
    """Return recent agent messages (captured from new_message SSE events + sent)."""
    limit = flask_request.args.get("limit", 100, type=int)
    with state_lock:
        msgs = list(state["messages"][-limit:])
    return jsonify(msgs)


@app.route("/api/messages/sent", methods=["POST"])
def api_messages_sent():
    """Receive a sent message record from the main app."""
    data = flask_request.get_json(force=True)
    if not data:
        return jsonify({"error": "no data"}), 400
    msg_entry = {
        "ts": data.get("ts", now_ts()),
        "sender_id": TEAM_ID,
        "sender_name": "SPAM!",
        "recipient_id": data.get("recipient_id"),
        "recipient_name": data.get("recipient_name", "?"),
        "text": data.get("text", ""),
        "turn_id": data.get("turn_id") or state.get("turn_id"),
        "direction": "sent",
        "arm": data.get("arm", ""),
        "desired_effect": data.get("desired_effect", ""),
    }
    with state_lock:
        state["messages"].append(msg_entry)
        if len(state["messages"]) > 200:
            state["messages"].pop(0)
    push_event("sent_message", msg_entry)
    return jsonify({"ok": True})


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


@app.route("/api/waiting_market")
def api_waiting_market():
    """Return market entries enriched with restaurant names, plus all menus.

    Falls back to live API calls if the poller hasn't populated state yet,
    so the page is useful even when the tracker just started.
    """
    with state_lock:
        names = dict(state["restaurants_names"])
        # Use raw state entries so we have all original fields for fallback parsing
        raw_state_market = dict(state["market"])          # id -> flattened
        raw_restaurants = {rid: dict(r) for rid, r in state["restaurants_raw"].items()}
        turn_id = state.get("turn_id")

    # ── If poller hasn't fetched yet, hit the API directly ──
    if not raw_restaurants:
        fresh = api_get("/restaurants")
        if fresh:
            rlist = fresh if isinstance(fresh, list) else fresh.get("restaurants", [])
            for r in rlist:
                rid = r.get("id")
                if rid is not None:
                    raw_restaurants[rid] = r
                    names[rid] = r.get("name", f"Team {rid}")

    if not raw_state_market:
        fresh_market = api_get("/market/entries")
        if fresh_market:
            entries_raw = fresh_market if isinstance(fresh_market, list) else fresh_market.get("entries", [])
            for e in entries_raw:
                eid = e.get("id")
                if eid is not None:
                    raw_state_market[eid] = flatten_market_entry(e)

    # ── Enrich market entries with restaurant names ──
    enriched = []
    for eid, entry in raw_state_market.items():
        e = dict(entry)
        e["id"] = eid
        sid = e.get("seller_id")
        bid = e.get("buyer_id")
        e["seller_name"] = names.get(sid, f"Team {sid}") if sid is not None else "—"
        e["buyer_name"] = names.get(bid, f"Team {bid}") if bid is not None else "—"
        enriched.append(e)

    # Sort: open first, then by id descending (newest first)
    enriched.sort(key=lambda x: (x.get("status") != "open", -(x.get("id") or 0)))

    # ── Build per-restaurant menu snapshot ──
    menus = {}
    for rid, r in raw_restaurants.items():
        raw_menu = r.get("menu") or {}
        if isinstance(raw_menu, dict):
            items = raw_menu.get("items") or []
        elif isinstance(raw_menu, list):
            items = raw_menu
        else:
            items = []
        # Normalize item shapes: server sometimes returns just strings
        norm_items = []
        for it in items:
            if isinstance(it, str):
                norm_items.append({"name": it, "price": None})
            elif isinstance(it, dict):
                norm_items.append(it)
        menus[rid] = {
            "name": names.get(rid, f"Team {rid}"),
            "is_open": r.get("isOpen", False),
            "balance": r.get("balance"),
            "reputation": r.get("reputation"),
            "items": norm_items,
        }

    return jsonify({
        "market_entries": enriched,
        "menus": menus,
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
    if USE_SSE:
        t1 = threading.Thread(target=sse_relay_thread, daemon=True, name="sse-relay")
        t1.start()
        print("  ⚡  SSE relay ENABLED (tracker owns the game stream)")
    else:
        print("  ⚠️   SSE relay DISABLED (SPAM bot owns /events/17 — using REST polling only)")
    t2 = threading.Thread(target=polling_thread, daemon=True, name="poller")
    t2.start()

    print("=" * 55)
    print("  🍕  SPAM! Server Tracker  (data sidecar)")
    print("  API at  http://localhost:5555/api/*")
    print("  Dashboard at  http://localhost:5556")
    print("  Press Ctrl+C to stop")
    print("=" * 55)
    app.run(host="0.0.0.0", port=5555, threaded=True, use_reloader=False)
