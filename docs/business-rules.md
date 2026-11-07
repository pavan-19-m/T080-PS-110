# Business Rules Register (BR-01 to BR-12)
**Team ID:** T080 | **Problem Statement:** PS-110  
**Project:** Cloud Kitchen Multi-brand Order Routing and Kitchen Capacity Engine  
**Team Members:** Pavan Neelappa Mirji & Padmavathi B (Section: CSD)

---

## Complete Rule Specification & Week 2 Implementation Status

| Rule ID | Rule Name | Specification & Logic | Week 2 Status | Test Coverage |
| :--- | :--- | :--- | :---: | :--- |
| **BR-01** | Kitchen Eligibility & Routing | Kitchen is eligible if: (1) serves brand, (2) listed in zone, (3) open at order time, (4) has all required stations. Select eligible kitchen with lowest projected ready time. Break ties by lowest current load, then lowest kitchen ID. | **IMPLEMENTED** | `tests/test_routing.py`<br>`tests/test_kitchen.py` |
| **BR-02** | Station Capacity & Batching | Station has configured slots. 1 item occupies 1 slot for prep minutes. Identical recipes placed within 3 minutes ($\le 3$ min) batch into 1 slot up to `max_batch_size`. Exact 3-minute boundary handled ($\Delta t \le 180\text{s}$). | **IMPLEMENTED** | `tests/test_scheduling.py` |
| **BR-03** | Order Sequencing & RUSH Priority | Default FIFO by order time. RUSH if channel priority flag is True OR order value > Rs. 1,500. RUSH order may jump up to 3 orders. An order cannot be delayed by > 2 jumps. Jumps tracked explicitly. | **IMPLEMENTED** | `tests/test_order.py` |
| **BR-04** | Ready Time & Dependencies | Ready time = max item completion + 3 min packaging. Predecessor recipes must finish before dependent recipes can start ($\text{start}_B \ge \text{end}_A$). | **IMPLEMENTED** | `tests/test_scheduling.py` |
| **BR-05** | Promised Time & Late Risk | Promised time = ready time + delivery minutes + 5-min buffer, rounded UP to 5-min boundary ($\lceil T/5 \rceil \times 5$). If ready time > order time + 45 min, evaluate rerouting ($\ge 10$ min saving needed), else set `LATE_RISK`. | **IMPLEMENTED** | `tests/test_routing.py`<br>`tests/test_scheduling.py` |
| **BR-06** | Load Shedding / Throttling | Projected ready time > 60 min marks kitchen `THROTTLED`. Throttled kitchen accepts only if sole eligible kitchen. Clears when load < 40 min. | **IMPLEMENTED** | `tests/test_routing.py` |
| **BR-07** | Stock-Out & Substitution | Out-of-stock item substituted if substitute price within Rs. 20 (inclusive). Otherwise remove item and reprice; cancel if 0 items remain. | *Week 3 Deliverable* | Prepared for Week 3 |
| **BR-08** | Cancellation Liability | Free before any prep starts. After prep starts, charge started items. Aggregator cancels: charge channel 100% of started items. Exact start instant counts as started. | *Week 3 Deliverable* | Prepared for Week 3 |
| **BR-09** | Channel Economics | Aggregator A: 22% commission. Aggregator B: 18% commission. Own App: 0% commission + Rs. 15 fee. Packaging: Rs. 10/item, max Rs. 40/order. GST: 5% on food. | **IMPLEMENTED** | `tests/test_accounting.py` |
| **BR-10** | Late Delivery Penalty | Hand-off > promised time: Rs. 50 per started 10 min late, capped at Rs. 200. Charge brand normally; charge kitchen cost centre if throttled routing caused lateness. | *Week 3 Deliverable* | Prepared for Week 3 |
| **BR-11** | Brand-Kitchen Rent | Brand pays Rs. 2/order + 3% net food value. < 30 orders/day at kitchen applies Rs. 500 minimum. Exactly 30 orders does not qualify for minimum. | *Week 3 Deliverable* | Prepared for Week 3 |
| **BR-12** | Rule Precedence | Pipeline order: Eligibility $\rightarrow$ Throttling $\rightarrow$ Substitution $\rightarrow$ Routing by ready time $\rightarrow$ Sequencing (RUSH jumps) $\rightarrow$ Batching $\rightarrow$ Dependencies $\rightarrow$ Promised time. | **IMPLEMENTED** | `src/services/order_service.py` |
