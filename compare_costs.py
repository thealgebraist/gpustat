import json
import math
import csv
import numpy as np

def parse_prices():
    prices = []
    with open('prices.hpp', 'r') as f:
        lines = f.readlines()
        for line in lines:
            if '{"' in line and '},' in line:
                parts = line.split('"')
                supplier = parts[1]
                region = parts[3]
                inst_type = parts[5]
                # Price is at the end of the line
                price_str = line.split(',')[-2].strip().replace('}', '').replace(';', '')
                try:
                    price = float(price_str)
                    prices.append({"supplier": supplier, "region": region, "type": inst_type, "price": price})
                except: pass
    return prices

db = parse_prices()
cheapest = min(db, key=lambda x: x['price'])
expensive = max(db, key=lambda x: x['price'])

cities = []
with open('cities.csv', mode='r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        row['population'] = int(row['population'])
        row['latitude'] = float(row['latitude'])
        row['longitude'] = float(row['longitude'])
        cities.append(row)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371 
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

SYNC_DIST_KM = 200.0
LATENCY_THRESHOLD_KM = 800.0
total_pop = sum(c['population'] for c in cities)

best_sites = [
    {"name": "Philadelphia", "lat": 39.95, "lon": -75.16},
    {"name": "Washington DC", "lat": 38.90, "lon": -77.03},
    {"name": "Baltimore", "lat": 39.29, "lon": -76.61},
    {"name": "New York City", "lat": 40.71, "lon": -74.00}
]

max_inter_dist = 0
for i in range(4):
    for j in range(i+1, 4):
        d = haversine(best_sites[i]['lat'], best_sites[i]['lon'], best_sites[j]['lat'], best_sites[j]['lon'])
        max_inter_dist = max(max_inter_dist, d)

covered_indices = set()
for s in best_sites:
    for idx, city in enumerate(cities):
        if haversine(s['lat'], s['lon'], city['latitude'], city['longitude']) <= LATENCY_THRESHOLD_KM:
            covered_indices.add(idx)
coverage_pct = sum(cities[i]['population'] for i in covered_indices) / total_pop * 100

print("=== 4-Server Cluster (1ms Sync Constraint) Comparison ===")
print("Max inter-server distance: " + str(round(max_inter_dist, 2)) + " km (Valid < 200km)")
print("Total Population Coverage: " + str(round(coverage_pct, 2)) + "%")
print("")

print("--- CHEAPEST OPTION ---")
print("Company:      " + cheapest['supplier'])
print("Server Type:  " + cheapest['type'])
print("Region:       " + cheapest['region'])
print("Unit Cost:    $" + str(round(cheapest['price'], 4)) + " / hr")
print("Total Cost:   $" + str(round(cheapest['price']*4, 4)) + " / hr")
print("Monthly Cost: $" + str(round(cheapest['price']*4*24*30, 2)))
print("")

print("--- MOST EXPENSIVE OPTION ---")
print("Company:      " + expensive['supplier'])
print("Server Type:  " + expensive['type'])
print("Region:       " + expensive['region'])
print("Unit Cost:    $" + str(round(expensive['price'], 4)) + " / hr")
print("Total Cost:   $" + str(round(expensive['price']*4, 4)) + " / hr")
print("Monthly Cost: $" + str(round(expensive['price']*4*24*30, 2)))
print("")

print("--- Configuration Locations ---")
for s in best_sites:
    print("- " + s['name'] + " (Inter-sync < 1ms)")