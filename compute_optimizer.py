import sqlite3
import math
import json
import sys

GPU_BENCHMARKS = {
    "H100": 989.0, "A100": 312.0, "A3": 312.0, "L4": 121.0, "T4": 65.0,
    "RTX 4090": 165.0, "RTX 3090": 142.0, "RTX 3080": 119.0, "V100": 125.0,
    "RTX 6000": 182.0, "L40": 181.0,
}

MODEL_INFERENCE_TFLOPS = {
    "SDXL": 1500.0, # Per Image
    "FLUX": 5000.0, # Per Image
    "AUDIO-HQ": 2000.0, # Per Minute of high-quality audio
    "SD1.5": 300.0, 
    "LLAMA-3-70B": 150.0
}

VENDOR_RISKS = {
    "Azure": 0.12, "AWS": 0.15, "GCP": 0.18, "Linode": 0.22, "Cloudflare": 0.20,
    "Scaleway": 0.24, "Hetzner": 0.25, "DigitalOcean": 0.28, "Oracle OCI": 0.35,
    "OVHcloud": 0.45, "Vultr": 0.38, "TensorDock": 0.65, "BuyVM": 0.55, "RackNerd": 0.65,
    "LowEndSpirit": 0.95, "Wishosting": 0.70
}

def solve_task(task_type, quantity, time_limit_hr, max_risk=1.0):
    total_tflops = MODEL_INFERENCE_TFLOPS.get(task_type, 1000.0) * quantity
    req_tflops_hr = total_tflops / time_limit_hr
    
    print(f"--- Task Analysis ---")
    print(f"Task: {quantity} units of {task_type} in {time_limit_hr}h")
    print(f"Total TFLOPs: {total_tflops:,.0f}")
    print(f"Required Throughput: {req_tflops_hr:,.2f} TFLOPS/hr\n")

    conn = sqlite3.connect('prices.db')
    cursor = conn.cursor()
    cursor.execute("SELECT supplier, region, instance_type, price FROM prices WHERE price >= 0.001")
    rows = cursor.fetchall()
    conn.close()

    candidates = []
    for s, r, i, p in rows:
        risk = VENDOR_RISKS.get(s, 0.5)
        if risk > max_risk: continue
        
        power = 0
        for key in GPU_BENCHMARKS:
            if key in i.upper() or key in i:
                mult = 1
                if '8x' in i.lower(): mult = 8
                elif '4x' in i.lower(): mult = 4
                elif '2x' in i.lower(): mult = 2
                power = GPU_BENCHMARKS[key] * mult
                break
        
        if power < 10.0: continue
            
        n = math.ceil(req_tflops_hr / power)
        candidates.append({
            "s": s, "r": r, "i": i, "n": n, "total": n*p, "job": n*p*time_limit_hr, "risk": risk
        })

    candidates.sort(key=lambda x: x['job'])
    
    if candidates:
        b = candidates[0]
        print(f"--- OPTIMAL CONFIGURATION ---")
        print(f"Provider: {b['s']} ({b['r']})")
        print(f"Instance: {b['i']}")
        print(f"Count:    {b['n']} nodes")
        print(f"Hourly:   ${b['total']:.2f}")
        print(f"Job Cost: ${b['job']:.2f}")
        print(f"Risk:     sigma = {b['risk']}")
    else:
        print("No suitable GPU candidates found.")

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 4:
        solve_task(args[0], int(args[1]), float(args[2]), float(args[3]))
    else:
        # Default: 10 hours (600 mins) of HQ audio in 2 hours
        solve_task("AUDIO-HQ", 600, 2.0, 1.0)
