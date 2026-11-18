# Architecture Decision Log (ADR)
**Team ID:** T080 | **Problem Statement:** PS-110  
**Project:** Cloud Kitchen Multi-brand Order Routing and Kitchen Capacity Engine  
**Team Members:** Padmavathi B (1AT24CG059) & Pavan Neelappa Mirji (1AT24CG060)  
**Academic Section:** CSD  

---

## ADR-001: Technology Stack Selection - Pure Python Backend
- **Status:** Approved
- **Context:** The capstone assignment requires a deterministic, database-free, command-line-driven backend application using Python 3.10+, pytest, dataclasses, enums, and comprehensive type hints. Web frameworks (Flask, Django, FastAPI) and GUI toolkits are strictly forbidden.
- **Decision:** Implement the entire engine using standard Python 3.10+ libraries (`pathlib`, `csv`, `dataclasses`, `enum`, `datetime`, `typing`, `math`) and `pytest` for automated test suites. Ingestion and outputs utilize standardized CSV formats with rich terminal reporting.

---

## ADR-002: Batching Window and Exact 3-Minute Boundary Definition (BR-02)
- **Status:** Approved
- **Context:** BR-02 states identical recipes placed within 3 minutes on the same station may batch together up to the recipe's maximum batch size. The system must deterministically handle the exact 3-minute boundary.
- **Decision:** The delta is calculated as $|t_2 - t_1|$. If $\Delta t \le 180.0$ seconds, the items batch together. Exactly 180 seconds apart triggers batching; 181 seconds does not. Batch size never exceeds `recipe.max_batch_size`.

---

## ADR-003: Multi-Order RUSH Jump Mechanics and Delay Throttling (BR-03)
- **Status:** Approved
- **Context:** A RUSH order (flagged via channel priority or order value $\ge$ ₹1,500) can jump ahead of up to 3 orders. An individual order cannot be delayed by more than 2 jumps.
- **Decision:** Each order in the sequencing queue tracks `delayed_jumps_count`, and each RUSH order tracks `rush_jumps_made`. A RUSH order scans preceding orders and swaps with them only if `preceding.delayed_jumps_count < 2` and `rush_jumps_made < 3`. This strictly prevents order starvation.

---

## ADR-004: Promised Delivery Time Mathematical Ceiling (BR-05)
- **Status:** Approved
- **Context:** BR-05 requires ready time + delivery zone minutes + 5-minute buffer, rounded UP to the next 5-minute boundary.
- **Decision:** If the raw sum is already on an exact 5-minute boundary with 0 seconds and 0 microseconds (e.g., 12:30:00), it remains unchanged. If any seconds/microseconds or non-multiple minutes exist (e.g., 12:30:01), it strictly rounds up to the next 5-minute multiple (12:35:00).

---

## ADR-005: Kitchen Current Load Metric for Tie-Breaking (BR-01)
- **Status:** Approved
- **Context:** Ties in projected ready time are broken by lowest current load, followed by lowest kitchen ID alphabetically.
- **Decision:** Current load is computed as the total remaining busy minutes across all workstation slots in that kitchen at the order arrival timestamp. If current loads are also identical, tie-break by lowest kitchen ID (`K-01 < K-02`).

---

## ADR-006: Throttling Hysteresis and Sole Eligible Kitchen Exception (BR-06)
- **Status:** Approved
- **Context:** A kitchen must be throttled when projected ready time exceeds 60 minutes. Throttling is cleared only when load drops below 40 minutes. Throttled kitchens cannot take normal orders unless they are the sole eligible hub.
- **Decision:** A stateful `is_throttled` flag is maintained on each `Kitchen`. When projected ready time $> 60$ minutes, `is_throttled` is set to `True`. During routing, throttled kitchens are excluded if any non-throttled eligible kitchens exist. If a throttled kitchen is the *only* eligible kitchen in the delivery zone for that brand/menu, it accepts the order under `throttled_routing=True`. When load drops $< 40$ minutes, throttling automatically clears.

---

## ADR-007: Stockout Substitutions and Price Differential Boundary (BR-07)
- **Status:** Approved
- **Context:** When an item is stocked out at a kitchen, the engine checks substitution tables. Substitutes are permitted only if their price difference does not exceed +₹20 compared to the original item.
- **Decision:** When `price(substitute) - price(original) <= 20.00`, the substitution is automatically applied with `status = SUBSTITUTED`. If the price delta is $> 20.00$, the item is rejected, causing the order to fail validation and transition to `REJECTED`.

---

## ADR-008: Cancellation Status Transition and Sunk Cost Accounting (BR-08)
- **Status:** Approved
- **Context:** Cancellations can arrive before preparation begins (free cancellation) or after preparation has started (charged cancellation with full customer charge and station slot occupancy).
- **Decision:** If cancellation timestamp $\le$ actual start time of the first item, the order transitions to `CANCELLED_FREE`, scheduled workstation slots are released, and ₹0 is charged. If cancellation timestamp $>$ actual start time, the order transitions to `CANCELLED_CHARGED`, customer pays full price (food + packaging + GST), stations complete preparation to avoid inventory waste, and platform accounting applies. At the exact prep start time ($t_{cancel} = t_{start}$), it is classified as `CANCELLED_FREE`.

---

## ADR-009: Revenue Sharing, Fixed Platform Fees, and GST Apportionment (BR-09)
- **Status:** Approved
- **Context:** Platform channels have distinct commercial agreements:
  - Aggregator A: 22% commission on food value.
  - Aggregator B: 18% commission on food value.
  - Own App: 0% commission + ₹15 fixed fee per order.
  Packaging is ₹10 for the first item + ₹5 for each subsequent item, capped at ₹40. GST is 5% on food value.
- **Decision:** All financial metrics are calculated with `round(val, 2)`. Net food value $= \text{Food Value} - \text{Commission} - \text{Fixed Fee}$. Total customer bill $= \text{Food Value} + \text{Packaging} + \text{GST}$.

---

## ADR-010: Late Hand-off Penalties and Kitchen vs Delivery Cost Centres (BR-10)
- **Status:** Approved
- **Context:** When actual hand-off exceeds promised delivery time, a late penalty of ₹50 per 10-minute delay block is charged, capped at ₹200. The cost centre must be attributed correctly based on kitchen ready time vs courier pickup delay.
- **Decision:** Delay blocks are calculated using ceiling division: $\lceil \Delta t / 10 \rceil \times 50$, capped at ₹200. If `actual_ready_time > scheduled_ready_time`, the fault lies with the kitchen (`KITCHEN_OPERATIONS`). If `actual_pickup_time > actual_ready_time`, the fault lies with the courier aggregator (`DELIVERY_FLEET`).

---

## ADR-011: Daily Kitchen Rent Settlement and Order Volume Threshold (BR-11)
- **Status:** Approved
- **Context:** Each virtual brand pays kitchen rent: ₹2 per order + 3% of net food value. If a brand generates fewer than 30 orders at a kitchen during the day, a minimum rent of ₹500 applies. Exactly 30 orders does not trigger the minimum.
- **Decision:** Group orders by `(brand_id, assigned_kitchen_id)`. Calculate raw rent $= 2 \times N + 0.03 \times \sum(\text{Net Food})$. If $N < 30$, `final_rent = max(500.0, raw_rent)` with `minimum_rent_applied = True`. If $N \ge 30$, `final_rent = raw_rent` with `minimum_rent_applied = False`.

---

## ADR-012: Pipeline Rule Execution Precedence (BR-12)
- **Status:** Approved
- **Context:** Conflicting rules must follow a strict, deterministic evaluation sequence.
- **Decision:** Enforce the following canonical pipeline:
  1. Data Ingestion & Schema Validation (DataValidator)
  2. Order Integrity & Stockout/Substitution Check (BR-07)
  3. Kitchen Eligibility Filtering (BR-01)
  4. Throttling State Verification (BR-06)
  5. Priority & Jump Queue Sequencing (BR-03)
  6. Station Capacity & Dependency Scheduling (BR-02, BR-04)
  7. Ready Time & Promised Time Calculation (BR-04, BR-05)
  8. Cancellation & Lifecycle Event Processing (BR-08, BR-10)
  9. Financial & P&L Settlement (BR-09, BR-10, BR-11)
  10. Audit Reporting & CSV Export (ReportGenerator)
