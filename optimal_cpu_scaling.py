import sqlite3
import math
import csv
import numpy as np

# 1. Load Population Data
cities = []
with open('cities.csv', mode='r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        row['population'] = int(row['population'])
        row['latitude'] = float(row['latitude'])
        row['longitude'] = float(row['longitude'])
        cities.append(row)

total_pop = sum(c['population'] for c in cities)

# 2. Regional Coordinates Mapping
region_map = {
    "eastus": (37.37, -78.78), "eastus2": (36.66, -78.38), "westus": (37.77, -122.41),
    "westus2": (47.23, -119.85), "southcentralus": (29.41, -98.50), "centralus": (41.59, -93.60),
    "northcentralus": (41.88, -87.62), "westcentralus": (41.59, -107.21),
    "canadacentral": (43.65, -79.38), "canadaeast": (46.81, -71.21),
    "us-east-1": (38.99, -77.45), "us-east-2": (40.09, -82.75), 
    "us-west-1": (37.44, -122.15), "us-west-2": (45.92, -119.27),
    "us-central1": (41.26, -95.93), "us-ashburn-1": (39.04, -77.48),
    "us-south": (29.76, -95.36), "NJ": (40.71, -74.00), "NY": (40.71, -74.00),
    "nyc3": (40.71, -74.00), "US-East": (40.00, -75.00), "US-West": (37.00, -120.00),
    "brazilsouth": (-23.55, -46.63), "southindia": (12.97, 77.59), "indonesiacentral": (-1.26, 116.82)
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371 
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# 3. Extract CPU sites from SQLite
conn = sqlite3.connect('prices.db')
cursor = conn.cursor()
cursor.execute("SELECT supplier, region, instance_type, price FROM prices WHERE category = 'cpu'")
rows = cursor.fetchall()
conn.close()

# Group by location, pick cheapest CPU per location
site_data = {}
for supplier, region, inst, price in rows:
    if region in region_map:
        lat, lon = region_map[region]
        key = (region, lat, lon)
        if key not in site_data or price < site_data[key]['price']:
            site_data[key] = {"supplier": supplier, "region": region, "type": inst, "price": price, "lat": lat, "lon": lon}

available_sites = list(site_data.values())
num_sites = len(available_sites)
num_cities = len(cities)

# 4. Precompute Coverage Matrix
LATENCY_THRESHOLD_KM = 800.0 # ~5ms
coverage_matrix = np.zeros((num_cities, num_sites))
for i, city in enumerate(cities):
    for j, site in enumerate(available_sites):
        if haversine(city['latitude'], city['longitude'], site['lat'], site['lon']) <= LATENCY_THRESHOLD_KM:
            coverage_matrix[i, j] = 1

def get_metrics(indices):
    if len(indices) < 3: return 0, 0
    server_counts = np.sum(coverage_matrix[:, indices], axis=1)
    # 2-fault tolerance: need 3 servers in range
    mask = (server_counts >= 3).astype(int)
    cov = np.sum(mask * [c['population'] for c in cities])
    cost = sum(available_sites[i]['price'] for i in indices)
    return cov, cost

print("OPTIMAL CPU CONFIGURATION SCALING (N=4 to 50)")
print("Constraints: 20ms sync, 2-fault tolerance (3x redundancy), 5ms latency\n")
print(f"{'N':>2} | {'Coverage %':>12} | {'Hourly Cost':>15} | {'Efficiency (Pop/$)':>15}")
print("-" * 65)

# 5. Iterative Scaling
selected_indices = []
for n in range(4, 51):
    best_idx = -1
    best_val = -1
    
    # Greedy step
    for i in range(num_sites):
        if i in selected_indices: continue
        test_indices = selected_indices + [i]
        cov, cost = get_metrics(test_indices)
        # We want to maximize coverage, then minimize cost
        if cost > 0:
            val = cov / cost 
        else:
            val = cov
            
        if val > best_val:
            best_val = val
            best_idx = i
            
    if best_idx != -1:
        selected_indices.append(best_idx)
    else:
        # If we run out of unique sites, we can repeat the cheapest site to increase fault tolerance
        cheapest_site_idx = np.argmin([s['price'] for s in available_sites])
        selected_indices.append(cheapest_site_idx)

    curr_cov, curr_cost = get_metrics(selected_indices)
    eff = curr_cov / curr_cost if curr_cost > 0 else 0
    print(f"{n:2} | {curr_cov/total_pop*100:11.2f}% | ${curr_cost:14.4f} | {eff:15.0f}")

print("\nTop 5 Sites used in Optimal Configuration:")
for idx in selected_indices[:5]:
    s = available_sites[idx]
    print(f"- {s['supplier']} in {s['region']} ({s['type']}): ${s['price']}/hr")
