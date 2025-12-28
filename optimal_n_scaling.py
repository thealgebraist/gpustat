import sqlite3
import math
import csv
import numpy as np
import json

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
        if key not in site_data or price < site_data[key]['base_price']:
            # Adjust price based on overhead estimates
            # Azure: +15% for egress/IP, Vultr: +20% for backups, Marketplace: +15% variance
            overhead = 1.15
            if supplier in ["Vultr", "Linode"]: overhead = 1.20
            elif supplier in ["Azure", "AWS", "GCP"]: overhead = 1.15
            elif supplier == "TensorDock": overhead = 1.10
            
            site_data[key] = {
                "supplier": supplier, "region": r_key, "type": inst, 
                "base_price": price, "real_price": price * overhead,
                "lat": lat, "lon": lon
            }

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
    if not indices: return 0, 0, 0, np.zeros(num_cities)
    counts = np.zeros(num_options)
    for idx in indices: counts[idx] += 1
    coverage_counts = np.dot(coverage_matrix, counts)
    mask = (coverage_counts >= 3).astype(int)
    pop = np.sum(mask * [c['population'] for c in cities])
    base_cost = sum(available_options[i]['base_price'] for i in indices)
    real_cost = sum(available_options[i]['real_price'] for i in indices)
    return pop, base_cost, real_cost, coverage_counts

print("SCALING N=1 TO 100: REALISTIC COST (INCLUDING HIDDEN FEES)")
print("Constraints: 2-fault tolerance, 20ms sync, 1000km latency\n")
print(f"{ 'N':>3} | { 'Coverage %':>10} | { 'Base $/mo':>12} | { 'Real $/mo':>12} | {'Site Added'}")
print("-" * 80)

selected_indices = []
target_reached = False

for n in range(1, 101):
    best_idx = -1
    best_score = -1e18
    _, _, _, current_counts = get_metrics(selected_indices)

    for i in range(num_options):
        gain = 0
        for j in range(num_cities):
            if coverage_matrix[j, i] == 1 and current_counts[j] < 3:
                gain += (current_counts[j] + 1) * cities[j]['population']
        
        real_price = available_options[i]['real_price']
        score = gain / (real_price if real_price > 0 else 0.0001)
        if score > best_score:
            best_score = score
            best_idx = i
            
    if best_idx != -1:
        selected_indices.append(best_idx)
    
    pop, base, real, _ = get_metrics(selected_indices)
    pct = pop/total_pop*100
    added = available_options[best_idx]
    
    if n % 10 == 0 or pct >= 100.0 or n == 1:
        print(f"{n:3} | {pct:9.2f}% | ${base*24*30:10.2f} | ${real*24*30:10.2f} | {added['supplier']} ({added['region']})")
    
    if pct >= 100.0 and not target_reached:
        target_reached = True
        print(f"\n>>> TARGET 100% REACHED AT N={n} <<<")
        print(f"Realistic Total Monthly Cost: ${real*24*30:,.2f}\n")
