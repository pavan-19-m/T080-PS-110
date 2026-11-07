# Architecture Design Decisions & ADR Register

**Project Title:** Cloud Kitchen Multi-Brand Order Routing and Kitchen Capacity Engine  
**Team ID:** T080 | **Problem Statement:** PS-110  
**Team Members:** Pavan Neelappa Mirji & Padmavathi B  

---

## 1. Summary of Architectural Decisions

| ADR ID | Decision Topic | Status | Impact Area |
| :--- | :--- | :--- | :--- |
| **ADR-01** | Database-Free In-Memory Time Slot Simulation | Accepted | Performance, Determinism |
| **ADR-02** | Topologically Sorted Dependency Management | Accepted | Recipe Predecessor Integrity |
| **ADR-03** | Two-Threshold Hysteresis for Kitchen Throttling | Accepted | Capacity Overload Prevention |
| **ADR-04** | Dual-Constraint Priority Queue (RUSH Jump Caps) | Accepted | Fairness, Anti-Starvation |
| **ADR-05** | Exact-Boundary Batching Window ($\le 180$ seconds) | Accepted | Cooking Concurrency |
| **ADR-06** | Modular Subsystem Separation for Accounting Engine | Accepted | Auditing, Maintainability |

---

## 2. Detailed Architecture Decision Records (ADRs)

### ADR-01: Database-Free In-Memory Time Slot Simulation
- **Context:** The engine must schedule high volumes of food orders across hundreds of culinary workstations in real time. Traditional SQL database locks (e.g. `SELECT FOR UPDATE`) introduce significant transaction overhead, deadlock hazards, and non-deterministic latency.
- **Decision:** Implement discrete in-memory time intervals `[start_time, end_time)` on `StationSlot` instances. To evaluate projected ready times during routing (BR-01/05), perform deep-copy simulation of workstation slots without mutating master kitchen state. Once the winning kitchen is chosen, commit the actual booking onto real slots.
- **Consequences:** Microsecond-speed routing simulations, deterministic tie-breaking, and zero database infrastructure dependencies.

---

### ADR-02: Topologically Sorted Dependency Management
- **Context:** Recipes frequently require multi-stage preparation prerequisites (e.g., a burger patty must be grilled before burger assembly can take place on the cold station).
- **Decision:** Use topological sorting (`DependencyManager.sort_items_by_dependency`) to sequence items within an order such that independent predecessor items are scheduled first. During subsequent dependent item scheduling, the earliest possible start time is constrained to:
  $$\text{Earliest Start} = \max(\text{Order Placement Time}, \text{Predecessor Prep End Time})$$
- **Consequences:** Guarantees that culinary preparation order is always physically valid and impossible to violate.

---

### ADR-03: Two-Threshold Hysteresis for Kitchen Throttling (BR-06)
- **Context:** If a kitchen throttles when load exceeds 60 minutes and immediately un-throttles at 59 minutes, rapid oscillation ("flapping") occurs under sustained peak order inflow.
- **Decision:** Adopt a hysteresis curve with two distinct thresholds:
  1. **Trigger Throttling:** Projected ready time delay $> 60\text{ minutes}$.
  2. **Clear Throttling:** Active load falls strictly $< 40\text{ minutes}$.
  3. **Sole Eligible Exception:** If all eligible kitchens are throttled, a throttled kitchen may accept orders if and only if it is the sole eligible kitchen.
- **Consequences:** Prevents kitchen flapping, smooths peak kitchen load, and prevents orders from failing when only one dark kitchen covers a neighborhood.

---

### ADR-04: Dual-Constraint Priority Queue with Starvation Prevention (BR-03)
- **Context:** High-value customers and priority platform channels require expedited preparation, but unlimited priority overrides cause starvation for regular customer orders.
- **Decision:** Enforce two bounding invariants:
  1. **Maximum Jumps Forward:** A RUSH order can jump forward past at most 3 non-RUSH orders (`max_rush_jumps = 3`).
  2. **Maximum Delays Backward:** An individual non-RUSH order can be jumped at most 2 times (`delayed_jumps_count <= 2`). Once an order hits 2 delayed jumps, it becomes immune to further priority overrides.
- **Consequences:** Guarantees VIP priority while bounding maximum waiting delay for regular orders.

---

### ADR-05: Exact-Boundary Window for Recipe Batching (BR-02)
- **Context:** BR-02 states: "Identical recipes on the same station within 3 minutes can be batched." There was ambiguity whether 3 minutes (180.0 seconds) is inclusive or exclusive.
- **Decision:** Implement inclusive boundary comparison:
  $$\Delta t = |t_{\text{order}} - t_{\text{first\_order\_in\_batch}}| \le 180.0\text{ seconds}$$
  If $\Delta t \le 180.0$s and `len(items) < max_batch_size`, items are merged into the same slot booking.
- **Consequences:** Maximizes fryer/oven throughput during peak bursts and satisfies Edge Case 1.

---

### ADR-06: Modular Subsystem Separation for Accounting & Penalties
- **Context:** Business stakeholders require transparent separation of platform commissions, packaging fees, government taxes, late delivery penalties, and physical kitchen lease settlements.
- **Decision:** Segregate financial domain logic into dedicated single-responsibility calculators:
  - `PenaltyCalculator`: Encapsulates BR-10 late hand-off blocks and cost centre assignment.
  - `RentCalculator`: Encapsulates BR-11 fixed order fee, food percentage, and ₹500 minimum volume threshold.
  - `AccountingEngine`: Orchestrates order-level financials, end-of-day brand P&L, and kitchen revenue reports.
- **Consequences:** High maintainability, zero side-effects during scheduling, and 100% testable accounting logic.
