# Project Glossary
**Team ID:** T080 | **Problem Statement:** PS-110  
**Project:** Cloud Kitchen Multi-brand Order Routing and Kitchen Capacity Engine  
**Team Members:** Pavan Neelappa Mirji & Padmavathi B (Section: CSD)

---

## 1. Cloud Kitchen & Operations Terminology
- **Cloud Kitchen (Ghost Kitchen / Dark Kitchen):** A centralized food production facility that prepares delivery-only food orders for multiple virtual brands without a dine-in storefront.
- **Virtual Food Brand:** A restaurant concept/brand (e.g., "BurgerCraze", "BowlStop", "CurryPoint") operated under the umbrella of a cloud kitchen company.
- **Station:** A distinct culinary work area inside a kitchen dedicated to specific preparation equipment and tasks:
  - `GRILL`: Flat tops, char-broilers, burger presses.
  - `FRYER`: Deep-fry stations for fries, nuggets, wings.
  - `WOK`: High-heat wok ranges for stir-fries, noodles, fried rice.
  - `COLD`: Salads, sushi, beverage assembly, cold desserts.
  - `BAKERY`: Ovens, dough handling, baking equipment.
- **Station Slot:** The unit of parallel concurrency within a station. If a `FRYER` has 2 slots, it can process at most 2 distinct cooking batches simultaneously.
- **Batching:** The operational grouping of identical recipes arriving within a narrow time window ($\le 3$ minutes) into a single station slot run, up to the maximum batch limit of that recipe.
- **Recipe Dependency:** A preparation prerequisite where one item in an order must finish before another dependent item begins (e.g., grilled patty must finish before burger assembly).

## 2. Order & Lifecycle Terminology
- **Channel:** The digital ordering platform where customer orders originate:
  - `AGGREGATOR_A` (e.g., Zomato-equivalent, 22% commission)
  - `AGGREGATOR_B` (e.g., Swiggy-equivalent, 18% commission)
  - `OWN_APP` (Direct-to-consumer mobile app / website, 0% commission + ₹15 fixed fee)
- **Delivery Zone:** The geographic delivery sector specifying transit duration (minutes) and lists of reachable kitchens.
- **Projected Ready Time:** The estimated timestamp when all items in an order finish cooking and pass packaging (including a mandatory 3-minute packaging buffer after the final item completes).
- **Promised Delivery Time:** The delivery estimate displayed to the customer:
  $$\text{Promised Time} = \text{Ready Time} + \text{Zone Delivery Minutes} + 5\text{ min buffer (rounded UP to 5-min boundary)}$$
- **RUSH Priority:** Expedited order status triggered either by a channel priority flag (`channelPriority == true`) or order value exceeding ₹1,500. A RUSH order can jump ahead of up to 3 non-RUSH orders in the scheduling queue.
- **Delayed Jump Count:** The number of times a given non-RUSH order has been skipped by RUSH orders. An order cannot be delayed by more than 2 jumps.
- **LATE_RISK:** A status flag stamped on an order when projected ready time exceeds 45 minutes from order intake and no alternative kitchen reduces the ready time by at least 10 minutes.
- **THROTTLED:** A load-shedding state triggered when a kitchen's projected ready time for a new order exceeds 60 minutes. While throttled, the kitchen accepts ONLY orders for which it is the sole eligible provider. Throttling clears when projected load falls strictly below 40 minutes.
- **Stock-Out:** Unavailability of one or more ingredients or items at a specific kitchen location.
- **Substitution:** Replacing an out-of-stock item with a designated substitute item from the brand substitution registry, provided the price difference is within ₹20 (inclusive).
- **Cancellation:** Order termination event. Cancellations occurring before any item starts cooking are free; cancellations occurring at or after the exact start instant incur charges.

## 3. Financial & Accounting Terminology
- **Gross Food Value:** Sum of base prices of all active items in the order.
- **Net Food Value:** Gross food value minus aggregator platform commission.
- **Packaging Fee:** ₹10 per item in the order, capped at a maximum of ₹40 per order.
- **GST:** 5% Goods and Services Tax charged on the food value.
- **Late Delivery Penalty:** ₹50 per started 10 minutes of lateness beyond promised time, capped at ₹200. Charged to the Brand unless lateness was caused by a `THROTTLED` kitchen routing, in which case it is charged to the Kitchen cost centre.
- **Brand Kitchen Rent:** Daily rent paid by each brand to each operating kitchen: ₹2 per order plus 3% of net food value. If daily orders at a kitchen are strictly fewer than 30 ($< 30$), a minimum fee of ₹500 applies. (Exactly 30 orders does not trigger the minimum).
