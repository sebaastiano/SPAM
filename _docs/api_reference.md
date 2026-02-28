# Hackapizza API Reference — Team SPAM! (id: 17)

---

## GET Endpoints

### All restaurants (full overview)
```bash
curl -s -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  "https://hackapizza.datapizza.tech/restaurants" | python3 -m json.tool
```
Returns: `id`, `name`, `balance`, `inventory`, `reputation`, `isOpen`, `kitchen`, `menu` for every team.

---

### Your restaurant details
```bash
curl -s -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  "https://hackapizza.datapizza.tech/restaurant/17" | python3 -m json.tool
```
Returns: full state of your restaurant only. Errors: `400` bad id, `403` not yours, `404` not found.

---

### Any restaurant's menu (public)
```bash
curl -s -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  "https://hackapizza.datapizza.tech/restaurant/17/menu" | python3 -m json.tool
```
Replace `17` with any team id to see their public menu. Errors: `400` bad id, `404` not found.

---

### All available recipes
```bash
curl -s -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  "https://hackapizza.datapizza.tech/recipes" | python3 -m json.tool
```
Returns: array of recipes with `name`, `preparationTimeMs`, `ingredients` (map of ingredient → quantity), `prestige`.

---

### Market entries (buy/sell listings)
```bash
curl -s -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  "https://hackapizza.datapizza.tech/market/entries" | python3 -m json.tool
```
Returns: active and closed market entries from all teams. Entries expire at end of turn.

---

### Meals served / client requests (per turn)
```bash
curl -s -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  "https://hackapizza.datapizza.tech/meals?turn_id=1&restaurant_id=17" | python3 -m json.tool
```
Replace `turn_id` with current turn number. Returns client orders with `executed` boolean (true = already served).

---

### Bid history (per turn)
```bash
curl -s -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  "https://hackapizza.datapizza.tech/bid_history?turn_id=1" | python3 -m json.tool
```
Returns all closed bids from all teams for the given turn. Useful for competitor analysis.

---

## MCP Tool Calls (POST /mcp)

All MCP calls use JSON-RPC. Format:
```bash
curl -s -X POST \
  -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"TOOL_NAME","arguments":{...}}}' \
  "https://hackapizza.datapizza.tech/mcp" | python3 -m json.tool
```

---

### `save_menu` — set your menu (speaking / closed_bid / waiting phase)
```bash
curl -s -X POST \
  -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0","id":1,"method":"tools/call",
    "params":{
      "name":"save_menu",
      "arguments":{
        "items":[
          {"name":"Nome Ricetta","price":100}
        ]
      }
    }
  }' \
  "https://hackapizza.datapizza.tech/mcp" | python3 -m json.tool
```

---

### `closed_bid` — submit ingredient bids (closed_bid phase only)
```bash
curl -s -X POST \
  -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0","id":1,"method":"tools/call",
    "params":{
      "name":"closed_bid",
      "arguments":{
        "bids":[
          {"ingredient":"Farina di Nettuno","bid":50,"quantity":3},
          {"ingredient":"Funghi Orbitali","bid":30,"quantity":2}
        ]
      }
    }
  }' \
  "https://hackapizza.datapizza.tech/mcp" | python3 -m json.tool
```
Note: last submission wins if you call multiple times in the same turn.

---

### `prepare_dish` — start cooking a dish (serving phase only)
```bash
curl -s -X POST \
  -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0","id":1,"method":"tools/call",
    "params":{
      "name":"prepare_dish",
      "arguments":{"dish_name":"Nome Ricetta"}
    }
  }' \
  "https://hackapizza.datapizza.tech/mcp" | python3 -m json.tool
```
Triggers SSE event `preparation_complete` when done.

---

### `serve_dish` — serve a ready dish to a client (serving phase only)
```bash
curl -s -X POST \
  -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0","id":1,"method":"tools/call",
    "params":{
      "name":"serve_dish",
      "arguments":{"dish_name":"Nome Ricetta","client_id":"CLIENT_ID_FROM_SSE"}
    }
  }' \
  "https://hackapizza.datapizza.tech/mcp" | python3 -m json.tool
```

---

### `update_restaurant_is_open` — open or close your restaurant
```bash
curl -s -X POST \
  -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0","id":1,"method":"tools/call",
    "params":{
      "name":"update_restaurant_is_open",
      "arguments":{"is_open":true}
    }
  }' \
  "https://hackapizza.datapizza.tech/mcp" | python3 -m json.tool
```
Cannot re-open during serving phase (can only close during serving).

---

### `create_market_entry` — list an ingredient for sale or post a buy offer
```bash
curl -s -X POST \
  -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0","id":1,"method":"tools/call",
    "params":{
      "name":"create_market_entry",
      "arguments":{
        "side":"SELL",
        "ingredient_name":"Funghi Orbitali",
        "quantity":2,
        "price":40
      }
    }
  }' \
  "https://hackapizza.datapizza.tech/mcp" | python3 -m json.tool
```
`side`: `"BUY"` or `"SELL"`. Creates a broadcast `message` SSE event visible to all teams.

---

### `execute_transaction` — accept a market entry from another team
```bash
curl -s -X POST \
  -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0","id":1,"method":"tools/call",
    "params":{
      "name":"execute_transaction",
      "arguments":{"market_entry_id":123}
    }
  }' \
  "https://hackapizza.datapizza.tech/mcp" | python3 -m json.tool
```
`market_entry_id` comes from `/market/entries`.

---

### `delete_market_entry` — remove your own market listing
```bash
curl -s -X POST \
  -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0","id":1,"method":"tools/call",
    "params":{
      "name":"delete_market_entry",
      "arguments":{"market_entry_id":123}
    }
  }' \
  "https://hackapizza.datapizza.tech/mcp" | python3 -m json.tool
```

---

### `send_message` — send a direct message to another team
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
Recipient gets a `new_message` SSE event (private). Replace `recipient_id` with their team id.

---

## SSE Stream (real-time events)

```bash
curl -N -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  -H "Accept: text/event-stream" \
  "https://hackapizza.datapizza.tech/events/17"
```

| Event | Recipient | Key fields |
|---|---|---|
| `game_started` | broadcast | `{}` |
| `game_phase_changed` | broadcast | `phase`: speaking → closed_bid → waiting → serving → stopped |
| `client_spawned` | your team only | `clientName`, `orderText` |
| `preparation_complete` | your team only | `dish` |
| `message` | broadcast | `sender`, `payload` |
| `new_message` | your team only | `messageId`, `senderId`, `senderName`, `text`, `datetime` |
| `heartbeat` | broadcast | `ts` (epoch ms) |
| `game_reset` | broadcast | `{}` |

---

## Phase → Allowed Operations

| Operation | speaking | closed_bid | waiting | serving | stopped |
|---|---|---|---|---|---|
| `save_menu` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `closed_bid` | ❌ | ✅ | ❌ | ❌ | ❌ |
| `prepare_dish` | ❌ | ❌ | ❌ | ✅ | ❌ |
| `serve_dish` | ❌ | ❌ | ❌ | ✅ | ❌ |
| `create_market_entry` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `execute_transaction` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `delete_market_entry` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `send_message` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `update_restaurant_is_open` | ✅ | ✅ | ✅ | ✅ (close only) | ❌ |
| `restaurant_info` (GET) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `get_meals` (GET) | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## MCP Response format

```json
{
  "result": {
    "isError": false,
    "content": [{"text": "..."}]
  }
}
```
`isError: true` = operation failed (read `content[0].text` for reason).  
HTTP `401` = bad API key. HTTP `429` = rate limited.
