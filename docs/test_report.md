# Capstone Test Execution Report & Verification Matrix

**Project Title:** Cloud Kitchen Multi-Brand Order Routing and Kitchen Capacity Engine  
**Team ID:** T080 | **Problem Statement:** PS-110  
**Team Members:** Padmavathi B (1AT24CG059) & Pavan Neelappa Mirji (1AT24CG060)  
**Academic Section:** CSD  
**Testing Framework:** pytest 9.2.0 (Python 3.14.7)  
**Execution Timestamp:** 2026-11-18  

---

## 1. Test Summary Executive Dashboard

```text
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\Erica Work\Desktop\T080-PS-110
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

- **Total Test Cases Executed:** 83
- **Passed:** 83 (100.0%)
- **Failed:** 0 (0.0%)
- **Errors / Skipped:** 0 (0.0%)
- **Execution Time:** 0.33 seconds

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
| **BR-08** | Order Cancellations: Free vs Charged | `test_br08_cancellation_rules_free_vs_charged` | `tests/test_business_rules.py` | **PASSED** |
| **BR-09** | Channel Commissions, Packaging Fee Cap & GST | `test_br09_commissions_packaging_and_gst` | `tests/test_business_rules.py` | **PASSED** |
| **BR-10** | Late Hand-Off Penalties & Cost Centres | `test_br10_late_handoff_penalties_and_cost_centres`| `tests/test_business_rules.py` | **PASSED** |
| **BR-11** | Kitchen Rent Calculation & Minimum Fee | `test_br11_kitchen_rent_and_minimum_fee` | `tests/test_business_rules.py` | **PASSED** |
| **BR-12** | Complete Rule Execution Precedence Pipeline | `test_br12_rule_execution_precedence` | `tests/test_business_rules.py` | **PASSED** |

---

## 3. Mandatory Edge Case Coverage Matrix (TC-01 through TC-08)

| Edge Case ID | Scenario Description | Dedicated Test Function | File | Status |
| :--- | :--- | :--- | :--- | :--- |
| **TC-01** | Identical recipes arriving exactly 3 minutes (180s) apart batch together | `test_edge_case_1_identical_recipe_arriving_exactly_3_minutes_apart` | `tests/test_edge_cases.py` | **PASSED** |
| **TC-02** | RUSH order attempting 4th jump is blocked by max-3 jump limit | `test_edge_case_2_rush_order_attempting_fourth_jump` | `tests/test_edge_cases.py` | **PASSED** |
| **TC-03** | Projected ready time at exactly 45 minutes does NOT trigger LATE_RISK | `test_edge_case_3_projected_ready_time_exactly_45_minutes` | `tests/test_edge_cases.py` | **PASSED** |
| **TC-04** | Kitchen load at exactly 60 minutes does NOT trigger THROTTLED state | `test_edge_case_4_kitchen_load_exactly_60_minutes` | `tests/test_edge_cases.py` | **PASSED** |
| **TC-05** | Substitute item priced at exactly ₹20 higher is accepted | `test_edge_case_5_substitute_price_exactly_20_higher` | `tests/test_edge_cases.py` | **PASSED** |
| **TC-06** | Cancellation at exact prep start timestamp is treated as free cancellation | `test_edge_case_6_cancellation_at_exact_prep_start` | `tests/test_edge_cases.py` | **PASSED** |
| **TC-07** | Packaging fee for exactly 5 items computes to ₹30 (below ₹40 cap) | `test_edge_case_7_packaging_calculation_for_5_items` | `tests/test_edge_cases.py` | **PASSED** |
| **TC-08** | Brand with exactly 30 orders at one kitchen does NOT trigger ₹500 minimum | `test_edge_case_8_exactly_30_brand_orders_at_one_kitchen` | `tests/test_edge_cases.py` | **PASSED** |

---

## 4. Verification Conclusion

All 83 automated test cases pass deterministically. The application has zero unhandled exceptions, zero database dependencies, and satisfies all 12 core business rules and edge scenarios required for final submission.
