# Cache — API Reference

Source: http://docs.datapizza.ai/0.0.9/API%20Reference/Clients/cache/

## `datapizza.core.cache.cache.Cache`

Bases: `ABC`

This is the abstract base class for all cache implementations. Concrete subclasses must provide implementations for the abstract methods that define how caching is handled.

When a cache instance is attached to a client, it will automatically store the results of the client's method calls. If the same method is invoked multiple times with identical arguments, the cache returns the stored result instead of re-executing the method.

---

### `get` `abstractmethod`

```python
get(key)
```

Retrieve an object from the cache.

**Parameters:**

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `key` | `str` | The key to retrieve the object for | required |

**Returns:**

| Type | Description |
|------|-------------|
| `object` | The object stored in the cache |

---

### `set` `abstractmethod`

```python
set(key, value)
```

Store an object in the cache.

**Parameters:**

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `key` | `str` | The key to store the object for | required |
| `value` | `str` | The object to store in the cache | required |
