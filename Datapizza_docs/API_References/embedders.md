# Datapizza AI — API Reference: Embedders

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Embedders/chunk_embedder/ ===

# ChunkEmbedder

## datapizza.embedders.ChunkEmbedder

Bases: `PipelineComponent`

### __init__

```python
__init__(
    client,
    model_name=None,
    embedding_name=None,
    batch_size=2047,
)
```

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| client | BaseEmbedder | The embedder client to use. | required |
| model_name | str \| None | The model name to use. | None |
| embedding_name | str \| None | The embedding name to use. | None |
| batch_size | int | The batch size to use. | 2047 |

### embed

```python
embed(nodes: list[Chunk]) -> list[Chunk]
```

### a_embed (async)

```python
a_embed(nodes: list[Chunk]) -> list[Chunk]
```

## Usage Example

```python
from datapizza.embedders import ChunkEmbedder
from datapizza.embedders.openai import OpenAIEmbedder
from datapizza.type import Chunk
import uuid

embedder_client = OpenAIEmbedder(api_key="your-openai-api-key")
embedder = ChunkEmbedder(
    client=embedder_client,
    embedding_name="dense_embeddings"
)

chunks = [
    Chunk(id=str(uuid.uuid4()), text="Hello, world!"),
    Chunk(id=str(uuid.uuid4()), text="Another chunk of text."),
]

embedded_chunks = embedder.embed(chunks)
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Embedders/cohere_embedder/ ===

# CohereEmbedder

## Installation

```
pip install datapizza-ai-embedders-cohere
```

## datapizza.embedders.cohere.CohereEmbedder

Bases: `BaseEmbedder`

### __init__

```python
__init__(
    api_key,
    base_url=None,
    input_type="search_document",
)
```

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| api_key | str | The API key for the Cohere API. | required |
| base_url | str \| None | The base URL for the Cohere API. | None |
| input_type | str | The input type ("search_document" or "search_query"). | "search_document" |

### embed

```python
embed(text_or_list, model_name)
```

### a_embed (async)

```python
a_embed(text_or_list, model_name)
```

## Examples

### Basic Usage

```python
from datapizza.embedders.cohere import CohereEmbedder

embedder = CohereEmbedder(api_key="your-cohere-api-key")
embeddings = embedder.embed("Hello, world!")
```

### Search Query

```python
embedder = CohereEmbedder(
    api_key="your-cohere-api-key",
    input_type="search_query"
)
embeddings = embedder.embed("What is machine learning?")
```

### Batch

```python
texts = ["First document", "Second document", "Third document"]
embeddings = embedder.embed(texts)
```

### Async

```python
import asyncio

async def main():
    embeddings = await embedder.a_embed("Hello, world!")

asyncio.run(main())
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Embedders/fast_embedder/ ===

# FastEmbedder

## Installation

```
pip install datapizza-ai-embedders-fastembedder
```

## datapizza.embedders.fastembedder.FastEmbedder

Bases: `BaseEmbedder`

Produces **sparse** embeddings; runs locally (no API calls).

## Usage Example

```python
from datapizza.embedders.fastembedder import FastEmbedder

embedder = FastEmbedder(
    model_name="Qdrant/bm25",
    embedding_name="bm25_embeddings"
)

embeddings = embedder.embed(["Hello world", "Another text"])
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Embedders/google_embedder/ ===

# GoogleEmbedder

## Installation

```
pip install datapizza-ai-embedders-google
```

## datapizza.embedders.google.GoogleEmbedder

Bases: `BaseEmbedder`

### __init__

```python
__init__(api_key)
```

### embed

```python
embed(text, model_name="models/embedding-001")
```

### a_embed (async)

```python
a_embed(text, model_name="models/embedding-001")
```

## Usage Example

```python
from datapizza.embedders.google import GoogleEmbedder

embedder = GoogleEmbedder(api_key="your-google-api-key")
embedding = embedder.embed("Hello, world!")
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Embedders/ollama_embedder/ ===

# OllamaEmbedder

Not a separate class — uses `OpenAIEmbedder` with a custom `base_url`.

## Usage Example

```python
from datapizza.embedders.openai import OpenAIEmbedder

embedder = OpenAIEmbedder(
    api_key="",
    base_url="http://localhost:11434/v1",
    model_name="nomic-embed-text"
)
embedding = embedder.embed("Hello, world!")
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Embedders/openai_embedder/ ===

# OpenAIEmbedder

## datapizza.embedders.openai.OpenAIEmbedder

Bases: `BaseEmbedder`

### __init__

```python
__init__(api_key, base_url=None)
```

### embed

```python
embed(text, model_name="text-embedding-ada-002")
```

### a_embed (async)

```python
a_embed(text, model_name="text-embedding-ada-002")
```

## Usage Example

```python
from datapizza.embedders.openai import OpenAIEmbedder

embedder = OpenAIEmbedder(api_key="your-openai-api-key")
embedding = embedder.embed("Hello, world!")
```
