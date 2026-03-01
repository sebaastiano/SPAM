"""Check MCP tool schemas to verify exact parameter names."""
import asyncio
from datapizza.tools.mcp_client import MCPClient

API_KEY = "dTpZhKpZ02-4ac2be8821b52df78bf06070"
BASE_URL = "https://hackapizza.datapizza.tech"


async def main():
    client = MCPClient(
        url=f"{BASE_URL}/mcp",
        headers={"x-api-key": API_KEY},
        timeout=30,
    )
    tools = await client.a_list_tools()
    for tool in tools:
        print(f"\n=== {tool.name} ===")
        print(f"  Description: {tool.description}")
        if tool.inputSchema:
            print(f"  Input schema: {tool.inputSchema}")


if __name__ == "__main__":
    asyncio.run(main())
