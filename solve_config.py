import json
import math
import random
import csv
import sys
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds

# Load Data
cities = []
with open('cities.csv', mode='r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        row['population'] = int(row['population'])
        row['latitude'] = float(row['latitude'])
        row['longitude'] = float(row['longitude'])
        cities.append(row)

regions = [
    {"name": "us-east-1 (Virginia)", "lat": 38.99, "lon": -77.45},
    {"name": "us-east-2 (Ohio)", "lat": 40.09, "lon": -82.75},
    {"name": "us-west-1 (California)", "lat": 37.44, "lon": -122.15},
    {"name": "us-west-2 (Oregon)", "lat": 45.92, "lon": -119.27},
    {"name": "us-central-1 (Omaha)", "lat": 41.26, "lon": -95.93},
]

sites = []
for c in cities:
    sites.append({"name": c['city'], "lat": c['latitude'], "lon": c['longitude']})
for r in regions:
    sites.append({"name": r['name'], "lat": r['lat'], "lon": r['lon']})

def haversine(lat1, lon1, lat2, lon2):
    R = 6371 
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

SYNC_DIST_KM = 4000.0 # ~20ms one-way
LATENCY_THRESHOLD_KM = 800.0 # ~5ms
MIN_SERVERS_FOR_COVERAGE = 3 # Can survive 2 failures
total_pop = sum(c['population'] for c in cities)

num_sites = len(sites)
num_cities = len(cities)

dist_matrix = np.zeros((num_sites, num_sites))
for i in range(num_sites):
    for j in range(num_sites):
        dist_matrix[i, j] = haversine(sites[i]['lat'], sites[i]['lon'], sites[j]['lat'], sites[j]['lon'])

coverage_matrix = np.zeros((num_cities, num_sites))
for i in range(num_cities):
    for j in range(num_sites):
        if haversine(cities[i]['latitude'], cities[i]['longitude'], sites[j]['lat'], sites[j]['lon']) <= LATENCY_THRESHOLD_KM:
            coverage_matrix[i, j] = 1

adj = (dist_matrix <= SYNC_DIST_KM)

# Generate potential clusters
def find_cliques_robust():
    cliques = []
    for i in range(num_sites):
        clique = {i}
        for j in range(num_sites):
            if i == j: continue
            can_add = True
            for member in clique:
                if not adj[member, j]:
                    can_add = False
                    break
            if can_add:
                clique.add(j)
        if clique not in cliques:
            cliques.append(clique)
    return [list(c) for c in cliques]

all_cliques = find_cliques_robust()

def get_coverage_of_sites(site_indices):
    if len(site_indices) < MIN_SERVERS_FOR_COVERAGE: return 0
    # A city is covered if it is within range of at least 3 servers
    server_counts = np.sum(coverage_matrix[:, site_indices], axis=1)
    mask = (server_counts >= MIN_SERVERS_FOR_COVERAGE).astype(int)
    return np.sum(mask * [c['population'] for c in cities])

print("\nN | Best Coverage % (with 2-Fault Tolerance) | Site List")
print("-" * 100)

for n in range(5, 21):
    best_n_pop = 0
    best_n_sites = []
    
    for clique in all_cliques:
        current_clique_sites = []
        if len(clique) <= n:
            current_clique_sites = clique
        else:
            # Greedy subset selection from clique for speed
            selected = []
            for _ in range(n):
                best_s = -1
                best_s_pop = -1
                for s in clique:
                    if s in selected: continue
                    pop = get_coverage_of_sites(selected + [s])
                    if pop > best_s_pop:
                        best_s_pop = pop
                        best_s = s
                if best_s != -1:
                    selected.append(best_s)
                else:
                    # If no single site improves coverage, pick one at random from clique
                    remaining = list(set(clique) - set(selected))
                    if remaining:
                        selected.append(remaining[0])
            current_clique_sites = selected
            
        pop = get_coverage_of_sites(current_clique_sites)
        if pop > best_n_pop:
            best_n_pop = pop
            best_n_sites = current_clique_sites
            
    site_names = [sites[idx]['name'] for idx in best_n_sites]
    print(f"{n:2} | {best_n_pop/total_pop*100:38.2f}% | {site_names}")
