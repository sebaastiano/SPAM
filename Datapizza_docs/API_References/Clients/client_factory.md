# Client Factory — API Reference

Source: http://docs.datapizza.ai/0.0.9/API%20Reference/Clients/client_factory/

The `ClientFactory` provides a convenient way to create LLM clients for different providers without having to import and instantiate each client type individually.

---

## `datapizza.clients.factory.ClientFactory`

Factory for creating LLM clients.

### `create` `staticmethod`

```python
create(
    provider,
    api_key,
    model,
    system_prompt="",
    temperature=0.7,
    **kwargs,
)
```

Create a client instance based on the specified provider.

**Parameters:**

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `provider` | `str \| Provider` | The LLM provider to use (openai, google, or anthropic) | required |
| `api_key` | `str` | API key for the provider | required |
| `model` | `str` | Model name to use (provider-specific) | required |
| `system_prompt` | `str` | System prompt to use | `''` |
| `temperature` | `float` | Temperature for generation (0-2) | `0.7` |
| `**kwargs` | | Additional provider-specific arguments | `{}` |

**Returns:**

| Type | Description |
|------|-------------|
| `Client` | An instance of the appropriate client |

**Raises:**

| Type | Description |
|------|-------------|
| `ValueError` | If the provider is not supported |

---

## Example Usage

```python
from datapizza.clients.factory import ClientFactory, Provider

# Create an OpenAI client
openai_client = ClientFactory.create(
    provider=Provider.OPENAI,
    api_key="OPENAI_API_KEY",
    model="gpt-4",
    system_prompt="You are a helpful assistant.",
    temperature=0.7
)

# Create a Google client using string provider
google_client = ClientFactory.create(
    provider="google",
    api_key="GOOGLE_API_KEY",
    model="gemini-pro",
    system_prompt="You are a helpful assistant.",
    temperature=0.5
)

# Create an Anthropic client with custom parameters
anthropic_client = ClientFactory.create(
    provider=Provider.ANTHROPIC,
    api_key="ANTHROPIC_API_KEY",
    model="claude-3-sonnet-20240229",
    system_prompt="You are a helpful assistant.",
    temperature=0.3,
)

# Use the client
response = openai_client.invoke("What is the capital of France?")
print(response.content)
```

---

## Supported Providers

- `openai` — OpenAI GPT models
- `google` — Google Gemini models
- `anthropic` — Anthropic Claude models
- `mistral` — Mistral AI models
