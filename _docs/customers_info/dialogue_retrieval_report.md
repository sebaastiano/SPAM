# Dialogue & Communication Retrieval Report — Hackapizza 2.0

**Team:** SPAM! (ID: 17)  
**Compiled:** February 28, 2026  
**Sources verified:** Hackapizza_instructions.md, api_reference.md, game_data_reference.md, client_template.py, Datapizza AI Memory API Reference

---

## Table of Contents

1. [Overview — Three Dialogue Channels](#1-overview--three-dialogue-channels)
2. [Channel 1: Game Client Orders](#2-channel-1-game-client-orders)
3. [Channel 2: Inter-Restaurant Private Messages](#3-channel-2-inter-restaurant-private-messages)
4. [Channel 3: Market Broadcasts](#4-channel-3-market-broadcasts)
5. [Retrieval Summary Matrix](#5-retrieval-summary-matrix)
6. [Framework Memory System (datapizza.memory.Memory)](#6-framework-memory-system-datapizzamemorymemory)
7. [Recommended Architecture: Capture & Store Everything](#7-recommended-architecture-capture--store-everything)

---

## 1. Overview — Three Dialogue Channels

The Hackapizza game has **three distinct communication channels**. Each has different visibility, persistence, and retrieval capabilities:

| Channel | Direction | Visibility | Persistent API? |
|---|---|---|---|
| **Client orders** (`client_spawned`) | Client → Restaurant (one-way) | Your team only | ✅ `GET /meals` |
| **Private messages** (`send_message` / `new_message`) | Restaurant ↔ Restaurant (bidirectional) | Sender + recipient only | ✅ Partial (`receivedMessages` field) |
| **Market broadcasts** (`message`) | System → All (broadcast) | All teams | ❌ SSE only |

**Critical finding:** There is **no back-and-forth dialogue with game clients** (restaurant customers). They send a one-shot order; you serve or don't. The only true dialogue channel is inter-restaurant messaging.

---

## 2. Channel 1: Game Client Orders

### What It Is

When a customer visits your restaurant during the serving phase, you receive their order as a natural-language string. This is a **one-way, one-shot communication** — there is no way to ask the client for clarification, negotiate, or converse.

### Real-Time Retrieval (SSE)

**Event:** `client_spawned`  
**Recipient:** Your team only  
**Payload:**
```json
{
  "clientName": "string",
  "orderText": "string",
  "client_id": "string"
}
```

- `clientName` — The client archetype (Esploratore Galattico, Astrobarone, Saggi del Cosmo, Famiglie Orbitali)
- `orderText` — Natural language order (e.g., "I'd like a Sinfonia Cosmica del Multiverso")
- `client_id` — Unique identifier needed for `serve_dish` (see discrepancy note below)

**Template code handling:**
```python
async def client_spawned(data: dict[str, Any]) -> None:
    client_name = data.get("clientName", "unknown")
    order_text = str(data.get("orderText", "unknown"))
    order_text = order_text.lower().replace("i'd like a ", "").replace("i'd like ", "")
```

### Historical Retrieval (HTTP)

**Endpoint:** `GET /meals?turn_id=X&restaurant_id=17`  
**Auth:** `x-api-key` header  
**Available in all phases:** speaking, closed_bid, waiting, serving, stopped

```bash
curl -s -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  "https://hackapizza.datapizza.tech/meals?turn_id=1&restaurant_id=17" | python3 -m json.tool
```

**Returns:** Array of client orders for the specified turn with:
- Client request details
- `executed` boolean — `true` if the meal was served, `false` otherwise

**Note:** At the time of data collection (pre-game), this endpoint returned `HTTP 400: Bad Request` because no turns had been played yet. It becomes available once game turns begin.

### What You CAN'T Do

- ❌ Ask the client clarifying questions
- ❌ Negotiate price with the client
- ❌ See what the client ordered at other restaurants
- ❌ Know in advance which clients will arrive

### ⚠️ Discrepancy: `client_id` Field

| Source | Fields listed for `client_spawned` |
|---|---|
| **Hackapizza_instructions.md** (official) | `clientName`, `orderText` — NO `client_id` |
| **api_reference.md** (team-compiled) | `clientName`, `orderText`, `client_id` |
| **serve_dish tool** (requires) | `client_id` as mandatory argument |

**Conclusion:** `client_id` must be present in the SSE payload (otherwise `serve_dish` would be impossible). The official instructions appear to have omitted it. Use defensive coding with a fallback.

---

## 3. Channel 2: Inter-Restaurant Private Messages

### What It Is

The only true **bidirectional dialogue channel** in the game. Teams can send direct messages to each other for negotiation, alliance-building, threats, or disinformation.

### Sending Messages

**MCP Tool:** `send_message`  
**Available phases:** speaking, closed_bid, waiting, serving (NOT stopped)

```bash
curl -s -X POST \
  -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0","id":1,"method":"tools/call",
    "params":{
      "name":"send_message",
      "arguments":{"recipient_id":5,"text":"Ciao, vuoi fare un accordo?"}
    }
  }' \
  "https://hackapizza.datapizza.tech/mcp" | python3 -m json.tool
```

**Arguments:**
| Field | Type | Description |
|---|---|---|
| `recipient_id` | `number` | Target team's ID (1–25) |
| `text` | `string` | Message content |

### Receiving Messages (Real-Time)

**SSE Event:** `new_message`  
**Recipient:** Your team only (private)

**Payload:**
```json
{
  "messageId": "string",
  "senderId": "number",
  "senderName": "string",
  "text": "string",
  "datetime": "string"
}
```

| Field | Type | Description |
|---|---|---|
| `messageId` | `string` | Unique message identifier |
| `senderId` | `number` | Team ID of the sender |
| `senderName` | `string` | Team name of the sender |
| `text` | `string` | Message content |
| `datetime` | `string` | Timestamp |

### Retrieving Received Messages (HTTP)

**Endpoint:** `GET /restaurant/17`  
**Returns:** Full restaurant state including a `receivedMessages` field.

```bash
curl -s -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  "https://hackapizza.datapizza.tech/restaurant/17" | python3 -m json.tool
```

The `receivedMessages` field is part of the restaurant object. The exact structure (whether it's a count or full message list) needs to be verified empirically during gameplay.

### Spying on Communication Volume

**Endpoint:** `GET /restaurants`  
**Returns:** Overview of ALL restaurants, each including `receivedMessages`.

```bash
curl -s -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  "https://hackapizza.datapizza.tech/restaurants" | python3 -m json.tool
```

This lets you see **how many messages each team has received** — useful for detecting alliances, active negotiators, or isolated teams. You can't read other teams' messages, but you can observe communication patterns.

### What You CAN Do

- ✅ Send messages to any team by ID
- ✅ Receive messages with full metadata (sender, text, timestamp)
- ✅ Retrieve your own received messages via REST
- ✅ See all teams' received message counts via `GET /restaurants`

### What You CAN'T Do

- ❌ Retrieve messages you **sent** (no outbox API — must log locally)
- ❌ Read other teams' private messages
- ❌ Delete or edit sent messages
- ❌ Send messages during `stopped` phase

---

## 4. Channel 3: Market Broadcasts

### What It Is

When any team creates a market entry (buy or sell offer), the system automatically sends a **broadcast `message` event** visible to all teams. This acts as a public bulletin board.

### Real-Time Retrieval (SSE)

**SSE Event:** `message`  
**Recipient:** Broadcast (all teams)

**Payload:**
```json
{
  "sender": "string",
  "payload": "string or object"
}
```

| Field | Type | Description |
|---|---|---|
| `sender` | `string` | Team name that created the market entry |
| `payload` | `string \| object` | Content of the broadcast (market listing details) |

### Related HTTP Endpoint

While broadcasts themselves aren't stored in a retrievable log, the underlying **market entries** ARE queryable:

```bash
curl -s -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  "https://hackapizza.datapizza.tech/market/entries" | python3 -m json.tool
```

Returns active and closed market entries from all teams. Entries expire at end of turn.

### What You CAN Do

- ✅ See all market broadcasts in real-time via SSE
- ✅ Query current/past market entries via `GET /market/entries`
- ✅ Infer which teams are active in trading

### What You CAN'T Do

- ❌ Retrieve past broadcast messages after the SSE moment passes
- ❌ Filter broadcasts by sender or type (must process all)

---

## 5. Retrieval Summary Matrix

| Data Type | Real-Time Source | Historical API | Can Read Others'? | Must Log Locally? |
|---|---|---|---|---|
| Client orders (your restaurant) | SSE `client_spawned` | ✅ `GET /meals?turn_id=X&restaurant_id=17` | ❌ | Recommended |
| Private messages received | SSE `new_message` | ✅ `GET /restaurant/17` → `receivedMessages` | ❌ (count only via `GET /restaurants`) | Recommended |
| Private messages sent | — | ❌ No outbox endpoint | ❌ | **Required** |
| Market broadcasts | SSE `message` | ❌ (but `GET /market/entries` for listings) | ✅ All public | Recommended |
| Other teams' message volume | — | ✅ `GET /restaurants` → `receivedMessages` per team | Count only | Optional |
| Bid history | — | ✅ `GET /bid_history?turn_id=X` | ✅ All teams | Recommended |

---

## 6. Framework Memory System (datapizza.memory.Memory)

The `datapizza.memory.Memory` class is a **local conversation history buffer for the LLM client**. It does NOT connect to the game server or retrieve game dialogues. It's purely for maintaining LLM context across multiple invocations.

### Key Methods

| Method | Description |
|---|---|
| `add_turn(blocks, role)` | Add a conversation turn (USER or ASSISTANT) |
| `new_turn(role)` | Start a new turn |
| `add_to_last_turn(block)` | Append a block to the most recent turn |
| `clear()` | Wipe all history |
| `copy()` | Deep copy the memory |
| `to_dict()` | Export as list of dicts |
| `json_dumps()` | Serialize to JSON string |
| `json_loads(json_str)` | Deserialize from JSON string |
| `iter_blocks()` | Iterate over all blocks |
| `__len__()` | Number of turns |
| `__getitem__(index)` | Access specific turn |
| `__delitem__(index)` | Delete specific turn |

### How to Use It for Game Dialogues

Memory is the right tool for **feeding game interaction history into the LLM agent**. The pattern:

```python
from datapizza.memory import Memory
from datapizza.type import ROLE, TextBlock

# Create a persistent memory for the agent
agent_memory = Memory()

# When a client order arrives via SSE
def on_client_spawned(client_name, order_text, client_id):
    agent_memory.add_turn(
        TextBlock(content=f"[CLIENT {client_name}] Order: {order_text} (id: {client_id})"),
        role=ROLE.USER
    )

# When a message from another restaurant arrives via SSE
def on_new_message(sender_name, text, datetime):
    agent_memory.add_turn(
        TextBlock(content=f"[MESSAGE from {sender_name} at {datetime}] {text}"),
        role=ROLE.USER
    )

# When a market broadcast arrives via SSE
def on_market_broadcast(sender, payload):
    agent_memory.add_turn(
        TextBlock(content=f"[MARKET BROADCAST from {sender}] {payload}"),
        role=ROLE.USER
    )
```

### Persistence

Memory is **in-memory only** by default. To persist across restarts:

```python
# Save
serialized = agent_memory.json_dumps()
with open("memory_backup.json", "w") as f:
    f.write(serialized)

# Load
with open("memory_backup.json", "r") as f:
    agent_memory.json_loads(f.read())
```

---

## 7. Recommended Architecture: Capture & Store Everything

Since most game data is ephemeral (SSE events disappear once consumed), the recommended approach is to **capture everything in real-time and store it locally**.

### Architecture

```
SSE Stream
    │
    ├── client_spawned ──────┐
    ├── new_message ─────────┤
    ├── message (broadcast) ──┤
    ├── preparation_complete ─┤
    ├── game_phase_changed ───┤
    └── game_started ─────────┤
                              ▼
                    ┌─────────────────┐
                    │  Event Logger   │
                    │  (append-only)  │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
            ┌──────────────┐  ┌──────────────────┐
            │  JSON Log    │  │  Agent Memory     │
            │  (full       │  │  (LLM context     │
            │   history)   │  │   window)         │
            └──────────────┘  └──────────────────┘
```

### What to Log Per Event

```python
import json
from datetime import datetime

def log_event(event_type: str, data: dict):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "data": data
    }
    with open("game_events.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")
```

| Event | Fields to Capture |
|---|---|
| `client_spawned` | `clientName`, `orderText`, `client_id`, timestamp |
| `new_message` | `messageId`, `senderId`, `senderName`, `text`, `datetime` |
| `message` (broadcast) | `sender`, `payload`, timestamp |
| `preparation_complete` | `dish`, timestamp |
| `game_phase_changed` | `phase`, timestamp |
| `game_started` | `turn_id`, timestamp |

### Supplementary Polling (Between Turns)

At the end of each turn (during `stopped` phase), poll historical endpoints to fill any gaps:

```python
async def end_of_turn_snapshot(turn_id: int):
    # Get all meals for this turn
    meals = await fetch(f"/meals?turn_id={turn_id}&restaurant_id=17")
    
    # Get our restaurant state (includes receivedMessages)
    our_state = await fetch(f"/restaurant/17")
    
    # Get all restaurants' state (communication volume)
    all_restaurants = await fetch("/restaurants")
    
    # Get bid history
    bids = await fetch(f"/bid_history?turn_id={turn_id}")
    
    # Get market entries
    market = await fetch("/market/entries")
    
    # Log everything
    snapshot = {
        "turn_id": turn_id,
        "meals": meals,
        "our_state": our_state,
        "all_restaurants": all_restaurants,
        "bids": bids,
        "market": market
    }
    with open(f"snapshots/turn_{turn_id}.json", "w") as f:
        json.dump(snapshot, f, indent=2)
```

### Using Vector Store for Semantic Search Over History

For advanced retrieval (e.g., "what did team 5 offer us last time?"), embed logged events into a vector store:

```python
from datapizza.vectorstores.qdrant import QdrantVectorstore
from datapizza.type import Chunk, DenseEmbedding, VectorConfig

vs = QdrantVectorstore(location=":memory:")
vs.create_collection("game_events", VectorConfig(size=1536, distance="Cosine"))

# When a message arrives, embed and store it
chunk = Chunk(
    id=message_id,
    text=f"[{sender_name}] {text}",
    embeddings=[DenseEmbedding(name="dense", vector=client.embed(text))],
    metadata={"sender_id": sender_id, "turn": current_turn, "type": "message"}
)
vs.add(chunk, "game_events")

# Later: semantic search
results = vs.search("game_events", query_vector, k=5)
```

---

*End of report. All information verified against primary sources in the workspace.*
