# Datapizza AI — API Reference: Modules

## Overview

Core modules (included with `datapizza-ai-core`):
- Parsers
- Captioners
- Metatagger
- Prompt
- Rewriters
- Splitters
- Treebuilder

Optional modules (separate pip install):
- Rerankers

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Modules/Parsers/text_parser/ ===

# TextParser

## datapizza.modules.parsers.TextParser

Bases: `Parser`

### __init__

```python
__init__()
```

No parameters.

### parse

```python
parse(text: str, metadata: dict = None) -> Node
```

Creates a DOCUMENT → PARAGRAPH → SENTENCE hierarchy.

## Convenience Function

```python
from datapizza.modules.parsers import parse_text

node = parse_text(text, metadata=None)
```

## Usage Examples

### Basic Usage

```python
from datapizza.modules.parsers import TextParser

parser = TextParser()
document = parser.parse("Hello, world!\n\nThis is a second paragraph.")
```

### Pipeline Integration

```python
from datapizza.pipeline.pipeline import IngestionPipeline
from datapizza.modules.parsers import TextParser
from datapizza.modules.splitters import RecursiveSplitter

pipeline = IngestionPipeline(
    modules=[TextParser(), RecursiveSplitter(max_char=500)]
)
chunks = pipeline.run("document.txt")
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Modules/Parsers/docling_parser/ ===

# DoclingParser

## Installation

```
pip install datapizza-ai-parsers-docling
```

## datapizza.modules.parsers.DoclingParser

### __init__

```python
__init__(
    json_output_dir=None,
    ocr_options=None
)
```

### parse

```python
parse(file_path) -> Node
```

## Features

- PDF processing with OCR support
- Hierarchical structure: document → sections → paragraphs / tables / figures
- Media extraction as base64 images
- Default config: Table structure detection, EasyOCR, PyPdfium backend

## OCROptions

```python
OCROptions(
    engine: OCREngine,
    tesseract_lang: list[str],
    easy_ocr_force_full_page: bool
)
```

### OCREngine Enum

- `OCREngine.TESSERACT`
- `OCREngine.EASY_OCR`
- `OCREngine.NONE`

### Tesseract Language Codes

`"eng"`, `"ita"`, `"fra"`, `"deu"`, `"spa"`, `"por"`, `"chi_sim"`, `"chi_tra"`, `"jpn"`, `"auto"`

## Usage Examples

### Basic PDF Parsing

```python
from datapizza.modules.parsers import DoclingParser

parser = DoclingParser()
document = parser.parse("document.pdf")
```

### With EasyOCR

```python
from datapizza.modules.parsers import DoclingParser
from datapizza.modules.parsers.docling import OCROptions, OCREngine

ocr_options = OCROptions(
    engine=OCREngine.EASY_OCR,
    easy_ocr_force_full_page=True
)
parser = DoclingParser(ocr_options=ocr_options)
document = parser.parse("scanned.pdf")
```

### With Tesseract

```python
from datapizza.modules.parsers.docling import OCROptions, OCREngine

ocr_options = OCROptions(
    engine=OCREngine.TESSERACT,
    tesseract_lang=["eng", "ita"]
)
parser = DoclingParser(ocr_options=ocr_options)
document = parser.parse("multilingual.pdf")
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Modules/Parsers/azure_parser/ ===

# AzureParser

## Installation

```
pip install datapizza-ai-parsers-azure
```

## datapizza.modules.parsers.azure.AzureParser

Bases: `Parser`

### __init__

```python
__init__(
    api_key: str,
    endpoint: str,
    result_type: str = "text"  # or "markdown"
)
```

### parse

```python
parse(file_path: str, metadata: dict = None) -> Node
```

Raises: `TypeError`

### a_parse (async)

```python
a_parse(file_path: str, metadata: dict = None) -> Node
```

Raises: `TypeError`

### __call__

```python
__call__(file_path: str, metadata: dict = None) -> Node
```

### parse_with_azure_ai

```python
parse_with_azure_ai(file_path: str) -> dict
```

## Node Hierarchy

DOCUMENT → SECTION → PARAGRAPH / TABLE / FIGURE

## Usage Examples

### Basic Document Processing

```python
from datapizza.modules.parsers.azure import AzureParser

parser = AzureParser(
    api_key="your-azure-api-key",
    endpoint="https://your-resource.cognitiveservices.azure.com/"
)
document = parser.parse("document.pdf")
```

### Async Processing

```python
import asyncio
from datapizza.modules.parsers.azure import AzureParser

async def main():
    parser = AzureParser(
        api_key="your-azure-api-key",
        endpoint="https://your-resource.cognitiveservices.azure.com/",
        result_type="markdown"
    )
    document = await parser.a_parse("document.pdf")

asyncio.run(main())
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Modules/treebuilder/ ===

# LLMTreeBuilder

## datapizza.modules.treebuilder.LLMTreeBuilder

TreeBuilder that creates a hierarchical tree from text using an LLM.
Hierarchy: document → sections → paragraphs → sentences.

### __init__

```python
__init__(client: Client)
```

### parse

```python
parse(text: str) -> Node
```

### invoke

```python
invoke(file_path: str) -> Node
```

## Features

- Semantic understanding of document structure
- Configurable tree depth
- Sync and async support
- Metadata extraction

## Usage Example

```python
from datapizza.modules.treebuilder import LLMTreeBuilder
from datapizza.clients.openai import OpenAIClient

client = OpenAIClient(api_key="your-openai-api-key")
builder = LLMTreeBuilder(client=client)

document = builder.parse("""
# Introduction
This is the introduction of the document.

# Main Section
This section contains main content.
""")

def print_structure(node, indent=0):
    print("  " * indent + f"[{node.node_type}] {node.content[:50] if node.content else ''}")
    for child in node.children or []:
        print_structure(child, indent + 1)

print_structure(document)
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Modules/captioners/ ===

# LLMCaptioner

## datapizza.modules.captioners.LLMCaptioner

Bases: `NodeCaptioner`

### __init__

```python
__init__(
    client,
    max_workers=3,
    system_prompt_table="Generate concise captions for tables.",
    system_prompt_figure="Generate descriptive captions for figures."
)
```

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| client | Client | The LLM client to use. | required |
| max_workers | int | Max parallel captioning workers. | 3 |
| system_prompt_table | str | System prompt for table captioning. | "Generate concise captions for tables." |
| system_prompt_figure | str | System prompt for figure captioning. | "Generate descriptive captions for figures." |

### caption

```python
caption(node) -> Node
```

### a_caption (async)

```python
a_caption(node) -> Node
```

### caption_media

```python
caption_media(media, system_prompt=None) -> str
```

### a_caption_media (async)

```python
a_caption_media(media, system_prompt=None) -> str
```

## Supported Node Types

- `FIGURE`
- `TABLE`

## Output Format

```
{original_content} <{node_type}> [{generated_caption}]
```

## Usage Example

```python
from datapizza.modules.captioners import LLMCaptioner
from datapizza.clients.openai import OpenAIClient

client = OpenAIClient(api_key="your-openai-api-key")
captioner = LLMCaptioner(client=client, max_workers=3)

captioned_document = captioner(document_node)
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Modules/Splitters/recursive_splitter/ ===

# RecursiveSplitter

## datapizza.modules.splitters.RecursiveSplitter

Bases: `Splitter`

Takes leaf nodes from a tree document structure and groups them into Chunk objects until reaching the maximum character limit. Each leaf Node represents the smallest unit of content.

### __init__

```python
__init__(max_char=5000, overlap=0)
```

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| max_char | int | The maximum number of characters per chunk. | 5000 |
| overlap | int | The number of characters to overlap between chunks. | 0 |

### split

```python
split(node: Node) -> list[Chunk]
```

## Features

- Uses multiple separator strategies in order of preference
- Recursive approach ensures optimal chunk boundaries
- Configurable chunk size and overlap for context preservation
- Handles various content types

## Usage Example

```python
from datapizza.modules.parsers import TextParser
from datapizza.modules.splitters import RecursiveSplitter

splitter = RecursiveSplitter(max_char=10, overlap=1)

parser = TextParser()
document = parser.parse("""
This is the first section of the document.
It contains important information about the topic.

This is the second section with more details.
It provides additional context and examples.

The final section concludes the document.
It summarizes the key points discussed.
""")

chunks = splitter.split(document)
print(chunks)
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Modules/Splitters/text_splitter/ ===

# TextSplitter

## datapizza.modules.splitters.TextSplitter

Bases: `Splitter`

A basic text splitter that operates directly on strings (not Node objects). Splits raw text into chunks while maintaining configurable size and overlap parameters.

### __init__

```python
__init__(max_char=5000, overlap=0)
```

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| max_char | int | The maximum number of characters per chunk. | 5000 |
| overlap | int | The number of characters to overlap between chunks. | 0 |

### split

```python
split(text: str) -> list[Chunk]
```

## Features

- Simple, straightforward text splitting
- Configurable chunk size and overlap
- Lightweight with minimal overhead
- Preserves character-level accuracy

## Usage Example

```python
from datapizza.modules.splitters import TextSplitter

splitter = TextSplitter(max_char=500, overlap=50)
chunks = splitter.split(text_content)
```

### Basic Usage

```python
from datapizza.modules.splitters import TextSplitter

splitter = TextSplitter(max_char=50, overlap=5)

text = """
This is a sample text that we want to split into smaller chunks.
The TextSplitter will divide this content based on the specified
chunk size and overlap parameters. This ensures that information
is preserved while creating manageable pieces of content.
"""

chunks = splitter.split(text)

for i, chunk in enumerate(chunks):
    print(f"Chunk {i+1}: {len(chunk.text)} chars")
    print(f"Content: {chunk.text}")
    print("---")
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Modules/Splitters/node_splitter/ ===

# NodeSplitter

## datapizza.modules.splitters.NodeSplitter

Bases: `Splitter`

Traverses a document tree from the root node. If the root node's content is smaller than `max_chars`, it becomes a single chunk. Otherwise, it recursively processes the node's children, creating chunks from the first level of children that fit within `max_chars`, continuing deeper into the tree as needed.

### __init__

```python
__init__(max_char=5000)
```

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| max_char | int | The maximum number of characters per chunk. | 5000 |

### split

```python
split(node: Node) -> list[Chunk]
```

## Features

- Maintains Node object structure and hierarchy
- Preserves metadata from original nodes
- Respects node boundaries when possible
- Handles nested node relationships intelligently

## Usage Example

```python
from datapizza.modules.splitters import NodeSplitter

splitter = NodeSplitter(max_char=800)
node_chunks = splitter.split(document_node)
```

### Basic Node Splitting

```python
from datapizza.modules.parsers import TextParser
from datapizza.modules.splitters import NodeSplitter

parser = TextParser()
document = parser.parse("""
This is the first section of the document.
It contains important information about the topic.

This is the second section with more details.
It provides additional context and examples.

The final section concludes the document.
It summarizes the key points discussed.
""")

splitter = NodeSplitter(max_char=150)
chunks = splitter.split(document)

for i, chunk in enumerate(chunks):
    print(f"Chunk {i+1}:")
    print(f"  Content length: {len(chunk.text)}")
    print(f"  Content preview: {chunk.text[:80]}...")
    print("---")
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Modules/Splitters/pdf_image_splitter/ ===

# PDFImageSplitter

## datapizza.modules.splitters.PDFImageSplitter

Bases: `Splitter`

Splits a PDF document into individual pages, saves each page as an image using fitz, and returns metadata about each page as a Chunk object.

### __init__

```python
__init__(
    image_format="png",
    output_base_dir="output_images",
    dpi=300,
)
```

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| image_format | Literal['png', 'jpeg'] | The format to save the images in. | 'png' |
| output_base_dir | str \| Path | The base directory where images will be saved. A subdirectory is created per PDF. | 'output_images' |
| dpi | int | Dots Per Inch for rendering the PDF page. Higher values = higher resolution + larger file size. | 300 |

### split

```python
split(pdf_path: str | Path) -> list[Chunk]
```

Processes the PDF using fitz: converts pages to images and returns Chunk objects (one per page).

## Features

- Specialized handling of PDF document structure
- Preserves image data and visual elements
- Maintains spatial layout information
- Includes page-level metadata and coordinates

## Usage Example

```python
from datapizza.modules.splitters import PDFImageSplitter

splitter = PDFImageSplitter()
pdf_chunks = splitter("pdf_path")
```

### Basic PDF Content Splitting

```python
from datapizza.modules.splitters import PDFImageSplitter

pdf_splitter = PDFImageSplitter()
pdf_chunks = pdf_splitter("pdf_path")

for i, chunk in enumerate(pdf_chunks):
    print(f"Chunk {i+1}:")
    print(f"  Content length: {len(chunk.content)}")
    print(f"  Page: {chunk.metadata.get('page_number', 'unknown')}")

    if hasattr(chunk, 'media') and chunk.media:
        print(f"  Media elements: {len(chunk.media)}")
        for media in chunk.media:
            print(f"    Type: {media.media_type}")

    if 'boundingRegions' in chunk.metadata:
        print(f"  Bounding regions: {len(chunk.metadata['boundingRegions'])}")

    print("---")
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Modules/metatagger/ ===

# Metatagger

Metataggers are pipeline components that add metadata tags to content chunks using language models.

## datapizza.modules.metatagger.KeywordMetatagger

Bases: `Metatagger`

Keyword metatagger that uses an LLM client to add metadata to a chunk.

### __init__

```python
__init__(
    client,
    max_workers=3,
    system_prompt=None,
    user_prompt=None,
    keyword_name="keywords",
)
```

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| client | Client | The LLM client to use. | required |
| max_workers | int | The maximum number of workers. | 3 |
| system_prompt | str \| None | The system prompt. | None |
| user_prompt | str \| None | The user prompt. | None |
| keyword_name | str | The name of the keyword field in metadata. | 'keywords' |

### tag

```python
tag(chunks) -> list[Chunk]
```

Add metadata to chunks.

### a_tag (async)

```python
a_tag(chunks) -> list[Chunk]
```

Async add metadata to chunks.

## Input / Output

- Input: `Chunk` objects or lists of `Chunk` objects
- Output: Same `Chunk` objects with additional metadata containing generated keywords

## Usage Example

```python
from datapizza.modules.metatagger import KeywordMetatagger
from datapizza.clients.openai import OpenAIClient

client = OpenAIClient(api_key="your-api-key")
metatagger = KeywordMetatagger(
    client=client,
    max_workers=3,
    system_prompt="Generate relevant keywords for the given text.",
    user_prompt="Extract 5-10 keywords from this text:",
    keyword_name="keywords"
)

tagged_chunks = metatagger.tag(chunks)
```

### Basic Keyword Extraction

```python
import uuid
from datapizza.clients.openai import OpenAIClient
from datapizza.modules.metatagger import KeywordMetatagger
from datapizza.type import Chunk

client = OpenAIClient(api_key="OPENAI_API_KEY", model="gpt-4o")
metatagger = KeywordMetatagger(
    client=client,
    system_prompt="You are a keyword extraction expert. Generate relevant, concise keywords.",
    user_prompt="Extract 5-8 important keywords from this text:",
    keyword_name="keywords"
)

chunks = [
    Chunk(id=str(uuid.uuid4()), text="Machine learning algorithms are transforming healthcare diagnostics."),
    Chunk(id=str(uuid.uuid4()), text="Climate change impacts ocean temperatures and marine ecosystems.")
]

tagged_chunks = metatagger.tag(chunks)

for chunk in tagged_chunks:
    print(f"Content: {chunk.text}")
    print(f"Keywords: {chunk.metadata.get('keywords', [])}")
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Modules/rewriters/ ===

# Rewriters

Rewriters are pipeline components that transform and rewrite text content using language models.

## datapizza.modules.rewriters.ToolRewriter

Bases: `Rewriter`

A tool-based query rewriter that uses LLMs to transform user queries through structured tool interactions.

### rewrite

```python
rewrite(user_prompt: str, memory: Memory | None = None) -> str
```

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| user_prompt | str | The user query to rewrite. | required |
| memory | Memory \| None | The memory to use for the rewrite. | None |

Returns: `str` — The rewritten query.

### a_rewrite (async)

```python
a_rewrite(user_prompt: str, memory: Memory | None = None) -> str
```

## Features

- Flexible content transformation with custom instructions
- Support for summarization, style changes, format conversion
- Integration with tool calling for enhanced capabilities
- Supports both sync and async processing

## Usage Example

```python
from datapizza.clients.openai import OpenAIClient
from datapizza.modules.rewriters import ToolRewriter

client = OpenAIClient(api_key="OPENAI_API_KEY", model="gpt-4o")

simplifier = ToolRewriter(
    client=client,
    system_prompt="You are an expert at simplifying complex text for general audiences.",
)

technical_text = """
The algorithmic implementation utilizes a recursive binary search methodology
to optimize computational complexity in logarithmic time scenarios.
"""

simplified_text = simplifier(technical_text)
print(simplified_text)
# Output: recursive binary search
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Modules/Rerankers/cohere_reranker/ ===

# CohereReranker

## Installation

```
pip install datapizza-ai-rerankers-cohere
```

## datapizza.modules.rerankers.cohere.CohereReranker

Bases: `Reranker`

A reranker that uses the Cohere API to rerank documents.

### __init__

```python
__init__(
    api_key,
    endpoint,
    top_n=10,
    threshold=None,
    model="model",
)
```

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| api_key | str | The API key for the Cohere API. | required |
| endpoint | str | The endpoint for the Cohere API. | required |
| top_n | int | The number of documents to return. | 10 |
| threshold | float \| None | The threshold for the reranker. | None |
| model | str | The model to use. | "model" |

### rerank

```python
rerank(query: str, documents: list[Chunk]) -> list[Chunk]
```

### a_rerank (async)

```python
a_rerank(query: str, documents: list[Chunk]) -> list[Chunk]
```

## Features

- High-quality semantic reranking using Cohere's models
- Configurable result count and score thresholds
- Support for both sync and async processing
- Automatic relevance scoring for retrieved content
- Flexible endpoint configuration

## Usage Example

```python
from datapizza.modules.rerankers.cohere import CohereReranker

reranker = CohereReranker(
    api_key="your-cohere-api-key",
    endpoint="https://api.cohere.ai/v1",
    top_n=10,
    threshold=0.5,
    model="rerank-v3.5",
)

query = "What are the benefits of machine learning?"
reranked_chunks = reranker.rerank(query, chunks)
```

### Basic Usage

```python
import uuid
from datapizza.modules.rerankers.cohere import CohereReranker
from datapizza.type import Chunk

reranker = CohereReranker(
    api_key="COHERE_API_KEY",
    endpoint="https://api.cohere.ai/v1",
    top_n=5,
    threshold=0.6,
    model="rerank-v3.5",
)

chunks = [
    Chunk(id=str(uuid.uuid4()), text="Machine learning enables computers to learn from data..."),
    Chunk(id=str(uuid.uuid4()), text="Deep learning is a subset of machine learning..."),
    Chunk(id=str(uuid.uuid4()), text="Neural networks consist of interconnected nodes..."),
    Chunk(id=str(uuid.uuid4()), text="Supervised learning uses labeled training data..."),
    Chunk(id=str(uuid.uuid4()), text="The weather forecast shows rain tomorrow...")
]

query = "What is deep learning and how does it work?"
reranked_chunks = reranker.rerank(query, chunks)

for i, chunk in enumerate(reranked_chunks):
    score = chunk.metadata.get('relevance_score', 'N/A')
    print(f"Rank {i+1} (Score: {score}): {chunk.text[:80]}...")
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Modules/Rerankers/together_reranker/ ===

# TogetherReranker

## Installation

```
pip install datapizza-ai-rerankers-together
```

## datapizza.modules.rerankers.together.TogetherReranker

Bases: `Reranker`

A reranker that uses the Together API to rerank documents.

### __init__

```python
__init__(api_key, model, top_n=10, threshold=None)
```

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| api_key | str | Together API key. | required |
| model | str | Model name to use for reranking. | required |
| top_n | int | Number of top documents to return. | 10 |
| threshold | Optional[float] | Minimum relevance score threshold. If None, no filtering is applied. | None |

### rerank

```python
rerank(query: str, documents: list[Chunk]) -> list[Chunk]
```

## Available Models

- `sentence-transformers/msmarco-bert-base-dot-v5`
- `sentence-transformers/all-MiniLM-L6-v2`
- `sentence-transformers/all-mpnet-base-v2`
- Custom fine-tuned models for specific domains

## Features

- Access to multiple reranking model options
- Flexible model selection for different use cases
- Score-based filtering with configurable thresholds
- Integration with Together AI's model ecosystem

## Usage Example

```python
from datapizza.modules.rerankers.together import TogetherReranker

reranker = TogetherReranker(
    api_key="your-together-api-key",
    model="sentence-transformers/msmarco-bert-base-dot-v5",
    top_n=15,
    threshold=0.3
)

query = "How to implement neural networks?"
reranked_results = reranker.rerank(query, document_chunks)
```

### Basic Usage

```python
import uuid
from datapizza.modules.rerankers.together import TogetherReranker
from datapizza.type import Chunk

reranker = TogetherReranker(
    api_key="TOGETHER_API_KEY",
    model="Salesforce/Llama-Rank-V1",
    top_n=10,
    threshold=0.4
)

chunks = [
    Chunk(id=str(uuid.uuid4()), text="Neural networks are computational models inspired by biological brains..."),
    Chunk(id=str(uuid.uuid4()), text="Deep learning uses multiple layers to learn complex patterns..."),
    Chunk(id=str(uuid.uuid4()), text="Backpropagation is the algorithm used to train neural networks..."),
    Chunk(id=str(uuid.uuid4()), text="The weather is sunny today with mild temperatures..."),
    Chunk(id=str(uuid.uuid4()), text="Convolutional neural networks excel at image recognition tasks...")
]

query = "How do neural networks learn?"
reranked_results = reranker.rerank(query, chunks)

for i, chunk in enumerate(reranked_results):
    score = chunk.metadata.get('relevance_score', 'N/A')
    print(f"Rank {i+1} (Score: {score}): {chunk.text[:70]}...")
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Modules/Prompt/ChatPromptTemplate/ ===

# ChatPromptTemplate

## datapizza.modules.prompt.ChatPromptTemplate

Bases: `Prompt`

Takes as input a Memory, Chunks, Prompt and creates a Memory with all existing messages + the user's query + function_call_retrieval + chunks retrieval.

Constructor args:
- `user_prompt_template: str` — The user prompt Jinja template
- `retrieval_prompt_template: str` — The retrieval prompt Jinja template

### format

```python
format(
    memory=None,
    chunks=None,
    user_prompt="",
    retrieval_query="",
) -> Memory
```

Creates a new Memory object that includes:
- Existing memory messages
- User's query
- Function call retrieval results
- Chunks retrieval results

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| memory | Memory \| None | The memory object to add new messages to. | None |
| chunks | list[Chunk] \| None | The chunks to add to the memory. | None |
| user_prompt | str | The user's query. | '' |
| retrieval_query | str | The query to search the vectorstore for. | '' |

Returns: `Memory`

## Usage Example

```python
import uuid
from datapizza.modules.prompt import ChatPromptTemplate
from datapizza.type import Chunk

system_prompt = ChatPromptTemplate(
    user_prompt_template="You are helping with data analysis tasks, this is the user prompt: {{ user_prompt }}",
    retrieval_prompt_template="Retrieved content:\n{% for chunk in chunks %}{{ chunk.text }}\n{% endfor %}"
)

result = system_prompt.format(
    user_prompt="Hello, how are you?",
    chunks=[
        Chunk(id=str(uuid.uuid4()), text="This is a chunk"),
        Chunk(id=str(uuid.uuid4()), text="This is another chunk")
    ]
)
print(result)
```
