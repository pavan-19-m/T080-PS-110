# Capstone Test Execution Report & Verification Matrix

**Project Title:** Cloud Kitchen Multi-Brand Order Routing and Kitchen Capacity Engine  
**Team ID:** T080 | **Problem Statement:** PS-110  
**Team Members:** Pavan Neelappa Mirji & Padmavathi B  
**Testing Framework:** pytest 9.2.0 (Python 3.14.7)  
**Execution Timestamp:** 2026-11-07  

---

## 1. Test Summary Executive Dashboard

```text
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\Erica Work\Desktop\T080-PS-110
collected 67 items

tests/test_accounting.py ........................................ [ 11%]
tests/test_business_rules.py .................................... [ 29%]
tests/test_edge_cases.py ........................................ [ 41%]
tests/test_kitchen.py ........................................... [ 47%]
tests/test_models.py ............................................ [ 58%]
tests/test_order.py ............................................. [ 68%]
tests/test_routing.py ........................................... [ 79%]
tests/test_scheduling.py ........................................ [ 89%]
tests/test_validation.py ........................................ [100%]

============================= 67 passed in 0.29s ==============================
```

- **Total Test Cases Executed:** 67
- **Passed:** 67 (100.0%)
- **Failed:** 0 (0.0%)
- **Errors / Skipped:** 0 (0.0%)
- **Execution Time:** 0.29 seconds

---

## 2. Business Rules Coverage Matrix (BR-01 through BR-12)

| Rule ID | Description | Primary Test Function | Test File | Status |
| :--- | :--- | :--- | :--- | :--- |
| **BR-01** | Kitchen Eligibility & Lowest Ready Routing | `test_br01_kitchen_eligibility_and_routing` | `tests/test_business_rules.py` | **PASSED** |
| **BR-02** | Station Capacity & 3-Min Batching | `test_br02_station_capacity_and_batching` | `tests/test_business_rules.py` | **PASSED** |
| **BR-03** | FIFO Order Sequencing & RUSH Jumps | `test_br03_fifo_and_rush_priority` | `tests/test_business_rules.py` | **PASSED** |
| **BR-04** | Ready-Time Calculation & Dependencies | `test_br04_ready_time_and_dependencies` | `tests/test_business_rules.py` | **PASSED** |
| **BR-05** | Promised-Time & Late-Risk Rerouting | `test_br05_promised_time_calculation_and_reroute` | `tests/test_business_rules.py` | **PASSED** |
| **BR-06** | Kitchen Throttling Trigger & Clearance | `test_br06_kitchen_throttling_trigger_and_recovery`| `tests/test_business_rules.py` | **PASSED** |
| **BR-07** | Stock-Outs & Within-₹20 Substitutions | `test_br07_stockouts_and_substitutions` | `tests/test_business_rules.py` | **PASSED** |
| **BR-08** | Cancellation Rules (Free vs Charged) | `test_br08_cancellation_rules_free_vs_charged` | `tests/test_business_rules.py` | **PASSED** |
| **BR-09** | Platform Commissions, Packaging, & GST | `test_br09_commissions_packaging_and_gst` | `tests/test_business_rules.py` | **PASSED** |
| **BR-10** | Late Hand-off Penalties & Cost Centres | `test_br10_late_handoff_penalties_and_cost_centres` | `tests/test_business_rules.py` | **PASSED** |
| **BR-11** | Kitchen Rent & Minimum Volume Threshold | `test_br11_kitchen_rent_and_minimum_fee` | `tests/test_business_rules.py` | **PASSED** |
| **BR-12** | Complete Rule Execution Precedence | `test_br12_rule_execution_precedence` | `tests/test_business_rules.py` | **PASSED** |

---

## 3. Mandatory Edge Cases Verification Matrix (Section 6)

| Edge Case | Exact Specification Tested | Test Function | Test File | Result |
| :--- | :--- | :--- | :--- | :--- |
| **EC-01** | Identical recipe items arriving exactly 3 minutes apart ($\Delta t = 180.0\text{s}$) | `test_edge_case_1_identical_recipe_arriving_exactly_3_minutes_apart` | `tests/test_edge_cases.py` | **PASSED** |
| **EC-02** | RUSH order attempting a fourth jump (strictly capped at 3 jumps) | `test_edge_case_2_rush_order_attempting_fourth_jump` | `tests/test_edge_cases.py` | **PASSED** |
| **EC-03** | Projected ready time exactly 45 minutes ($= 45.0\text{m}$, not $> 45\text{m}$) | `test_edge_case_3_projected_ready_time_exactly_45_minutes` | `tests/test_edge_cases.py` | **PASSED** |
| **EC-04** | Kitchen load exactly 60 minutes ($= 60.0\text{m}$, not $> 60\text{m}$) | `test_edge_case_4_kitchen_load_exactly_60_minutes` | `tests/test_edge_cases.py` | **PASSED** |
| **EC-05** | Substitute item price exactly ₹20 higher ($|\Delta P| = 20.0$, allowed) | `test_edge_case_5_substitute_price_exactly_20_higher` | `tests/test_edge_cases.py` | **PASSED** |
| **EC-06** | Cancellation at the exact instant first item starts prep ($t_{\text{cancel}} == t_{\text{start}}$) | `test_edge_case_6_cancellation_at_exact_prep_start` | `tests/test_edge_cases.py` | **PASSED** |
| **EC-07** | Packaging fee calculation for 5 items ($5 \times 10 = 50$, capped at ₹40) | `test_edge_case_7_packaging_calculation_for_5_items` | `tests/test_edge_cases.py` | **PASSED** |
| **EC-08** | Exactly 30 brand orders at one kitchen (does not trigger ₹500 min rent) | `test_edge_case_8_exactly_30_brand_orders_at_one_kitchen` | `tests/test_edge_cases.py` | **PASSED** |

---

## 4. Test Suite Categorization

1. **`tests/test_models.py` (7 tests):** Validates dataclass models, enums, load calculations, time windows, and event types.
2. **`tests/test_validation.py` (7 tests):** Tests structural integrity, negative prices/prep times, unknown foreign keys, empty items list.
3. **`tests/test_routing.py` (7 tests):** Tests kitchen eligibility checks, load tie-breaks, late-risk flags, and throttling filters.
4. **`tests/test_scheduling.py` (7 tests):** Tests workstation slot concurrency, topological dependency order, and promised-time rounding.
5. **`tests/test_accounting.py` (8 tests):** Tests Aggregator A/B economics, Own App payment fees, packaging caps, GST, and kitchen rent formulas.
6. **`tests/test_kitchen.py` (4 tests):** Tests operating hours, overnight shifts (e.g. 20:00 to 02:00), brand/zone support.
7. **`tests/test_order.py` (7 tests):** Tests RUSH criteria, jump limits, and anti-starvation invariants.
8. **`tests/test_business_rules.py` (12 tests):** Direct tests for BR-01 through BR-12.
9. **`tests/test_edge_cases.py` (8 tests):** Dedicated tests for the 8 mandatory edge cases.
