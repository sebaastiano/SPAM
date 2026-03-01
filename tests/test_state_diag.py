"""Quick diagnostic: print full restaurant state and check field names."""
import asyncio
import aiohttp
import json

API_KEY = "dTpZhKpZ02-4ac2be8821b52df78bf06070"
BASE_URL = "https://hackapizza.datapizza.tech"
TEAM_ID = 17


async def main():
    async with aiohttp.ClientSession() as session:
        # Full restaurant state
        async with session.get(
            f"{BASE_URL}/restaurant/{TEAM_ID}",
            headers={"x-api-key": API_KEY},
        ) as resp:
            data = await resp.json()
            print("=== FULL RESTAURANT JSON ===")
            print(json.dumps(data, indent=2, ensure_ascii=False))

        # Check all restaurants to see is_open field for others
        async with session.get(
            f"{BASE_URL}/restaurants",
            headers={"x-api-key": API_KEY},
        ) as resp:
            all_r = await resp.json()
            print("\n=== OTHER RESTAURANTS is_open ===")
            if isinstance(all_r, list):
                for r in all_r[:5]:
                    print(f"  {r.get('name', '?')}: is_open={r.get('is_open', 'N/A')}, "
                          f"isOpen={r.get('isOpen', 'N/A')}, "
                          f"menu_len={len(r.get('menu', {}).get('items', [])) if isinstance(r.get('menu'), dict) else len(r.get('menu', []))}")
            elif isinstance(all_r, dict):
                for k, r in list(all_r.items())[:5]:
                    print(f"  {k}: {r}")

        # Check meals for current turn
        for turn_id in [44, 45, 46, 47, 48]:
            async with session.get(
                f"{BASE_URL}/meals?turn_id={turn_id}&restaurant_id={TEAM_ID}",
                headers={"x-api-key": API_KEY},
            ) as resp:
                if resp.status == 200:
                    meals = await resp.json()
                    print(f"\n=== MEALS turn {turn_id} ({len(meals)} entries) ===")
                    if meals:
                        print(json.dumps(meals[:2], indent=2, ensure_ascii=False))
                else:
                    print(f"\n=== MEALS turn {turn_id}: HTTP {resp.status} ===")


if __name__ == "__main__":
    asyncio.run(main())
