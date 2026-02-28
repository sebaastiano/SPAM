# Datapizza AI Framework — Complete Field & Retrieval Reference

**Team:** SPAM! (ID: 17)  
**Compiled:** February 28, 2026  
**Source:** [datapizza-labs/datapizza-ai](https://github.com/datapizza-labs/datapizza-ai) (v0.0.23 core)

---

## How This Relates to Hackapizza

In Hackapizza 2.0 the game server exposes an **MCP server**. Our bot connects via `MCPClient` and receives tool results as `CallToolResult` objects (JSON with `isError` + `content[0].text`). SSE events arrive as raw JSON dicts. We use the Datapizza framework to:
1. **Parse MCP tool results** → `FunctionCallResultBlock.result` (string)
2. **Store/retrieve game knowledge** → `Chunk` (vectorstore) or `Memory` (conversation)
3. **Have an Agent reason** → `Agent.run()` / `Agent.a_run()` → `StepResult`

---

## 1. SSE Event Data (raw `dict[str, Any]`)

These are NOT framework types — they're plain JSON from the game server. The framework doesn't define these; we handle them in our `client_template.py` event handlers.

| Event | Fields in `data` dict | How to access |
|---|---|---|
| `game_started` | `turn_id` (observed in template, but INSTR says `{}`) | `data.get("turn_id", 0)` |
| `game_phase_changed` | `phase: str` (speaking / closed_bid / waiting / serving / stopped) | `data.get("phase", "unknown")` |
| `client_spawned` | `clientName: str`, `orderText: str`, *possibly* `client_id` at runtime | `data.get("clientName")`, `data.get("orderText")` |
| `preparation_complete` | `dish: str` | `data.get("dish", "unknown")` |
| `message` (broadcast) | `sender: str`, `payload: str|object` | `data.get("sender")`, `data.get("payload")` |
| `new_message` (DM) | `messageId`, `senderId`, `senderName`, `text`, `datetime` | `data.get("messageId")`, etc. |
| `heartbeat` | `ts: int` (epoch ms) | `data.get("ts")` |
| `game_reset` | `{}` (empty) | — |

---

## 2. MCP Tool Call Results

### How the framework handles MCP calls

```python
from datapizza.tools.mcp_client import MCPClient

# Connect to Hackapizza MCP server
mcp = MCPClient(url="https://hackapizza.datapizza.tech/mcp", headers={"x-api-key": KEY})
tools = mcp.list_tools()  # → list[Tool]

# Each tool becomes a callable. When executed:
result = await mcp.call_tool("serve_dish", {"dish_name": "...", "client_id": "..."})
# result is mcp.types.CallToolResult → serialized via result.model_dump_json()
```

### `CallToolResult` fields (from `mcp.types`)
| Field | Type | Description |
|---|---|---|
| `isError` | `bool` | `False` = success, `True` = operation failed |
| `content` | `list[Content]` | Usually `[TextContent(text="...")]` |

Access pattern in agent flow: `FunctionCallResultBlock.result` is a **string** (the JSON-dumped `CallToolResult`).

### MCP Tools and their argument fields

| Tool | Arguments | Returns on success |
|---|---|---|
| `serve_dish` | `dish_name: str`, `client_id: str` | confirmation text |
| `prepare_dish` | `dish_name: str` | triggers `preparation_complete` SSE |
| `send_message` | `recipient_id: number`, `text: str` | confirmation; triggers `new_message` SSE for recipient |
| `create_market_entry` | `side: "BUY"|"SELL"`, `ingredient_name: str`, `quantity: int`, `price: int` | triggers broadcast `message` SSE |
| `execute_transaction` | (undocumented args) | — |
| `delete_market_entry` | (undocumented args) | — |
| `save_menu` | (menu data) | — |
| `closed_bid` | (bid data) | — |
| `update_restaurant_is_open` | (bool) | — |

---

## 3. HTTP Endpoint Response Fields

These come from `GET` requests — parsed as JSON in our code.

### `GET /restaurants`
Returns array of objects per team:
| Field | Type |
|---|---|
| `id` | `int` |
| `name` | `str` |
| `balance` | `number` |
| `inventory` | `object` |
| `reputation` | `number` |
| `isOpen` | `bool` |
| `kitchen` | `object` |
| `menu` | `array` |
| `Received Messages` | `int` (observed in GAMEDATA, not in official docs) |

### `GET /restaurant/:id` (own restaurant only)
Same fields as above, for a single restaurant. Plus per-restaurant detail.

### `GET /restaurant/:id/menu`
Returns: array of menu item objects.

### `GET /recipes`
Array of recipe objects:
| Field | Type |
|---|---|
| `name` | `str` |
| `preparationTimeMs` | `int` |
| `ingredients` | `dict[str, int]` (ingredient → quantity) |
| `prestige` | `number` |

### `GET /meals?turn_id=<id>&restaurant_id=<id>`
Returns client orders:
| Field | Type |
|---|---|
| `client_id` | `str` (this is how we get client_id!) |
| `orderText` | `str` |
| `executed` | `bool` (true if already served) |

### `GET /bid_history?turn_id=<id>`
All closed bids from all teams for a given turn.

### `GET /market/entries`
Active and closed market entries:
| Field | Type |
|---|---|
| `side` | `"BUY"` or `"SELL"` |
| `ingredient_name` | `str` |
| `quantity` | `int` |
| `price` | `int` |
| (entry metadata) | expiration, team id, etc. |

---

## 4. Datapizza Framework — All Retrievable Types & Fields

### 4.1 `ClientResponse` — what the LLM returns

```python
from datapizza.core.clients import ClientResponse
```

| Field/Property | Type | Description |
|---|---|---|
| `content` | `list[Block]` | All response blocks |
| `delta` | `str \| None` | Streaming delta |
| `stop_reason` | `str \| None` | Why generation stopped |
| `usage` | `TokenUsage` | Token counts |
| `.text` | `str` | Concatenated text from all `TextBlock`s |
| `.first_text` | `str \| None` | First `TextBlock` content |
| `.function_calls` | `list[FunctionCallBlock]` | All tool calls |
| `.structured_data` | `list[StructuredBlock]` | All structured responses |
| `.thoughts` | `list[ThoughtBlock]` | All thinking blocks |
| `.is_pure_text()` | `bool` | Only text blocks? |
| `.is_pure_function_call()` | `bool` | Only function calls? |

### 4.2 Block Types — `datapizza.type`

| Class | Fields |
|---|---|
| **`TextBlock`** | `content: str`, `type="text"` |
| **`ThoughtBlock`** | `content: str`, `type="thought"` |
| **`FunctionCallBlock`** | `id: str`, `name: str`, `arguments: dict[str, Any]`, `tool: Tool`, `type="function"` |
| **`FunctionCallResultBlock`** | `id: str`, `tool: Tool`, `result: str`, `type="function_call_result"` |
| **`StructuredBlock`** | `content: BaseModel`, `type="structured"` |
| **`MediaBlock`** | `media: Media`, `type="media"` |

All blocks have: `to_dict() → dict`, `from_dict(data) → Block` (on parent class)

### 4.3 `Chunk` — the vectorstore data unit

```python
from datapizza.type import Chunk, DenseEmbedding, SparseEmbedding
```

| Field | Type | Default | Description |
|---|---|---|---|
| `id` | `str` | *required* | Unique identifier |
| `text` | `str` | *required* | Text content |
| `embeddings` | `list[Embedding]` | `[]` | Dense/sparse vectors |
| `metadata` | `dict` | `{}` | Arbitrary key-value metadata |

Embedding types:
- `DenseEmbedding(name: str, vector: list[float])`
- `SparseEmbedding(name: str, values: list[float], indices: list[int])`

### 4.4 `Memory` — conversation history

```python
from datapizza.memory import Memory
```

| Method | Signature | Returns |
|---|---|---|
| `add_turn` | `(blocks: list[Block] \| Block, role: ROLE)` | — |
| `add_to_last_turn` | `(block: Block)` | — |
| `new_turn` | `(role=ROLE.ASSISTANT)` | — |
| `clear` | `()` | — |
| `copy` | `()` | `Memory` |
| `iter_blocks` | `()` | iterator over all blocks |
| `to_dict` | `()` | `list[dict]` |
| `json_dumps` | `()` | `str` |
| `json_loads` | `(json_str: str)` | — |
| `__len__` | `()` | `int` (number of turns) |
| `__getitem__` | `(index)` | `Turn` |

`ROLE` enum: `ASSISTANT`, `USER`, `SYSTEM`, `TOOL`

### 4.5 `Tool` — function tool definition

```python
from datapizza.tools import Tool, tool
```

| Field | Type | Default |
|---|---|---|
| `func` | `callable \| None` | `None` |
| `name` | `str \| None` | `None` |
| `description` | `str \| None` | `None` |
| `end` | `bool` | `False` (marks tool as agent-terminating) |
| `properties` | `dict \| None` | JSON Schema properties |
| `required` | `list \| None` | Required param names |
| `strict` | `bool` | `False` |

Decorator: `@tool` converts a function into a `Tool` automatically.

### 4.6 `Agent` — autonomous reasoning loop

```python
from datapizza.agents import Agent, StepResult
```

Constructor:
| Field | Type | Default |
|---|---|---|
| `name` | `str` | *required* |
| `client` | `Client` | *required* |
| `system_prompt` | `str` | `"You are a helpful assistant."` |
| `tools` | `list[Tool]` | `None` |
| `max_steps` | `int` | `None` (unlimited) |
| `terminate_on_text` | `bool` | `True` |
| `stateless` | `bool` | `True` |
| `gen_args` | `dict[str, Any]` | `None` |
| `memory` | `Memory` | `None` |
| `stream` | `bool` | `None` |
| `can_call` | `list[Agent]` | `None` (multi-agent) |
| `planning_interval` | `int` | `0` |

Methods:
| Method | Returns |
|---|---|
| `run(task, tool_choice="auto")` | `StepResult \| None` |
| `a_run(task, tool_choice="auto")` | `StepResult \| None` |
| `stream_invoke(task)` | yields `ClientResponse \| StepResult \| Plan` |

`StepResult` fields:
| Field | Type |
|---|---|
| `.text` | `str` (concatenated text blocks) |
| `.content` | `list[Block]` |
| `.tools_used` | `list[FunctionCallBlock]` |
| `.usage` | `TokenUsage` |
| `.index` | `int` (step number) |

### 4.7 `MCPClient` — connecting to MCP servers

```python
from datapizza.tools.mcp_client import MCPClient
```

| Field | Type | Default |
|---|---|---|
| `url` | `str \| None` | — |
| `command` | `str \| None` | — |
| `headers` | `dict[str, str]` | `{}` |
| `args` | `list[str]` | `[]` |
| `env` | `dict[str, str]` | `{}` |
| `timeout` | `int` | `30` |

| Method | Returns |
|---|---|
| `list_tools()` | `list[Tool]` |
| `a_list_tools()` | `list[Tool]` (async) |
| `call_tool(name, args)` | `CallToolResult` (async) |
| `list_resources()` | `ListResourcesResult` (async) |
| `list_resource_templates()` | result (async) |
| `read_resource(uri)` | `ReadResourceResult` (async) |
| `list_prompts()` | `ListPromptsResult` |
| `get_prompt(name, args)` | `GetPromptResult` (async) |

Two modes:
- **Stateless** (HTTP): `MCPClient(url="...")` — each call opens/closes a session
- **Persistent** (stdio/stateful): `async with MCPClient(command="...") as client:` — session stays open

### 4.8 `Vectorstore` — storing and retrieving embeddings

```python
from datapizza.vectorstores.qdrant import QdrantVectorstore
from datapizza.core.vectorstore import VectorConfig, Distance
```

`VectorConfig`:
| Field | Type |
|---|---|
| `name` | `str` |
| `dimensions` | `int` |
| `format` | `EmbeddingFormat` (`DENSE` / `SPARSE`) |
| `distance` | `Distance` (`COSINE` / `EUCLID` / `DOT` / `MANHATTAN`) |

Common methods (Qdrant & Milvus):
| Method | Signature | Returns |
|---|---|---|
| `create_collection` | `(name, vector_config)` | — |
| `add` | `(chunk, collection_name)` | — |
| `search` | `(collection_name, query_vector, k=10, vector_name=None)` | `list[Chunk]` |
| `a_search` | async same | `list[Chunk]` |
| `retrieve` | `(collection_name, ids)` | `list[Chunk]` |
| `remove` | `(collection_name, ids)` | — |
| `dump_collection` | `(collection_name, page_size=100)` | `Generator[Chunk]` |
| `as_retriever` | `(**kwargs)` | `Retriever` (pipeline component) |

### 4.9 `TokenUsage`

| Field | Type |
|---|---|
| `prompt_tokens` | `int` |
| `completion_tokens` | `int` |
| `cached_tokens` | `int` |
| `thinking_tokens` | `int` |

### 4.10 `Node` — document tree structure

| Field | Type |
|---|---|
| `children` | `list[Node]` |
| `metadata` | `dict` |
| `node_type` | `NodeType` (SECTION, PARAGRAPH, DOCUMENT, SENTENCE, PAGE, TABLE, FIGURE) |
| `content` | `str \| None` (leaf) or computed from children |
| `id` | `UUID` (auto-generated) |
| `is_leaf` | `bool` (property) |

### 4.11 `Media`

| Field | Type |
|---|---|
| `extension` | `str \| None` |
| `media_type` | `"image"`, `"video"`, `"audio"`, `"pdf"` |
| `source_type` | `"url"`, `"base64"`, `"path"`, `"pil"`, `"raw"` |
| `source` | `Any` |
| `detail` | `str` (default `"high"`) |

---

## 5. Embedders

| Class | Package | Default model |
|---|---|---|
| `OpenAIEmbedder` | `datapizza.embedders.openai` | `text-embedding-ada-002` |
| `GoogleEmbedder` | `datapizza.embedders.google` | `models/embedding-001` |
| `CohereEmbedder` | `datapizza.embedders.cohere` | — |
| `FastEmbedder` | `datapizza.embedders.fastembedder` | local, no API |

All expose: `embed(text) → list[float]`, `a_embed(text) → list[float]`

Wrapped for pipelines: `ChunkEmbedder(client=embedder, embedding_name="name") → embed(list[Chunk]) → list[Chunk]`

---

## 6. Pipeline Types

### `IngestionPipeline`
Modules chain: `Parser → Splitter → Embedder → VectorStore`
- `run(file_path)` → `list[Chunk] | None`

### `DagPipeline`
DAG of modules connected by `connect(source, target, target_key)`:
- `run(data: dict)` → `dict` of results per node

### `FunctionalPipeline`
Fluent builder: `.run() → .then() → .then() → .execute()`

---

## 7. Practical Field Retrieval Patterns for Hackapizza

### Getting `client_id` (needed for `serve_dish`)
```python
# Option 1: From /meals endpoint
meals = requests.get(f"{BASE_URL}/meals?turn_id={turn}&restaurant_id=17", headers=h).json()
# Each meal has client_id, orderText, executed

# Option 2: Possibly from client_spawned event data
client_id = data.get("client_id")  # test at runtime — undocumented but referenced
```

### Getting ingredients/recipes
```python
recipes = requests.get(f"{BASE_URL}/recipes", headers=h).json()
# Each: {name, preparationTimeMs, ingredients: {name: qty}, prestige}
```

### Using framework Memory to track conversation with agents
```python
from datapizza.memory import Memory
from datapizza.type import ROLE, TextBlock

memory = Memory()
memory.add_turn(TextBlock(content="Game state: ..."), role=ROLE.USER)
# Pass to agent or client
response = await client.a_invoke("What should we cook?", memory=memory)
```

### Storing game data in vectorstore for RAG retrieval
```python
from datapizza.type import Chunk, DenseEmbedding
from datapizza.vectorstores.qdrant import QdrantVectorstore

vs = QdrantVectorstore(location=":memory:")
vs.create_collection("game_data", vector_config=[VectorConfig(name="emb", dimensions=1536)])

chunk = Chunk(
    id="recipe-carbonara",
    text="Carbonara: prep 5000ms, ingredients: pasta=2 guanciale=1 ...",
    metadata={"type": "recipe", "prestige": 8, "prep_ms": 5000},
    embeddings=[DenseEmbedding(name="emb", vector=embedding)]
)
vs.add(chunk, collection_name="game_data")

# Later retrieve
results = vs.search("game_data", query_vector=query_emb, k=5)
for r in results:
    print(r.text, r.metadata)  # All fields available
```

---

*End of reference. All framework types sourced from [datapizza-labs/datapizza-ai](https://github.com/datapizza-labs/datapizza-ai) main branch.*
