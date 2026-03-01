"""
VectorSpaceDashboard — Real-time web visualization for vector spaces.

Launches a lightweight Flask-based dashboard that renders interactive
2D/3D scatter plots of agent positions, zone centroids, and trajectory
trails in real time.

Requires the ``dashboard`` optional dependency::

    pip install datapizza-ai-observability-vectorspace[dashboard]

Usage::

    from datapizza.tools.vectorspace import VectorSpaceDashboard

    dashboard = VectorSpaceDashboard(
        snapshot_store=store,
        tracker=tracker,
        projector=projector,
    )

    # As a standalone server
    dashboard.launch(port=5050)

    # As an agent tool
    agent = Agent(name="...", tools=[dashboard.launch_dashboard], ...)
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any

logger = logging.getLogger("datapizza.tools.vectorspace.dashboard")

try:
    from flask import Flask, jsonify, render_template_string
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False


# ── HTML template (self-contained, no external files needed) ──

_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vector Space — datapizza observability</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'SF Mono', 'Fira Code', monospace; background: #0a0a0f; color: #e0e0e0; }
.header { padding: 12px 20px; background: #111118; border-bottom: 1px solid #2a2a3a; display: flex; justify-content: space-between; align-items: center; }
.header h1 { font-size: 14px; color: #ff6b35; font-weight: 600; }
.header .meta { font-size: 11px; color: #666; }
.container { display: flex; height: calc(100vh - 45px); }
.canvas-wrap { flex: 1; position: relative; }
canvas { width: 100%; height: 100%; }
.sidebar { width: 280px; background: #111118; border-left: 1px solid #2a2a3a; overflow-y: auto; padding: 12px; }
.sidebar h2 { font-size: 12px; color: #888; margin: 12px 0 6px; text-transform: uppercase; letter-spacing: 1px; }
.entity-card { background: #1a1a24; border: 1px solid #2a2a3a; border-radius: 6px; padding: 10px; margin-bottom: 8px; cursor: pointer; transition: border-color 0.2s; }
.entity-card:hover { border-color: #ff6b35; }
.entity-card .name { font-size: 13px; font-weight: 600; color: #fff; }
.entity-card .class { font-size: 11px; padding: 2px 6px; border-radius: 3px; display: inline-block; margin-top: 4px; }
.class-stable { background: #0d3320; color: #4ade80; }
.class-drifting { background: #332200; color: #fbbf24; }
.class-oscillating { background: #33001a; color: #f472b6; }
.class-accelerating { background: #1a0033; color: #a78bfa; }
.class-converging { background: #003333; color: #22d3ee; }
.class-active, .class-new { background: #222; color: #999; }
.metrics { font-size: 11px; color: #888; margin-top: 6px; }
.metrics span { margin-right: 10px; }
.legend { padding: 8px; background: #1a1a24; border-radius: 6px; margin-bottom: 12px; }
.legend-item { display: flex; align-items: center; font-size: 11px; margin: 4px 0; }
.legend-dot { width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; }
.controls { margin-bottom: 12px; }
.controls button { background: #2a2a3a; border: 1px solid #3a3a4a; color: #ccc; padding: 4px 10px; border-radius: 4px; font-size: 11px; cursor: pointer; margin-right: 4px; }
.controls button:hover { background: #3a3a4a; }
.controls button.active { background: #ff6b35; color: #fff; border-color: #ff6b35; }
#status { position: absolute; bottom: 10px; left: 10px; font-size: 11px; color: #555; }
</style>
</head>
<body>
<div class="header">
    <h1>datapizza / observability / vectorspace</h1>
    <div class="meta">
        <span id="step-counter">Step: —</span> ·
        <span id="entity-count">Entities: —</span>
    </div>
</div>
<div class="container">
    <div class="canvas-wrap">
        <canvas id="canvas"></canvas>
        <div id="status">Connecting...</div>
    </div>
    <div class="sidebar">
        <div class="controls">
            <button id="btn-trails" class="active" onclick="toggleTrails()">Trails</button>
            <button id="btn-zones" class="active" onclick="toggleZones()">Zones</button>
            <button id="btn-labels" class="active" onclick="toggleLabels()">Labels</button>
        </div>
        <div class="legend" id="legend"></div>
        <h2>Entities</h2>
        <div id="entity-list"></div>
    </div>
</div>
<script>
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
let W, H, showTrails = true, showZones = true, showLabels = true;
let entities = {}, centroids = {}, trailHistory = {}, selectedEntity = null;
const COLORS = ['#ff6b35','#4ade80','#60a5fa','#f472b6','#fbbf24','#a78bfa','#22d3ee','#f87171','#34d399','#818cf8'];
let colorMap = {};

function resize() {
    const r = canvas.parentElement.getBoundingClientRect();
    canvas.width = W = r.width * devicePixelRatio;
    canvas.height = H = r.height * devicePixelRatio;
    canvas.style.width = r.width + 'px';
    canvas.style.height = r.height + 'px';
    ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    W = r.width; H = r.height;
}
window.addEventListener('resize', resize);
resize();

function getColor(id) {
    if (!colorMap[id]) colorMap[id] = COLORS[Object.keys(colorMap).length % COLORS.length];
    return colorMap[id];
}

function toScreen(coords) {
    if (!coords || coords.length < 2) return [W/2, H/2];
    // Auto-scale: find bounds
    let allX = [], allY = [];
    Object.values(entities).forEach(e => { if(e.coordinates) { allX.push(e.coordinates[0]); allY.push(e.coordinates[1]); }});
    Object.values(centroids).forEach(c => { allX.push(c[0]); allY.push(c[1]); });
    if (allX.length < 2) return [W/2, H/2];
    let minX = Math.min(...allX), maxX = Math.max(...allX), minY = Math.min(...allY), maxY = Math.max(...allY);
    let rangeX = maxX - minX || 1, rangeY = maxY - minY || 1;
    let pad = 60;
    let x = pad + ((coords[0] - minX) / rangeX) * (W - 2*pad);
    let y = pad + ((coords[1] - minY) / rangeY) * (H - 2*pad);
    return [x, y];
}

function draw() {
    ctx.clearRect(0, 0, W, H);
    // Grid
    ctx.strokeStyle = '#1a1a24'; ctx.lineWidth = 0.5;
    for (let i = 0; i < W; i += 40) { ctx.beginPath(); ctx.moveTo(i,0); ctx.lineTo(i,H); ctx.stroke(); }
    for (let i = 0; i < H; i += 40) { ctx.beginPath(); ctx.moveTo(0,i); ctx.lineTo(W,i); ctx.stroke(); }

    // Centroids
    if (showZones) {
        Object.entries(centroids).forEach(([name, coords]) => {
            let [x,y] = toScreen(coords);
            ctx.beginPath(); ctx.arc(x, y, 16, 0, Math.PI*2);
            ctx.fillStyle = 'rgba(255,107,53,0.15)'; ctx.fill();
            ctx.strokeStyle = '#ff6b35'; ctx.lineWidth = 1.5; ctx.stroke();
            if (showLabels) {
                ctx.fillStyle = '#ff6b35'; ctx.font = '10px monospace'; ctx.textAlign = 'center';
                ctx.fillText(name, x, y - 22);
            }
        });
    }

    // Trails
    if (showTrails) {
        Object.entries(trailHistory).forEach(([id, trail]) => {
            if (trail.length < 2) return;
            let col = getColor(id);
            for (let i = 1; i < trail.length; i++) {
                let [x0,y0] = toScreen(trail[i-1]);
                let [x1,y1] = toScreen(trail[i]);
                let alpha = 0.1 + 0.6 * (i / trail.length);
                ctx.beginPath(); ctx.moveTo(x0,y0); ctx.lineTo(x1,y1);
                ctx.strokeStyle = col.replace(')', `,${alpha})`).replace('rgb','rgba');
                ctx.lineWidth = 1.5; ctx.stroke();
            }
        });
    }

    // Entities
    Object.entries(entities).forEach(([id, e]) => {
        if (!e.coordinates) return;
        let [x,y] = toScreen(e.coordinates);
        let col = getColor(id);
        let r = selectedEntity === id ? 8 : 5;
        ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI*2);
        ctx.fillStyle = col; ctx.fill();
        if (selectedEntity === id) { ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.stroke(); }
        if (showLabels) {
            ctx.fillStyle = '#ccc'; ctx.font = '10px monospace'; ctx.textAlign = 'center';
            ctx.fillText(id, x, y - 10);
        }
    });

    requestAnimationFrame(draw);
}
draw();

function toggleTrails() { showTrails = !showTrails; document.getElementById('btn-trails').classList.toggle('active'); }
function toggleZones() { showZones = !showZones; document.getElementById('btn-zones').classList.toggle('active'); }
function toggleLabels() { showLabels = !showLabels; document.getElementById('btn-labels').classList.toggle('active'); }

function updateSidebar() {
    let list = document.getElementById('entity-list');
    list.innerHTML = '';
    Object.entries(entities).forEach(([id, e]) => {
        let cls = e.trajectory_class || 'active';
        let card = document.createElement('div');
        card.className = 'entity-card';
        card.onclick = () => { selectedEntity = selectedEntity === id ? null : id; updateSidebar(); };
        if (selectedEntity === id) card.style.borderColor = getColor(id);
        card.innerHTML = `
            <div class="name" style="color:${getColor(id)}">${id}</div>
            <span class="class class-${cls}">${cls}</span>
            <div class="metrics">
                ${e.momentum != null ? '<span>M:'+e.momentum.toFixed(3)+'</span>' : ''}
                ${e.drift != null ? '<span>D:'+e.drift.toFixed(3)+'</span>' : ''}
                ${e.stability != null ? '<span>S:'+e.stability.toFixed(3)+'</span>' : ''}
            </div>`;
        list.appendChild(card);
    });
}

function poll() {
    fetch('/api/vectorspace/state')
        .then(r => r.json())
        .then(data => {
            if (data.entities) {
                entities = data.entities;
                Object.entries(entities).forEach(([id, e]) => {
                    if (e.coordinates) {
                        if (!trailHistory[id]) trailHistory[id] = [];
                        trailHistory[id].push(e.coordinates);
                        if (trailHistory[id].length > 50) trailHistory[id].shift();
                    }
                });
            }
            if (data.centroids) centroids = data.centroids;
            document.getElementById('step-counter').textContent = 'Step: ' + (data.step || '—');
            document.getElementById('entity-count').textContent = 'Entities: ' + Object.keys(entities).length;
            document.getElementById('status').textContent = 'Live · ' + new Date().toLocaleTimeString();
            updateSidebar();
        })
        .catch(() => { document.getElementById('status').textContent = 'Disconnected'; });
}
setInterval(poll, 2000);
poll();
</script>
</body>
</html>"""


class VectorSpaceDashboard:
    """
    Web-based real-time vector space visualization.

    Serves an interactive dashboard that polls the SnapshotStore for
    the latest entity positions and renders them as a 2D scatter plot
    with trajectory trails, zone centroids, and entity cards.

    Parameters
    ----------
    snapshot_store : SnapshotStore | None
        Data source for entity positions and trajectories.
    tracker : TrajectoryTracker | None
        Live trajectory data source.
    projector : VectorSpaceModule | None
        For projecting raw features into 2D/3D coordinates.
    host : str
        Flask bind host. Default: ``"127.0.0.1"``.
    port : int
        Flask bind port. Default: ``5050``.
    """

    def __init__(
        self,
        snapshot_store=None,
        tracker=None,
        projector=None,
        host: str = "127.0.0.1",
        port: int = 5050,
    ):
        if not HAS_FLASK:
            raise ImportError(
                "Flask is required for VectorSpaceDashboard. "
                "Install with: pip install datapizza-ai-observability-vectorspace[dashboard]"
            )

        self.store = snapshot_store
        self.tracker = tracker
        self.projector = projector
        self.host = host
        self.port = port
        self._app: Flask | None = None
        self._thread: threading.Thread | None = None

    def _create_app(self) -> Flask:
        """Create the Flask app with routes."""
        app = Flask(__name__)
        store = self.store
        tracker = self.tracker
        projector = self.projector

        @app.route("/")
        def index():
            return render_template_string(_DASHBOARD_HTML)

        @app.route("/api/vectorspace/state")
        def api_state():
            """Return the current vector space state for the dashboard."""
            entities_out = {}
            centroids_out = {}
            step = None

            # From snapshot store
            if store:
                latest = store.get_latest(1)
                if latest:
                    snap = latest[0]
                    step = snap.step
                    centroids_out = snap.centroid_projections
                    for eid, es in snap.entities.items():
                        entities_out[eid] = {
                            "coordinates": es.coordinates,
                            "features": es.features,
                            "trajectory_class": es.trajectory_class,
                            "momentum": es.momentum,
                            "drift": es.drift,
                            "stability": es.stability,
                        }

            # Supplement with live tracker data if store is empty
            if not entities_out and tracker:
                import numpy as np

                all_features = {}
                for eid in tracker.get_all_entities():
                    history = tracker.get_history(eid)
                    if history:
                        all_features[eid] = history[-1].features

                # Project if we have a projector
                if all_features and projector:
                    proj_result = projector.run({"features": all_features})
                    projections = proj_result.get("projections", {})
                    centroids_out = proj_result.get("centroid_projections", {})
                    for eid, proj in projections.items():
                        traj = tracker.get_trajectory(eid)
                        entities_out[eid] = {
                            "coordinates": proj.get("coordinates") if isinstance(proj, dict) else None,
                            "features": all_features.get(eid, []),
                            "trajectory_class": traj.classification if traj else None,
                            "momentum": traj.momentum if traj else None,
                            "drift": traj.drift if traj else None,
                            "stability": traj.stability if traj else None,
                        }
                elif all_features:
                    for eid, fv in all_features.items():
                        traj = tracker.get_trajectory(eid)
                        entities_out[eid] = {
                            "coordinates": fv[:2] if len(fv) >= 2 else fv,
                            "features": fv,
                            "trajectory_class": traj.classification if traj else None,
                            "momentum": traj.momentum if traj else None,
                            "drift": traj.drift if traj else None,
                            "stability": traj.stability if traj else None,
                        }

            return jsonify({
                "entities": entities_out,
                "centroids": centroids_out,
                "step": step,
            })

        @app.route("/api/vectorspace/history/<entity_id>")
        def api_history(entity_id: str):
            """Return position history for one entity."""
            if store:
                history = store.get_entity_history(entity_id, last_n=50)
                return jsonify({"entity_id": entity_id, "history": history})
            return jsonify({"error": "No store configured"}), 404

        return app

    # ── Launch methods ──

    def launch(self, host: str | None = None, port: int | None = None, debug: bool = False):
        """
        Launch the dashboard server (blocking).

        Parameters
        ----------
        host : str | None
            Override bind host.
        port : int | None
            Override bind port.
        debug : bool
            Enable Flask debug mode.
        """
        self._app = self._create_app()
        h = host or self.host
        p = port or self.port
        logger.info(f"Vector space dashboard at http://{h}:{p}")
        self._app.run(host=h, port=p, debug=debug)

    def launch_background(self, host: str | None = None, port: int | None = None) -> str:
        """
        Launch the dashboard in a background thread.

        Returns the URL of the dashboard.
        """
        self._app = self._create_app()
        h = host or self.host
        p = port or self.port
        url = f"http://{h}:{p}"

        self._thread = threading.Thread(
            target=self._app.run,
            kwargs={"host": h, "port": p, "debug": False, "use_reloader": False},
            daemon=True,
        )
        self._thread.start()
        logger.info(f"Vector space dashboard started at {url}")
        return url

    # ── Agent tool method ──

    def launch_dashboard(self, port: int = 5050) -> str:
        """
        Launch the vector space visualization dashboard in the background.

        Starts a web server that shows an interactive 2D scatter plot of all
        entities in the vector space. The dashboard auto-refreshes every 2 seconds
        with the latest positions, trajectory trails, and zone centroids.

        Args:
            port: The port to run the dashboard on (default: 5050).

        Returns:
            The URL of the launched dashboard.
        """
        url = self.launch_background(port=port)
        return f"Dashboard launched at {url} — open in your browser to see the vector space."
