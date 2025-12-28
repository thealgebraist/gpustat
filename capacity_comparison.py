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
TOTAL_USERS = 10000
AVG_USAGE_HOURS_DAY = 1.0 # 1 hour of 3080 time per day

# Pricing and Capacity
# TensorDock: 1x RTX 3080
CHEAP_PRICE = 0.25
CHEAP_CAPACITY_UNITS = 1.0 # 1 RTX 3080 unit per server

# AWS: 8x H100
# 1x H100 is roughly 2.5x - 3x faster than a 3080 for general compute.
# 8x H100 * 2.5x factor = 20x RTX 3080 units per server
EXPENSIVE_PRICE = 98.32
EXPENSIVE_CAPACITY_UNITS = 20.0 

def haversine(lat1, lon1, lat2, lon2):
    R = 6371 
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

LATENCY_THRESHOLD_KM = 800.0 # ~5ms
MIN_SERVERS = 3 # 2-fault tolerance

num_cities = len(cities)
coverage_matrix = np.zeros((num_cities, num_cities))
for i in range(num_cities):
    for j in range(num_cities):
        if haversine(cities[i]['latitude'], cities[i]['longitude'], 
                     cities[j]['latitude'], cities[j]['longitude']) <= LATENCY_THRESHOLD_KM:
            coverage_matrix[i, j] = 1

def get_geo_coverage_pct(indices):
    if len(indices) < MIN_SERVERS: return 0
    server_counts = np.sum(coverage_matrix[:, indices], axis=1)
    mask = (server_counts >= MIN_SERVERS).astype(int)
    return np.sum(mask * [c['population'] for c in cities]) / total_pop

print(f"Scenario: 10,000 Users @ {AVG_USAGE_HOURS_DAY} hr/day of RTX 3080 time")
print(f"Constraints: 2-fault tolerance, 20ms sync, 5ms service latency\n")
print(f"{ 'N':>2} | {'Cheap Served':>12} | {'Exp Served':>12} | {'Cheap $/mo':>12} | {'Exp $/mo':>12}")
print("-" * 75)

selected_indices = []
for n in range(5, 31):
    # Greedy geographical expansion
    best_s = -1
    best_geo_pop = -1
    for s in range(num_cities):
        if s in selected_indices: continue
        pop = get_geo_coverage_pct(selected_indices + [s])
        if pop > best_geo_pop:
            best_geo_pop = pop
            best_s = s
    
    if best_s != -1:
        selected_indices.append(best_s)
    else:
        rem = [i for i in range(num_cities) if i not in selected_indices]
        if rem: selected_indices.append(rem[0])

    geo_cov_pct = get_geo_coverage_pct(selected_indices)
    geo_potential_users = TOTAL_USERS * geo_cov_pct
    
    # Capacity constraints
    # Total available user-hours per day = N * Capacity_Units * 24 hours
    cheap_daily_hours = n * CHEAP_CAPACITY_UNITS * 24
    exp_daily_hours = n * EXPENSIVE_CAPACITY_UNITS * 24
    
    # Users actually served is the minimum of geographical reach and compute capacity
    served_cheap = int(min(geo_potential_users, cheap_daily_hours / AVG_USAGE_HOURS_DAY))
    served_exp = int(min(geo_potential_users, exp_daily_hours / AVG_USAGE_HOURS_DAY))
    
    cost_cheap = n * CHEAP_PRICE * 24 * 30
    cost_exp = n * EXPENSIVE_PRICE * 24 * 30
    
    print(f"{n:2} | {served_cheap:12,d} | {served_exp:12,d} | ${cost_cheap:10,.0f} | ${cost_exp:10,.0f}")

print("\n(Note: 'Cheap' capacity is limited by GPU hours at this scale, 'Exp' serves all reached users.)")