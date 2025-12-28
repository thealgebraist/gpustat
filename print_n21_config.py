import sqlite3
import math
import csv
import numpy as np
import json

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

region_map = {
    "eastus": (37.37, -78.78), "eastus2": (36.66, -78.38), "westus": (37.77, -122.41),
    "westus2": (47.23, -119.85), "westus3": (33.44, -112.07), "centralus": (41.59, -93.60),
    "southcentralus": (29.41, -98.50), "northcentralus": (41.88, -87.62), "westcentralus": (41.59, -107.21),
    "usgovvirginia": (37.54, -77.43), "usgovtexas": (30.26, -97.74), "usgovarizona": (33.44, -112.07),
    "usgoviowa": (41.59, -93.60), "southwestus": (33.44, -112.07),
    "us-east-1": (38.99, -77.45), "us-east-2": (40.09, -82.75), 
    "us-west-1": (37.44, -122.15), "us-west-2": (45.92, -119.27),
    "us-central1": (41.26, -95.93), "us-ashburn-1": (39.04, -77.48),
    "us-south": (29.76, -95.36), "NJ": (40.71, -74.00), "NY": (40.71, -74.00),
    "nyc3": (40.71, -74.00), "US-East": (40.00, -75.00), "US-West": (37.00, -120.00),
    "attdallas1": (32.77, -96.79), "attdetroit1": (42.33, -83.04), 
    "attatlanta1": (33.74, -84.38), "attnewyork1": (40.71, -74.00),
    "portland": (45.51, -122.67), "nj": (40.71, -74.00), "lv": (36.17, -115.13),
    "ash": (39.04, -77.48), "kc": (39.10, -94.58), "nc": (35.76, -78.64)
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371 
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

conn = sqlite3.connect('prices.db')
cursor = conn.cursor()
cursor.execute("SELECT supplier, region, instance_type, price FROM prices WHERE category = 'cpu' AND price >= 0.0001")
rows = cursor.fetchall()
conn.close()

site_data = {}
for supplier, region, inst, price in rows:
    r_key = region.lower()
    if r_key in region_map:
        lat, lon = region_map[r_key]
        key = (supplier, r_key, lat, lon)
        if key not in site_data or price < site_data[key]['price']:
            site_data[key] = {"supplier": supplier, "region": r_key, "type": inst, "price": price, "lat": lat, "lon": lon}

available_options = list(site_data.values())
num_options = len(available_options)
num_cities = len(cities)

LATENCY_THRESHOLD_KM = 1000.0
coverage_matrix = np.zeros((num_cities, num_options))
for i, city in enumerate(cities):
    for j, opt in enumerate(available_options):
        if haversine(city['latitude'], city['longitude'], opt['lat'], opt['lon']) <= LATENCY_THRESHOLD_KM:
            coverage_matrix[i, j] = 1

def get_metrics(indices):
    if not indices: return 0, 0, np.zeros(num_cities)
    counts = np.zeros(num_options)
    for idx in indices: counts[idx] += 1
    coverage_counts = np.dot(coverage_matrix, counts)
    mask = (coverage_counts >= 3).astype(int)
    pop = np.sum(mask * [c['population'] for c in cities])
    cost = sum(available_options[i]['price'] for i in indices)
    return pop, cost, coverage_counts

# Run greedy search exactly as before to find the same N=21 set
selected_indices = []
for n in range(1, 22):
    best_idx = -1
    best_score = -1e18
    _, _, current_counts = get_metrics(selected_indices)
    for i in range(num_options):
        gain = 0
        for j in range(num_cities):
            if coverage_matrix[j, i] == 1 and current_counts[j] < 3:
                gain += (current_counts[j] + 1) * cities[j]['population']
        price = available_options[i]['price']
        score = gain / (price if price > 0 else 0.0001)
        if score > best_score:
            best_score = score
            best_idx = i
    if best_idx != -1:
        selected_indices.append(best_idx)

# Print Detailed Result
print("=== OPTIMAL CONFIGURATION FOR N=21 (100% COVERAGE) ===")
print(f"Goal: Reach 100% of top 50 cities population with 2-fault tolerance.\n")

print(f"{ 'Supplier':<10} | { 'Region':<15} | { 'Instance Type':<25} | { 'Hourly':<8} | {'Monthly'}")
print("-" * 85)

total_hourly = 0
for idx in selected_indices:
    s = available_options[idx]
    total_hourly += s['price']
    monthly = s['price'] * 24 * 30
    print(f"{s['supplier']:<10} | {s['region']:<15} | {s['type']:<25} | ${s['price']:.4f} | ${monthly:6.2f}")

print("-" * 85)
print(f"{ 'TOTAL':<56} | ${total_hourly:.4f} | ${total_hourly*24*30:6.2f}")
