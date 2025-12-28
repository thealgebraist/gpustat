# US Infrastructure Cost Variance & Hidden Fees Report (2025)

## Overview
Standard "sticker prices" for cloud servers often ignore critical operational costs such as data egress, IP addresses, and the risk/penalty of sudden cancellation. Below is a breakdown of the variance found in actual provider agreements.

## 1. Azure (Major Provider)
- **Base Price Variance:** Low (Fixed per hour).
- **Hidden Fees:**
    - **Egress (Bandwidth):** First 100GB/mo is free. Thereafter, **$0.05 to $0.087 per GB** (North America). For high-traffic apps, this can easily double the base compute cost.
    - **Cancellation (Reserved):** Currently no early termination fee, but a **12% penalty** is proposed for future updates. Refunds are capped at **$50,000/year**.
    - **Stopped vs. Allocated:** You are billed for the full price if the VM is "Stopped" but not "Deallocated."
- **Median Variance:** ±5% (mostly driven by bandwidth fluctuations).

## 2. Vultr (VPS Specialist)
- **Base Price Variance:** Moderate (Regional differences).
- **Hidden Fees:**
    - **The "Stopped" Trap:** You are billed 100% of the price even if the server is powered off. You must "Destroy" the instance to stop billing.
    - **Bandwidth:** Generous 2TB free tier, then **$0.01 per GB**.
    - **Backups:** Automatic backups add a mandatory **20% surcharge** to the base fee.
- **Median Variance:** +20% (if backups are enabled).

## 3. TensorDock (Marketplace)
- **Base Price Variance:** **High** (Dynamic marketplace).
- **Hidden Fees:**
    - **Non-Cancellable:** Offers are "firm commitments." Once a session starts, you cannot withdraw or refund easily.
    - **Downtime Risk:** Compensation is only **5x to 10x** the hourly rate, which often doesn't cover the business impact of an outage.
- **Median Variance:** ±15% (Prices change based on host availability).

## 4. AT&T Edge (Azure Integrated)
- **Base Price Variance:** **Unknown** (Private/Custom quotes only).
- **Hidden Fees:**
    - Likely subject to premium egress rates due to the 5G/LTE backhaul requirements.
    - Expect a **2x - 5x premium** over standard regional compute for the "last mile" low-latency benefit.

---

## Latency vs. Cost Sensitivity Analysis
| Factor | Typical Range | Impact on Configuration |
| :--- | :--- | :--- |
| **Bandwidth (Egress)** | $0.01 - $0.12 / GB | High-traffic services should favor Vultr/Hetzner. |
| **IP Addresses** | $0.005 - $0.01 / hr | Significant for many tiny (N=100+) instances. |
| **Snapshots** | $0.05 / GB / mo | Important for stateful backup nodes. |
