# Response — API Reference

Source: http://docs.datapizza.ai/0.0.9/API%20Reference/Clients/models/

## `datapizza.core.clients.ClientResponse`

A class for storing the response from a client. Contains a list of blocks that can be text, function calls, or structured data, maintaining the order in which they were generated.

**Parameters:**

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `content` | `List[Block]` | A list of blocks | required |
| `delta` | `str` | The delta of the response. Used for streaming responses | `None` |
| `usage` | `TokenUsage` | Aggregated token usage | `None` |
| `stop_reason` | `str` | Stop reason | `None` |

---

### `first_text` `property`

```python
first_text
```

Returns the content of the first `TextBlock` or `None`.

---

### `function_calls` `property`

```python
function_calls
```

Returns all function calls in order.

---

### `structured_data` `property`

```python
structured_data
```

Returns all structured data in order.

---

### `text` `property`

```python
text
```

Returns concatenated text from all `TextBlock`s in order.

---

### `thoughts` `property`

```python
thoughts
```

Returns all thoughts in order.

---

### `is_pure_function_call`

```python
is_pure_function_call()
```

Returns `True` if response contains only `FunctionCallBlock`s.

---

### `is_pure_text`

```python
is_pure_text()
```

Returns `True` if response contains only `TextBlock`s.
