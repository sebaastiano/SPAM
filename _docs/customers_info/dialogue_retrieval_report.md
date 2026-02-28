# Dialogue & Communication Retrieval Report — Hackapizza 2.0

**Team:** SPAM! (ID: 17)  
**Compiled:** February 28, 2026  
**Methodology:** Every claim below is directly quoted or paraphrased from a specific source with line/section references. Nothing is inferred.

### Sources used

| Abbreviation | File | Type |
|---|---|---|
| **INSTR** | `_docs/Hackapizza_instructions.md` | Official instructions from organizers |
| **API** | `_docs/api_reference.md` | Team-compiled API reference |
| **TEMPLATE** | `templates/client_template.py` | Official starter template from organizers |
| **GAMEDATA** | `_docs/game_data_reference.md` | Snapshot of real API responses (pre-game) |
| **MEMORY** | `Datapizza_docs/API_References/vectorstores_memory.md` | Datapizza framework docs |

---

## 1. SSE Events — What the sources say

### Event: `client_spawned`

**INSTR line 339:**
> `client_spawned` | solo ristorante destinatario | `clientName`: string, `orderText`: string

**API line 269:**
> `client_spawned` | your team only | `clientName`, `orderText`

**TEMPLATE lines 61–64:**
```python
async def client_spawned(data: dict[str, Any]) -> None:
    client_name = data.get("clientName", "unknown")
    order_text = str(data.get("orderText", "unknown"))
    order_text = order_text.lower().replace("i'd like a ", "").replace("i'd like ", "")
```

**Fields confirmed across sources:**
- `clientName` — string (INSTR, API, TEMPLATE)
- `orderText` — string (INSTR, API, TEMPLATE)

**Regarding `client_id`:**
- The `client_spawned` SSE event table in INSTR (line 339) lists only `clientName` and `orderText`. It does NOT list `client_id`.
- The TEMPLATE does not access `client_id` from this event.
- However, INSTR line 385 defines the `serve_dish` tool as requiring `dish_name: string, client_id: string`.
- INSTR line 358 states: `GET /meals` — "restituisce le richieste dei clienti con i relativi **id**" (returns client requests with their respective IDs).
- API line 155 (serve_dish curl example) uses `"client_id":"CLIENT_ID_FROM_SSE"` in the arguments.

**Conclusion from sources:** `client_id` exists as a concept in the game (required by `serve_dish`, returned by `/meals`). The API reference labels it "FROM_SSE" but the official SSE event table does not list it under `client_spawned`. Where exactly it appears at runtime is not confirmed in any source document.

---

### Event: `new_message`

**INSTR line 342:**
> `new_message` | solo ristorante destinatario | `messageId`, `senderId`, `senderName`, `text`, `datetime`

**API line 272:**
> `new_message` | your team only | `messageId`, `senderId`, `senderName`, `text`, `datetime`

**TEMPLATE:** No handler for `new_message` exists in the template (EVENT_HANDLERS dict at line 105 does not include it).

**Fields listed (names only — no types given in any source):**
- `messageId`
- `senderId`
- `senderName`
- `text`
- `datetime`

---

### Event: `message`

**INSTR line 341:**
> `message` | broadcast | `sender`: string, `payload`: testo/oggetto

**API line 271:**
> `message` | broadcast | `sender`, `payload`

**TEMPLATE lines 72–74:**
```python
async def message(data: dict[str, Any]) -> None:
    sender = data.get("sender", "unknown")
    text = data.get("payload", "")
```

**Fields confirmed:**
- `sender` — string (INSTR, TEMPLATE)
- `payload` — "testo/oggetto" i.e. text or object (INSTR)

**What triggers this event:**
- INSTR line 391: `create_market_entry`: "in caso di successo viene inviato un evento broadcast `message`."
- API line 199: `create_market_entry`: "Creates a broadcast `message` SSE event visible to all teams."

---

### Event: `game_started`

**INSTR line 337:**
> `game_started` | broadcast | oggetto vuoto `{}`

**API line 266:**
> `game_started` | broadcast | `{}`

**TEMPLATE lines 37–39:**
```python
async def game_started(data: dict[str, Any]) -> None:
    turn_id = data.get("turn_id", 0)
    log("EVENT", "game started, turn id: " + str(turn_id))
```

**Discrepancy:** INSTR and API say the payload is an empty object `{}`. The TEMPLATE reads `data.get("turn_id", 0)` from it.

---

### Event: `game_phase_changed`

**INSTR line 338:**
> `game_phase_changed` | broadcast | `phase`: speaking | closed_bid | waiting | serving | stopped

**API line 267:**
> `game_phase_changed` | broadcast | `phase`: speaking → closed_bid → waiting → serving → stopped

**TEMPLATE lines 78–92:**
```python
async def game_phase_changed(data: dict[str, Any]) -> None:
    phase = data.get("phase", "unknown")
    handlers: dict[str, Callable[[], Awaitable[None]]] = {
        "speaking": speaking_phase_started,
        "closed_bid": closed_bid_phase_started,
        "waiting": waiting_phase_started,
        "serving": serving_phase_started,
        "stopped": end_turn,
    }
```

**Fields confirmed:**
- `phase` — one of: `speaking`, `closed_bid`, `waiting`, `serving`, `stopped` (INSTR, API, TEMPLATE)

---

### Event: `preparation_complete`

**INSTR line 340:**
> `preparation_complete` | solo ristorante destinatario | `dish`: string

**API line 270:**
> `preparation_complete` | your team only | `dish`

**TEMPLATE lines 67–69:**
```python
async def preparation_complete(data: dict[str, Any]) -> None:
    dish_name = data.get("dish", "unknown")
```

**Fields confirmed:**
- `dish` — string (INSTR, TEMPLATE)

**What triggers this:**
- API line 141: `prepare_dish` "Triggers SSE event `preparation_complete` when done."

---

### Events: `heartbeat` and `game_reset`

**INSTR lines 343–344:**
> `heartbeat` | broadcast | `ts`: epoch milliseconds  
> `game_reset` | broadcast | oggetto vuoto `{}`

**INSTR line 345:**
> Nota: `heartbeat` e `game_reset` sono eventi di servizio piattaforma; gestiscili senza bloccare la logica di gioco.

**TEMPLATE lines 96–100:**
```python
async def game_reset(data: dict[str, Any]) -> None:
    if data:
        log("EVENT", f"game reset: {data}")
    else:
        log("EVENT", "game reset")
```

---

## 2. HTTP Endpoints — What the sources say

### `GET /meals`

**INSTR line 358:**
> `GET /meals` — restituisce le richieste dei clienti con i relativi id per un dato ristorante in un dato turno. Query obbligatorie: `turn_id`, `restaurant_id`. Include campo booleano `executed` (true se pasto servito).

**API lines 56–62:**
```
curl -s -H "x-api-key: ..." "https://hackapizza.datapizza.tech/meals?turn_id=1&restaurant_id=17"
```
> Returns client orders with `executed` boolean (true = already served).

**INSTR line 320 (phase table):** Available in all phases (speaking through stopped).

---

### `GET /restaurants`

**INSTR line 359:**
> `GET /restaurants` — overview di tutti i ristoranti in gioco.

**API lines 7–12:**
> Returns: `id`, `name`, `balance`, `inventory`, `reputation`, `isOpen`, `kitchen`, `menu` for every team.

**GAMEDATA lines 49–55:** Real API response showed columns: ID, Name, Balance, Reputation, Open, Clients.

---

### `GET /restaurant/:id`

**INSTR line 362:**
> `GET /restaurant/:id` — informazioni sul proprio ristorante. Vincolo: puoi leggere solo il tuo. Errori: `400` id non valido, `403` id non tuo, `404` non trovato.

**API lines 17–22:**
> Returns: full state of your restaurant only. Errors: `400` bad id, `403` not yours, `404` not found.

**GAMEDATA lines 30–38 (actual response for our restaurant):**
> Fields observed: Name, ID, Balance, Reputation, Is Open, Kitchen, **Received Messages** (value: 0)

---

### `GET /restaurant/:id/menu`

**INSTR line 363:**
> `GET /restaurant/:id/menu` — Errori: `400` id non valido, `404` non trovato. Risposta: array voci menu.

**API lines 24–29:**
> Replace `17` with any team id to see their public menu. Errors: `400` bad id, `404` not found.

---

### `GET /recipes`

**INSTR line 360:**
> `GET /recipes` — array ricette con ingredienti e tempi.

**API lines 31–36:**
> Returns: array of recipes with `name`, `preparationTimeMs`, `ingredients` (map of ingredient → quantity), `prestige`.

---

### `GET /bid_history?turn_id=<id>`

**INSTR line 361:**
> `GET /bid_history?turn_id=<id>` — tutte le puntate già concluse di tutti i team in un dato turno.

**API lines 64–69:**
> Returns all closed bids from all teams for the given turn. Useful for competitor analysis.

---

### `GET /market/entries`

**INSTR line 365:**
> `GET /market/entries` — array entry mercato attive/chiuse.

**API lines 44–49:**
> Returns: active and closed market entries from all teams. Entries expire at end of turn.

**INSTR line 268:**
> Le offerte vengono annullate alla fine di ogni turno.

---

## 3. MCP Tools — Communication-Related

### `serve_dish`

**INSTR line 385:**
> `serve_dish` | `dish_name`: string, `client_id`: string | Serve piatto a cliente

**INSTR line 313:** Available in serving phase only.

**API lines 144–158 (curl example):**
```json
{
  "name": "serve_dish",
  "arguments": {"dish_name": "Nome Ricetta", "client_id": "CLIENT_ID_FROM_SSE"}
}
```

---

### `send_message`

**INSTR line 387:**
> `send_message` | `recipient_id`: number, `text`: string | Messaggio diretto a un team

**INSTR line 390:**
> `send_message`: il destinatario riceve evento SSE `new_message`.

**INSTR line 317 (phase table):** Available in speaking, closed_bid, waiting, serving. NOT in stopped.

**API lines 239–253:**
```json
{
  "name": "send_message",
  "arguments": {"recipient_id": 5, "text": "Ciao, vuoi fare un accordo?"}
}
```
> Recipient gets a `new_message` SSE event (private).

---

### `create_market_entry`

**INSTR line 383:**
> `create_market_entry` | `side`: BUY|SELL, `ingredient_name`, `quantity`, `price` | Crea proposta acquisto/vendita

**INSTR line 391:**
> `create_market_entry`: in caso di successo viene inviato un evento broadcast `message`.

**INSTR line 268:**
> Le offerte vengono annullate alla fine di ogni turno.

**API line 199:**
> `side`: `"BUY"` or `"SELL"`. Creates a broadcast `message` SSE event visible to all teams.

---

### `prepare_dish`

**INSTR line 384:**
> `prepare_dish` | `dish_name`: string | Avvia preparazione piatto

**API line 141:**
> Triggers SSE event `preparation_complete` when done.

---

## 4. Phase → Allowed Operations

**Source: INSTR lines 309–321 and API lines 279–291 (identical)**

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

## 5. Client Archetypes

**Source: INSTR lines 224–252**

INSTR line 226: "Non sono semplici avventori, ma **archetipi sociali**, ognuno con aspettative, vincoli e priorità diverse."

INSTR line 228: "Qual è il target del tuo ristorante? Tutto dipende dai piatti che avrai nel tuo menù!"

| Archetype | Traits (quoted from INSTR) |
|---|---|
| **🚀 Esploratore Galattico** | ha poco tempo, ha poco budget, la qualità non è una priorità. **Cosa premia:** piatti semplici, economici e rapidissimi. |
| **💰 Astrobarone** | ha pochissimo tempo, pretende buoni piatti, guarda poco al prezzo. **Cosa premia:** qualità, rapidità e un menu che comunichi status e prestigio. |
| **🔭 Saggi del Cosmo** | cercano ottimi piatti, hanno tempo da perdere, badano poco al prezzo. **Cosa premia:** ricette prestigiose, ingredienti rari, coerenza narrativa e culturale. |
| **👨‍👩‍👧‍👦 Famiglie Orbitali** | hanno molto tempo, osservano prezzo e qualità. **Cosa premia:** equilibrio tra costo e valore, piatti curati ma accessibili, menu ben progettato. |

**Note:** The `client_spawned` event carries `clientName: string` (INSTR line 339). No source states what values `clientName` takes or whether it maps to these archetype names.

---

## 6. Intollerances

**INSTR lines 215–221:**
> "Nel Multiverso, un errore alimentare non è solo un reclamo. Può essere un incidente diplomatico. O peggio."  
> "Ignorare le intolleranze significa rischiare vite, reputazione e sanzioni federali."  
> "**Fai attenzione alle intolleranze dei clienti.** Non servire loro piatti che potrebbero avere conseguenze indesiderate."

No source specifies how intollerances are communicated (whether in `orderText`, a separate field, or elsewhere).

---

## 7. `Received Messages` field

**GAMEDATA line 36:** Our restaurant API response includes `Received Messages: 0`.

**API line 12:** `GET /restaurants` returns: `id`, `name`, `balance`, `inventory`, `reputation`, `isOpen`, `kitchen`, `menu` — does NOT list `receivedMessages`.

**INSTR:** Does not mention `receivedMessages` anywhere.

**Conclusion from sources:** The field was observed in a real API response (GAMEDATA) but is not documented in official instructions or the team API reference's field list for `GET /restaurants`.

---

## 8. MCP Response Format

**INSTR lines 373–374:**
> Successo operativo: `result.isError = false`  
> Errore operativo: `result.isError = true` con messaggio testuale in `result.content[0].text`  
> Errore auth: `401`

**API lines 297–305:**
```json
{
  "result": {
    "isError": false,
    "content": [{"text": "..."}]
  }
}
```
> `isError: true` = operation failed (read `content[0].text` for reason).  
> HTTP `401` = bad API key. HTTP `429` = rate limited.

**INSTR line 392:**
> Rate limit: In caso di superamento limite viene restituito errore `429`.

---

## 9. SSE Connection

**INSTR lines 327–330:**
> Metodo: `GET`, Path: `/events/:restaurantId`, Header: `x-api-key`

**INSTR lines 330–331 (rules):**
> - puoi aprire lo stream solo per il tuo `restaurantId`
> - una sola connessione SSE attiva per ristorante
> - in caso di errore: `401` (api key), `403` (id non tuo), `404` (ristorante inesistente), `409` (connessione già attiva)

**INSTR lines 332–333 (format):**
> - handshake iniziale: `data: connected`
> - poi messaggi JSON con struttura `type` + `data`

**API lines 257–262:**
```bash
curl -N -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  -H "Accept: text/event-stream" \
  "https://hackapizza.datapizza.tech/events/17"
```

**TEMPLATE lines 163–170:**
```python
async def listen_once(session: aiohttp.ClientSession) -> None:
    url = f"{BASE_URL}/events/{TEAM_ID}"
    headers = {"Accept": "text/event-stream", "x-api-key": TEAM_API_KEY}
    async with session.get(url, headers=headers) as response:
        response.raise_for_status()
        async for line in response.content:
            await handle_line(line)
```

---

## 10. Framework Memory System

**Source: MEMORY (Datapizza docs)**

`datapizza.memory.memory.Memory` — Methods listed:

```python
__bool__()
__delitem__(index)
__eq__(other)
__getitem__(index)
__hash__()
__iter__()
__len__()
__repr__()
__setitem__(index, value)
__str__()

add_to_last_turn(block: Block)
add_turn(blocks: list[Block] | Block, role: ROLE)
clear()
copy()
iter_blocks()
json_dumps() -> str
json_loads(json_str: str)
new_turn(role=ROLE.ASSISTANT)
to_dict() -> list[dict]
```

No source describes what Memory is used for. The method signatures suggest it is a conversation history buffer with serialization support. It is part of the Datapizza framework, not connected to the game server.

---

## 11. Summary of Discrepancies Between Sources

| Topic | Discrepancy |
|---|---|
| `client_spawned` fields | INSTR lists `clientName`, `orderText`. `serve_dish` requires `client_id` (INSTR line 385). API serve_dish example says `CLIENT_ID_FROM_SSE`. But NO source lists `client_id` as a field of `client_spawned`. |
| `game_started` payload | INSTR and API say `{}` (empty object). TEMPLATE reads `data.get("turn_id", 0)`. |
| `GET /restaurants` fields | API says: `id`, `name`, `balance`, `inventory`, `reputation`, `isOpen`, `kitchen`, `menu`. GAMEDATA shows "Received Messages" in the per-restaurant view. INSTR doesn't list fields. |
| `clientName` values | INSTR describes 4 archetypes (section 8) and lists `clientName: string` in SSE (line 339). No source connects the two. |
| `new_message` handler | INSTR and API list `new_message` as an SSE event. TEMPLATE does not include a handler for it. |

---

*End of report. Every claim references its source document and line number.*
