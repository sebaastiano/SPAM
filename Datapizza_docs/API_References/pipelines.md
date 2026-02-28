# Datapizza AI — API Reference: Pipelines

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Pipelines/dag/ ===

# DagPipeline

## datapizza.pipeline.dag_pipeline.DagPipeline

A pipeline that runs a dependency graph of nodes.

### Methods

#### run

```python
run(data: dict) -> dict
```

#### a_run (async)

```python
a_run(data: dict) -> dict
```

#### add_module

```python
add_module(node_name: str, node: PipelineComponent)
```

#### connect

```python
connect(
    source_node: str,
    target_node: str,
    target_key: str,
    source_key: str = None
)
```

#### from_yaml (classmethod)

```python
from_yaml(config_path: str) -> DagPipeline
```

## Usage Example

```python
from datapizza.pipeline.dag_pipeline import DagPipeline

pipeline = DagPipeline()
pipeline.add_module("parser", text_parser)
pipeline.add_module("splitter", splitter)
pipeline.connect("parser", "splitter", target_key="node", source_key=None)

result = pipeline.run({"text": "Hello, world!"})
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Pipelines/functional/ ===

# FunctionalPipeline

## datapizza.pipeline.functional_pipeline.FunctionalPipeline

Pipeline for executing a series of nodes with dependencies.

### Methods

#### run

```python
run(
    name: str,
    node: PipelineComponent,
    dependencies=None,
    kwargs=None
) -> FunctionalPipeline
```

#### then

```python
then(
    name: str,
    node: PipelineComponent,
    target_key: str,
    dependencies=None,
    kwargs=None
) -> FunctionalPipeline
```

#### branch

```python
branch(
    condition: Callable,
    if_true: FunctionalPipeline,
    if_false: FunctionalPipeline,
    dependencies=None
) -> FunctionalPipeline
```

#### foreach

```python
foreach(
    name: str,
    do: PipelineComponent,
    dependencies=None
) -> FunctionalPipeline
```

#### execute

```python
execute(
    initial_data: dict = None,
    context: dict = None
) -> dict
```

#### get

```python
get(name: str) -> FunctionalPipeline
```

#### from_yaml (staticmethod)

```python
from_yaml(yaml_path: str) -> FunctionalPipeline
```

Raises: `ValueError`, `KeyError`, `FileNotFoundError`, `YAMLError`, `ImportError`, `AttributeError`

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Pipelines/ingestion/ ===

# IngestionPipeline

## datapizza.pipeline.pipeline.IngestionPipeline

A pipeline for ingesting data into a vector store.

### __init__

```python
__init__(
    modules: list[PipelineComponent] = None,
    vector_store: Vectorstore = None,
    collection_name: str = None
)
```

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| modules | list[PipelineComponent] \| None | The modules to use. | None |
| vector_store | Vectorstore \| None | The vector store to use. | None |
| collection_name | str \| None | The collection name to use. | None |

### Methods

#### run

```python
run(
    file_path: str | list[str],
    metadata: dict = None
) -> list[Chunk] | None
```

Returns chunks if no `vector_store` is set, else `None` after storing.

#### a_run (async)

```python
a_run(
    file_path: str | list[str],
    metadata: dict = None
) -> list[Chunk] | None
```

#### from_yaml (classmethod)

```python
from_yaml(config_path: str) -> IngestionPipeline
```

## Usage Example

```python
from datapizza.pipeline.pipeline import IngestionPipeline
from datapizza.modules.parsers import TextParser
from datapizza.modules.splitters import RecursiveSplitter

pipeline = IngestionPipeline(
    modules=[TextParser(), RecursiveSplitter(max_char=500)],
    vector_store=vs,
    collection_name="my_collection"
)

pipeline.run("document.pdf")
```
