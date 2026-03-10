"""
SnapshotStore — Persistent time-series store for vector snapshots.

A ``datapizza`` PipelineComponent that persists feature vectors, projections,
and trajectory metrics across pipeline runs. Enables historical analysis,
replay, and dashboard queries.

Supports two backends:
    - **json** (default) — Simple JSON-lines file. Zero dependencies.
    - **sqlite** — Structured storage with indexed queries. Uses stdlib ``sqlite3``.

Integration::

    from datapizza.pipeline.dag_pipeline import DagPipeline
    from datapizza.modules.observability import (
        VectorSpaceModule, TrajectoryTracker, SnapshotStore,
    )

    pipeline = DagPipeline()
    pipeline.add_module("features", my_feature_extractor)
    pipeline.add_module("vectorspace", VectorSpaceModule(n_components=2))
    pipeline.add_module("trajectory", TrajectoryTracker(window=5))
    pipeline.add_module("store", SnapshotStore(path="./run_data", backend="json"))

    pipeline.connect("features", "vectorspace", target_key="features")
    pipeline.connect("features", "trajectory", target_key="features")
    pipeline.connect("vectorspace", "store", target_key="projections")
    pipeline.connect("trajectory", "store", target_key="trajectories")
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger("datapizza.modules.observability.snapshot_store")


# ── Data types ──

@dataclass
class Snapshot:
    """A single point-in-time snapshot of the vector space state."""

    step: int
    timestamp: float
    entities: dict[str, EntitySnapshot]
    centroid_projections: dict[str, list[float]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "timestamp": self.timestamp,
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
            "centroid_projections": self.centroid_projections,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Snapshot:
        return cls(
            step=d["step"],
            timestamp=d["timestamp"],
            entities={k: EntitySnapshot.from_dict(v) for k, v in d.get("entities", {}).items()},
            centroid_projections=d.get("centroid_projections", {}),
            metadata=d.get("metadata", {}),
        )


@dataclass
class EntitySnapshot:
    """Per-entity data within a snapshot."""

    entity_id: str
    features: list[float]
    coordinates: list[float] | None = None       # projected 2D/3D
    trajectory_class: str | None = None           # stable/drifting/etc
    momentum: float | None = None
    drift: float | None = None
    stability: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "features": self.features,
            "coordinates": self.coordinates,
            "trajectory_class": self.trajectory_class,
            "momentum": self.momentum,
            "drift": self.drift,
            "stability": self.stability,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> EntitySnapshot:
        return cls(
            entity_id=d["entity_id"],
            features=d["features"],
            coordinates=d.get("coordinates"),
            trajectory_class=d.get("trajectory_class"),
            momentum=d.get("momentum"),
            drift=d.get("drift"),
            stability=d.get("stability"),
            metadata=d.get("metadata", {}),
        )


# ── Backends ──

class _JsonBackend:
    """JSON-lines file backend: one JSON object per line per snapshot."""

    def __init__(self, path: Path):
        self.path = path / "snapshots.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # In-memory index for fast queries
        self._index: list[tuple[int, float, int]] = []  # (step, timestamp, byte_offset)
        self._build_index()

    def _build_index(self):
        """Scan existing file to build byte-offset index."""
        if not self.path.exists():
            return
        with open(self.path, "r") as f:
            while True:
                offset = f.tell()
                line = f.readline()
                if not line:
                    break
                try:
                    header = json.loads(line)
                    self._index.append((header["step"], header["timestamp"], offset))
                except (json.JSONDecodeError, KeyError):
                    continue

    def save(self, snapshot: Snapshot):
        """Append a snapshot as a single JSON line."""
        with open(self.path, "a") as f:
            offset = f.tell()
            json.dump(snapshot.to_dict(), f, separators=(",", ":"))
            f.write("\n")
        self._index.append((snapshot.step, snapshot.timestamp, offset))

    def load_step(self, step: int) -> Snapshot | None:
        """Load a snapshot by step number."""
        for s, _, offset in self._index:
            if s == step:
                return self._read_at(offset)
        return None

    def load_range(self, start_step: int, end_step: int) -> list[Snapshot]:
        """Load snapshots within a step range (inclusive)."""
        results = []
        for s, _, offset in self._index:
            if start_step <= s <= end_step:
                snap = self._read_at(offset)
                if snap:
                    results.append(snap)
        return results

    def load_latest(self, n: int = 1) -> list[Snapshot]:
        """Load the N most recent snapshots."""
        recent = self._index[-n:]
        results = []
        for _, _, offset in recent:
            snap = self._read_at(offset)
            if snap:
                results.append(snap)
        return results

    def load_all(self) -> list[Snapshot]:
        """Load all snapshots."""
        results = []
        for _, _, offset in self._index:
            snap = self._read_at(offset)
            if snap:
                results.append(snap)
        return results

    def entity_history(self, entity_id: str, last_n: int | None = None) -> list[dict]:
        """Load time series for a specific entity across all snapshots."""
        entries = self._index if last_n is None else self._index[-last_n:]
        history = []
        for _, _, offset in entries:
            snap = self._read_at(offset)
            if snap and entity_id in snap.entities:
                e = snap.entities[entity_id]
                history.append({
                    "step": snap.step,
                    "timestamp": snap.timestamp,
                    **e.to_dict(),
                })
        return history

    def _read_at(self, offset: int) -> Snapshot | None:
        """Read a snapshot from a byte offset."""
        try:
            with open(self.path, "r") as f:
                f.seek(offset)
                line = f.readline()
                return Snapshot.from_dict(json.loads(line))
        except (json.JSONDecodeError, IOError):
            return None

    @property
    def step_count(self) -> int:
        return len(self._index)


class _SqliteBackend:
    """SQLite backend: structured storage with indexed queries."""

    def __init__(self, path: Path):
        self.db_path = path / "snapshots.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS snapshots (
                step INTEGER PRIMARY KEY,
                timestamp REAL NOT NULL,
                centroid_projections TEXT DEFAULT '{}',
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS entity_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                step INTEGER NOT NULL,
                entity_id TEXT NOT NULL,
                features TEXT NOT NULL,
                coordinates TEXT,
                trajectory_class TEXT,
                momentum REAL,
                drift REAL,
                stability REAL,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (step) REFERENCES snapshots(step)
            );

            CREATE INDEX IF NOT EXISTS idx_entity_step
            ON entity_snapshots(entity_id, step);

            CREATE INDEX IF NOT EXISTS idx_step
            ON entity_snapshots(step);
        """)

    def save(self, snapshot: Snapshot):
        cur = self._conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO snapshots (step, timestamp, centroid_projections, metadata) "
            "VALUES (?, ?, ?, ?)",
            (
                snapshot.step,
                snapshot.timestamp,
                json.dumps(snapshot.centroid_projections),
                json.dumps(snapshot.metadata),
            ),
        )
        # Delete old entity rows for this step (if replacing)
        cur.execute("DELETE FROM entity_snapshots WHERE step = ?", (snapshot.step,))
        for eid, es in snapshot.entities.items():
            cur.execute(
                "INSERT INTO entity_snapshots "
                "(step, entity_id, features, coordinates, trajectory_class, "
                "momentum, drift, stability, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    snapshot.step,
                    eid,
                    json.dumps(es.features),
                    json.dumps(es.coordinates) if es.coordinates else None,
                    es.trajectory_class,
                    es.momentum,
                    es.drift,
                    es.stability,
                    json.dumps(es.metadata),
                ),
            )
        self._conn.commit()

    def load_step(self, step: int) -> Snapshot | None:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM snapshots WHERE step = ?", (step,))
        row = cur.fetchone()
        if not row:
            return None
        return self._build_snapshot(row)

    def load_range(self, start_step: int, end_step: int) -> list[Snapshot]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT * FROM snapshots WHERE step BETWEEN ? AND ? ORDER BY step",
            (start_step, end_step),
        )
        return [self._build_snapshot(r) for r in cur.fetchall()]

    def load_latest(self, n: int = 1) -> list[Snapshot]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM snapshots ORDER BY step DESC LIMIT ?", (n,))
        rows = cur.fetchall()
        rows.reverse()
        return [self._build_snapshot(r) for r in rows]

    def load_all(self) -> list[Snapshot]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM snapshots ORDER BY step")
        return [self._build_snapshot(r) for r in cur.fetchall()]

    def entity_history(self, entity_id: str, last_n: int | None = None) -> list[dict]:
        cur = self._conn.cursor()
        query = (
            "SELECT es.*, s.timestamp FROM entity_snapshots es "
            "JOIN snapshots s ON es.step = s.step "
            "WHERE es.entity_id = ? ORDER BY es.step"
        )
        if last_n:
            query += f" DESC LIMIT {last_n}"
        cur.execute(query, (entity_id,))
        rows = cur.fetchall()
        if last_n:
            rows.reverse()
        history = []
        for row in rows:
            # id, step, entity_id, features, coordinates, traj_class, momentum, drift, stability, metadata, timestamp
            history.append({
                "step": row[1],
                "timestamp": row[10],
                "entity_id": row[2],
                "features": json.loads(row[3]),
                "coordinates": json.loads(row[4]) if row[4] else None,
                "trajectory_class": row[5],
                "momentum": row[6],
                "drift": row[7],
                "stability": row[8],
                "metadata": json.loads(row[9]),
            })
        return history

    def _build_snapshot(self, row) -> Snapshot:
        step, timestamp, centroids_json, meta_json = row
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM entity_snapshots WHERE step = ?", (step,))
        entities = {}
        for er in cur.fetchall():
            eid = er[2]
            entities[eid] = EntitySnapshot(
                entity_id=eid,
                features=json.loads(er[3]),
                coordinates=json.loads(er[4]) if er[4] else None,
                trajectory_class=er[5],
                momentum=er[6],
                drift=er[7],
                stability=er[8],
                metadata=json.loads(er[9]),
            )
        return Snapshot(
            step=step,
            timestamp=timestamp,
            entities=entities,
            centroid_projections=json.loads(centroids_json),
            metadata=json.loads(meta_json),
        )

    @property
    def step_count(self) -> int:
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM snapshots")
        return cur.fetchone()[0]

    def close(self):
        self._conn.close()


# ── PipelineComponent ──

class SnapshotStore:
    """
    Persistent time-series store for vector space snapshots.

    Aggregates projection results and trajectory metrics from upstream
    pipeline modules and persists them for historical queries, replay,
    and dashboard visualization.

    Can be connected downstream of both VectorSpaceModule and
    TrajectoryTracker in a DagPipeline.

    Parameters
    ----------
    path : str | Path
        Directory where snapshot data is stored.
    backend : str
        Storage backend: ``"json"`` or ``"sqlite"``. Default: ``"json"``.
    auto_flush : bool
        Whether to write to disk on every ``run()`` call. Default: True.
    session_id : str | None
        Optional session identifier for multi-run grouping.
    """

    def __init__(
        self,
        path: str | Path = "./vectorspace_data",
        backend: Literal["json", "sqlite"] = "json",
        auto_flush: bool = True,
        session_id: str | None = None,
    ):
        self.path = Path(path)
        self.backend_type = backend
        self.auto_flush = auto_flush
        self.session_id = session_id or f"session_{int(time.time())}"

        session_path = self.path / self.session_id
        if backend == "sqlite":
            self._backend = _SqliteBackend(session_path)
        else:
            self._backend = _JsonBackend(session_path)

        self._step_counter = 0
        self._pending: list[Snapshot] = []

    # ── datapizza PipelineComponent interface ──

    def run(self, data: dict | None = None, **kwargs) -> dict:
        """
        Synchronous pipeline entry point.

        Accepts upstream data from VectorSpaceModule and/or TrajectoryTracker
        and persists a unified snapshot.

        Parameters
        ----------
        data : dict
            Expected keys (all optional — uses what's available):
            - ``"projections"`` — from VectorSpaceModule
            - ``"trajectories"`` — from TrajectoryTracker
            - ``"features"`` — raw feature vectors ``{entity_id: list}``
            - ``"step"`` — explicit step counter
            - ``"metadata"`` — arbitrary metadata dict

        Returns
        -------
        dict
            ``{"snapshot": Snapshot.to_dict(), "step": int, "total_snapshots": int}``
        """
        return self._process(data or {}, **kwargs)

    async def a_run(self, data: dict | None = None, **kwargs) -> dict:
        """Async pipeline entry point."""
        return self._process(data or {}, **kwargs)

    # ── Core logic ──

    def _process(self, data: dict, **kwargs) -> dict:
        # Resolve upstream data — DagPipeline may nest dicts from connected modules
        projections = data.get("projections", {})
        trajectories = data.get("trajectories", {})
        features_raw = data.get("features", {})
        centroid_projections = data.get("centroid_projections", {})

        # Unpack from nested upstream — e.g., {"vectorspace": {"projections": ...}}
        for key, val in data.items():
            if isinstance(val, dict):
                if "projections" in val and not projections:
                    projections = val["projections"]
                    centroid_projections = val.get("centroid_projections", centroid_projections)
                if "trajectories" in val and not trajectories:
                    trajectories = val["trajectories"]
                if "features" in val and not features_raw:
                    features_raw = val["features"]

        step = data.get("step", self._step_counter)
        self._step_counter = step + 1
        timestamp = time.time()

        # Build entity snapshots by merging all available data sources
        entity_ids = set()
        entity_ids.update(projections.keys())
        entity_ids.update(trajectories.keys())
        entity_ids.update(features_raw.keys())

        entities = {}
        for eid in entity_ids:
            eid_str = str(eid)

            # Features — from raw features or from projections
            feat = features_raw.get(eid_str, [])
            if not feat and eid_str in projections:
                proj = projections[eid_str]
                if isinstance(proj, dict):
                    feat = proj.get("raw_features", [])

            # Coordinates — from projections
            coords = None
            if eid_str in projections:
                proj = projections[eid_str]
                if isinstance(proj, dict):
                    coords = proj.get("coordinates")

            # Trajectory metrics
            traj = trajectories.get(eid_str, {})
            if isinstance(traj, dict):
                traj_class = traj.get("classification")
                momentum = traj.get("momentum")
                drift = traj.get("drift")
                stability = traj.get("stability")
            else:
                traj_class = momentum = drift = stability = None

            entities[eid_str] = EntitySnapshot(
                entity_id=eid_str,
                features=feat if isinstance(feat, list) else list(feat),
                coordinates=coords,
                trajectory_class=traj_class,
                momentum=momentum,
                drift=drift,
                stability=stability,
            )

        snapshot = Snapshot(
            step=step,
            timestamp=timestamp,
            entities=entities,
            centroid_projections=centroid_projections,
            metadata=data.get("metadata", {}),
        )

        if self.auto_flush:
            self._backend.save(snapshot)
        else:
            self._pending.append(snapshot)

        logger.info(
            f"Snapshot step={step}: {len(entities)} entities "
            f"(total={self._backend.step_count + len(self._pending)})"
        )

        return {
            "snapshot": snapshot.to_dict(),
            "step": step,
            "total_snapshots": self._backend.step_count + len(self._pending),
            "session_id": self.session_id,
        }

    # ── Flush pending (when auto_flush=False) ──

    def flush(self):
        """Write all pending snapshots to disk."""
        for snap in self._pending:
            self._backend.save(snap)
        count = len(self._pending)
        self._pending.clear()
        logger.info(f"Flushed {count} pending snapshots to {self.backend_type}")

    # ── Query API ──

    def get_snapshot(self, step: int) -> Snapshot | None:
        """Retrieve a snapshot by step number."""
        return self._backend.load_step(step)

    def get_range(self, start: int, end: int) -> list[Snapshot]:
        """Retrieve snapshots within a step range (inclusive)."""
        return self._backend.load_range(start, end)

    def get_latest(self, n: int = 1) -> list[Snapshot]:
        """Retrieve the N most recent snapshots."""
        return self._backend.load_latest(n)

    def get_all(self) -> list[Snapshot]:
        """Retrieve all snapshots."""
        return self._backend.load_all()

    def get_entity_history(self, entity_id: str, last_n: int | None = None) -> list[dict]:
        """
        Get the time-series for a specific entity across all snapshots.

        Returns a list of dicts with step, timestamp, features, coordinates,
        trajectory_class, momentum, drift, stability.
        """
        return self._backend.entity_history(entity_id, last_n)

    @property
    def total_snapshots(self) -> int:
        return self._backend.step_count + len(self._pending)

    def close(self):
        """Release backend resources."""
        if hasattr(self._backend, "close"):
            self._backend.close()
