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

vendor_risks = {
    "Azure": 0.12, "AWS": 0.15, "GCP": 0.18, "Linode": 0.22, "Cloudflare": 0.20,
    "Scaleway": 0.24, "Hetzner": 0.25, "DigitalOcean": 0.28, "Oracle OCI": 0.35,
    "OVHcloud": 0.45, "Vultr": 0.38, "BuyVM": 0.55, "RackNerd": 0.65, "LowEndSpirit": 0.95,
    "Wishosting": 0.70, "HudsonValleyHost": 0.60
}

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

conn = sqlite3.connect('prices.db')
cursor = conn.cursor()
cursor.execute("SELECT supplier, region, price FROM prices WHERE category = 'cpu' AND price >= 0.0001")
rows = cursor.fetchall()
conn.close()

low_risk_opts, high_risk_opts = [], []
for s, r, p in rows:
    r_key = r if r in region_map else r.lower()
    if r_key in region_map:
        lat, lon = region_map[r_key]
        risk = vendor_risks.get(s, 0.5)
        item = {"supplier": s, "region": r_key, "price": p, "lat": lat, "lon": lon}
        if risk <= 0.35: low_risk_opts.append(item)
        else: high_risk_opts.append(item)

num_cities = len(cities)
LATENCY_THRESHOLD_KM = 1000.0

def build_mat(opts):
    mat = np.zeros((num_cities, len(opts)))
    for i, city in enumerate(cities):
        for j, opt in enumerate(opts):
            if haversine(city['latitude'], city['longitude'], opt['lat'], opt['lon']) <= LATENCY_THRESHOLD_KM:
                mat[i, j] = 1
    return mat

low_mat = build_mat(low_risk_opts)
high_mat = build_mat(high_risk_opts)

def get_cov(l_idx, h_idx):
    if not l_idx and not h_idx: return 0, np.zeros(num_cities)
    l_counts = np.sum(low_mat[:, l_idx], axis=1) if l_idx else np.zeros(num_cities)
    h_counts = np.sum(high_mat[:, h_idx], axis=1) if h_idx else np.zeros(num_cities)
    total = l_counts + h_counts
    pop = np.sum((total >= 4).astype(int) * [c['population'] for c in cities])
    return pop, total

print("OPTIMIZING FOR 50/50 RISK SPLIT (1000km Threshold)")
print(f"{ 'N':>3} | {'Coverage %':>12} | {'Monthly Cost':>15} | {'Low/High Count'}")
print("-" * 75)

sel_l, sel_h = [], []
target_reached = False

for n in range(1, 101):
    add_low = (len(sel_l) <= len(sel_h))
    best_idx, best_score = -1, -1e100
    _, curr_counts = get_cov(sel_l, sel_h)
    
    target_opts = low_risk_opts if add_low else high_risk_opts
    target_mat = low_mat if add_low else high_mat
    
    for i in range(len(target_opts)):
        gain = 0
        for j in range(num_cities):
            if target_mat[j, i] == 1 and curr_counts[j] < 4:
                gain += (curr_counts[j] + 1) * cities[j]['population']
        
        score = gain / (target_opts[i]['price'] if target_opts[i]['price'] > 0 else 0.0001)
        if score > best_score:
            best_score, best_idx = score, i
            
    if best_idx != -1:
        if add_low: sel_l.append(best_idx)
        else: sel_h.append(best_idx)
    
    pop, _ = get_cov(sel_l, sel_h)
    pct = pop / total_pop * 100
    cost = sum(low_risk_opts[i]['price'] for i in sel_l) + sum(high_risk_opts[i]['price'] for i in sel_h)
    
    if n % 10 == 0 or pct >= 100 or n == 1:
        print(f"{n:3} | {pct:11.2f}% | ${cost*24*30:14.2f} | {len(sel_l)}L / {len(sel_h)}H")
    
    if pct >= 100 and not target_reached:
        target_reached = True
        print(f"\n>>> 100% COVERAGE REACHED AT N={n} <<<")