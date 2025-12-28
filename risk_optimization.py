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

def haversine(lat1, lon1, lat2, lon2):
    R = 6371 
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2*R*math.atan2(math.sqrt(a), math.sqrt(1-a))

# 2. Simulate High-Risk Data Center Presence in all major cities
# Since physical high-risk DCs are sparse, we model the "Theoretical Optimal" 
# by allowing placement in any city with a high-risk profile.
high_risk_sites = []
for c in cities:
    high_risk_sites.append({
        "supplier": "Generic High-Risk",
        "city": c['city'],
        "price": 0.005, # Budget price
        "risk": 0.70, # High risk
        "lat": c['latitude'],
        "lon": c['longitude']
    })

num_options = len(high_risk_sites)
num_cities = len(cities)

# 3. Coverage Matrix (1ms constraint = 150km)
LATENCY_1MS_KM = 150.0
coverage_matrix = np.zeros((num_cities, num_options))
for i, city in enumerate(cities):
    for j, site in enumerate(high_risk_sites):
        if haversine(city['latitude'], city['longitude'], site['lat'], site['lon']) <= LATENCY_1MS_KM:
            coverage_matrix[i, j] = 1

def get_metrics(indices):
    if not indices: return 0, 0, np.zeros(num_cities)
    counts = np.zeros(num_options)
    for idx in indices: counts[idx] += 1
    coverage_counts = np.dot(coverage_matrix, counts)
    mask = (coverage_counts >= 4).astype(int) # 4x redundancy
    pop = np.sum(mask * [c['population'] for c in cities])
    cost = sum(high_risk_sites[i]['price'] for i in indices)
    return pop, cost, coverage_counts

# 4. Solve
print("OPTIMIZING FOR THEORETICAL 100% COVERAGE (HIGH-RISK ONLY)")
print("Constraints: 4x Redundancy, 1ms Latency (150km), N up to 300\n")
print(f"{ 'N':>3} | {'Coverage %':>12} | {'Monthly Cost':>15} | {'Site Added'}")
print("-" * 80)

selected_indices = []
target_reached = False
pct = 0.0

for n in range(1, 301):
    best_idx = -1
    best_utility = -1e100
    _, _, current_counts = get_metrics(selected_indices)

    for i in range(num_options):
        utility = 0
        for j in range(num_cities):
            if coverage_matrix[j, i] == 1 and current_counts[j] < 4:
                # Value added to progress toward 4x threshold
                utility += (current_counts[j] + 1) * cities[j]['population']
        
        # Priority = (Gain * Risk) / Price
        score = utility * 0.70 / 0.005
        if score > best_utility:
            best_utility = score
            best_idx = i
            
    if best_idx != -1:
        selected_indices.append(best_idx)
    else:
        break
    
    pop, cost, _ = get_metrics(selected_indices)
    pct = pop/total_pop*100
    added = high_risk_sites[best_idx]
    
    if n % 25 == 0 or pct >= 100.0 or n == 1:
        print(f"{n:3} | {pct:11.2f}% | ${cost*24*30:14.2f} | {added['city']}")
    
    if pct >= 100.0 and not target_reached:
        target_reached = True
        print(f"\n>>> TARGET 100% REACHED AT N={n} <<<")
        print(f"Final High-Risk Monthly Cost: ${cost*24*30:,.2f}\n")

if not target_reached:
    print(f"\nMax achievable coverage: {pct:.2f}%")