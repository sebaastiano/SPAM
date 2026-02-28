# Datapizza AI — API Reference: Clients

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Clients/Avaiable_Clients/openai/ ===

# OpenAI Client

## Installation

```
pip install datapizza-ai-clients-openai
```

## datapizza.clients.openai.OpenAIClient

Bases: `Client`

### __init__

```python
__init__(
    api_key,
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

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| api_key | str | The API key for the OpenAI API. | required |
| model | str | The model to use. | "gpt-4o-mini" |
| system_prompt | str | The system prompt to use. | "" |
| temperature | float \| None | The temperature to use. | None |
| cache | Cache \| None | The cache to use. | None |
| base_url | str \| None | The base URL to use. | None |
| organization | str \| None | The organization to use. | None |
| project | str \| None | The project to use. | None |
| webhook_secret | str \| None | The webhook secret to use. | None |
| websocket_base_url | str \| None | The websocket base URL to use. | None |
| timeout | float \| None | The timeout to use. | None |
| max_retries | int | The maximum number of retries to use. | 2 |
| default_headers | dict \| None | The default headers to use. | None |
| default_query | dict \| None | The default query to use. | None |
| http_client | httpx.Client \| None | The HTTP client to use. | None |

## Usage Example

```python
import os
from datapizza.clients.openai import OpenAIClient

client = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"))
response = client.invoke("Hello!")
print(response.text)
```

## Include thinking example

```python
client.invoke("Hi", reasoning={"effort": "low", "summary": "auto"})
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Clients/Avaiable_Clients/google/ ===

# Google Client

## Installation

```
pip install datapizza-ai-clients-google
```

## datapizza.clients.google.GoogleClient

Bases: `Client`

### __init__

```python
__init__(
    api_key=None,
    model="gemini-2.0-flash",
    system_prompt="",
    temperature=None,
    cache=None,
    project_id=None,
    location=None,
    credentials_path=None,
    use_vertexai=False,
)
```

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| api_key | str \| None | The API key for the Google API. | None |
| model | str | The model to use. | "gemini-2.0-flash" |
| system_prompt | str | The system prompt to use. | "" |
| temperature | float \| None | The temperature to use. | None |
| cache | Cache \| None | The cache to use. | None |
| project_id | str \| None | The project ID for Vertex AI. | None |
| location | str \| None | The location for Vertex AI. | None |
| credentials_path | str \| None | The path to the credentials file for Vertex AI. | None |
| use_vertexai | bool | Whether to use Vertex AI. | False |

## Usage Example

```python
import os
from datapizza.clients.google import GoogleClient

client = GoogleClient(api_key=os.getenv("GOOGLE_API_KEY"))
response = client.invoke("Hello!")
print(response.text)
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Clients/Avaiable_Clients/anthropic/ ===

# Anthropic Client

## Installation

```
pip install datapizza-ai-clients-anthropic
```

## datapizza.clients.anthropic.AnthropicClient

Bases: `Client`

### __init__

```python
__init__(
    api_key,
    model="claude-3-5-sonnet-latest",
    system_prompt="",
    temperature=None,
    cache=None,
)
```

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| api_key | str | The API key for the Anthropic API. | required |
| model | str | The model to use. | "claude-3-5-sonnet-latest" |
| system_prompt | str | The system prompt to use. | "" |
| temperature | float \| None | The temperature to use. | None |
| cache | Cache \| None | The cache to use. | None |

## Usage Example

```python
import os
from datapizza.clients.anthropic import AnthropicClient

client = AnthropicClient(api_key=os.getenv("ANTHROPIC_API_KEY"))
response = client.invoke("Hello!")
print(response.text)
```

## Show thinking example

```python
client.invoke("Hi", thinking={"type": "enabled", "budget_tokens": 1024})
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Clients/Avaiable_Clients/mistral/ ===

# Mistral Client

## Installation

```
pip install datapizza-ai-clients-mistral
```

## datapizza.clients.mistral.MistralClient

Bases: `Client`

### __init__

```python
__init__(
    api_key,
    model="mistral-large-latest",
    system_prompt="",
    temperature=None,
    cache=None,
)
```

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| api_key | str | The API key for the Mistral API. | required |
| model | str | The model to use. | "mistral-large-latest" |
| system_prompt | str | The system prompt to use. | "" |
| temperature | float \| None | The temperature to use. | None |
| cache | Cache \| None | The cache to use. | None |

## Usage Example

```python
import os
from datapizza.clients.mistral import MistralClient

client = MistralClient(api_key=os.getenv("MISTRAL_API_KEY"))
response = client.invoke("Hello!")
print(response.text)
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Clients/Avaiable_Clients/openai-like/ ===

# OpenAI-Like Client

## Installation

```
pip install datapizza-ai-clients-openai-like
```

## datapizza.clients.openai_like.OpenAILikeClient

Bases: `Client`

Key difference: Uses the **chat completions API** (not the responses API like `OpenAIClient`). Compatible with Ollama and other OpenAI-compatible providers.

## Usage Example

```python
from datapizza.clients.openai_like import OpenAILikeClient

client = OpenAILikeClient(
    api_key="your-api-key",
    base_url="http://localhost:11434/v1",
    model="llama3"
)
response = client.invoke("What is the capital of France?")
print(response.content)
```
