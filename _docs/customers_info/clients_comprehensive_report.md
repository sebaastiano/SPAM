# Comprehensive Clients Report — Hackapizza 2.0

**Team:** SPAM! (ID: 17)  
**Compiled:** February 28, 2026  
**Sources verified:** Hackapizza_instructions.md, api_reference.md, game_data_reference.md, vectorization_strategy.md, client_template.py, Datapizza AI documentation (API References + Guides)

---

## Table of Contents

1. [Game Clients (Restaurant Customers)](#1-game-clients-restaurant-customers)
   - [1.1 Client Archetypes](#11-client-archetypes)
   - [1.2 Client Lifecycle (Technical)](#12-client-lifecycle-technical)
   - [1.3 Intolerance System](#13-intolerance-system)
   - [1.4 Menu → Client Attraction](#14-menu--client-attraction)
   - [1.5 Client-Facing API & Events](#15-client-facing-api--events)
   - [1.6 Discrepancies Found During Verification](#16-discrepancies-found-during-verification)
   - [1.7 Strategic Implications for Client Handling](#17-strategic-implications-for-client-handling)
2. [Datapizza AI Framework Clients (LLM Clients)](#2-datapizza-ai-framework-clients-llm-clients)
   - [2.1 Available Client Implementations](#21-available-client-implementations)
   - [2.2 Base Client Class — Full Method Reference](#22-base-client-class--full-method-reference)
   - [2.3 ClientResponse Object](#23-clientresponse-object)
   - [2.4 Key Client Capabilities](#24-key-client-capabilities)
   - [2.5 ClientFactory](#25-clientfactory)
   - [2.6 OpenAILikeClient (Hackathon Primary)](#26-openailikeclient-hackathon-primary)
   - [2.7 Cache System](#27-cache-system)
   - [2.8 Integration with Agents & MCP](#28-integration-with-agents--mcp)
3. [How Both "Clients" Connect in Our Architecture](#3-how-both-clients-connect-in-our-architecture)

---

## 1. Game Clients (Restaurant Customers)

During the **serving phase** of each turn, virtual customers visit restaurants. They are called "clients" in the game. They are **archetypes** — not random — and your menu determines which types you attract.

### 1.1 Client Archetypes

There are exactly **4 client archetypes** defined in the official instructions:

| Archetype | Emoji | Time Tolerance | Budget | Quality Expectation | What They Reward |
|---|---|---|---|---|---|
| **Esploratore Galattico** | 🚀 | Low ("poco tempo") | Low ("poco budget") | Low ("purché sia commestibile") | Simple, cheap, very fast dishes |
| **Astrobarone** | 💰 | Very low ("pochissimo tempo") | High ("guarda poco al prezzo") | High ("pretende buoni piatti") | Quality + speed + status/prestige on the menu |
| **Saggi del Cosmo** | 🔭 | High ("tempo da perdere") | High ("badano poco al prezzo") | Very high ("ottimi piatti") | Prestigious recipes, rare ingredients, cultural/narrative coherence |
| **Famiglie Orbitali** | 👨‍👩‍👧‍👦 | High ("molto tempo") | Medium ("osservano prezzo e qualità") | Medium-high | Balance of cost vs value, curated but accessible, well-designed menu |

**Source:** Hackapizza_instructions.md, Section 8 — "I clienti: archetipi del Multiverso"

#### Key Observations Per Archetype

**Esploratore Galattico:**
- Lowest revenue potential per client
- Easiest to satisfy — any dish works as long as it's fast and cheap
- Best served with low-prestige, low-ingredient, fast-cooking recipes
- Ideal target: recipes with prestige 23–50, prep time ≤ 5s, 5 ingredients

**Astrobarone:**
- High revenue potential (price-insensitive) but demands speed
- Contradiction: wants quality AND fast service → need high-prestige + low-prep-time recipes
- Per statistical analysis: S-tier recipes (prestige 90–100) average only 7.4s prep time — these are ideal for Astrobarones
- Ideal target: prestige ≥ 80, prep time ≤ 6s

**Saggi del Cosmo:**
- Highest quality requirement — will not accept mediocre food
- Time-tolerant, so long prep times are acceptable
- Price-insensitive — high prices are fine
- Best served with top-prestige recipes using rare, high-Δ ingredients (Polvere di Crononite, Shard di Prisma Stellare, Lacrime di Andromeda)
- Ideal target: prestige ≥ 85, any prep time

**Famiglie Orbitali:**
- The "balanced" archetype — watches both price and quality
- Time-tolerant, so prep time is not a bottleneck
- Must find the sweet spot: good dishes at fair prices
- Ideal target: prestige 60–80, medium pricing

### 1.2 Client Lifecycle (Technical)

The complete lifecycle of a game client:

```
1. RESTAURANT IS OPEN + HAS MENU
   └── Makes the restaurant visible to incoming clients
   
2. SERVING PHASE BEGINS
   └── SSE event: game_phase_changed { phase: "serving" }
   
3. CLIENT ARRIVES
   └── SSE event: client_spawned {
         clientName: string,    // archetype name
         orderText: string      // natural language order (e.g., "I'd like a ...")
       }
   
4. PARSE THE ORDER
   └── orderText is natural language, must be interpreted
   └── client_template.py strips "I'd like a " / "I'd like " prefix
   └── Need to match to a recipe on your menu
   └── Must check intolerance compatibility
   
5. PREPARE THE DISH
   └── MCP tool: prepare_dish { dish_name: "Recipe Name" }
   └── Takes preparationTimeMs (3000ms–15000ms depending on recipe)
   └── SSE event on completion: preparation_complete { dish: "Recipe Name" }
   
6. SERVE THE DISH
   └── MCP tool: serve_dish { dish_name: "Recipe Name", client_id: "..." }
   └── client_id comes from the client_spawned event (see Section 1.6)
   
7. OUTCOME
   ├── SUCCESS: client pays the menu price → balance increases, reputation increases
   └── FAILURE (wrong dish / intolerance violation / not served):
       └── No payment, reputation damage
```

#### Time Sensitivity

- Each turn's serving phase has a **finite duration** (not fixed — follow SSE events)
- Preparation time is real: a 15s recipe blocks your kitchen for 15 seconds
- Multiple dishes can potentially be prepared in sequence within the serving window
- Faster recipes = more clients served = more revenue per turn

### 1.3 Intolerance System

**Source:** Hackapizza_instructions.md, Section 7

The instructions are deliberately vague about intolerance mechanics:

> *"Nel Multiverso, un errore alimentare non è solo un reclamo. Può essere un incidente diplomatico. O peggio."*

> *"Ignorare le intolleranze significa rischiare vite, reputazione e sanzioni federali."*

**What we know for certain:**
- Clients can have intolerances to specific ingredients
- Serving a dish containing an intolerance-triggering ingredient = **reputation loss + no payment**
- The instructions say "fai attenzione alle intolleranze dei clienti" but do NOT specify how intolerance info is communicated

**What is NOT explicitly documented:**
- Whether the `orderText` contains intolerance hints
- Whether the `clientName` encodes intolerance patterns (e.g., specific archetypes having predictable intolerances)
- The exact reputation penalty magnitude
- Whether there is an API to query client intolerances directly

**Implication:** Intolerance information must be inferred from the `orderText` field, the `clientName`, or possibly from context in the game lore. This is an area that needs empirical testing during game runs.

### 1.4 Menu → Client Attraction

The menu is the primary mechanism for determining which client archetypes visit your restaurant:

> *"Qual è il target del tuo ristorante? Tutto dipende dai piatti che avrai nel tuo menù!"*

**How it works:**
- **Low-priced menu** → attracts price-sensitive clients (Esploratori, Famiglie)
- **High-priced menu** → attracts price-insensitive clients (Astrobaroni, Saggi)
- **High-prestige dishes** → attracts quality-seekers (Astrobaroni, Saggi)
- **Balanced dishes** → attracts Famiglie Orbitali

**Critical rules:**
- A restaurant that is **closed** receives no clients
- A restaurant with **no menu** receives no clients
- Menu can be set during: `speaking`, `closed_bid`, `waiting` phases (NOT during `serving` or `stopped`)
- Menu is set via MCP tool `save_menu`: `{ items: [{ name: "Recipe Name", price: 100 }] }`

### 1.5 Client-Facing API & Events

#### SSE Events Related to Clients

| Event | When | Recipient | Payload Fields | Purpose |
|---|---|---|---|---|
| `client_spawned` | Serving phase | Your team only | `clientName`, `orderText` (+ likely `client_id`) | A new client has arrived at your restaurant |
| `preparation_complete` | Serving phase | Your team only | `dish` | A dish you started cooking is ready |

#### MCP Tools for Client Service

| Tool | Phase | Arguments | Description |
|---|---|---|---|
| `prepare_dish` | Serving only | `{ dish_name: string }` | Start cooking a dish. Fires `preparation_complete` when done |
| `serve_dish` | Serving only | `{ dish_name: string, client_id: string }` | Serve a ready dish to a specific client |

#### HTTP Endpoints for Client Data

| Endpoint | Method | Query Params | Returns |
|---|---|---|---|
| `/meals?turn_id=X&restaurant_id=17` | GET | `turn_id` (required), `restaurant_id` (required) | Array of client orders with `executed` boolean (true = already served) |

#### Example curl — Get meals for a turn

```bash
curl -s -H "x-api-key: dTpZhKpZ02-4ac2be8821b52df78bf06070" \
  "https://hackapizza.datapizza.tech/meals?turn_id=1&restaurant_id=17" | python3 -m json.tool
```

#### Example curl — Prepare a dish

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

#### Example curl — Serve a dish

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

### 1.6 Discrepancies Found During Verification

⚠️ **The following inconsistencies were found across sources and should be validated empirically:**

#### Discrepancy 1: `client_id` in `client_spawned` event

| Source | `client_spawned` fields listed |
|---|---|
| **Hackapizza_instructions.md** (official rules) | `clientName`, `orderText` — **NO** `client_id` |
| **api_reference.md** (team-compiled reference) | `clientName`, `orderText`, `client_id` |
| **serve_dish MCP tool** (requires) | `client_id` as a mandatory argument |

**Analysis:** The `serve_dish` tool requires a `client_id`, which must come from somewhere. It almost certainly comes from `client_spawned`, but the official instructions only list `clientName` and `orderText`. Our api_reference.md added `client_id` — likely discovered during testing or inferred from the `serve_dish` requirement. **Assume `client_id` IS present in the SSE payload** — it would be impossible to serve without it.

#### Discrepancy 2: `game_started` event payload

| Source | `game_started` payload |
|---|---|
| **Hackapizza_instructions.md** | `{}` (empty object) |
| **api_reference.md** | `turn_id` |
| **client_template.py** | `data.get("turn_id", 0)` — expects `turn_id` |

**Analysis:** The instructions say empty, but both the api_reference and the template code assume `turn_id` is present. Likely the instructions were simplified. The template defaulting to `0` provides safe fallback. **Treat `turn_id` as available but use defensive coding.**

#### Discrepancy 3: OpenAILikeClient response access

| Source | Response access |
|---|---|
| **Datapizza API Reference (OpenAILikeClient example)** | `response.content` |
| **Quick Start Guide (OpenAIClient example)** | `response.text` |
| **ClientResponse API** | Both `.text` (concatenated TextBlocks) and `.content` (raw List[Block]) are valid properties |

**Analysis:** Both work. `.text` returns a clean string. `.content` returns the raw block list. The OpenAILikeClient example used `.content` but `.text` is the preferred convenience property for simple text responses. **Use `.text` for string output, `.content` for structured access.**

### 1.7 Strategic Implications for Client Handling

Based on the statistical analysis (287 recipes, 62 ingredients) and game mechanics:

#### Optimal Recipe Selection Per Archetype

| Target Archetype | Prestige Range | Max Prep Time | Ingredients | Price Strategy |
|---|---|---|---|---|
| Esploratore Galattico | 23–50 | ≤ 5s | 5 (minimal) | Low |
| Astrobarone | ≥ 80 | ≤ 6s | 5–7 | High |
| Saggi del Cosmo | ≥ 85 | Any | 5–9 | High |
| Famiglie Orbitali | 60–80 | Any | 5–7 | Medium |

#### Key Statistical Insights for Client Strategy

1. **Prep time does NOT correlate positively with prestige** (Pearson r = −0.12). S-tier recipes (90–100) average only 7.4s — the fastest tier. This means high-quality service to Astrobaroni and Saggi is inherently efficient.

2. **Ingredient count weakly correlates with prestige** (r = 0.17). Many prestige-100 recipes have only 5 ingredients. Fewer ingredients = fewer bids needed = lower cost = better margins.

3. **High-Δ ingredients** to prioritize for premium clients:
   - Polvere di Crononite (+9.9 Δ, p=0.00)
   - Shard di Prisma Stellare (+8.8 Δ, p=0.01)
   - Lacrime di Andromeda (+8.3 Δ, p=0.02)
   - Essenza di Tachioni (+6.0 Δ, p=0.04)

4. **Revenue flywheel (from strategy doc):**
   ```
   Serve correctly → Reputation ↑ → Better archetypes (Astrobaroni, Saggi) → Higher revenue per client → More bidding power → Better ingredients → Better dishes → (repeat)
   ```

5. **Throughput matters:** During a finite serving window, the number of clients you can serve is bounded by dish prep times. Prioritizing recipes ≤ 5s lets you potentially serve 3× more clients than a single 15s recipe.

#### Top 5 Recipes for Astrobarone/Saggi Clients (Fast + High Prestige)

| Recipe | Prestige | Prep Time | Ingredients |
|---|---|---|---|
| Sinfonia del Multiverso Calante | 85 | 3.97s | 5 |
| Eterea Sinfonia di Gravità con Infusione Temporale | 84 | 3.46s | 6 |
| Sinfonia del Multiverso Nascente | 84 | 3.80s | 6 |
| Sinfonia Cosmica di Proteine Interstellari | 77 | 3.04s | 5 |
| Sinfonia Temporale di Fenice e Xenodonte su Pane degli Abissi... | 95 | 4.05s | 5 |

#### Top 3 Recipes for Maximum Prestige (Saggi del Cosmo)

| Recipe | Prestige | Prep Time | Ingredients |
|---|---|---|---|
| Portale Cosmico: Sinfonia di Gnocchi del Crepuscolo... | 100 | 5.22s | 5 |
| Sinfonia Cosmica del Multiverso | 100 | 5.64s | 7 |
| Sinfonia Astrale — Risotto Multiversale con Risacca Celeste | 100 | 9.97s | 9 |

---

## 2. Datapizza AI Framework Clients (LLM Clients)

The Datapizza AI framework provides a unified client abstraction for calling LLMs. These are the software components used to build the restaurant agent.

### 2.1 Available Client Implementations

| Client Class | Full Path | Package | Default Model | Key Difference |
|---|---|---|---|---|
| `OpenAIClient` | `datapizza.clients.openai.OpenAIClient` | `datapizza-ai-clients-openai` | `gpt-4o-mini` | Uses OpenAI Responses API |
| `GoogleClient` | `datapizza.clients.google.GoogleClient` | `datapizza-ai-clients-google` | `gemini-2.0-flash` | Supports Vertex AI via `use_vertexai=True` |
| `AnthropicClient` | `datapizza.clients.anthropic.AnthropicClient` | `datapizza-ai-clients-anthropic` | `claude-3-5-sonnet-latest` | Supports `thinking` parameter |
| `MistralClient` | `datapizza.clients.mistral.MistralClient` | `datapizza-ai-clients-mistral` | `mistral-large-latest` | Simple API key + model |
| `OpenAILikeClient` | `datapizza.clients.openai_like.OpenAILikeClient` | `datapizza-ai-clients-openai-like` | (user-specified) | Uses Chat Completions API; compatible with Ollama, Regolo.ai, etc. |

All clients inherit from the abstract base class `datapizza.core.clients.client.Client` (which extends `ChainableProducer`).

#### Constructor Parameters by Client

**OpenAIClient** (most parameters):
```python
OpenAIClient(
    api_key,                    # required
    model="gpt-4o-mini",
    system_prompt="",
    temperature=None,
    cache=None,
    base_url=None,
    organization=None,
    project=None,
    webhook_secret=None,
    websocket_base_url=None,
    timeout=None,
    max_retries=2,
    default_headers=None,
    default_query=None,
    http_client=None,
)
```

**GoogleClient**:
```python
GoogleClient(
    api_key=None,
    model="gemini-2.0-flash",
    system_prompt="",
    temperature=None,
    cache=None,
    project_id=None,            # Vertex AI
    location=None,              # Vertex AI
    credentials_path=None,      # Vertex AI
    use_vertexai=False,
)
```

**AnthropicClient**:
```python
AnthropicClient(
    api_key,                    # required
    model="claude-3-5-sonnet-latest",
    system_prompt="",
    temperature=None,
    cache=None,
)
```

**MistralClient**:
```python
MistralClient(
    api_key,                    # required
    model="mistral-large-latest",
    system_prompt="",
    temperature=None,
    cache=None,
)
```

**OpenAILikeClient** (inferred from usage — same base as OpenAIClient):
```python
OpenAILikeClient(
    api_key,
    model,
    base_url,                   # required for non-OpenAI providers
    system_prompt="",
    temperature=None,
    cache=None,
    # ... inherits other OpenAI-style params
)
```

#### Common Constructor Parameters (All Clients)

| Parameter | Type | Description | Default |
|---|---|---|---|
| `api_key` | `str` | Provider API key | required (None for Google) |
| `model` | `str` | Model identifier | provider-specific |
| `system_prompt` | `str` | System-level instructions | `""` |
| `temperature` | `float \| None` | Randomness control (0–2) | `None` |
| `cache` | `Cache \| None` | Cache instance for deduplication | `None` |

### 2.2 Base Client Class — Full Method Reference

All methods below are available on every client implementation:

#### Synchronous Methods

| Method | Signature | Returns | Description |
|---|---|---|---|
| `invoke` | `(input, tools=None, memory=None, tool_choice="auto", temperature=None, max_tokens=None, system_prompt=None, **kwargs)` | `ClientResponse` | Single inference request |
| `stream_invoke` | Same as `invoke` | `Iterator[ClientResponse]` | Streams response token-by-token |
| `structured_response` | `(*, input, output_cls, memory=None, temperature=None, max_tokens=None, system_prompt=None, tools=None, tool_choice="auto", **kwargs)` | `ClientResponse` | Returns structured Pydantic output |
| `embed` | `(text, model_name=None, **kwargs)` | `list[float]` | Generate text embeddings |

#### Asynchronous Methods

| Method | Signature | Returns | Description |
|---|---|---|---|
| `a_invoke` | Same as `invoke` | `ClientResponse` | Async single inference |
| `a_stream_invoke` | Same as `invoke` | `AsyncIterator[ClientResponse]` | Async streaming |
| `a_structured_response` | Same as `structured_response` | `ClientResponse` | Async structured response |
| `a_embed` | Same as `embed` | `list[float] \| list[list[float]]` | Async embeddings |

#### Key Parameter Details

| Parameter | Type | Description | Default |
|---|---|---|---|
| `input` | `str \| list[Block]` | Text prompt or multimodal blocks | required |
| `tools` | `List[Tool] \| None` | Tools the model can call | `None` |
| `memory` | `Memory \| None` | Conversation history | `None` |
| `tool_choice` | `str \| list[str]` | `"auto"`, `"required"`, `"none"`, or `["tool_name"]` | `"auto"` |
| `temperature` | `float \| None` | Overrides constructor temperature | `None` |
| `max_tokens` | `int \| None` | Max response tokens | `None` |
| `system_prompt` | `str \| None` | Overrides constructor system_prompt | `None` |
| `output_cls` | `Type[BaseModel]` | Pydantic model for structured output | required (structured_response only) |

### 2.3 ClientResponse Object

`datapizza.core.clients.ClientResponse` — the universal return type from all client methods.

#### Constructor Parameters

| Name | Type | Description | Default |
|---|---|---|---|
| `content` | `List[Block]` | Ordered list of response blocks | required |
| `delta` | `str` | Streaming chunk text | `None` |
| `usage` | `TokenUsage` | Token usage stats | `None` |
| `stop_reason` | `str` | Why generation stopped | `None` |

#### Properties

| Property | Returns | Description |
|---|---|---|
| `.text` | `str` | Concatenated text from all `TextBlock`s |
| `.first_text` | `str \| None` | Content of the first `TextBlock` only |
| `.content` | `List[Block]` | Raw ordered list of all blocks |
| `.function_calls` | `List[FunctionCallBlock]` | All function calls in order |
| `.structured_data` | `List[StructuredBlock]` | All structured data in order |
| `.thoughts` | `List[ThoughtBlock]` | All thought/reasoning blocks |
| `.delta` | `str` | Streaming delta (for streaming responses) |
| `.usage` | `TokenUsage` | Token usage with `.completion_tokens_used`, `.prompt_tokens_used`, `.cached_tokens_used` |
| `.stop_reason` | `str` | Stop reason string |

#### Methods

| Method | Returns | Description |
|---|---|---|
| `.is_pure_text()` | `bool` | True if response contains only `TextBlock`s |
| `.is_pure_function_call()` | `bool` | True if response contains only `FunctionCallBlock`s |

#### Block Types (content elements)

| Block Type | Fields | Description |
|---|---|---|
| `TextBlock` | `content: str` | Plain text output |
| `MediaBlock` | `media: Media` | Image/PDF/audio response |
| `ThoughtBlock` | `content: str` | Reasoning/thinking content |
| `FunctionCallBlock` | `id: str, arguments: dict, name: str, tool: Tool` | Model requesting a tool call |
| `FunctionCallResultBlock` | `id: str, tool: Tool, result: str` | Result from executing a tool call |
| `StructuredBlock` | `content: BaseModel` | Pydantic model instance |

### 2.4 Key Client Capabilities

#### 2.4.1 Memory (Conversation History)

```python
from datapizza.memory import Memory
from datapizza.type import ROLE, TextBlock

memory = Memory()

# Invoke with memory context
response = client.invoke("My name is Alice", memory=memory)

# Update memory after each turn
memory.add_turn(TextBlock(content="My name is Alice"), role=ROLE.USER)
memory.add_turn(response.content, role=ROLE.ASSISTANT)

# Subsequent invocations remember context
response2 = client.invoke("What's my name?", memory=memory)
```

#### 2.4.2 Tool Calling

```python
from datapizza.tools import tool

@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    return f"Sunny in {location}"

response = client.invoke("What's the weather?", tools=[get_weather])

# Execute returned tool calls
for fc in response.function_calls:
    result = fc.tool(**fc.arguments)
```

**Tool choice options:**
| Value | Behavior |
|---|---|
| `"auto"` | Model decides whether to use tools (default) |
| `"required"` | Model must use a tool |
| `"none"` | Model cannot use tools |
| `["tool_name"]` | Force specific tool |

#### 2.4.3 Structured Responses

```python
from pydantic import BaseModel

class Person(BaseModel):
    name: str
    age: int

response = client.structured_response(input="Create a profile", output_cls=Person)
person = response.structured_data[0]  # Person instance
```

#### 2.4.4 Streaming

```python
# Synchronous
for chunk in client.stream_invoke("Write a story"):
    if chunk.delta:
        print(chunk.delta, end="", flush=True)

# Asynchronous
async for chunk in client.a_stream_invoke("Write a story"):
    if chunk.delta:
        print(chunk.delta, end="", flush=True)
```

#### 2.4.5 Multimodality

Supported media types:

| Type | Formats | Sources |
|---|---|---|
| Images | PNG, JPEG, GIF, WebP | file path, URL, base64, PIL, raw |
| PDFs | PDF | file path, base64 |
| Audio | MP3, etc. | file path (Google client only for inline audio) |

```python
from datapizza.type import Media, MediaBlock, TextBlock

image = Media(media_type="image", source_type="path", source="photo.png", extension="png")

response = client.invoke(
    input=[TextBlock(content="Describe this image"), MediaBlock(media=image)],
    max_tokens=200
)
```

#### 2.4.6 Provider-Specific Reasoning/Thinking

**OpenAI** (reasoning):
```python
client.invoke("Solve this", reasoning={"effort": "low", "summary": "auto"})
```

**Anthropic** (extended thinking):
```python
client.invoke("Solve this", thinking={"type": "enabled", "budget_tokens": 1024})
```

### 2.5 ClientFactory

`datapizza.clients.factory.ClientFactory` — creates clients without importing each provider individually.

```python
from datapizza.clients.factory import ClientFactory, Provider

client = ClientFactory.create(
    provider=Provider.OPENAI,   # or "openai", "google", "anthropic", "mistral"
    api_key="...",
    model="gpt-4",
    system_prompt="You are helpful",
    temperature=0.7
)
```

**Supported providers:** `openai`, `google`, `anthropic`, `mistral`

### 2.6 OpenAILikeClient (Hackathon Primary)

This is the client we must use for the hackathon, since the inference provider is **Regolo.ai**.

**Key difference from OpenAIClient:** Uses the **Chat Completions API** (not the Responses API). This makes it compatible with any OpenAI-compatible provider (Ollama, Regolo.ai, vLLM, etc.).

#### Hackathon Setup

```python
from datapizza.clients.openai_like import OpenAILikeClient
import os

client = OpenAILikeClient(
    api_key=os.getenv("REGOLO_API_KEY"),
    model="gpt-oss-120b",
    base_url="https://api.regolo.ai/v1",
)
```

#### Available Models (Regolo.ai)

| Model | Notes |
|---|---|
| `gpt-oss-120b` | Primary large model |
| `gpt-oss-20b` | Smaller/faster model |
| `qwen3-vl-32b` | Vision-language model |

Full list: [regolo.ai/models-library](https://regolo.ai/models-library/)

#### Local Model Setup (Ollama)

```python
client = OpenAILikeClient(
    api_key="",                                    # Ollama doesn't require a key
    model="gemma2:2b",
    base_url="http://localhost:11434/v1",
    system_prompt="You are a helpful assistant.",
)
```

### 2.7 Cache System

`datapizza.core.cache.cache.Cache` — abstract base class for caching client results.

When attached to a client, it automatically stores results of method calls. If the same method is invoked with identical arguments, the cached result is returned instead of re-executing.

**Interface:**
```python
class Cache(ABC):
    @abstractmethod
    def get(self, key: str) -> object: ...

    @abstractmethod
    def set(self, key: str, value: str) -> None: ...
```

**Usage:**
```python
client = OpenAIClient(api_key="...", cache=my_cache_instance)
# Duplicate calls with same args → cached result returned
```

### 2.8 Integration with Agents & MCP

#### Agent Integration

The `Client` is the core dependency of any `Agent`:

```python
from datapizza.agents import Agent

agent = Agent(
    name="my_agent",
    client=client,                  # any Client subclass
    system_prompt="...",
    tools=[...],
    max_steps=10,
    terminate_on_text=True,         # stop when client returns plain text
    memory=memory,
    stream=False,
    planning_interval=0
)

result = agent.run("task", tool_choice="required_first")
```

**Agent tool_choice values:**
| Value | Behavior |
|---|---|
| `"auto"` | Model decides at every step |
| `"required"` | Must use a tool every step |
| `"required_first"` | Must use a tool on step 1, then auto |
| `"none"` | No tools |
| `["tool_name"]` | Force specific tool |

#### MCP Integration (Game Server)

```python
from datapizza.tools.mcp_client import MCPClient

mcp_client = MCPClient(
    url="https://hackapizza.datapizza.tech/mcp",
    headers={"x-api-key": "dTpZhKpZ02-4ac2be8821b52df78bf06070"}
)
tools = mcp_client.list_tools()

agent = Agent(name="game_agent", client=client, tools=tools)
```

The MCPClient parameters:

| Parameter | Type | Description |
|---|---|---|
| `url` | `str` | MCP server URL |
| `command` | `str \| None` | Command to run MCP server |
| `headers` | `dict \| None` | HTTP headers (for auth) |
| `args` | `list[str] \| None` | Server arguments |
| `env` | `dict \| None` | Environment variables |
| `timeout` | `int` | Connection timeout (default 30) |

---

## 3. How Both "Clients" Connect in Our Architecture

The word "clients" in this project refers to two distinct things that are tightly interlinked:

```
┌─────────────────────────────────────────────────────────┐
│                  OUR AGENT SYSTEM                        │
│                                                         │
│  ┌──────────────────┐     ┌──────────────────────────┐  │
│  │ LLM Client       │     │ MCP Client               │  │
│  │ (OpenAILikeClient│     │ (Hackapizza server tools) │  │
│  │  + Regolo.ai)    │     │                          │  │
│  └────────┬─────────┘     └────────────┬─────────────┘  │
│           │                            │                │
│           ▼                            ▼                │
│  ┌──────────────────────────────────────────────────┐   │
│  │                  AGENT                            │   │
│  │  Uses LLM Client for reasoning/parsing            │   │
│  │  Uses MCP tools for game actions                  │   │
│  └──────────────────────────┬───────────────────────┘   │
│                             │                           │
└─────────────────────────────┼───────────────────────────┘
                              │
                              ▼
            ┌─────────────────────────────────┐
            │     HACKAPIZZA GAME SERVER       │
            │                                 │
            │  SSE Stream ← client_spawned    │
            │              (game clients      │
            │               arrive here)      │
            │                                 │
            │  MCP ← prepare_dish, serve_dish │
            │         (we serve game clients) │
            └─────────────────────────────────┘
```

**The flow:**
1. **Game clients** (Esploratore, Astrobarone, Saggi, Famiglie) arrive via SSE `client_spawned` events
2. The **LLM client** (OpenAILikeClient → Regolo.ai) parses their `orderText` into a concrete dish match
3. The **Agent** decides what to cook based on available ingredients, menu, and intolerance constraints
4. **MCP tools** (`prepare_dish`, `serve_dish`) execute the cooking and serving
5. Revenue flows in, reputation changes, and the cycle repeats

**Critical performance note:** Per the strategy document, the LLM client should NOT be in the hot path during serving. The order → dish mapping should be pre-computed or use a fast lookup, with the LLM only used for ambiguous/novel orders. This prevents client timeouts from LLM latency.

---

*End of report. All information verified against primary sources in the workspace. Discrepancies documented in Section 1.6.*
