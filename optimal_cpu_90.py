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

# 2. Expanded Regional Mapping including new cheap providers
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
    "portland": (45.51, -122.67),
    # New VPS/Cheap Provider regions
    "losangeles": (34.05, -118.24),
    "ashburn": (39.04, -77.48),
    "dallas": (32.77, -96.79),
    "lasvegas": (36.17, -115.13),
    "us-east": (40.71, -74.00),
    "us-central": (41.87, -87.62),
    "atlanta": (33.74, -84.38)
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

LATENCY_THRESHOLD_KM = 1000.0
coverage_matrix = np.zeros((num_cities, num_sites))
for i, city in enumerate(cities):
    for j, site in enumerate(available_sites):
        if haversine(city['latitude'], city['longitude'], site['lat'], site['lon']) <= LATENCY_THRESHOLD_KM:
            coverage_matrix[i, j] = 1

def get_status(indices):
    counts = np.zeros(num_sites)
    for idx in indices: counts[idx] += 1
    coverage_counts = np.dot(coverage_matrix, counts)
    mask = (coverage_counts >= 3).astype(int)
    pop = np.sum(mask * [c['population'] for c in cities])
    return pop, coverage_counts

print("Optimizing for 90% Coverage using VPS + Budget Providers...")
selected = []
target_reached = False

while not target_reached and len(selected) < 300:
    best_idx = -1
    best_gain_score = -1e18
    current_pop, current_counts = get_status(selected)
    
    for i in range(num_sites):
        gain_score = 0
        for j in range(num_cities):
            if coverage_matrix[j, i] == 1:
                if current_counts[j] < 3:
                    # Value added by this server to city j
                    gain_score += (current_counts[j] + 1) * cities[j]['population']
        
        # Priority score: gain / cost
        # Add tiny epsilon to price to avoid div zero
        price = available_sites[i]['price']
        score = gain_score / (price if price > 0 else 0.0001)
        
        if score > best_gain_score:
            best_gain_score = score
            best_idx = i
            
    if best_idx == -1: break
    
    selected.append(best_idx)
    new_pop, _ = get_status(selected)
    pct = new_pop / total_pop * 100
    
    if len(selected) % 5 == 0 or pct >= 90:
        cost = sum(available_sites[idx]['price'] for idx in selected)
        print(f"N={len(selected):2} | Coverage: {pct:6.2f}% | Monthly: ${cost*24*30:8.2f}")
        
    if pct >= 90.0:
        target_reached = True
        print(f"\n>>> TARGET 90% REACHED AT N={len(selected)} <<<")

print("\nFinal Optimal Configuration (VPS + Budget Focus):")
counts = {}
for idx in selected:
    name = available_sites[idx]['region']
    counts[name] = counts.get(name, 0) + 1
for name in sorted(counts):
    s = next(site for site in available_sites if site['region'] == name)
    print(f"- {name:15}: {counts[name]} servers ({s['supplier']} {s['type']} @ ${s['price']}/hr)")
