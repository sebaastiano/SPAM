# Clients — API Reference

Source: http://docs.datapizza.ai/0.0.9/API%20Reference/Clients/clients/

## `datapizza.core.clients.client.Client`

Bases: `ChainableProducer`

Represents the base class for all clients. Concrete implementations must implement the abstract methods to handle the actual inference.

---

### `a_embed` `async`

```python
a_embed(text, model_name=None, **kwargs)
```

Embed a text using the model.

**Parameters:**

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `text` | `str \| list[str]` | The text to embed | required |
| `model_name` | `str` | The name of the model to use. Defaults to None. | `None` |
| `**kwargs` | | Additional keyword arguments to pass to the model's embedding method | `{}` |

**Returns:**

| Type | Description |
|------|-------------|
| `list[float] \| list[list[float]]` | The embedding vector for the text |

---

### `a_invoke` `async`

```python
a_invoke(
    input,
    tools=None,
    memory=None,
    tool_choice="auto",
    temperature=None,
    max_tokens=None,
    system_prompt=None,
    **kwargs,
)
```

Performs a single inference request to the model.

**Parameters:**

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `input` | `str` | The input text/prompt to send to the model | required |
| `tools` | `List[Tool]` | List of tools available for the model to use | `None` |
| `memory` | `Memory` | Memory object containing conversation history | `None` |
| `tool_choice` | `str` | Controls which tool to use | `'auto'` |
| `temperature` | `float` | Controls randomness in responses | `None` |
| `max_tokens` | `int` | Maximum number of tokens in the response | `None` |
| `system_prompt` | `str` | System-level instructions for the model | `None` |
| `**kwargs` | | Additional keyword arguments to pass to the model's inference method | `{}` |

**Returns:**

| Type | Description |
|------|-------------|
| `ClientResponse` | A ClientResponse object containing the model's response |

---

### `a_stream_invoke` `async`

```python
a_stream_invoke(
    input,
    tools=None,
    memory=None,
    tool_choice="auto",
    temperature=None,
    max_tokens=None,
    system_prompt=None,
    **kwargs,
)
```

Streams the model's response token by token asynchronously.

**Parameters:**

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `input` | `str` | The input text/prompt to send to the model | required |
| `tools` | `List[Tool]` | List of tools available for the model to use | `None` |
| `memory` | `Memory` | Memory object containing conversation history | `None` |
| `tool_choice` | `str` | Controls which tool to use | `'auto'` |
| `temperature` | `float` | Controls randomness in responses | `None` |
| `max_tokens` | `int` | Maximum number of tokens in the response | `None` |
| `system_prompt` | `str` | System-level instructions for the model | `None` |
| `**kwargs` | | Additional keyword arguments to pass to the model's inference method | `{}` |

**Returns:**

| Type | Description |
|------|-------------|
| `AsyncIterator[ClientResponse]` | An async iterator yielding ClientResponse objects |

---

### `a_structured_response` `async`

```python
a_structured_response(
    *,
    input,
    output_cls,
    memory=None,
    temperature=None,
    max_tokens=None,
    system_prompt=None,
    tools=None,
    tool_choice="auto",
    **kwargs,
)
```

Structures the model's response according to a specified output class.

**Parameters:**

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `input` | `str` | The input text/prompt to send to the model | required |
| `output_cls` | `Type[Model]` | The class type to structure the response into | required |
| `memory` | `Memory` | Memory object containing conversation history | `None` |
| `temperature` | `float` | Controls randomness in responses | `None` |
| `max_tokens` | `int` | Maximum number of tokens in the response | `None` |
| `system_prompt` | `str` | System-level instructions for the model | `None` |
| `tools` | `List[Tool]` | List of tools available for the model to use | `None` |
| `tool_choice` | `Literal['auto', 'required', 'none'] \| list[str]` | Controls which tool to use | `'auto'` |
| `**kwargs` | | Additional keyword arguments to pass to the model's inference method | `{}` |

**Returns:**

| Type | Description |
|------|-------------|
| `ClientResponse` | A ClientResponse object containing the structured response |

---

### `embed`

```python
embed(text, model_name=None, **kwargs)
```

Embed a text using the model.

**Parameters:**

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `text` | `str \| list[str]` | The text to embed | required |
| `model_name` | `str` | The name of the model to use | `None` |
| `**kwargs` | | Additional keyword arguments to pass to the model's embedding method | `{}` |

**Returns:**

| Type | Description |
|------|-------------|
| `list[float]` | The embedding vector for the text |

---

### `invoke`

```python
invoke(
    input,
    tools=None,
    memory=None,
    tool_choice="auto",
    temperature=None,
    max_tokens=None,
    system_prompt=None,
    **kwargs,
)
```

Performs a single inference request to the model.

**Parameters:**

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `input` | `str` | The input text/prompt to send to the model | required |
| `tools` | `List[Tool]` | List of tools available for the model to use | `None` |
| `memory` | `Memory` | Memory object containing conversation history | `None` |
| `tool_choice` | `str` | Controls which tool to use | `'auto'` |
| `temperature` | `float` | Controls randomness in responses | `None` |
| `max_tokens` | `int` | Maximum number of tokens in the response | `None` |
| `system_prompt` | `str` | System-level instructions for the model | `None` |
| `**kwargs` | | Additional keyword arguments to pass to the model's inference method | `{}` |

**Returns:**

| Type | Description |
|------|-------------|
| `ClientResponse` | A ClientResponse object containing the model's response |

---

### `stream_invoke`

```python
stream_invoke(
    input,
    tools=None,
    memory=None,
    tool_choice="auto",
    temperature=None,
    max_tokens=None,
    system_prompt=None,
    **kwargs,
)
```

Streams the model's response token by token.

**Parameters:**

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `input` | `str` | The input text/prompt to send to the model | required |
| `tools` | `List[Tool]` | List of tools available for the model to use | `None` |
| `memory` | `Memory` | Memory object containing conversation history | `None` |
| `tool_choice` | `str` | Controls which tool to use | `'auto'` |
| `temperature` | `float` | Controls randomness in responses | `None` |
| `max_tokens` | `int` | Maximum number of tokens in the response | `None` |
| `system_prompt` | `str` | System-level instructions for the model | `None` |
| `**kwargs` | | Additional keyword arguments to pass to the model's inference method | `{}` |

**Returns:**

| Type | Description |
|------|-------------|
| `Iterator[ClientResponse]` | An iterator yielding ClientResponse objects |

---

### `structured_response`

```python
structured_response(
    *,
    input,
    output_cls,
    memory=None,
    temperature=None,
    max_tokens=None,
    system_prompt=None,
    tools=None,
    tool_choice="auto",
    **kwargs,
)
```

Structures the model's response according to a specified output class.

**Parameters:**

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `input` | `str` | The input text/prompt to send to the model | required |
| `output_cls` | `Type[Model]` | The class type to structure the response into | required |
| `memory` | `Memory` | Memory object containing conversation history | `None` |
| `temperature` | `float` | Controls randomness in responses | `None` |
| `max_tokens` | `int` | Maximum number of tokens in the response | `None` |
| `system_prompt` | `str` | System-level instructions for the model | `None` |
| `tools` | `List[Tool]` | List of tools available for the model to use | `None` |
| `tool_choice` | `Literal['auto', 'required', 'none'] \| list[str]` | Controls which tool to use | `'auto'` |
| `**kwargs` | | Additional keyword arguments to pass to the model's inference method | `{}` |

**Returns:**

| Type | Description |
|------|-------------|
| `ClientResponse` | A ClientResponse object containing the structured response |
