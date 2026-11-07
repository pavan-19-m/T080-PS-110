# Week 2 Milestone Progress Report
**Team ID:** T080 | **Problem Statement:** PS-110  
**Project Title:** Cloud Kitchen Multi-brand Order Routing and Kitchen Capacity Engine  
**Team Members:** Pavan Neelappa Mirji & Padmavathi B (Section: CSD)

---

## 1. Executive Summary
During Week 2, Team T080 successfully designed and implemented the core foundation and happy-path execution of the Cloud Kitchen Multi-brand Order Routing and Kitchen Capacity Engine in Python 3.10+. All 14 Week 2 deliverables and acceptance criteria have been met with 100% test pass rates across 33 unit tests.

---

## 2. Week 2 Completed Deliverables
1. **Clean Python 3.10+ Project:** Complete object-oriented codebase using dataclasses, enums, type hints, and separation of concerns.
2. **Directory & Module Structure:** Standard modular layout (`src.models`, `src.input`, `src.routing`, `src.scheduling`, `src.accounting`, `src.reporting`, `src.services`).
3. **Kitchen & Station Management (BR-01):** Operating hours, brand support, delivery zone coverage, workstation slot capacity, and remaining load calculation.
4. **Brand & Catalog Registration:** Brand mapping to menu items and culinary recipes.
5. **CSV Ingestion & Validation:** Robust loading using `pathlib` and `csv` standard libraries; comprehensive entity and referential integrity validator.
6. **Kitchen Eligibility & Routing (BR-01):** Four-step eligibility filter, lowest projected ready time simulation, load tie-breaking, and kitchen ID tie-breaking.
7. **Order Sequencing & RUSH Priority (BR-03):** FIFO queue ordering, RUSH qualification (channel priority or order value > Rs. 1,500), maximum 3 jumps, and maximum 2 delays per order.
8. **Station Scheduling, Batching & Dependencies (BR-02, BR-04):** Slot concurrency, exact 3-minute recipe batching boundary, predecessor recipe dependency enforcement, and 3-minute packaging buffer.
9. **Promised Delivery Time & Throttling (BR-05, BR-06):** 5-minute buffer and ceil-rounding, 45-minute late-risk rerouting evaluation, 60-minute kitchen throttling, and 40-minute clearance.
10. **Channel Economics & Accounting (BR-09):** Aggregator A (22%), Aggregator B (18%), Own App (0% + Rs. 15), packaging fee capping (Rs. 10/item, max Rs. 40), 5% GST, and net brand earnings.
11. **Sample CSV Datasets:** Realistic, internally consistent CSV files (`kitchens.csv`, `stations.csv`, `brands.csv`, `menu_items.csv`, `recipes.csv`, `zones.csv`, `orders.csv`).
12. **Reporting & CLI Output:** Rich terminal report and automated CSV exports (`routing_decisions.csv`, `station_timelines.csv`, `order_financials.csv`).
13. **Comprehensive Pytest Suite:** 33 automated unit tests with descriptive BR-ID identifiers.
14. **Documentation:** Full system architecture, business rules register, architecture decision log, and README guide.

---

## 3. Test Execution Verification
- **Test Framework:** `pytest 9.2.0`
- **Tests Executed:** 33 tests
- **Tests Passed:** 33 passed (100% pass rate)
- **Execution Time:** ~0.24 seconds

---

## 4. Planned Week 3 Features (Roadmap)
The following advanced business rules will be implemented during Week 3:
- **BR-07 (Stock-out & Substitution):** Dynamic out-of-stock event handling, brand substitution table lookup, Rs. 20 price boundary evaluation, order repricing, and empty-order cancellation.
- **BR-08 (Cancellation Liability):** Pre-start free cancellation vs post-start liability, aggregator-initiated cancellation charging 100% of started items, and exact prep-start boundary resolution.
- **BR-10 (Late Delivery Penalty):** Lateness assessment against promised time (Rs. 50 per started 10 minutes, max Rs. 200), brand vs kitchen cost-centre attribution when lateness stems from throttled routing.
- **BR-11 (Brand-Kitchen Rent):** Daily rent calculations (Rs. 2/order + 3% net food value), Rs. 500 minimum rent when daily orders at kitchen < 30, and boundary handling for exactly 30 orders.
