# Vendor Analysis: Cloudflare

## Overview
Cloudflare is a global leader in edge computing and security, providing a massive network that brings compute closer to the end-user via its "Workers" and "Workers AI" platforms.

## Economic & Operational Profile
- **Founded:** 2009.
- **Employees:** ~4,263 (as of 2025).
- **Revenue:** $2.01 Billion (Trailing 12mo 2025).
- **Stock:** NYSE: NET. Public since 2019. Stock has shown significant growth (up ~80% in 2025).
- **Incidents:**
    - **Fires:** No major fire incidents reported at their edge facilities.
    - **Outages:** Notable 5-hour global outage in Nov 2025 caused by a Bot Management bug. Frequent, shorter disruptions in R2 and Dashboard APIs.

## Economic Risk Analysis
Cloudflare is highly stable with strong revenue growth and a dominant position in the CDN/WAF market. The primary risk is its role as a "Single Point of Failure" for a massive portion of the web. A technical flaw in their centralized configuration management (as seen in late 2025) has a nearly unparalleled global blast radius.

## Gaussian Risk Variable
**$\sigma_{risk}$ = 0.20** (Low)
*Confidence Interval: [0.16, 0.24]*
Low economic risk due to strong financials, but operational risk is pinned to its centralized control plane.
