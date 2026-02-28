# Datapizza AI — API Reference: Vectorstores & Memory

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Vectorstore/milvus_vectorstore/ ===

# MilvusVectorstore

## Installation

```
pip install datapizza-ai-vectorstores-milvus
```

## datapizza.vectorstores.milvus.MilvusVectorstore

Connect via `host/port` OR `uri` (Milvus Lite: `uri="./milvus.db"`).

### Methods

#### create_collection

```python
create_collection(collection_name, vector_config)
```

#### add

```python
add(chunks, collection_name)
```

#### a_add (async)

```python
a_add(chunks, collection_name)
```

#### search

```python
search(collection_name, query_vector, vector_name, k=5)
```

#### a_search (async)

```python
a_search(collection_name, query_vector, vector_name, k=5)
```

#### retrieve

```python
retrieve(collection_name, ids)
```

#### update

```python
update(collection_name, chunk)
```

#### remove

```python
remove(collection_name, ids)
```

#### dump_collection

```python
dump_collection(collection_name, page_size=100)
```

#### get_collections

```python
get_collections()
```

#### delete_collection

```python
delete_collection(collection_name)
```

## Usage Examples

### Basic Setup

```python
from datapizza.vectorstores.milvus import MilvusVectorstore

# Milvus Lite (local file)
vs = MilvusVectorstore(uri="./milvus.db")

# Remote Milvus
vs = MilvusVectorstore(host="localhost", port=19530)
```

### Add / Search

```python
from datapizza.type import Chunk, DenseEmbedding
import uuid

vector_config = {
    "dense_embeddings": {"dim": 1536, "metric_type": "COSINE"}
}
vs.create_collection("my_collection", vector_config)

chunk = Chunk(
    id=str(uuid.uuid4()),
    text="Hello, world!",
    embeddings=[DenseEmbedding(name="dense_embeddings", vector=[0.1] * 1536)]
)
vs.add([chunk], "my_collection")

results = vs.search("my_collection", [0.1] * 1536, "dense_embeddings", k=5)
```

### Retrieve / Update / Remove

```python
retrieved = vs.retrieve("my_collection", [chunk.id])
vs.update("my_collection", chunk)
vs.remove("my_collection", [chunk.id])
```

### Async API

```python
import asyncio

async def main():
    await vs.a_add([chunk], "my_collection")
    results = await vs.a_search("my_collection", [0.1] * 1536, "dense_embeddings")

asyncio.run(main())
```

### Multi-Vector (Dense + Sparse)

```python
from datapizza.type import DenseEmbedding, SparseEmbedding

vector_config = {
    "dense_embeddings": {"dim": 1536, "metric_type": "COSINE"},
    "bm25_embeddings": {"metric_type": "BM25"}
}
vs.create_collection("multi_vector_collection", vector_config)

chunk = Chunk(
    id=str(uuid.uuid4()),
    text="Machine learning is fascinating",
    embeddings=[
        DenseEmbedding(name="dense_embeddings", vector=[0.1] * 1536),
        SparseEmbedding(name="bm25_embeddings", vector={0: 0.5, 1: 0.3})
    ]
)
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Vectorstore/qdrant_vectorstore/ ===

# QdrantVectorstore

## Installation

```
pip install datapizza-ai-vectorstores-qdrant
```

## datapizza.vectorstores.qdrant.QdrantVectorstore

Bases: `Vectorstore`

### __init__

```python
__init__(host=None, port=6333, api_key=None, **kwargs)
```

Also supports: `QdrantVectorstore(location=":memory:")`

### Methods

#### create_collection

```python
create_collection(collection_name, vector_config, **kwargs)
```

#### add

```python
add(chunk, collection_name)
```

#### search

```python
search(collection_name, query_vector, k=10, vector_name=None, **kwargs) -> list[Chunk]
```

#### a_search (async)

```python
a_search(collection_name, query_vector, k=10, vector_name=None, **kwargs) -> list[Chunk]
```

#### retrieve

```python
retrieve(collection_name, ids, **kwargs)
```

#### remove

```python
remove(collection_name, ids, **kwargs)
```

#### delete_collection

```python
delete_collection(collection_name, **kwargs)
```

#### dump_collection

```python
dump_collection(collection_name, page_size=100, with_vectors=False)
```

#### get_collections

```python
get_collections()
```

## Usage Example

```python
from datapizza.vectorstores.qdrant import QdrantVectorstore
from datapizza.type import Chunk, DenseEmbedding, VectorConfig
import uuid

vs = QdrantVectorstore(location=":memory:")

vector_config = VectorConfig(size=1536, distance="Cosine")
vs.create_collection("my_collection", vector_config)

chunk = Chunk(
    id=str(uuid.uuid4()),
    text="Hello, world!",
    embeddings=[DenseEmbedding(name="dense", vector=[0.1] * 1536)]
)
vs.add(chunk, "my_collection")

results = vs.search("my_collection", [0.1] * 1536, k=5)
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/memory/ ===

# Memory

## datapizza.memory.memory.Memory

### Methods

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
