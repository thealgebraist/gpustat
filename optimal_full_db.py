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

# 2. Map Regions to Coordinates
# Common Cloud Regions
region_map = {
    # Azure
    "eastus": (37.37, -78.78), "eastus2": (36.66, -78.38), "westus": (37.77, -122.41),
    "westus2": (47.23, -119.85), "southcentralus": (29.41, -98.50), "centralus": (41.59, -93.60),
    "northcentralus": (41.88, -87.62), "westcentralus": (41.59, -107.21),
    # AWS/GCP (from previous)
    "us-east-1": (38.99, -77.45), "us-east-2": (40.09, -82.75), 
    "us-west-1": (37.44, -122.15), "us-west-2": (45.92, -119.27),
    "us-central1": (41.26, -95.93), "us-ashburn-1": (39.04, -77.48),
    "us-south": (29.76, -95.36), "NJ": (40.71, -74.00), "NY": (40.71, -74.00),
    "nyc3": (40.71, -74.00), "US-East": (40.00, -75.00), "US-West": (37.00, -120.00)
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371 
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# 3. Extract GPU sites from SQLite
conn = sqlite3.connect('prices.db')
cursor = conn.cursor()
cursor.execute("SELECT supplier, region, instance_type, price FROM prices WHERE category = 'gpu'")
rows = cursor.fetchall()
conn.close()

# Consolidate: Find cheapest GPU at each unique location
site_data = {}
for supplier, region, inst, price in rows:
    if region in region_map:
        lat, lon = region_map[region]
        key = (region, lat, lon)
        if key not in site_data or price < site_data[key]['price']:
            site_data[key] = {"supplier": supplier, "region": region, "type": inst, "price": price, "lat": lat, "lon": lon}

available_sites = list(site_data.values())
num_sites = len(available_sites)
print(f"Loaded {len(rows)} GPU entries. Consolidated into {num_sites} unique geographic sites.")

# 4. Coverage Matrix (Cities x Sites)
LATENCY_THRESHOLD_KM = 800.0 # 5ms
coverage_matrix = np.zeros((len(cities), num_sites))
for i, city in enumerate(cities):
    for j, site in enumerate(available_sites):
        if haversine(city['latitude'], city['longitude'], site['lat'], site['lon']) <= LATENCY_THRESHOLD_KM:
            coverage_matrix[i, j] = 1

def get_performance(indices):
    if len(indices) < 3: return 0, 0
    # 2-fault tolerance: city needs 3 servers in range
    server_counts = np.sum(coverage_matrix[:, indices], axis=1)
    mask = (server_counts >= 3).astype(int)
    cov = np.sum(mask * [c['population'] for c in cities])
    cost = sum(available_sites[i]['price'] for i in indices)
    return cov, cost

# 5. Greedy Search for Optimal N=30
print("\nSolving for N=30 optimal configuration...")
selected_indices = []
for _ in range(30):
    best_idx = -1
    best_val = -1
    for i in range(num_sites):
        if i in selected_indices: continue
        cov, cost = get_performance(selected_indices + [i])
        # Value = Coverage / Cost (Efficiency)
        if cost > 0:
            val = cov / cost
        else:
            val = cov
        if val > best_val:
            best_val = val
            best_idx = i
    if best_idx != -1:
        selected_indices.append(best_idx)

final_cov, final_cost = get_performance(selected_indices)

print("-" * 60)
print(f"OPTIMAL CONFIGURATION (N=30)")
print(f"Population Coverage: {final_cov/total_pop*100:.2f}%")
print(f"Total Hourly Cost:   ${final_cost:.4f}")
print(f"Monthly Cost:        ${final_cost*24*30:,.2f}")
print("-" * 60)
print(f"{ 'Supplier':<15} | { 'Region':<15} | { 'Type':<20} | {'Price/hr'}")
for idx in selected_indices:
    s = available_sites[idx]
    print(f"{s['supplier']:<15} | {s['region']:<15} | {s['type']:<20} | ${s['price']}")
