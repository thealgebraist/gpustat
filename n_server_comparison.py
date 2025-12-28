import json
import math
import csv
import numpy as np

# 1. Load Data
cities = []
with open('cities.csv', mode='r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        row['population'] = int(row['population'])
        row['latitude'] = float(row['latitude'])
        row['longitude'] = float(row['longitude'])
        cities.append(row)

# Curated Pricing from database
CHEAP_COMPANY = "TensorDock"
CHEAP_TYPE = "1x NVIDIA RTX 3080"
CHEAP_PRICE = 0.25

EXPENSIVE_COMPANY = "AWS"
EXPENSIVE_TYPE = "p5.48xlarge (8xH100)"
EXPENSIVE_PRICE = 98.32

def haversine(lat1, lon1, lat2, lon2):
    R = 6371 
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

SYNC_DIST_KM = 4000.0 # ~20ms
LATENCY_THRESHOLD_KM = 800.0 # ~5ms
MIN_SERVERS_FOR_COVERAGE = 3 # 2-fault tolerance
total_pop = sum(c['population'] for c in cities)

num_cities = len(cities)
# We treat each city as a potential server site
coverage_matrix = np.zeros((num_cities, num_cities))
for i in range(num_cities):
    for j in range(num_cities):
        if haversine(cities[i]['latitude'], cities[i]['longitude'], 
                     cities[j]['latitude'], cities[j]['longitude']) <= LATENCY_THRESHOLD_KM:
            coverage_matrix[i, j] = 1

def get_coverage(indices):
    if len(indices) < MIN_SERVERS_FOR_COVERAGE: return 0
    server_counts = np.sum(coverage_matrix[:, indices], axis=1)
    mask = (server_counts >= MIN_SERVERS_FOR_COVERAGE).astype(int)
    return np.sum(mask * [c['population'] for c in cities])

print(f"Comparison: {CHEAP_COMPANY} (${CHEAP_PRICE}/hr) vs {EXPENSIVE_COMPANY} (${EXPENSIVE_PRICE}/hr)")
print(f"Constraints: 20ms sync, 2-fault tolerance (3 servers per city), 5ms user latency\n")
print(f"{'N':>2} | {'Coverage %':>10} | {'Cheapest ($/hr)':>15} | {'Expensivest ($/hr)':>18} | {'Monthly Diff ($)':>15}")
print("-" * 75)

selected_indices = []
for n in range(5, 31):
    # Greedy expansion for coverage
    best_s = -1
    best_pop = -1
    for s in range(num_cities):
        if s in selected_indices: continue
        pop = get_coverage(selected_indices + [s])
        if pop > best_pop:
            best_pop = pop
            best_s = s
    
    if best_s != -1:
        selected_indices.append(best_s)
    else:
        # Pick largest population city if no improvement
        rem = [i for i in range(num_cities) if i not in selected_indices]
        if rem: selected_indices.append(rem[0])

    cov_pct = get_coverage(selected_indices) / total_pop * 100
    cost_cheap = n * CHEAP_PRICE
    cost_exp = n * EXPENSIVE_PRICE
    monthly_diff = (cost_exp - cost_cheap) * 24 * 30
    
    print(f"{n:2} | {cov_pct:9.2f}% | {cost_cheap:15.2f} | {cost_exp:18.2f} | {monthly_diff:15.0f}")

print("\nFinal Config (N=30) Locations:")
for idx in selected_indices:
    print(f"- {cities[idx]['city']}")
