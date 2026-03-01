"""
SPAM! Strategic Dashboard
==========================
Flask app on port 5556 that reads ALL data from the existing tracker
(localhost:5555). Never calls the game server directly.

Run:  python -m dashboard.app
"""

import json
import logging
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests
from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request as flask_request,
)

from dashboard.analytics import (
    TEAM_ID,
    analyse_bids,
    analyse_competitors,
    analyse_market,
    analyse_our_performance,
)

# ── Configuration ──────────────────────────────────────────

TRACKER_URL = os.getenv("TRACKER_URL", "http://localhost:5555")
DASH_PORT = int(os.getenv("DASH_PORT", "5556"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [DASH] %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("spam.dashboard")

# ── Flask app ──────────────────────────────────────────────

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)


# ── Tracker Data Fetcher ──────────────────────────────────

def tracker_get(endpoint: str, params: dict | None = None, timeout: float = 4.0):
    """Fetch JSON from the tracker sidecar. Returns parsed data or None."""
    url = f"{TRACKER_URL}{endpoint}"
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("tracker_get %s failed: %s", endpoint, e)
        return None


def get_restaurant_names() -> dict[int, str]:
    """Get {restaurant_id: name} mapping from tracker."""
    data = tracker_get("/api/all_restaurants") or {}
    names = {}
    for rid_str, rdata in data.items():
        rid = int(rid_str)
        name = rdata.get("name") or rdata.get("_flat", {}).get("name") or f"Team {rid}"
        names[rid] = name
    return names


# ── HTML Page Routes ──────────────────────────────────────

@app.route("/")
def page_overview():
    return render_template("overview.html")


@app.route("/bids")
def page_bids():
    return render_template("bids.html")


@app.route("/market")
def page_market():
    return render_template("market.html")


@app.route("/competitors")
def page_competitors():
    return render_template("competitors.html")


@app.route("/messages")
def page_messages():
    return render_template("messages.html")


# ── API Routes (proxy + analytics) ───────────────────────

@app.route("/api/overview")
def api_overview():
    """Aggregated overview: game state + our performance + quick stats."""
    game_state = tracker_get("/api/game_state") or {}
    restaurants = tracker_get("/api/all_restaurants") or {}
    names = {int(k): v.get("name", f"Team {k}") for k, v in restaurants.items()}

    bid_history = tracker_get("/api/bid_history") or []
    market = tracker_get("/api/market") or []
    meals = tracker_get("/api/meals") or []

    bid_analysis = analyse_bids(bid_history, names)
    market_analysis = analyse_market(market, names)

    our_data = restaurants.get(str(TEAM_ID), {})
    our_perf = analyse_our_performance(our_data, bid_analysis, market_analysis, meals)

    # Leaderboard by balance
    leaderboard = sorted(
        [
            {
                "id": int(rid),
                "name": names.get(int(rid), f"Team {rid}"),
                "balance": r.get("_flat", r).get("balance", 0) or r.get("balance", 0),
                "reputation": r.get("_flat", r).get("reputation", 0) or r.get("reputation", 0),
                "is_us": int(rid) == TEAM_ID,
            }
            for rid, r in restaurants.items()
        ],
        key=lambda x: x["balance"],
        reverse=True,
    )

    return jsonify({
        "game_state": game_state,
        "our_performance": our_perf,
        "leaderboard": leaderboard,
        "bid_summary": bid_analysis.get("summary", {}),
        "market_summary": market_analysis.get("summary", {}),
    })


@app.route("/api/bids")
def api_bids():
    """Full bid intelligence with analytics."""
    bid_history = tracker_get("/api/bid_history") or []
    restaurants = tracker_get("/api/all_restaurants") or {}
    names = {int(k): v.get("name", f"Team {k}") for k, v in restaurants.items()}
    analysis = analyse_bids(bid_history, names)
    return jsonify(analysis)


@app.route("/api/market_intel")
def api_market_intel():
    """Market analysis with arbitrage detection."""
    market = tracker_get("/api/market") or []
    restaurants = tracker_get("/api/all_restaurants") or {}
    names = {int(k): v.get("name", f"Team {k}") for k, v in restaurants.items()}
    analysis = analyse_market(market, names)
    return jsonify(analysis)


@app.route("/api/competitors")
def api_competitors():
    """Competitor profiles with threat levels."""
    restaurants = tracker_get("/api/all_restaurants") or {}
    names = {int(k): v.get("name", f"Team {k}") for k, v in restaurants.items()}
    bid_history = tracker_get("/api/bid_history") or []
    market = tracker_get("/api/market") or []

    bid_analysis = analyse_bids(bid_history, names)
    market_analysis = analyse_market(market, names)
    profiles = analyse_competitors(restaurants, bid_analysis, market_analysis)
    return jsonify(profiles)


@app.route("/api/messages_intel")
def api_messages_intel():
    """Proxy messages from tracker."""
    msgs = tracker_get("/api/messages") or []
    return jsonify(msgs)


@app.route("/api/raw/<path:endpoint>")
def api_raw_proxy(endpoint):
    """
    Raw proxy to tracker — use for debugging.
    Example: /api/raw/api/game_state → tracker /api/game_state
    """
    data = tracker_get(f"/{endpoint}", params=dict(flask_request.args))
    if data is None:
        return jsonify({"error": "tracker unreachable"}), 502
    return jsonify(data)


# ── SSE Relay ─────────────────────────────────────────────

@app.route("/stream")
def stream():
    """Relay SSE from tracker to dashboard clients."""

    def event_stream():
        try:
            url = f"{TRACKER_URL}/stream"
            with requests.get(url, stream=True, timeout=60) as resp:
                for line in resp.iter_lines(decode_unicode=True):
                    if line:
                        yield f"{line}\n"
                    else:
                        yield "\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'msg': str(e)})}\n\n"

    return Response(event_stream(), mimetype="text/event-stream")


# ── Entrypoint ────────────────────────────────────────────

def main():
    log.info("SPAM Dashboard starting on http://localhost:%d", DASH_PORT)
    log.info("Reading data from tracker at %s", TRACKER_URL)
    app.run(host="0.0.0.0", port=DASH_PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()
