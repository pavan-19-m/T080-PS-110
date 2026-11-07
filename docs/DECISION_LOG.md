# Architecture Decision Log (ADR)
**Team ID:** T080 | **Problem Statement:** PS-110  
**Project:** Cloud Kitchen Multi-brand Order Routing and Kitchen Capacity Engine  
**Team Members:** Pavan Neelappa Mirji & Padmavathi B (Section: CSD)

---

## ADR-001: Language & Architecture Style
- **Status:** Approved
- **Context:** Project requires Java 17+, modular OOP architecture, and command-file-driven execution.
- **Decision:** Use Java 17 LTS syntax (records, pattern matching, streams) with domain-driven modular packages (`model`, `routing`, `scheduling`, `event`, `accounting`, `reporting`, `input`). Avoid monoliths and bloated external libraries to ensure high portability, zero runtime conflicts, and transparent defense in college viva.

## ADR-002: CSV Input/Output Design
- **Status:** Approved
- **Context:** The system must accept CSV datasets and produce deterministic CSV outputs without hardcoded sample data.
- **Decision:** Implement a standard, lightweight RFC-4180 compliant CSV parser and writer using `java.io.BufferedReader` and `java.io.PrintWriter`. Explicit validation ensures empty lines, bad numbers, and missing fields are rejected with clear, friendly error messages.

## ADR-003: Kitchen Load Metric Definition (BR-01)
- **Status:** Approved
- **Context:** BR-01 requires breaking ties in routing by "lowest current load".
- **Decision:** Current load is quantified as the total remaining scheduled preparation minutes across all occupied slots in that kitchen at the order arrival timestamp. This accurately mirrors real-world cloud kitchen capacity stress.

## ADR-004: Promised Time Ceil-Rounding Behavior (BR-05)
- **Status:** Approved
- **Context:** BR-05 specifies rounding up to the next 5-minute boundary.
- **Decision:** We implement mathematical ceiling to the 5-minute boundary:
  $$\text{ceil5}(M) = \begin{cases} M & \text{if } M \pmod 5 = 0 \\ M + (5 - (M \pmod 5)) & \text{if } M \pmod 5 \neq 0 \end{cases}$$
  An exact 5-minute boundary (e.g. 12:40:00) remains unchanged; any second or minute beyond (e.g. 12:40:01) rounds up to 12:45:00.

## ADR-005: RUSH Priority Multi-Order Jump Tracking (BR-03)
- **Status:** Approved
- **Context:** A RUSH order can jump ahead of up to 3 orders, but no order can be delayed by more than 2 jumps.
- **Decision:** Each order in the scheduling queue tracks `delayedCount`. When a RUSH order attempts to jump, it iterates through orders ahead of it in reverse: it jumps an order only if `delayedCount < 2`. The RUSH order stops jumping once it has performed 3 successful jumps or encounters an order that cannot be delayed further.

## ADR-006: Throttling State & Sole Kitchen Rule (BR-06)
- **Status:** Approved
- **Context:** When projected ready time exceeds 60 minutes, mark kitchen THROTTLED.
- **Decision:** Throttling is evaluated on arrival. If a kitchen is THROTTLED, it is excluded from eligible kitchens unless it is the single, sole eligible kitchen that can physically fulfill the order. Throttling is cleared when projected load drops strictly below 40 minutes.

## ADR-007: Net Food Value in Rent Calculation (BR-11)
- **Status:** Approved
- **Context:** BR-11 defines rent as ₹2 per order + 3% of net food value.
- **Decision:** Net food value is computed as `Gross Food Price - Aggregator Commission`. Delivery fee, packaging fee, and GST are separate pass-through components and excluded from brand food rent.
