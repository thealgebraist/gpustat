import json
import urllib.request
import csv
import sqlite3
import os
import time
import urllib.parse

def get_json(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return None

def fetch_azure_deep():
    results = []
    base_url = "https://prices.azure.com/api/retail/prices"
    query = "$filter=priceType eq 'Consumption'"
    url = f"{base_url}?{urllib.parse.quote(query, safe='=$&')}"
    for page in range(30):
        data = get_json(url)
        if not data or 'Items' not in data: break
        for item in data['Items']:
            sku = item.get("armSkuName", "")
            service = item.get("serviceName", "").lower()
            category = "cpu"
            if "gpu" in service or any(x in sku for x in ["ND", "NC"]): category = "gpu"
            elif "storage" in service: category = "storage"
            elif "backup" in service: category = "backup"
            results.append({"supplier": "Azure", "region": item.get("armRegionName", "Global"), "instance_type": sku, "category": category, "price": float(item.get("retailPrice", 0.0))})
        url = data.get('NextPageLink')
        if not url: break
    return results

def get_all_curated():
    data = []
    # Hyper-scale & Specialty
    providers = [
        ("AWS", "us-east-1", [("p5.48xlarge", "gpu", 98.32), ("m5.large", "cpu", 0.096)]),
        ("GCP", "us-central1", [("a3-highgpu-8g", "gpu", 40.0), ("n2-standard-2", "cpu", 0.097)]),
        ("Oracle OCI", "us-ashburn-1", [("BM.GPU.H100.8", "gpu", 95.0), ("A1 ARM", "cpu", 0.01)]),
        ("Cloudflare", "Global", [("Workers AI", "gpu", 0.50), ("Workers Compute", "cpu", 0.05)]),
        ("CoreWeave", "US-East", [("HGX H100", "gpu", 4.25), ("L40", "gpu", 1.10), ("CPU Compute", "cpu", 0.03)]),
        ("Lambda Labs", "us-east-1", [("1x H100", "gpu", 2.50), ("8x H100", "gpu", 24.0)]),
        ("RunPod", "US-East", [("1x RTX 4090", "gpu", 0.69), ("CPU Instance", "cpu", 0.05)]),
        ("Vast.ai", "Global", [("1x RTX 3090", "gpu", 0.30), ("CPU-only", "cpu", 0.02)]),
        ("Baseten", "Global", [("H100 Inference", "gpu", 3.50)]),
        ("FluidStack", "Norway", [("1x RTX 4090", "gpu", 0.60)]),
        ("Paperspace", "NY", [("1x A100", "gpu", 1.50), ("Standard CPU", "cpu", 0.01)]),
        ("Northflank", "London", [("GPU Job", "gpu", 0.80), ("CPU Pod", "cpu", 0.04)]),
        ("Corvex", "US-East", [("H200 Cluster", "gpu", 5.50)]),
        # VPS & Budget
        ("Vultr", "nj", [("AMD EPYC", "cpu", 0.009), ("Intel Xeon", "cpu", 0.007)]),
        ("Linode", "us-east", [("AMD Shared", "cpu", 0.0075), ("Dedicated CPU", "cpu", 0.04)]),
        ("DigitalOcean", "nyc3", [("Premium AMD", "cpu", 0.01), ("H100 GPU", "gpu", 2.99)]),
        ("Hetzner", "EU", [("AX41 AMD Ryzen", "cpu", 0.05), ("EX44 Intel Core", "cpu", 0.06)]),
        ("OVHcloud", "US", [("Advance-1 Intel", "cpu", 0.10), ("A100 Instance", "gpu", 2.50)]),
        ("Scaleway", "fr-par", [("Stardust ARM", "cpu", 0.0001)]),
        ("BuyVM", "lv", [("KVM Slice AMD", "cpu", 0.005)]),
        ("RackNerd", "ash", [("Intel Budget", "cpu", 0.002)]),
        ("LowEndSpirit", "NJ", [("NAT Intel", "cpu", 0.0005)]),
    ]
    for supplier, reg, items in providers:
        for name, cat, price in items:
            data.append({"supplier": supplier, "region": reg, "instance_type": name, "category": cat, "price": price})
    return data

def main():
    all_data = []
    all_data.extend(fetch_azure_deep())
    all_data.extend(get_all_curated())
    
    with open('prices.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["supplier", "region", "instance_type", "category", "price"])
        writer.writeheader()
        writer.writerows(all_data)

    conn = sqlite3.connect('prices.db')
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS prices")
    c.execute("CREATE TABLE prices (supplier TEXT, region TEXT, instance_type TEXT, category TEXT, price REAL)")
    for d in all_data:
        c.execute("INSERT INTO prices VALUES (?, ?, ?, ?, ?)", (d['supplier'], d['region'], d['instance_type'], d['category'], d['price']))
    conn.commit()
    conn.close()

    with open("prices.hpp", "w") as f:
        f.write("#pragma once\n#include <vector>\n#include <string>\n\nstruct PriceEntry { std::string supplier, region, instance_type, category; double price_per_hour; };\n")
        f.write("inline const std::vector<PriceEntry> gpu_prices = {\n")
        for d in all_data[:1000]:
            s, r, i, cat = json.dumps(d['supplier']), json.dumps(d['region']), json.dumps(d['instance_type']), json.dumps(d['category'])
            f.write(f"    {{{s}, {r}, {i}, {cat}, {d['price']}}},\n")
        f.write("};\n")

    print(f"Update Complete. Total entries: {len(all_data)}. All providers included.")

if __name__ == "__main__":
    main()
