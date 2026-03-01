"""Diagnostic test for MCP calls: save_menu, update_restaurant_is_open, send_message."""
import asyncio
import aiohttp
from datapizza.tools.mcp_client import MCPClient

API_KEY = "dTpZhKpZ02-4ac2be8821b52df78bf06070"
BASE_URL = "https://hackapizza.datapizza.tech"
TEAM_ID = 17


async def get_restaurant_state():
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/restaurant/{TEAM_ID}",
            headers={"x-api-key": API_KEY},
        ) as resp:
            return await resp.json()


async def main():
    client = MCPClient(
        url=f"{BASE_URL}/mcp",
        headers={"x-api-key": API_KEY},
        timeout=30,
    )

    # 1. Check current state
    state = await get_restaurant_state()
    print("=== CURRENT STATE ===")
    print(f"  is_open: {state.get('is_open')}")
    print(f"  menu: {state.get('menu')}")
    print(f"  balance: {state.get('balance')}")
    print(f"  reputation: {state.get('reputation')}")
    inv = state.get("inventory", {})
    print(f"  inventory: {len(inv)} types, {sum(inv.values()) if inv else 0} units")
    print()

    # 2. Test save_menu
    test_menu = [
        {"name": "Sinfonia del Multiverso Calante", "price": 50},
        {"name": "Sinfonia del Multiverso", "price": 40},
    ]
    print(f"=== CALLING save_menu with {len(test_menu)} items ===")
    result = await client.call_tool("save_menu", {"items": test_menu})
    print(f"  isError: {result.isError}")
    for c in result.content:
        print(f"  content: {getattr(c, 'text', str(c))}")
    print()

    # Check state after
    state2 = await get_restaurant_state()
    print(f"  menu after save: {state2.get('menu')}")
    print()

    # 3. Test update_restaurant_is_open
    print("=== CALLING update_restaurant_is_open(true) ===")
    result2 = await client.call_tool("update_restaurant_is_open", {"is_open": True})
    print(f"  isError: {result2.isError}")
    for c in result2.content:
        print(f"  content: {getattr(c, 'text', str(c))}")

    state3 = await get_restaurant_state()
    print(f"  is_open after: {state3.get('is_open')}")
    print()

    # 4. Test send_message (to ourselves or another team)
    print("=== CALLING send_message ===")
    result3 = await client.call_tool("send_message", {
        "recipient_id": 1,  # some other team
        "text": "Test message from team 17",
    })
    print(f"  isError: {result3.isError}")
    for c in result3.content:
        print(f"  content: {getattr(c, 'text', str(c))}")
    print()

    # 5. Also check: what does the menu endpoint return?
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/restaurant/{TEAM_ID}/menu",
            headers={"x-api-key": API_KEY},
        ) as resp:
            menu_data = await resp.json()
            print(f"=== GET /restaurant/{TEAM_ID}/menu ===")
            print(f"  {menu_data}")


if __name__ == "__main__":
    asyncio.run(main())
