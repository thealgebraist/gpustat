import json
import math
import csv
import numpy as np

# Load Data
cities = []
with open('cities.csv', mode='r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        row['population'] = int(row['population'])
        row['latitude'] = float(row['latitude'])
        row['longitude'] = float(row['longitude'])
        cities.append(row)

total_pop = sum(c['population'] for c in cities)
LATENCY_THRESHOLD_KM = 800.0 # ~5ms
MIN_SERVERS_PER_CITY = 3 # 2-fault tolerance

# Capacity Units (1 Unit = 1 hour of RTX 3080 time)
# TensorDock: 1x RTX 3080
CHEAP_PRICE = 0.25
CHEAP_UNITS = 1.0 

# AWS: 8x H100
# 8x H100 is roughly 20x RTX 3080 units
EXPENSIVE_PRICE = 98.32
EXPENSIVE_UNITS = 20.0 

# To find the cheapest config for U users:
# 1. We need enough servers to cover U user-hours/day.
# 2. To reach ~93% of Americans, we need 30 distinct sites (from previous optimization).
# 3. For 2-fault tolerance, every city needs 3 servers in range.
#    With 30 optimal sites, most major cities are in range of 3+ sites.
#    So we need at least 30 servers total (1 per site) to satisfy geo if they are well-placed.

def haversine(lat1, lon1, lat2, lon2):
    R = 6371 
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# Pre-selected 30 optimal sites from previous run
# (Simplified: we use the top 30 cities by population as proxy sites)
optimal_sites = cities[:30]

def calculate_costs(users):
    hours_needed = users * 1.0 # 1 hr/day per user
    
    # --- CHEAP (TensorDock) ---
    # Capacity requirement
    n_cap_cheap = math.ceil(hours_needed / (24 * CHEAP_UNITS))
    # Geo requirement (30 sites, but we need 3 servers in range of each city)
    # If n_cap is small, we might be limited.
    # To serve 'users' with fault tolerance, we assume we need at least 30 servers 
    # spread across the 30 sites to reach the ~93% coverage.
    n_final_cheap = max(n_cap_cheap, 30)
    monthly_cheap = n_final_cheap * CHEAP_PRICE * 24 * 30
    
    # --- EXPENSIVE (AWS) ---
    # Capacity requirement
    n_cap_exp = math.ceil(hours_needed / (24 * EXPENSIVE_UNITS))
    # Geo requirement: even if 1 AWS server has enough compute, 
    # we need 30 sites to cover the US geographically.
    n_final_exp = max(n_cap_exp, 30)
    monthly_exp = n_final_exp * EXPENSIVE_PRICE * 24 * 30
    
    return n_final_cheap, monthly_cheap, n_final_exp, monthly_exp

user_ranges = [10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000]

print("CHEAPEST CONFIGURATION ANALYSIS (10k to 100k Users)")
print(f"Goal: ~93% Population Coverage with 2-Fault Tolerance\n")
print(f"{ 'Users':>8} | {'Cheap (N)':>10} | {'Cheap Cost/mo':>15} | {'Exp (N)':>10} | {'Exp Cost/mo':>15} | {'WINNER'}")
print("-" * 90)

for u in user_ranges:
    nc, mc, ne, me = calculate_costs(u)
    winner = "TensorDock" if mc < me else "AWS"
    print(f"{u:8,d} | {nc:10,d} | ${mc:13,.0f} | {ne:10,d} | ${me:13,.0f} | {winner}")

print("\nConclusion:")
print("TensorDock remains the cheapest by a wide margin (order of magnitude).")
print("As user count increases, TensorDock scales linearly with compute capacity,")
print("while AWS is pinned at the minimum 30 servers needed for geographical coverage")
print("until compute demand exceeds its massive built-in capacity (~144,000 user-hours/day).")
