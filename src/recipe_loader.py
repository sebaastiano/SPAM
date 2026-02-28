"""
SPAM! — Recipe Database Loader
================================
Fetches and normalizes recipes from the game server.
"""

import logging

import aiohttp

from src.config import BASE_URL, HEADERS

logger = logging.getLogger("spam.recipe_loader")


async def load_recipes() -> dict[str, dict]:
    """
    Fetch all recipes from GET /recipes and normalise into a dict.

    Returns:
        dict mapping recipe_name → {
            name: str,
            ingredients: dict[str, int],  # ingredient_name → quantity
            prestige: float,
            prep_time: float,
        }
    """
    url = f"{BASE_URL}/recipes"
    headers = {
        "x-api-key": HEADERS["x-api-key"],
        "Accept": "application/json",
    }

    recipe_db: dict[str, dict] = {}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    logger.error(f"Failed to load recipes: HTTP {resp.status}")
                    return recipe_db

                data = await resp.json()
                logger.info(f"Loaded {len(data)} raw recipes from server")

                for recipe in data:
                    name = recipe.get("name", "")
                    if not name:
                        continue

                    # Normalise ingredient format
                    raw_ingredients = recipe.get("ingredients", {})
                    if isinstance(raw_ingredients, list):
                        # Some formats list ingredients as [{name, quantity}]
                        ingredients = {}
                        for ing in raw_ingredients:
                            if isinstance(ing, dict):
                                ing_name = ing.get("name", ing.get("ingredient", ""))
                                ing_qty = ing.get("quantity", ing.get("qty", 1))
                                if ing_name:
                                    ingredients[ing_name] = int(ing_qty)
                            elif isinstance(ing, str):
                                ingredients[ing] = 1
                    elif isinstance(raw_ingredients, dict):
                        ingredients = {
                            k: int(v) for k, v in raw_ingredients.items()
                        }
                    else:
                        ingredients = {}

                    recipe_db[name] = {
                        "name": name,
                        "ingredients": ingredients,
                        "prestige": float(recipe.get("prestige", 50)),
                        "prep_time": float(
                            recipe.get("prep_time", recipe.get("prepTime", 5.0))
                        ),
                    }

                logger.info(f"Normalised {len(recipe_db)} recipes")

    except Exception as e:
        logger.error(f"Error loading recipes: {e}", exc_info=True)

    return recipe_db


async def load_our_restaurant() -> dict:
    """Fetch our restaurant state from GET /restaurant/17."""
    url = f"{BASE_URL}/restaurant/17"
    headers = {
        "x-api-key": HEADERS["x-api-key"],
        "Accept": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.error(f"Failed to load our restaurant: HTTP {resp.status}")
    except Exception as e:
        logger.error(f"Error loading restaurant: {e}", exc_info=True)

    return {}
