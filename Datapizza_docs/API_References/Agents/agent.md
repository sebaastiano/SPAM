# Agent — API Reference

Source: http://docs.datapizza.ai/0.0.9/API%20Reference/Agents/agent/

## `datapizza.agents.agent.Agent`

### `__init__`

```python
__init__(
    name=None,
    client=None,
    *,
    system_prompt=None,
    tools=None,
    max_steps=None,
    terminate_on_text=True,
    stateless=True,
    gen_args=None,
    memory=None,
    stream=None,
    can_call=None,
    logger=None,
    planning_interval=0,
    planning_prompt=PLANNING_PROMT,
)
```

Initialize the agent.

**Parameters:**

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `name` | `str` | The name of the agent | `None` |
| `client` | `Client` | The client to use for the agent | `None` |
| `system_prompt` | `str` | The system prompt to use for the agent | `None` |
| `tools` | `list[Tool]` | A list of tools to use with the agent | `None` |
| `max_steps` | `int` | The maximum number of steps to execute | `None` |
| `terminate_on_text` | `bool` | Whether to terminate the agent on text | `True` |
| `stateless` | `bool` | Whether to use stateless execution | `True` |
| `gen_args` | `dict[str, Any]` | Additional arguments to pass to the agent's execution | `None` |
| `memory` | `Memory` | The memory to use for the agent | `None` |
| `stream` | `bool` | Whether to stream the agent's execution | `None` |
| `can_call` | `list[Agent]` | A list of agents that can call the agent | `None` |
| `logger` | `AgentLogger` | The logger to use for the agent | `None` |
| `planning_interval` | `int` | The planning interval to use for the agent | `0` |
| `planning_prompt` | `str` | The planning prompt to use for the agent planning steps | `PLANNING_PROMT` |

---

### `a_run` `async`

```python
a_run(task_input, tool_choice='auto', **gen_kwargs)
```

Run the agent on a task input asynchronously.

**Parameters:**

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `task_input` | `str` | The input text/prompt to send to the model | required |
| `tool_choice` | `Literal['auto', 'required', 'none', 'required_first'] \| list[str]` | Controls which tool to use | `'auto'` |
| `**gen_kwargs` | | Additional keyword arguments to pass to the agent's execution | `{}` |

**Returns:**

| Type | Description |
|------|-------------|
| `StepResult \| None` | The final result of the agent's execution |

---

### `a_stream_invoke` `async`

```python
a_stream_invoke(task_input, tool_choice="auto", **gen_kwargs)
```

Stream the agent's execution asynchronously, yielding intermediate steps and final result.

**Parameters:**

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `task_input` | `str` | The input text/prompt to send to the model | required |
| `tool_choice` | `Literal['auto', 'required', 'none', 'required_first'] \| list[str]` | Controls which tool to use | `'auto'` |
| `**gen_kwargs` | | Additional keyword arguments to pass to the agent's execution | `{}` |

**Yields:**

| Type | Description |
|------|-------------|
| `AsyncGenerator[ClientResponse \| StepResult \| Plan \| None]` | The intermediate steps and final result of the agent's execution |

---

### `run`

```python
run(task_input, tool_choice='auto', **gen_kwargs)
```

Run the agent on a task input.

**Parameters:**

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `task_input` | `str` | The input text/prompt to send to the model | required |
| `tool_choice` | `Literal['auto', 'required', 'none', 'required_first'] \| list[str]` | Controls which tool to use | `'auto'` |
| `**gen_kwargs` | | Additional keyword arguments to pass to the agent's execution | `{}` |

**Returns:**

| Type | Description |
|------|-------------|
| `StepResult \| None` | The final result of the agent's execution |

---

### `stream_invoke`

```python
stream_invoke(task_input, tool_choice='auto', **gen_kwargs)
```

Stream the agent's execution, yielding intermediate steps and final result.

**Parameters:**

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `task_input` | `str` | The input text/prompt to send to the model | required |
| `tool_choice` | `Literal['auto', 'required', 'none', 'required_first'] \| list[str]` | Controls which tool to use | `'auto'` |
| `**gen_kwargs` | | Additional keyword arguments to pass to the agent's execution | `{}` |

**Yields:**

| Type | Description |
|------|-------------|
| `ClientResponse \| StepResult \| Plan \| None` | The intermediate steps and final result of the agent's execution |
