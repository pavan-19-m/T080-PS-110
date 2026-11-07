# Cloud Kitchen Multi-brand Order Routing and Kitchen Capacity Engine

**Capstone Project for 10 SECONDS**  
**Team ID:** T080  
**Problem Statement:** PS-110  
**Team Members:** Pavan Neelappa Mirji & Padmavathi B  
**Section:** CSD  
**Technology Stack:** Python 3.10+, pytest, CSV, Dataclasses, Object-Oriented Architecture  

---

## 1. Project Overview & Problem Statement
The growth of delivery-first food platforms requires cloud kitchens (dark kitchens) to host and fulfill orders for multiple virtual restaurant brands under single physical roofs. When orders surge during peak meal hours, cloud kitchen operators face severe operational challenges:
1. Which physical kitchen should fulfill an incoming order?
2. How should culinary workstations (Grill, Fryer, Wok, Cold, Bakery) be scheduled without exceeding parallel slot limits?
3. How can identical recipes placed within narrow time windows be batched to maximize kitchen throughput?
4. How do high-value or priority RUSH orders expedite through the kitchen queue without starving regular orders?
5. How are accurate ready and promised delivery times calculated?
6. How are platform commissions, packaging fees, GST, and net brand earnings tracked?

This engine provides a command-file-driven, deterministic backend simulation solving order routing, workstation scheduling, priority jumps, capacity throttling, and financial accounting.

---

## 2. System Architecture & Folder Layout

```text
T080-PS-110/
├── README.md                      <-- Project guide, execution, testing & viva tips
├── requirements.txt               <-- Python dependencies (pytest)
├── .gitignore                     <-- Python and IDE exclusions
├── docs/
│   ├── architecture.md            <-- Detailed architectural component diagram
│   ├── business-rules.md          <-- BR-01 through BR-12 specifications & status
│   ├── week2-progress.md          <-- Week 2 milestone deliverables report
│   └── decision-log.md            <-- Architecture Decision Records (ADRs)
├── sample-data/                   <-- Realistic illustrative CSV dataset
│   ├── kitchens.csv
│   ├── stations.csv
│   ├── brands.csv
│   ├── menu_items.csv
│   ├── recipes.csv
│   ├── zones.csv
│   └── orders.csv
├── output/                        <-- Generated audit and report CSV files
│   ├── routing_decisions.csv
│   ├── station_timelines.csv
│   └── order_financials.csv
├── src/
│   ├── __init__.py
│   ├── main.py                    <-- CLI application entry point
│   ├── models/                    <-- Domain entities
│   │   ├── kitchen.py
│   │   ├── station.py
│   │   ├── brand.py
│   │   ├── menu_item.py
│   │   ├── recipe.py
│   │   ├── order.py
│   │   ├── order_item.py
│   │   └── delivery_zone.py
│   ├── input/                     <-- CSV parsing and schema validation
│   │   ├── csv_loader.py
│   │   └── validator.py
│   ├── routing/                   <-- Eligibility and kitchen selection (BR-01, 05, 06)
│   │   └── order_router.py
│   ├── scheduling/                <-- Workstation slot booking, batching, sequencing
│   │   ├── scheduler.py           (BR-02, BR-04)
│   │   ├── batching.py            (BR-02 exact 3-min window)
│   │   ├── dependency_manager.py  (BR-04 predecessor constraints)
│   │   └── order_sequencer.py     (BR-03 FIFO & RUSH jumps)
│   ├── accounting/                <-- Channel commissions, packaging cap, GST (BR-09)
│   │   └── accounting_engine.py
│   ├── reporting/                 <-- Console display & CSV exporters
│   │   └── report_generator.py
│   └── services/                  <-- End-to-end pipeline orchestration
│       └── order_service.py
└── tests/                         <-- Pytest unit test suite
    ├── test_kitchen.py
    ├── test_routing.py
    ├── test_scheduling.py
    ├── test_order.py
    ├── test_accounting.py
    └── test_validation.py
```

---

## 3. Implemented Business Rules (Week 2 MVP)

- **BR-01 Kitchen Eligibility & Routing:** A kitchen is eligible only if it serves the brand, is listed in the delivery zone's kitchen list, is operating at the order time, and has every required workstation. Routes to the eligible kitchen with the lowest projected ready time, breaking ties by lowest current load, then lowest kitchen ID.
- **BR-02 Station Capacity & Batching:** Each station has a fixed number of slots. Items occupy 1 slot for their recipe duration. Identical recipes arriving within 3 minutes ($\le 3$ min) batch into a single slot up to the recipe's maximum batch size. Handles the exact 3-minute boundary ($\le 180$ seconds).
- **BR-03 Order Sequencing & RUSH Priority:** Default FIFO ordering by order time. RUSH priority is granted if `channel_priority == True` or order value $> \text{Rs. 1,500}$. A RUSH order may jump ahead of up to 3 non-RUSH orders. An individual non-RUSH order cannot be delayed by more than 2 jumps.
- **BR-04 Ready Time & Dependencies:** Predecessor recipes must finish before dependent recipes can begin ($\text{start}_B \ge \text{end}_A$). Ready time is the maximum completion time across all items plus 3 minutes of packaging.
- **BR-05 Promised Time & Late Risk:** Promised time = ready time + delivery minutes + 5-minute buffer, rounded UP to the next 5-minute boundary ($\lceil T/5 \rceil \times 5$). If ready time exceeds order time + 45 minutes, alternative kitchens are evaluated (rerouting requires saving $\ge 10$ minutes); otherwise accepts with `LATE_RISK`.
- **BR-06 Throttling:** When projected ready time exceeds 60 minutes, the kitchen is marked `THROTTLED` and accepts only orders where it is the sole eligible kitchen. Clears when load drops below 40 minutes.
- **BR-09 Channel Economics:**
  - Aggregator A: 22% commission.
  - Aggregator B: 18% commission.
  - Own App: 0% commission + Rs. 15 fixed payment fee.
  - Packaging Fee: Rs. 10 per item, capped at a maximum of Rs. 40 per order.
  - GST: 5% on food value.
- **BR-12 Sequential Execution:** Pipeline executes in exact order: Eligibility $\rightarrow$ Throttling $\rightarrow$ Routing by ready time $\rightarrow$ Sequencing (RUSH jumps) $\rightarrow$ Batching $\rightarrow$ Dependencies $\rightarrow$ Ready & Promised times $\rightarrow$ Financial Accounting.

---

## 4. Setup & Execution Instructions

### Prerequisites
- Python 3.10 or higher.
- `pip` (Python package manager).

### 1. Installation
Clone or navigate to the project directory:
```bash
cd T080-PS110
pip install -r requirements.txt
```

### 2. Run the Main Application
Run the command-file-driven pipeline using the sample CSV dataset:
```bash
python -m src.main
```
Or specify custom data and output directories:
```bash
python -m src.main --data-dir sample-data --output-dir output
```

### 3. Run the Unit Tests
Execute the comprehensive `pytest` test suite:
```bash
python -m pytest -v
```

---

## 5. CSV Input File Schemas

| File | Headers | Description |
| :--- | :--- | :--- |
| `kitchens.csv` | `kitchen_id,name,open_time,close_time,supported_brands,delivery_zones` | Operating hours, supported brands, and covered delivery zones. |
| `stations.csv` | `kitchen_id,station_type,capacity` | Parallel slot count per workstation type. |
| `brands.csv` | `brand_id,name` | Virtual restaurant brand catalog. |
| `recipes.csv` | `recipe_id,station_type,prep_minutes,max_batch_size,dependency_recipe_id` | Cooking station, prep duration, batch limit, predecessor prerequisite. |
| `menu_items.csv` | `item_id,brand_id,name,price,recipe_id` | Retail item price and recipe link. |
| `zones.csv` | `zone_id,delivery_minutes,eligible_kitchen_ids` | Transit time and reachable kitchen list. |
| `orders.csv` | `order_id,brand_id,items,channel,delivery_zone,order_time,channel_priority` | Incoming customer orders. |

---

## 6. Sample Terminal Output
```text
==========================================================================================
 10 SECONDS CAPSTONE PROJECT | TEAM T080 | PROBLEM STATEMENT: PS-110
 Cloud Kitchen Multi-brand Order Routing and Kitchen Capacity Engine
 Data Directory:   sample-data
 Output Directory: output
==========================================================================================

[1/5] Loading configuration and catalogs...
  -> Loaded 2 virtual brands
  -> Loaded 5 recipes
  -> Loaded 5 menu items
  -> Loaded 2 delivery zones
  -> Loaded 2 physical kitchens with 10 workstations

[2/5] Ingesting and validating incoming orders...
  -> Loaded and validated 6 customer orders

[3/5] Executing routing, scheduling, priority jumps, and accounting...
  -> Successfully processed 6 orders through pipeline

[4/5] Pipeline execution results:
---------------------------------------------------------------------------------------------------------
Order ID: ORD-106 [RUSH PRIORITY]
  Brand: B-01 | Channel: AGGREGATOR_A | Zone: ZONE-CENTRAL
  Placed At: 2026-11-06 12:08:00
  Selected Kitchen: K-01
  Routing Reason: Selected by lowest projected ready time (12:14:00), load tie-break, ID K-01
  Timing: Ready At = 12:17:00 | Promised To Customer = 12:35:00
  Status: SCHEDULED
  Station Timeline & Item Allocation:
    - ITM-BURGER (Recipe: REC-BURGER): 12:08:00 -> 12:11:00 [Slot #1, Batch: BATCH-0003]
    - ITM-BURGER (Recipe: REC-BURGER): 12:08:00 -> 12:11:00 [Slot #1, Batch: BATCH-0003]
    - ...
  Financial Breakdown:
    Food Value: Rs. 1540.00 | Commission (22%): Rs. 338.80
    Packaging Fee: Rs. 40.00 | GST (5%): Rs. 77.00
    Customer Bill: Rs. 1657.00 | Net Brand Earnings: Rs. 1201.20
---------------------------------------------------------------------------------------------------------

[5/5] Exporting CSV audit reports...
  -> Reports written to: output/
     - routing_decisions.csv
     - station_timelines.csv
     - order_financials.csv

 Pipeline execution finished successfully.
```

---

## 7. Viva Q&A Guide for Students

> **Q1: How does your engine enforce station capacity?**  
> **A:** Each workstation (e.g. Grill with capacity 2) contains $N$ discrete `StationSlot` instances. When an item or batch is scheduled, the engine scans all slots and finds the earliest contiguous window of length `prep_minutes`. Subsequent items wait until an active slot becomes free.

> **Q2: How does the RUSH jump algorithm prevent starvation?**  
> **A:** A RUSH order can jump at most 3 non-RUSH orders. Crucially, each normal order maintains a `delayed_jumps_count` counter. If an order has already been delayed 2 times, no further RUSH orders are allowed to jump ahead of it, preventing starvation.

> **Q3: How does recipe batching work at the exact 3-minute boundary?**  
> **A:** If two identical recipe items arrive at $t_1$ and $t_2$, we evaluate $|t_2 - t_1| \le 180\text{ seconds}$. If the difference is $\le 180$s and the batch has not exceeded `max_batch_size`, the new item shares the same slot booking and start time.

> **Q4: How is promised delivery time rounded up?**  
> **A:** We compute raw delivery time = ready time + zone delivery minutes + 5-minute buffer. If the raw time is already on an exact 5-minute mark (e.g. 12:30:00), it stays unchanged; any non-zero remainder or additional seconds rounds up to the next 5-minute multiple (e.g. 12:30:01 becomes 12:35:00).

---

## 8. Git Version Control & Submission

To initialize and commit your repository locally:
```bash
git init
git add .
git commit -m "feat: complete Week 2 MVP for PS-110 Cloud Kitchen Engine (T080)"
```

To link and push to your GitHub repository:
```bash
git branch -M main
git remote add origin https://github.com/<your-username>/T080-PS-110.git
git push -u origin main
```
*(Do not push to GitHub until authorized by the team).*
