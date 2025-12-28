import sqlite3
import math
import csv
import numpy as np
import json

# 1. Load Data
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
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2*R*math.atan2(math.sqrt(a), math.sqrt(1-a))

# 2. Extract Options
conn = sqlite3.connect('prices.db')
cursor = conn.cursor()
cursor.execute("SELECT supplier, region, price FROM prices WHERE category = 'cpu' AND price >= 0.0001")
rows = cursor.fetchall()
conn.close()

site_data = {}
for supplier, region, price in rows:
    r_key = region if region in region_map else region.lower()
    if r_key in region_map:
        lat, lon = region_map[r_key]
        key = (supplier, r_key)
        overhead = 1.15
        if supplier in ["Vultr", "Linode"]: overhead = 1.20
        real_p = price * overhead
        if key not in site_data or real_p < site_data[key]['real_price']:
            site_data[key] = {"supplier": supplier, "region": r_key, "real_price": real_p, "lat": lat, "lon": lon}

opts = list(site_data.values())
num_opts = len(opts)
num_cities = len(cities)

# 3. Coverage Matrix
LATENCY_THRESHOLD_KM = 1000.0
cov_mat = np.zeros((num_cities, num_opts))
for i, city in enumerate(cities):
    for j, opt in enumerate(opts):
        if haversine(city['latitude'], city['longitude'], opt['lat'], opt['lon']) <= LATENCY_THRESHOLD_KM:
            cov_mat[i, j] = 1

def check_reachability():
    # A city is reachable if at least 2 distinct vendors are in range
    reachable_count = 0
    for i in range(num_cities):
        sups = set()
        for j in range(num_opts):
            if cov_mat[i, j]:
                sups.add(opts[j]['supplier'])
        if len(sups) < 2:
            print(f"City UNREACHABLE under Multi-Vendor rule: {cities[i]['city']} (Vendors in range: {sups})")
        else:
            reachable_count += 1
    return reachable_count

print(f"Reachable cities: {check_reachability()}/{num_cities}")

def get_cov_pct(indices):
    if not indices: return 0
    cnts = np.zeros(num_cities)
    sups = [set() for _ in range(num_cities)]
    for idx in indices:
        for i in range(num_cities):
            if cov_mat[i, idx]:
                cnts[i] += 1
                sups[i].add(opts[idx]['supplier'])
    pop = 0
    for i in range(num_cities):
        if cnts[i] >= 3 and len(sups[i]) >= 2:
            pop += cities[i]['population']
    return pop / total_pop * 100

# 4. Solve
print("\nSolving for Multi-Vendor Redundancy...")
selected = []
target_met = False

for n in range(1, 101):
    best_idx = -1
    best_score = -1e100
    
    cnts_curr = np.zeros(num_cities)
    sups_curr = [set() for _ in range(num_cities)]
    for idx in selected:
        for i in range(num_cities):
            if cov_mat[i, idx]:
                cnts_curr[i] += 1
                sups_curr[i].add(opts[idx]['supplier'])

    for i in range(num_opts):
        opt = opts[i]
        utility = 0
        for j in range(num_cities):
            if cov_mat[j, i]:
                pop = cities[j]['population']
                # If city j needs a vendor or more servers
                if cnts_curr[j] < 3 or len(sups_curr[j]) < 2:
                    # Utility for count progress
                    utility += pop * 1
                    # Utility for vendor progress
                    if opt['supplier'] not in sups_curr[j]:
                        utility += pop * 50 # Bonus for new vendor
        
        score = utility / opt['real_price']
        if score > best_score:
            best_score = score
            best_idx = i
            
    if best_idx == -1: break
    
    selected.append(best_idx)
    pct = get_cov_pct(selected)
    cost = sum(opts[idx]['real_price'] for idx in selected)
    
    if n % 10 == 0 or pct >= 100 or n == 1:
        print(f"N={n:3} | Coverage: {pct:9.2f}% | Monthly: ${cost*24*30:10.2f} | Added: {opts[best_idx]['supplier']} ({opts[best_idx]['region']})")
    
    if pct >= 100 and not target_met:
        target_met = True
        print(f"\n>>> TARGET 100% REACHED AT N={n} <<<")

print("\nFinal Configuration Summary:")
vm = {}
for idx in selected:
    s = opts[idx]['supplier']
    vm[s] = vm.get(s, 0) + 1
for v in sorted(vm): print(f"- {v}: {vm[v]} servers")