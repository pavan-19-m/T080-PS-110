# Capstone Demonstration Script (5-Minute Evaluation Walkthrough)
**Team ID:** T080 | **Problem Statement:** PS-110  
**Project:** Cloud Kitchen Multi-Brand Order Routing and Kitchen Capacity Engine  
**Team Members:** Padmavathi B (1AT24CG059) & Pavan Neelappa Mirji (1AT24CG060)  
**Academic Section:** CSD  

---

## 1. Overview & Setup

This demonstration script provides an evaluator-ready, step-by-step 5-minute walkthrough of the Cloud Kitchen Engine. It demonstrates the live terminal execution, business rules enforcement, station scheduling, dynamic batching, priority queue jumping, and end-of-day financial settlement.

- **Project Video Demonstration (Google Drive):** [Watch Video (T080-PS_110.mp4)](https://drive.google.com/file/d/1CkfR5VdzqK_3mf63K-Z7Ge5rqvkp7-ts/view?usp=drive_link)

### Prerequisites & Environment Verification
Ensure you are in the project root directory and Python 3.10+ is available:
```bash
python --version
# Expected: Python 3.10+ (or 3.14)
```

---

## 2. Five-Minute Evaluation Timeline

| Time | Phase | Focus Areas & Business Rules |
| :--- | :--- | :--- |
| **00:00 - 01:00** | Introduction & Test Suite | Architecture overview, 83 unit & edge case tests passing in <1s |
| **01:00 - 02:00** | Data Ingestion & Routing | Multi-brand eligibility, delivery zones, 45-min reroute/late risk (BR-01, BR-05, BR-06) |
| **02:00 - 03:00** | Capacity & Batching | Station slots, 3-minute batching window, parallel prep (BR-02, BR-04) |
| **03:00 - 04:00** | Priority & Lifecycle Events | RUSH order jump limits (3 jumps max, 2 delay max), cancellations (BR-03, BR-07, BR-08) |
| **04:00 - 05:00** | Accounting & Audit Reports | Channel commissions, packaging caps, late penalties, brand P&L (BR-09, BR-10, BR-11) |

---

## 3. Minute-by-Minute Walkthrough Script

### Minute 00:00 - 01:00: Test Suite Verification & Codebase Integrity

**Speaking Point:**  
> *"Good morning respected evaluators. We are Team T080, presenting our capstone project: the Cloud Kitchen Multi-Brand Order Routing and Kitchen Capacity Engine. Our engine is built in Python 3.10+ using object-oriented, database-free architecture. Before running the full pipeline, we demonstrate our automated test suite comprising 83 tests covering all 12 core business rules and mandatory edge cases."*

**Command to Execute:**
```bash
pytest -v
```

**Expected Terminal Output:**
```text
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\...\T080-PS-110
collected 83 items

tests/test_accounting.py ............                                   [ 14%]
tests/test_business_rules.py ............                               [ 28%]
tests/test_edge_cases.py ........                                       [ 38%]
tests/test_kitchen.py ....                                              [ 43%]
tests/test_models.py ........                                           [ 53%]
tests/test_order.py ........                                            [ 62%]
tests/test_routing.py ..............                                    [ 79%]
tests/test_scheduling.py ........                                       [ 89%]
tests/test_validation.py ............                                   [100%]

============================= 83 passed in 0.33s ==============================
```

---

### Minute 01:00 - 02:00: Main Pipeline Execution & Intelligent Routing

**Speaking Point:**  
> *"Now we execute the main engine pipeline against our realistic production dataset in `sample-data/`. The system ingests kitchens, stations, brands, recipes, delivery zones, and customer orders. Notice how incoming orders are evaluated across physical hubs."*

**Command to Execute:**
```bash
python main.py
```

**Key Explanations for Evaluators:**
1. **Kitchen Eligibility (BR-01):**  
   Order `ORD-101` (Brand `B-01`, Zone `ZONE-CENTRAL`) routes to `K-01` because `K-01` serves `B-01`, operates during order hours, has available `GRILL` and `FRYER` stations, and projected ready time is 12:08:00.
2. **Rejection Handling:**  
   Order `ORD-114` (Brand `B-03` in `ZONE-NORTH`) is immediately flagged as `REJECTED` because no kitchen in `ZONE-NORTH` possesses both the brand license and the requisite `BAKERY` station.

---

### Minute 02:00 - 03:00: Culinary Station Scheduling, Batching, and Dependencies

**Speaking Point:**  
> *"In multi-brand cloud kitchens, culinary stations like Fryers and Grills are scarce resources. Our engine schedules discrete time slots and dynamically batches identical recipes arriving within 3 minutes."*

**Demonstration Scenarios:**
1. **Dynamic Batching Window (BR-02):**  
   - Show how `ORD-101` and `ORD-102` items sharing `REC-FRIES` on Fryer Station Slot #1 are merged into a single cooking batch (`BATCH-0002`), reducing total cooking cycles by 50%.
   - Explain edge case TC-01: An order arriving at 12:00:00 and another at 12:03:00 are exactly 180 seconds apart and batch successfully.
2. **Prerequisite Recipe Dependencies (BR-04):**  
   - Show `REC-GARLICBREAD` requiring `REC-DOUGH`. The scheduler ensures `REC-DOUGH` is completed on Bakery Station before `REC-GARLICBREAD` begins, with parallel items (e.g. Pasta on Wok) cooking concurrently.
3. **Packaging Phase:**  
   - Exactly 3 minutes of packaging is appended after the final item completes to determine final Ready Time.

---

### Minute 03:00 - 04:00: Order Sequencing, RUSH Priority Jumps, and Lifecycle Events

**Speaking Point:**  
> *"We maintain a deterministic FIFO queue that accommodates RUSH orders (orders over ₹1,500 or aggregator priority flags) while strictly preventing order starvation."*

**Demonstration Scenarios:**
1. **RUSH Queue Jump Restrictions (BR-03):**  
   - Order `ORD-106` (value ₹1,657.00) qualifies as `RUSH`. It jumps ahead of earlier regular orders in the scheduling queue.
   - Point to the code enforcing:  
     a) Max 3 jumps per RUSH order (`rush_jumps_made < 3`).  
     b) Max 2 delays per normal order (`delayed_jumps_count < 2`).
2. **Order Lifecycle Events (BR-08):**  
   - `ORD-101`: Cancelled at 12:01:00 (before preparation starts at 12:02:00) $\rightarrow$ `CANCELLED_FREE`, slots released, ₹0 charged.
   - `ORD-104`: Cancelled at 12:12:00 (after prep began at 12:08:00) $\rightarrow$ `CANCELLED_CHARGED`, slots maintained to avoid food waste, customer charged in full.

---

### Minute 04:00 - 05:00: Financial Auditing, P&L Settlement, and Generated Reports

**Speaking Point:**  
> *"Finally, our engine acts as an automated settlement clearinghouse across virtual brands, physical kitchen landlords, and ordering aggregators."*

**Demonstration Scenarios:**
1. **Channel Economics (BR-09):**  
   - Aggregator A: 22% commission deducted from food value.
   - Aggregator B: 18% commission deducted.
   - Own App: 0% commission + ₹15 fixed fee.
   - Packaging fee: ₹10 for item 1, ₹5 per additional item, strictly capped at ₹40.
2. **Daily Kitchen Rent & Minimum Fee (BR-11):**  
   - Rent Formula: ₹2 per order + 3% of net food value.
   - If a brand executes $< 30$ orders at a kitchen, minimum ₹500 rent applies.
   - Point out the terminal table where brands with low volumes show `YES (Rs. 500)` under the minimum rent trigger column.
3. **Audit Artifacts in `output/`:**  
   Inspect generated CSV reports:
   ```bash
   dir output
   # Lists:
   # routing_decisions.csv
   # station_timelines.csv
   # order_financials.csv
   # daily_brand_pnl.csv
   # kitchen_daily_reports.csv
   # channel_reports.csv
   ```

---

## 4. Evaluator Q&A Quick Reference

| Potential Question | Concise Technical Answer |
| :--- | :--- |
| **Why not use an external SQL database?** | In high-throughput cloud kitchens, sub-millisecond in-memory scheduling avoids database transaction locks. In-memory dataclasses allow deterministic discrete-event simulation with CSV ingestion and export. |
| **How do you ensure RUSH orders don't starve normal orders?** | Every order tracks its historical `delayed_jumps_count`. Once an order has been delayed twice, subsequent RUSH orders are blocked from overtaking it. |
| **How is circular recipe dependency prevented?** | `DataValidator.validate_recipes_dependency_graph` executes depth-first cycle detection during initial CSV ingestion, rejecting cyclic graphs before runtime. |
| **What happens when actual hand-off is late?** | BR-10 calculates ₹50 per 10-minute block capped at ₹200. Cost centre attribution separates kitchen prep delays from courier arrival delays. |
