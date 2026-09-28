# -----------------------------------------------------------------------
# Static game data. This is the file to edit to rebalance the economy —
# nothing here is hardcoded into the engine logic in main.py.
# -----------------------------------------------------------------------

# Resource id -> (display name, mohurs to extract one unit)
RESOURCES = {
    "farm_produce": ("Farm produce", 6),
    "timber": ("Timber", 4),
    "fish": ("Fish", 7),
    "stone_sand": ("Stone and sand", 3),
    "freshwater": ("Freshwater", 2),
    "coal": ("Coal", 5),
    "iron_ore": ("Iron ore", 5),
    "crude_oil": ("Crude oil", 11),
    "natural_gas": ("Natural gas", 8),
    "copper_ore": ("Copper ore", 8),
    "bauxite": ("Bauxite", 6),
    "lithium": ("Lithium", 20),
    "rare_earths": ("Rare earths", 30),
    "energy": ("Energy", 7),
}

# Product id -> dict:
#   name, category (which resource chain it belongs to, for grouping in the UI),
#   inputs: list of (item_id, qty) where item_id is "res:<resource_id>" or "prod:<product_id>",
#   sell_low / sell_high: reference sell price range (midpoint used as the default
#     value for the live Round 1 leaderboard estimate — NOT the official score),
#   energy_yield: units of energy produced as a free byproduct per unit made (0 if none)
PRODUCTS = {
    # ---- Farmland ----
    "packaged_food": {"name": "Packaged food", "category": "Farmland",
                       "inputs": [("res:farm_produce", 2)], "sell_low": 12, "sell_high": 16},
    "textiles": {"name": "Textiles", "category": "Farmland",
                 "inputs": [("res:farm_produce", 3)], "sell_low": 18, "sell_high": 23},
    "biofuel": {"name": "Biofuel", "category": "Farmland",
                "inputs": [("res:farm_produce", 4)], "sell_low": 24, "sell_high": 48},
    "bioplastics": {"name": "Bioplastics", "category": "Farmland",
                    "inputs": [("res:farm_produce", 6)], "sell_low": 36, "sell_high": 94},
    # ---- Timber ----
    "sawn_lumber": {"name": "Sawn lumber", "category": "Timber",
                    "inputs": [("res:timber", 2)], "sell_low": 8, "sell_high": 10},
    "paper_pulp": {"name": "Paper and pulp", "category": "Timber",
                   "inputs": [("res:timber", 3)], "sell_low": 12, "sell_high": 19},
    "furniture": {"name": "Furniture and plywood", "category": "Timber",
                  "inputs": [("prod:sawn_lumber", 2)], "sell_low": 20, "sell_high": 40},
    "biomass_power": {"name": "Biomass power", "category": "Timber",
                       "inputs": [("res:timber", 3)], "sell_low": 12, "sell_high": 14, "energy_yield": 2},
    # ---- Fisheries ----
    "dried_fish": {"name": "Dried fish", "category": "Fisheries",
                   "inputs": [("res:fish", 2)], "sell_low": 14, "sell_high": 18},
    "canned_seafood": {"name": "Canned seafood", "category": "Fisheries",
                       "inputs": [("res:fish", 3)], "sell_low": 21, "sell_high": 34},
    "fish_meal_oil": {"name": "Fish meal and oil", "category": "Fisheries",
                      "inputs": [("res:fish", 4)], "sell_low": 28, "sell_high": 56},
    "marine_biotech": {"name": "Marine biotech compounds", "category": "Fisheries",
                       "inputs": [("res:fish", 6)], "sell_low": 42, "sell_high": 147},
    # ---- Stone and sand ----
    "aggregate": {"name": "Aggregate", "category": "Stone and sand",
                  "inputs": [("res:stone_sand", 2)], "sell_low": 6, "sell_high": 8},
    "glass": {"name": "Glass", "category": "Stone and sand",
              "inputs": [("res:stone_sand", 4)], "sell_low": 12, "sell_high": 19},
    "cement": {"name": "Cement", "category": "Stone and sand",
               "inputs": [("res:stone_sand", 3), ("res:coal", 1)], "sell_low": 14, "sell_high": 22},
    "silicon": {"name": "Solar-grade silicon", "category": "Stone and sand",
                "inputs": [("res:stone_sand", 8)], "sell_low": 24, "sell_high": 84},
    # ---- Freshwater ----
    "treated_water": {"name": "Treated water", "category": "Freshwater",
                      "inputs": [("res:freshwater", 2)], "sell_low": 4, "sell_high": 5},
    "hydropower": {"name": "Hydropower", "category": "Freshwater",
                   "inputs": [("res:freshwater", 3)], "sell_low": 6, "sell_high": 21, "energy_yield": 3},
    # ---- Coal ----
    "coke": {"name": "Coke", "category": "Coal",
             "inputs": [("res:coal", 2)], "sell_low": 10, "sell_high": 13},
    "coal_power": {"name": "Coal power", "category": "Coal",
                   "inputs": [("res:coal", 2)], "sell_low": 10, "sell_high": 14, "energy_yield": 2},
    "coal_chemicals": {"name": "Coal chemicals", "category": "Coal",
                       "inputs": [("res:coal", 4)], "sell_low": 20, "sell_high": 40},
    # ---- Iron ore ----
    "pig_iron": {"name": "Pig iron", "category": "Iron ore",
                 "inputs": [("res:iron_ore", 2)], "sell_low": 10, "sell_high": 13},
    "steel": {"name": "Steel", "category": "Iron ore",
              "inputs": [("res:iron_ore", 2), ("res:coal", 1)], "sell_low": 15, "sell_high": 24},
    "structural_steel": {"name": "Structural steel", "category": "Iron ore",
                         "inputs": [("prod:steel", 2)], "sell_low": 48, "sell_high": 77},
    "heavy_machinery": {"name": "Heavy machinery", "category": "Iron ore",
                        "inputs": [("prod:steel", 3), ("prod:copper_wire", 1)], "sell_low": 127, "sell_high": 203},
    # ---- Copper ----
    "refined_copper": {"name": "Refined copper", "category": "Copper",
                       "inputs": [("res:copper_ore", 2)], "sell_low": 16, "sell_high": 21},
    "copper_wire": {"name": "Copper wire and cable", "category": "Copper",
                    "inputs": [("prod:refined_copper", 2)], "sell_low": 42, "sell_high": 55},
    "electric_motor": {"name": "Electric motors", "category": "Copper",
                       "inputs": [("prod:steel", 1), ("prod:copper_wire", 1)], "sell_low": 79, "sell_high": 126},
    # ---- Bauxite ----
    "alumina": {"name": "Alumina", "category": "Bauxite",
                "inputs": [("res:bauxite", 3)], "sell_low": 18, "sell_high": 23},
    "aluminium": {"name": "Aluminium", "category": "Bauxite",
                  "inputs": [("prod:alumina", 2), ("res:energy", 3)], "sell_low": 67, "sell_high": 87},
    "alloy": {"name": "Aircraft-grade alloys", "category": "Bauxite",
              "inputs": [("prod:aluminium", 2)], "sell_low": 174, "sell_high": 278},
    # ---- Crude oil ----
    "petroleum_fuel": {"name": "Petroleum fuel", "category": "Crude oil",
                       "inputs": [("res:crude_oil", 2)], "sell_low": 22, "sell_high": 29},
    "lubricants": {"name": "Lubricants and asphalt", "category": "Crude oil",
                   "inputs": [("res:crude_oil", 3)], "sell_low": 33, "sell_high": 53},
    "plastics": {"name": "Plastics", "category": "Crude oil",
                 "inputs": [("res:crude_oil", 3), ("res:natural_gas", 1)], "sell_low": 41, "sell_high": 82},
    "synthetic_rubber": {"name": "Synthetic rubber", "category": "Crude oil",
                         "inputs": [("res:crude_oil", 4)], "sell_low": 44, "sell_high": 88},
    "pharma": {"name": "Pharmaceuticals", "category": "Crude oil",
               "inputs": [("res:crude_oil", 6)], "sell_low": 66, "sell_high": 231},
    # ---- Natural gas ----
    "heating_gas": {"name": "Heating and cooking gas", "category": "Natural gas",
                    "inputs": [("res:natural_gas", 2)], "sell_low": 16, "sell_high": 21},
    "gas_power": {"name": "Gas power", "category": "Natural gas",
                  "inputs": [("res:natural_gas", 2)], "sell_low": 16, "sell_high": 21, "energy_yield": 3},
    "fertilizer": {"name": "Fertilizer", "category": "Natural gas",
                   "inputs": [("res:natural_gas", 3)], "sell_low": 24, "sell_high": 38},
    "lng_export": {"name": "Liquefied gas for export", "category": "Natural gas",
                   "inputs": [("res:natural_gas", 4)], "sell_low": 32, "sell_high": 64},
    "hydrogen_fuel": {"name": "Hydrogen fuel", "category": "Natural gas",
                      "inputs": [("res:natural_gas", 5)], "sell_low": 40, "sell_high": 140},
    # ---- Lithium ----
    "lithium_carbonate": {"name": "Lithium carbonate", "category": "Lithium",
                          "inputs": [("res:lithium", 3)], "sell_low": 60, "sell_high": 78},
    "battery": {"name": "Batteries", "category": "Lithium",
                "inputs": [("prod:lithium_carbonate", 2), ("prod:refined_copper", 1)], "sell_low": 177, "sell_high": 283},
    # ---- Rare earths ----
    "rare_earth_oxide": {"name": "Rare-earth oxides", "category": "Rare earths",
                         "inputs": [("res:rare_earths", 2)], "sell_low": 60, "sell_high": 78},
    "magnet": {"name": "Permanent magnets", "category": "Rare earths",
               "inputs": [("prod:rare_earth_oxide", 2)], "sell_low": 156, "sell_high": 250},
    "precision_electronics": {"name": "Precision electronics and radar", "category": "Rare earths",
                              "inputs": [("prod:magnet", 1), ("prod:circuit_board", 1)], "sell_low": 414, "sell_high": 538},
    # ---- Cross-chain (need inputs from several resource chains — forces trade) ----
    "automobiles": {"name": "Automobiles", "category": "Cross-chain",
                    "inputs": [("prod:steel", 3), ("prod:plastics", 1), ("prod:synthetic_rubber", 1)],
                    "sell_low": 242, "sell_high": 314},
    "circuit_board": {"name": "Circuit boards", "category": "Cross-chain",
                      "inputs": [("prod:refined_copper", 2), ("prod:silicon", 1)], "sell_low": 126, "sell_high": 164},
    "solar_panel": {"name": "Solar panels", "category": "Cross-chain",
                    "inputs": [("prod:silicon", 2), ("prod:aluminium", 1), ("prod:glass", 1)],
                    "sell_low": 274, "sell_high": 356},
    "aircraft_parts": {"name": "Aircraft parts", "category": "Cross-chain",
                       "inputs": [("prod:alloy", 1), ("prod:electric_motor", 1), ("prod:circuit_board", 1)],
                       "sell_low": 568, "sell_high": 738},
    "electric_vehicle": {"name": "Electric vehicles", "category": "Cross-chain",
                         "inputs": [("prod:battery", 1), ("prod:steel", 3), ("prod:electric_motor", 1), ("prod:circuit_board", 1)],
                         "sell_low": 645, "sell_high": 838},
    "satellite": {"name": "Satellites", "category": "Cross-chain",
                  "inputs": [("prod:magnet", 2), ("prod:circuit_board", 3), ("prod:alloy", 1), ("prod:hydrogen_fuel", 1)],
                  "sell_low": 1410, "sell_high": 1833},
}

# The 15 national crises. "requirement_text" is shown to the team privately;
# it is NOT enforced by the software (Round 3 is judged manually) — it exists
# so the audit / position paper has something concrete to reference.
CRISES = {
    "drought": {"name": "Drought", "requirement_text": "40 treated water + 25 packaged food, sustained for 3 turns."},
    "famine": {"name": "Famine", "requirement_text": "60 packaged food, or 30 packaged food + 20 fertilizer to replant."},
    "blackout": {"name": "Energy blackout", "requirement_text": "50 units of energy from any source, within 1 turn."},
    "disease": {"name": "Disease outbreak", "requirement_text": "30 pharmaceuticals + 20 treated water, over 3 turns."},
    "housing_collapse": {"name": "Housing collapse", "requirement_text": "40 cement + 25 structural steel to rebuild."},
    "transport_failure": {"name": "Transport network failure", "requirement_text": "35 structural steel + 20 petroleum fuel."},
    "fuel_shortage": {"name": "Fuel shortage", "requirement_text": "45 petroleum fuel, or 30 natural gas, or 25 hydrogen fuel."},
    "industrial_accident": {"name": "Industrial accident", "requirement_text": "30 steel + 15 heavy machinery to rebuild."},
    "currency_shock": {"name": "Currency shock", "requirement_text": "Liquidate 200 mohurs of Tier-3+ products at market, immediately."},
    "cyberattack": {"name": "Cyberattack", "requirement_text": "20 circuit boards to patch critical systems."},
    "comms_blackout": {"name": "Communications blackout", "requirement_text": "25 copper wire and cable + 15 circuit boards."},
    "heatwave": {"name": "Heatwave / cold snap", "requirement_text": "40 energy (any source) + 20 treated water."},
    "coastal_storm": {"name": "Coastal storm", "requirement_text": "35 cement + 20 structural steel."},
    "toxic_spill": {"name": "Toxic spill", "requirement_text": "25 bioplastics to contain and clean."},
    "refugee_influx": {"name": "Refugee influx", "requirement_text": "50 packaged food + 30 treated water + 25 cement."},
}

# 15 countries with the event team's FINALIZED resource/crisis assignment
# (confirmed 2026-09-24 — this is their own final call, not an AI-generated
# draft). Country display names and their separate access codes are listed
# below. Resource and crisis assignments are kept here as the event team's
# finalized setup; the rest of the code refers to countries by their data.
_COUNTRY_SETUP = [
    ("Matsyadhara",  ["farm_produce", "fish", "lithium"],           "blackout",             "UVAW9E"),
    ("Annashila",    ["farm_produce", "stone_sand", "freshwater"],  "fuel_shortage",        "HPXZSP"),
    ("Ratnashail",   ["farm_produce", "stone_sand", "rare_earths"], "heatwave",             "UMHSDN"),
    ("Jaldhaan",     ["farm_produce", "freshwater", "bauxite"],     "transport_failure",    "7VS44S"),
    ("Vanshail",     ["timber", "stone_sand", "rare_earths"],       "industrial_accident",  "R6AUJA"),
    ("Koylavan",     ["timber", "coal", "rare_earths"],             "cyberattack",           "XNXB8A"),
    ("Vanratna",     ["timber", "crude_oil", "lithium"],            "refugee_influx",        "45MGM9"),
    ("Matsyaneer",   ["fish", "freshwater", "bauxite"],             "toxic_spill",           "NTJJWB"),
    ("Tamrameen",    ["fish", "coal", "copper_ore"],                "currency_shock",        "32UN3N"),
    ("Matsyaloh",    ["fish", "iron_ore", "crude_oil"],             "famine",                "8VNSVH"),
    ("Lohagiri",     ["stone_sand", "iron_ore", "natural_gas"],     "disease",               "Z6QBB3"),
    ("Jaltej",       ["freshwater", "crude_oil", "bauxite"],        "coastal_storm",         "EM885U"),
    ("Lohkhan",      ["coal", "iron_ore", "bauxite"],               "comms_blackout",       "8KHG36"),
    ("Urjaratna",    ["natural_gas", "copper_ore", "lithium"],      "drought",               "EN54V7"),
    ("Dhaturatna",   ["natural_gas", "copper_ore", "rare_earths"],  "housing_collapse",     "C4HCWQ"),
]

COUNTRIES = []
for name, res, crisis, access_code in _COUNTRY_SETUP:
    COUNTRIES.append({"name": name, "resources": res, "crisis": crisis, "access_code": access_code})

STARTING_TREASURY = 1000
STARTING_POPULATION = 1_000_000
BASE_CAPACITY = 35
FACTORY_BASE_CAPACITY = 35
FACTORY_LEVEL_COST = {1: 10, 2: 20, 3: 30}   # cost to go FROM level-1 TO this level
FACTORY_LEVEL_BONUS = 5                       # extra capacity per level, per factory
NEW_FACTORY_COST = 80

TRADE_CAPACITY_BASE = 10
TRADE_CAPACITY_TIERS = [  # (tier number, cost, capacity AFTER buying this tier)
    (1, 20, 20),
    (2, 40, 40),
    (3, 60, 90),
]

ADMIN_PASSWORD = "todarmal2026"  # change before the event
MAX_SESSIONS_PER_TEAM = 1
SESSION_TIMEOUT_SECONDS = 90
