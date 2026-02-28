# Datapizza AI — API Reference: Types

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Type/block/ ===

# Blocks

## datapizza.type.Block

Abstract base class.

### Methods

```python
to_dict()  # abstractmethod
```

## datapizza.type.TextBlock

```python
TextBlock(content: str, type='text')
```

## datapizza.type.MediaBlock

```python
MediaBlock(media: Media, type='media')
```

## datapizza.type.ThoughtBlock

```python
ThoughtBlock(content: str, type='thought')
```

## datapizza.type.FunctionCallBlock

```python
FunctionCallBlock(
    id: str,
    arguments: dict[str, Any],
    name: str,
    tool: Tool,
    type='function'
)
```

## datapizza.type.FunctionCallResultBlock

```python
FunctionCallResultBlock(
    id: str,
    tool: Tool,
    result: str,
    type='function_call_result'
)
```

## datapizza.type.StructuredBlock

```python
StructuredBlock(content: BaseModel, type='structured')
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Type/chunk/ ===

# Chunk

## datapizza.type.Chunk

Dataclass. The fundamental data structure used throughout the RAG pipeline for text processing, embedding, and retrieval operations. Serializable.

### __init__

```python
__init__(
    id: str,
    text: str,
    embeddings: list[Embedding] = [],
    metadata: dict = {}
)
```

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| id | str | Unique identifier for the chunk. | required |
| text | str | The text content of the chunk. | required |
| embeddings | list[Embedding] | List of embeddings for the chunk. | [] |
| metadata | dict | Metadata associated with the chunk. | {} |

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Type/media/ ===

# Media

## datapizza.type.Media

### __init__

```python
__init__(
    *,
    extension=None,
    media_type: Literal['image', 'video', 'audio', 'pdf'],
    source_type: Literal['url', 'base64', 'path', 'pil', 'raw'],
    source: Any,
    detail="high"
)
```

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| extension | str \| None | The file extension. | None |
| media_type | Literal['image','video','audio','pdf'] | The type of media. | required |
| source_type | Literal['url','base64','path','pil','raw'] | The source type of the media. | required |
| source | Any | The source of the media. | required |
| detail | str | The detail level ("high", "low", "auto"). | "high" |

### Methods

```python
to_dict()
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Type/node/ ===

# Node

## datapizza.type.Node

### Properties

- `content` — Get the textual content of the node and its children.
- `is_leaf` — Returns True if the node has no children.

### __init__

```python
__init__(
    children=None,
    metadata=None,
    node_type=NodeType.SECTION,
    content=None
)
```

### Methods

```python
__eq__(other)
__hash__()
add_child(child)
remove_child(child)
```

## datapizza.type.MediaNode

Bases: `Node`

A media node in the document graph.

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Type/tool/ ===

# Tool

## datapizza.tools.Tool

### __init__

```python
__init__(
    func=None,
    name=None,
    description=None,
    end=False,
    properties=None,
    required=None,
    strict=False
)
```

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| func | callable \| None | The function to call. | None |
| name | str \| None | The name of the tool. | None |
| description | str \| None | The description of the tool. | None |
| end | bool | Whether the tool ends the conversation. | False |
| properties | dict \| None | The properties of the tool. | None |
| required | list \| None | The required properties of the tool. | None |
| strict | bool | Whether to use strict mode. | False |

### Methods

```python
to_dict()
```
