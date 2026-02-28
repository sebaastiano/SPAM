# Datapizza AI — Complete API Reference (v0.0.9)

All 42 documentation pages scraped from http://docs.datapizza.ai/0.0.9/

---

## Files in this reference

| File | URLs Covered |
|------|-------------|
| [clients.md](API_References/clients.md) | URLs 1–5: OpenAI, Google, Anthropic, Mistral, OpenAI-Like clients |
| [embedders.md](API_References/embedders.md) | URLs 6–11: ChunkEmbedder, CohereEmbedder, FastEmbedder, GoogleEmbedder, OllamaEmbedder, OpenAIEmbedder |
| [vectorstores_memory.md](API_References/vectorstores_memory.md) | URLs 12–14: MilvusVectorstore, QdrantVectorstore, Memory |
| [types.md](API_References/types.md) | URLs 15–19: Blocks, Chunk, Media, Node, Tool |
| [pipelines.md](API_References/pipelines.md) | URLs 20–22: DagPipeline, FunctionalPipeline, IngestionPipeline |
| [modules.md](API_References/modules.md) | URLs 23–37: Modules overview, all Parsers, Treebuilder, Captioners, all Splitters, Metatagger, Rewriters, Rerankers, ChatPromptTemplate |
| [tools.md](API_References/tools.md) | URLs 38–42: MCPClient, DuckDuckGo, FileSystem, SQLDatabase, WebFetch |

---

## Quick Index

### Clients
- `datapizza.clients.openai.OpenAIClient` — model default: `gpt-4o-mini`
- `datapizza.clients.google.GoogleClient` — model default: `gemini-2.0-flash`
- `datapizza.clients.anthropic.AnthropicClient` — model default: `claude-3-5-sonnet-latest`
- `datapizza.clients.mistral.MistralClient` — model default: `mistral-large-latest`
- `datapizza.clients.openai_like.OpenAILikeClient` — chat completions API, Ollama-compatible

### Embedders
- `datapizza.embedders.ChunkEmbedder` — wraps any BaseEmbedder for use in pipelines
- `datapizza.embedders.cohere.CohereEmbedder`
- `datapizza.embedders.fastembedder.FastEmbedder` — sparse embeddings, local
- `datapizza.embedders.google.GoogleEmbedder`
- `datapizza.embedders.openai.OpenAIEmbedder` — also used for Ollama

### Vectorstores
- `datapizza.vectorstores.milvus.MilvusVectorstore` — supports dense + sparse
- `datapizza.vectorstores.qdrant.QdrantVectorstore`

### Memory & Types
- `datapizza.memory.memory.Memory`
- `datapizza.type.Block` (abstract), `TextBlock`, `MediaBlock`, `ThoughtBlock`, `FunctionCallBlock`, `FunctionCallResultBlock`, `StructuredBlock`
- `datapizza.type.Chunk` — core RAG dataclass
- `datapizza.type.Media` — image/video/audio/pdf wrapper
- `datapizza.type.Node`, `datapizza.type.MediaNode`
- `datapizza.tools.Tool`

### Pipelines
- `datapizza.pipeline.dag_pipeline.DagPipeline`
- `datapizza.pipeline.functional_pipeline.FunctionalPipeline`
- `datapizza.pipeline.pipeline.IngestionPipeline`

### Modules
- **Parsers**: `TextParser`, `DoclingParser`, `AzureParser`
- **Treebuilder**: `LLMTreeBuilder`
- **Captioners**: `LLMCaptioner`
- **Splitters**: `RecursiveSplitter`, `TextSplitter`, `NodeSplitter`, `PDFImageSplitter`
- **Metatagger**: `KeywordMetatagger`
- **Rewriters**: `ToolRewriter`
- **Rerankers**: `CohereReranker`, `TogetherReranker`
- **Prompt**: `ChatPromptTemplate`

### Tools
- `datapizza.tools.mcp_client.MCPClient`
- `datapizza.tools.duckduckgo.DuckDuckGoSearchTool`
- `datapizza.tools.filesystem.FileSystem`
- `datapizza.tools.SQLDatabase.SQLDatabase`
- `datapizza.tools.web_fetch.base.WebFetchTool`
