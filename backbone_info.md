# US Internet Backbone Information (2025)

## Overview
The US internet backbone is a high-capacity network of fiber-optic cables owned and operated by Tier 1 Internet Service Providers (ISPs). These networks form the primary data routes between major metropolitan areas.

## Key Tier 1 Providers
- **Lumen Technologies (formerly Level 3/CenturyLink):** Operates one of the most interconnected backbones in the world.
- **AT&T:** Extensive national fiber reach with deep integration into consumer and enterprise sectors.
- **Verizon:** Robust backbone primarily focused on the Northeast and major coastal hubs.
- **Zayo Group:** Specialized in dark fiber and high-bandwidth connectivity for data centers.
- **Cogent Communications:** High-capacity IP transit specialist with a footprint in most major IXPs.

## Major Internet Exchange Points (IXPs)
Data "hops" between backbones at critical exchange points, often located in the following hubs:
- **Ashburn, VA (Data Center Alley):** The primary global hub for internet traffic, serving the DC/Northern Virginia area.
- **New York, NY:** Critical for trans-Atlantic connectivity and financial services.
- **Chicago, IL:** The central hub for trans-continental traffic (East-West).
- **Dallas, TX:** The main hub for the South-Central US and traffic to Mexico.
- **San Jose/Palo Alto, CA (Silicon Valley):** The primary hub for Pacific-bound traffic and tech infrastructure.
- **Seattle, WA:** Key for North-Pacific and Canadian connectivity.
- **Atlanta, GA:** The primary gateway for the Southeastern US.

## Fiber Route Characteristics
- **Path Redundancy:** Major cities are usually connected by multiple redundant fiber paths.
- **Latency (Speed of Light):** In fiber-optic cables, light travels at approximately 2/3 the speed of light in a vacuum (~200,000 km/s). This results in a baseline latency of ~1ms per 100km (one-way).
- **Backbone Topology:** The US backbone follows a roughly "star" or "mesh" topology around major IXPs. Coast-to-coast latency (NY to SF) typically ranges from 60ms to 80ms RTT (Round Trip Time).

## Latency Refinement for Modeling
When modeling US latency:
1. **Intra-Region (1-2ms):** Servers within the same metro area (e.g., Ashburn to DC).
2. **Short-Haul (5-15ms):** Nearby cities (e.g., NY to DC, Chicago to Detroit).
3. **Mid-Haul (20-40ms):** Trans-regional (e.g., NY to Chicago, Dallas to Atlanta).
4. **Long-Haul (60-80ms):** Coast-to-coast (e.g., NY to LA).
