# System Architecture: Cloud Kitchen Engine (PS-110)
**Team ID:** T080 | **Problem Statement:** PS-110  
**Project Title:** Cloud Kitchen Multi-brand Order Routing and Kitchen Capacity Engine  
**Team Members:** Pavan Neelappa Mirji & Padmavathi B (Section: CSD)

---

## 1. Architectural Philosophy
The Cloud Kitchen Multi-brand Order Routing and Kitchen Capacity Engine is a command-file-driven, event-simulating backend application built strictly with **Python 3.10+**. It applies modern object-oriented principles, modular separation of concerns, dataclasses, enums, and comprehensive type annotations.

```mermaid
graph TD
    subgraph Data Layer [Data Input Layer]
        K_CSV[kitchens.csv]
        S_CSV[stations.csv]
        B_CSV[brands.csv]
        M_CSV[menu_items.csv]
        R_CSV[recipes.csv]
        Z_CSV[zones.csv]
        O_CSV[orders.csv]
    end

    subgraph Parsing and Validation [Input & Validation Subsystem]
        LOADER[CsvLoader - pathlib & csv]
        VALIDATOR[Validator - Entity & Referential Integrity]
    end

    subgraph Core Pipeline [Execution Pipeline - BR-12]
        SEQ[OrderSequencer - FIFO & RUSH Priority BR-03]
        ROUTER[OrderRouter - Eligibility, Throttling & Tie-breaks BR-01, BR-05, BR-06]
        SCHED[StationScheduler - Multi-slot Allocation BR-02, BR-04]
        BATCH[BatchingEngine - Exact 3-minute Window BR-02]
        DEP[DependencyManager - Predecessor Constraints BR-04]
        ACCT[AccountingEngine - Channel Fees, Packaging & GST BR-09]
    end

    subgraph Reporting Layer [Output Subsystem]
        REPORT[ReportGenerator]
        OUT_ROUTING[output/routing_decisions.csv]
        OUT_TIMELINES[output/station_timelines.csv]
        OUT_FINANCIALS[output/order_financials.csv]
        TERMINAL[Terminal Summary Table]
    end

    Data Layer --> LOADER
    LOADER --> VALIDATOR
    VALIDATOR --> SEQ
    SEQ --> ROUTER
    ROUTER --> SCHED
    SCHED --> BATCH
    SCHED --> DEP
    SCHED --> ACCT
    ACCT --> REPORT
    REPORT --> OUT_ROUTING
    REPORT --> OUT_TIMELINES
    REPORT --> OUT_FINANCIALS
    REPORT --> TERMINAL
```

---

## 2. Package & Module Organization
- `src.models`: Pure domain entities (`Kitchen`, `Station`, `StationSlot`, `Recipe`, `MenuItem`, `Brand`, `Order`, `OrderItem`, `DeliveryZone`, `Channel`, `StationType`, `OrderStatus`).
- `src.input`: Robust CSV loaders using Python's standard `pathlib.Path` and `csv.DictReader`, plus domain validation ensuring referential integrity across brands, recipes, and zones.
- `src.routing`: Multi-criteria kitchen eligibility evaluation (brand support, delivery zone coverage, operating hours, required equipment), ready-time projection, load/ID tie-breaking, rerouting logic, and kitchen throttling.
- `src.scheduling`: Parallel workstation slot capacity manager, exact 3-minute recipe batching engine, item dependency graph resolver, 3-minute packaging buffer addition, and 5-minute ceil-rounding for promised delivery times.
- `src.accounting`: Aggregator commission calculation (22% / 18% / 0% + Rs. 15), item packaging fee capping (max Rs. 40), 5% GST computation, and net brand earnings.
- `src.services`: High-level workflow orchestration uniting sequencing, routing, station slot commitment, and financial accounting.
- `src.reporting`: Console status table output and CSV audit generation (`routing_decisions.csv`, `station_timelines.csv`, `order_financials.csv`).
- `tests`: Thorough unit test suite powered by `pytest`.
