# Architecture Decision Log (ADR)
**Team ID:** T080 | **Problem Statement:** PS-110  
**Project:** Cloud Kitchen Multi-brand Order Routing and Kitchen Capacity Engine  
**Team Members:** Pavan Neelappa Mirji & Padmavathi B (Section: CSD)

---

## ADR-001: Technology Stack Pivot from Java to Python
- **Status:** Approved
- **Context:** The team capstone assignment Week 2 specifically requires Python 3.10+, pytest, dataclasses, enums, type hints, and zero external GUI/Spring overhead.
- **Decision:** Pivot fully to clean Python 3.10+ standard libraries (`pathlib`, `csv`, `dataclasses`, `enum`, `datetime`, `typing`) with `pytest` for unit testing. The few preliminary Java files created during initial setup were preserved in `legacy_java/` without being deleted.

## ADR-002: Batching Exact 3-Minute Boundary Definition (BR-02)
- **Status:** Approved
- **Context:** BR-02 states identical recipes placed within 3 minutes may batch together up to recipe batch size, and must handle the exact 3-minute boundary.
- **Decision:** The delta is calculated as $|t_2 - t_1|$. If delta in seconds is $\le 180.0$, the items batch together. Exactly 180 seconds apart triggers batching; 181 seconds does not.

## ADR-003: Multi-Order RUSH Jump Mechanics (BR-03)
- **Status:** Approved
- **Context:** A RUSH order can jump ahead of up to 3 orders. An individual order cannot be delayed by more than 2 jumps.
- **Decision:** Each order in the sequencing queue tracks `delayed_jumps_count`, and each RUSH order tracks `rush_jumps_made`. A RUSH order scans preceding orders and swaps with them only if `preceding.delayed_jumps_count < 2` and `rush_jumps_made < 3`.

## ADR-004: Promised Delivery Time Mathematical Ceiling (BR-05)
- **Status:** Approved
- **Context:** BR-05 requires ready time + delivery zone minutes + 5-minute buffer, rounded UP to the next 5-minute boundary.
- **Decision:** If the raw sum is already on an exact 5-minute boundary with 0 seconds and 0 microseconds (e.g. 12:30:00), it remains unchanged. If any seconds/microseconds or non-multiple minutes exist (e.g. 12:30:01), it strictly rounds up to the next 5-minute multiple (12:35:00).

## ADR-005: Kitchen Current Load Metric for Tie-Breaking (BR-01)
- **Status:** Approved
- **Context:** Ties in projected ready time are broken by lowest current load.
- **Decision:** Current load is computed as the total remaining busy minutes across all workstation slots in that kitchen at the order arrival timestamp. If current loads are also identical, tie-break by lowest kitchen ID alphabetically.
