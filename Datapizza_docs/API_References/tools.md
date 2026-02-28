# Datapizza AI — API Reference: Tools

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Tools/mcp/ ===

# MCPClient

## datapizza.tools.mcp_client.MCPClient

Helper for interacting with Model Context Protocol servers.

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| url | str | The URL of the MCP server. | required |
| command | str \| None | The command to run the MCP server. | None |
| headers | dict[str, str] \| None | The headers to pass to the MCP server. | None |
| args | list[str] \| None | The arguments to pass to the MCP server. | None |
| env | dict[str, str] \| None | The environment variables to pass to the MCP server. | None |
| timeout | int | The timeout for the MCP server. | 30 |
| sampling_callback | SamplingFnT \| None | The sampling callback. | None |

### Methods

#### a_list_prompts (async)

```python
a_list_prompts() -> ListPromptsResult
```

List the prompts available on the MCP server.

#### a_list_tools (async)

```python
a_list_tools() -> list[Tool]
```

List the tools available on the MCP server.

#### call_tool (async)

```python
call_tool(
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    progress_callback: ProgressFnT | None = None
) -> CallToolResult
```

Call a tool on the MCP server.

#### get_prompt (async)

```python
get_prompt(prompt_name, arguments=None)
```

Get a prompt from the MCP server.

#### list_prompts

```python
list_prompts() -> ListPromptsResult
```

List the prompts available on the MCP server (sync).

#### list_resources (async)

```python
list_resources() -> ListResourcesResult
```

List the resources available on the MCP server.

#### list_tools

```python
list_tools() -> list[Tool]
```

List the tools available on the MCP server (sync).

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Tools/duckduckgo/ ===

# DuckDuckGo

## Installation

```
pip install datapizza-ai-tools-duckduckgo
```

## datapizza.tools.duckduckgo.DuckDuckGoSearchTool

Bases: `Tool`

The DuckDuckGo Search tool. Allows you to search the web for a given query.

### __init__

```python
__init__()
```

Initializes the DuckDuckGoSearch tool.

### search

```python
search(query) -> list[dict]
```

Search the web for the given query. Returns list of results with keys: `title`, `href`, `body`.

### __call__

```python
__call__(query)
```

Invoke the tool.

## Features

- Web search using DuckDuckGo's search engine
- Privacy-focused (DuckDuckGo doesn't track users)
- Simple integration with AI agents and pipelines
- Real-time results

## Usage Example

```python
from datapizza.tools.duckduckgo import DuckDuckGoSearchTool

search_tool = DuckDuckGoSearchTool()

results = search_tool.search("latest AI developments 2024")

for result in results:
    print(f"Title: {result.get('title', 'N/A')}")
    print(f"URL: {result.get('href', 'N/A')}")
    print(f"Body: {result.get('body', 'N/A')}")
    print("---")
```

## Integration with Agents

```python
from datapizza.agents import Agent
from datapizza.clients.openai import OpenAIClient
from datapizza.tools.duckduckgo import DuckDuckGoSearchTool

agent = Agent(
    name="agent",
    tools=[DuckDuckGoSearchTool()],
    client=OpenAIClient(api_key="OPENAI_API_KEY", model="gpt-4.1"),
)

response = agent.run("What is datapizza? and who are the founders?", tool_choice="required_first")
print(response)
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Tools/filesystem/ ===

# FileSystem

## Installation

```
pip install datapizza-ai-tools-filesystem
```

## Overview

Provides a robust interface for `datapizza-ai` agents to perform various operations on the local file system: listing, reading, writing, creating, deleting, moving, copying, and precisely replacing content within files.

> ⚠️ **Warning: Risk of Data Loss and System Modification**
> Operations like `delete_file`, `delete_directory`, and `write_file` can lead to **permanent data loss** if not used carefully.

## Features

```python
list_directory(path: str)
read_file(file_path: str)
write_file(file_path: str, content: str)
create_directory(path: str)
delete_file(file_path: str)
delete_directory(path: str, recursive: bool = False)
move_item(source_path: str, destination_path: str)
copy_file(source_path: str, destination_path: str)
replace_in_file(file_path: str, old_string: str, new_string: str)
```

`replace_in_file` — Replaces a block of text only if it appears **exactly once** (requires context in `old_string` for safety).

## Usage Example

```python
import os
import tempfile
import shutil
from datapizza.tools.filesystem import FileSystem

fs_tool = FileSystem()

temp_dir_path = tempfile.mkdtemp()
print(f"Working in temporary directory: {temp_dir_path}")

fs_tool.create_directory(os.path.join(temp_dir_path, "my_folder"))
fs_tool.write_file(os.path.join(temp_dir_path, "my_folder", "my_file.txt"), "Hello, world!\nAnother line.")

fs_tool.replace_in_file(
    os.path.join(temp_dir_path, "my_folder", "my_file.txt"),
    old_string="Hello, world!",
    new_string="Goodbye, world!"
)

content = fs_tool.read_file(os.path.join(temp_dir_path, "my_folder", "my_file.txt"))
print(f"File content: {content}")

shutil.rmtree(temp_dir_path)
```

## Integration with Agents

```python
from datapizza.agents import Agent
from datapizza.clients.openai import OpenAIClient
from datapizza.tools.filesystem import FileSystem

fs_tool = FileSystem()

agent = Agent(
    name="filesystem_manager",
    client=OpenAIClient(api_key="YOUR_API_KEY"),
    system_prompt="You are an expert and careful file system manager.",
    tools=[
        fs_tool.list_directory,
        fs_tool.read_file,
        fs_tool.write_file,
        fs_tool.create_directory,
        fs_tool.delete_file,
        fs_tool.delete_directory,
        fs_tool.move_item,
        fs_tool.copy_file,
        fs_tool.replace_in_file,
    ]
)

response = agent.run("In the file 'test.txt', replace the line 'Hello!' with 'Hello, precisely!'")
print(response)
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Tools/SQLDatabase/ ===

# SQLDatabase

## Installation

```
pip install datapizza-ai-tools-sqldatabase
```

## datapizza.tools.SQLDatabase.SQLDatabase

A collection of tools to interact with a SQL database using SQLAlchemy.

### __init__

```python
__init__(db_uri: str)
```

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| db_uri | str | The database URI (e.g., `"sqlite:///my_database.db"`). | required |

### list_tables

```python
list_tables() -> str
```

Returns a newline-separated string of available table names in the database.

### get_table_schema

```python
get_table_schema(table_name: str) -> str
```

Returns the schema of a specific table in a human-readable format.

### run_sql_query

```python
run_sql_query(query: str) -> str
```

Executes a SQL query and returns the result.
- For `SELECT` statements: returns a JSON string of the rows.
- For other statements (`INSERT`, `UPDATE`, `DELETE`): returns a success message.

## Features

- Broad database support: SQLite, PostgreSQL, MySQL, and any SQLAlchemy-supported DB
- Schema inspection for context-aware querying
- Table listing to help agent orient itself

## Integration with Agents

```python
from datapizza.agents import Agent
from datapizza.clients.openai import OpenAIClient
from datapizza.tools.SQLDatabase import SQLDatabase

db_uri = "sqlite:///company.db"
db_tool = SQLDatabase(db_uri=db_uri)

agent = Agent(
    name="database_expert",
    client=OpenAIClient(api_key="YOUR_API_KEY"),
    system_prompt="You are a database expert. Use the available tools to answer questions about the database.",
    tools=[
        db_tool.list_tables,
        db_tool.get_table_schema,
        db_tool.run_sql_query
    ]
)

response = agent.run("How many people work in the Engineering department?")
print(response)
```

---

=== http://docs.datapizza.ai/0.0.9/API%20Reference/Tools/web_fetch/ ===

# WebFetch

## Installation

```
pip install datapizza-ai-tools-web-fetch
```

## datapizza.tools.web_fetch.base.WebFetchTool

Bases: `Tool`

The Web Fetch tool. Allows you to fetch the content of a given URL with configurable timeouts and specific error handling.

### __init__

```python
__init__(timeout=None, user_agent=None)
```

Parameters:

| Name | Type | Description | Default |
|------|------|-------------|---------|
| timeout | float \| None | The timeout for the request in seconds. | None |
| user_agent | str \| None | The User-Agent header to use for the request. | None |

### __call__

```python
__call__(url) -> str
```

Invoke the tool (fetch content from URL).

## Features

- Live web access: fetches content from any public URL
- Error handling for common HTTP errors (timeouts, 404, 503)
- Configurable timeouts and User-Agent strings
- Seamless integration with `datapizza-ai` agents

## Usage Example

```python
from datapizza.tools.web_fetch import WebFetchTool

fetch_tool = WebFetchTool()
content = fetch_tool("https://example.com")
print(content)
```

## Integration with Agents

```python
from datapizza.agents import Agent
from datapizza.clients.openai import OpenAIClient
from datapizza.tools.web_fetch import WebFetchTool

web_tool = WebFetchTool(timeout=15.0)

agent = Agent(
    name="web_researcher",
    client=OpenAIClient(api_key="YOUR_API_KEY"),
    system_prompt="You are a research assistant. Use the web_fetch tool to get information from URLs to answer questions.",
    tools=[web_tool]
)

response = agent.run("Please summarize the content of https://loremipsum.io/")
print(response.text)
```
