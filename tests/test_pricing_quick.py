"""Quick functional test of intelligence-driven pricing logic."""
from src.decision.ilp_solver import compute_menu_price, compute_bid_price

# Test 1: Monopoly scenario (no competitors)
price_monopoly = compute_menu_price(
    {'name': 'Test Dish', 'prestige': 80},
    'PREMIUM_MONOPOLIST',
    100.0,
    {}
)
print(f'Monopoly menu price: {price_monopoly}')
assert price_monopoly > 0, "Price must be positive"

# Test 2: No-intel menu price
price_no_intel = compute_menu_price(
    {'name': 'Test Dish', 'prestige': 80},
    'PREMIUM_MONOPOLIST',
    100.0,
    None
)
print(f'No-intel menu price: {price_no_intel}')
assert price_no_intel > 0

# Test 3: Bid price with no competition
bid_no_comp = compute_bid_price('Essenza di Stellapolvere', {}, {})
print(f'Bid price (no competition): {bid_no_comp}')
assert bid_no_comp == 18, f"Expected 18 for monopoly bid (non-high-delta floor), got {bid_no_comp}"

# Test 4: Bid price with dormant/disconnected competitors
# NOTE: These briefings have is_connected defaulting to False (not set),
# so they are correctly treated as inactive/disconnected.
dormant_briefings = {
    1: {'is_active': True, 'menu_size': 0, 'strategy': 'DORMANT'},
    2: {'is_active': False, 'menu_size': 0, 'strategy': 'DORMANT'},
}
bid_dormant = compute_bid_price('Essenza di Stellapolvere', dormant_briefings, {})
print(f'Bid price (dormant competitors): {bid_dormant}')
assert bid_dormant == 18, f"Expected 18 for dormant (no is_connected), got {bid_dormant}"

# Test 5: Active competitor wanting same ingredient
# NOTE: is_connected=True is required for the competitor to count as active
active_briefings = {
    1: {
        'is_connected': True,
        'menu_size': 3,
        'strategy': 'AGGRESSIVE_HOARDER',
        'top_bid_ingredients': ['Essenza di Stellapolvere'],
        'predicted_bid_spend': 100,
        'menu_price_avg': 120,
    },
}
bid_active = compute_bid_price(
    'Essenza di Stellapolvere',
    active_briefings,
    {'Essenza di Stellapolvere': 5},
)
print(f'Bid price (active competitor): {bid_active}')
assert bid_active > 18, f"Should bid higher against active connected competitor"

# Test 6: Menu price with active competition
price_active = compute_menu_price(
    {'name': 'Test Dish', 'prestige': 80},
    'PREMIUM_MONOPOLIST',
    100.0,
    active_briefings,
)
print(f'Active competition menu price: {price_active}')
assert price_active > 0

# Test 7: Zone selector monopoly
from src.decision.zone_selector import select_zone
zone = select_zone(
    competitor_briefings={},
    competitor_clusters={},
    reputation=100.0,
    balance=10000.0,
    inventory={'Essenza di Stellapolvere': 5},
    recipes=[{'name': 'Test', 'ingredients': {'Essenza di Stellapolvere': 1}, 'prestige': 80}],
)
print(f'Zone with no competition: {zone}')
assert zone == 'PREMIUM_MONOPOLIST', f"Expected PREMIUM_MONOPOLIST, got {zone}"

print()
print('=== ALL TESTS PASS ===')
