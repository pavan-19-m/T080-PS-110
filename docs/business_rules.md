# Business Rules Register (BR-01 to BR-12)

**Project Title:** Cloud Kitchen Multi-Brand Order Routing and Kitchen Capacity Engine  
**Team ID:** T080 | **Problem Statement:** PS-110  
**Team Members:** Pavan Neelappa Mirji & Padmavathi B  

---

## Complete Business Rule Specifications

### BR-01: Kitchen Eligibility and Routing
- **Rule Statement:** A kitchen is eligible for an incoming order only if:
  1. It supports the requested brand (`brand_id in kitchen.supported_brands`).
  2. It is listed in the delivery zone's eligible kitchen list (`kitchen_id in zone.eligible_kitchen_ids`).
  3. It is open at the order timestamp (`open_time <= t <= close_time`, including overnight shifts).
  4. It contains all culinary workstations required by the order's items with capacity $> 0$.
- **Tie-Breaker Hierarchy:**
  1. Lowest projected ready time.
  2. Lowest current active workload (remaining busy minutes across all slots).
  3. Lowest alphanumeric kitchen ID.
- **Code Implementation:** `src/routing/kitchen_eligibility.py` (`KitchenEligibilityChecker`) and `src/routing/order_router.py`.

---

### BR-02: Station Capacity and Batching
- **Rule Statement:**
  - Each item occupies exactly one workstation slot for the duration of its recipe's `prep_minutes`.
  - Items sharing an identical `recipe_id` on the same workstation arriving within 3 minutes ($\le 180$ seconds) can be batched together into a single slot.
  - The batch size must never exceed the recipe's `max_batch_size`.
  - The exact 3-minute boundary ($\Delta t = 180.0\text{ seconds}$) is strictly treated as within the batching window.
- **Code Implementation:** `src/scheduling/batching.py` (`BatchingEngine`), `src/models/batch.py`, and `src/scheduling/station_scheduler.py`.

---

### BR-03: FIFO and RUSH Priority
- **Rule Statement:**
  - Normal orders follow First-In, First-Out (FIFO) sequencing based on order placement timestamp.
  - An order qualifies as **RUSH** if its ordering channel has `channel_priority == True` OR its gross food value exceeds ₹1,500 (`food_value > 1500.0`).
  - A RUSH order can jump ahead of up to 3 non-RUSH orders (`max_rush_jumps = 3`).
  - Starvation Prevention: An individual non-RUSH order cannot be delayed by more than 2 jumps (`max_delay_jumps = 2`).
- **Code Implementation:** `src/scheduling/order_sequencer.py` (`OrderSequencer`).

---

### BR-04: Ready-Time Calculation & Dependencies
- **Rule Statement:**
  - Preparation dependencies must be respected: if Recipe $B$ depends on Recipe $A$, item $B$ cannot begin preparation until item $A$ has completed its cooking duration ($\text{start}_B \ge \text{end}_A$).
  - Order ready time is the maximum completion time across all ordered items plus 3 minutes of packaging:
    $$\text{Ready Time} = \max_{i \in \text{Items}}(\text{end}_i) + 3\text{ minutes}$$
- **Code Implementation:** `src/scheduling/dependency_manager.py` and `src/scheduling/station_scheduler.py`.

---

### BR-05: Promised-Time Calculation & Late-Risk Rerouting
- **Rule Statement:**
  - Base formula:
    $$\text{Raw Promised Time} = \text{Ready Time} + \text{Delivery Minutes} + 5\text{ minutes buffer}$$
  - The raw promised time is rounded **UP** to the next 5-minute boundary ($\lceil T/5 \rceil \times 5$). If the raw time falls on an exact 5-minute mark with 0 seconds, it remains unchanged.
  - If the projected ready time is **more than 45 minutes** after order placement:
    - Check alternative eligible kitchens.
    - Reroute only if an alternative kitchen reduces projected ready time by **at least 10 minutes** ($\Delta \text{ready} \ge 10\text{ minutes}$).
    - If no alternative kitchen achieves a $\ge 10$-minute reduction, accept the order with `LATE_RISK`.
- **Code Implementation:** `src/routing/order_router.py` (`OrderRouter.calculate_promised_time`).

---

### BR-06: Kitchen Throttling (Hysteresis)
- **Rule Statement:**
  - When a kitchen's projected ready time for a new order exceeds 60 minutes after placement ($\text{delay} > 60\text{ minutes}$), the kitchen is marked `THROTTLED`.
  - A throttled kitchen accepts new orders **only when it is the sole eligible kitchen** for that order.
  - Throttling is cleared when the kitchen's projected ready delay or active load drops strictly below 40 minutes ($< 40\text{ minutes}$).
- **Code Implementation:** `src/routing/order_router.py` (`filter_throttling`).

---

### BR-07: Stock-Outs and Substitutions
- **Rule Statement:**
  - If an item is unavailable at the selected kitchen (`item_id in kitchen.stock_out`), check the brand's substitution catalog.
  - A substitute item is accepted if its retail price is within ₹20 of the original item's price:
    $$|\text{price}_{\text{substitute}} - \text{price}_{\text{original}}| \le \text{Rs. 20.00}$$
  - An exact ₹20 difference is explicitly allowed.
  - If no acceptable substitute exists, the unavailable item is removed and the order is repriced.
  - If no items remain in the order, the order is marked `CANCELLED`.
- **Code Implementation:** `src/services/substitution_service.py` (`SubstitutionService`).

---

### BR-08: Cancellation Rules
- **Rule Statement:**
  - Cancellation before any item begins preparation ($\text{cancelled\_at} < \min(\text{prep\_start})$): **Free cancellation** (Charge = ₹0).
  - Cancellation after preparation begins: The customer is charged 100% of the retail price of all started items.
  - Aggregator cancellation after preparation begins: The channel platform is charged 100% of the retail price of started items.
  - Exact Instant Rule (Edge Case 6): If cancellation occurs at the exact second preparation starts ($\text{cancelled\_at} == \min(\text{prep\_start})$), preparation is treated as started; the charge applies.
- **Code Implementation:** `src/services/cancellation_service.py` (`CancellationService`).

---

### BR-09: Channel Commissions, Packaging, and GST
- **Platform Economics:**
  - **Aggregator A:** 22% commission on gross food value.
  - **Aggregator B:** 18% commission on gross food value.
  - **Own App:** 0% commission + ₹15 fixed transaction payment fee.
- **Packaging Fee:**
  - ₹10 per item, capped at a maximum of ₹40 per order:
    $$\text{Packaging Fee} = \min(\text{Item Count} \times 10, 40)$$
- **GST:**
  - 5% tax on gross food value:
    $$\text{GST} = \text{Food Value} \times 0.05$$
- **Code Implementation:** `src/accounting/accounting_engine.py` (`AccountingEngine.calculate_order_financials`).

---

### BR-10: Late Hand-off Penalties
- **Rule Statement:**
  - If courier hand-off occurs after the promised delivery time ($\text{handoff\_time} > \text{promised\_time}$), a penalty is assessed:
    $$\text{Blocks} = \lceil \text{Lateness Minutes} / 10 \rceil$$
    $$\text{Penalty} = \min(\text{Blocks} \times \text{Rs. 50}, \text{Rs. 200})$$
  - Cost Centre Responsibility:
    - Default: Charged to the **Brand**.
    - If lateness was caused by routed through a `THROTTLED` kitchen: Charged to the **Kitchen** cost centre.
- **Code Implementation:** `src/accounting/penalty_calculator.py` (`PenaltyCalculator`).

---

### BR-11: Kitchen Rent and Lease Settlements
- **Rule Statement:**
  - Brand pays the kitchen operator:
    $$\text{Calculated Rent} = (\text{Order Count} \times \text{Rs. 2}) + (\text{Net Food Sales} \times 3\%)$$
  - Minimum Rent Threshold:
    - If a brand processes fewer than 30 orders in a day at a physical kitchen ($\text{count} < 30$), a minimum rent of ₹500 applies:
      $$\text{Final Rent} = \max(\text{Calculated Rent}, \text{Rs. 500})$$
    - **Edge Case 8:** Exactly 30 orders ($\text{count} == 30$) does **NOT** trigger the minimum rent.
- **Code Implementation:** `src/accounting/rent_calculator.py` (`RentCalculator`).

---

### BR-12: Rule Execution Precedence
- **Pipeline Execution Sequence:**
  1. Kitchen Eligibility Filtering (BR-01).
  2. Kitchen Throttling Evaluation (BR-06).
  3. Kitchen Selection via Projected Ready-Time Simulation (BR-01, BR-05).
  4. Brand Substitution Evaluation before slot booking (BR-07).
  5. Order Sequencing and RUSH Priority Jumps (BR-03).
  6. Multi-Item Dynamic Batching (BR-02).
  7. Workstation Topological Dependency Scheduling (BR-04).
  8. Ready-Time and Promised-Time Calculation (BR-04, BR-05).
  9. Financial Settlement, Commission, Packaging, GST, Penalties, and Rent (BR-09, BR-10, BR-11).
- **Code Implementation:** `src/services/order_service.py` (`OrderService.process_all_orders`).
