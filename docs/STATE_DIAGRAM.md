# Order State Diagram
**Team ID:** T080 | **Problem Statement:** PS-110  
**Project:** Cloud Kitchen Multi-brand Order Routing and Kitchen Capacity Engine  
**Team Members:** Pavan Neelappa Mirji & Padmavathi B (Section: CSD)

---

```mermaid
stateDiagram-v2
    [*] --> RECEIVED: Order Placed at Channel

    RECEIVED --> STOCK_OUT_EVALUATED: Stock Check at Eligible Kitchens
    STOCK_OUT_EVALUATED --> CANCELLED: All Items Out-of-Stock (No Valid Subs)
    STOCK_OUT_EVALUATED --> ROUTED: Kitchen Selected (BR-01, BR-05, BR-06)
    
    ROUTED --> QUEUED: Enqueued in Kitchen Order Queue
    QUEUED --> SEQUENCED: FIFO + RUSH Priority Jumps (BR-03)
    
    SEQUENCED --> SCHEDULED: Slots Allocated on Stations (BR-02, BR-04)
    SCHEDULED --> PREPARING: First Item Reaches Prep Start Time
    
    PREPARING --> READY: All Items Finished + 3 min Packaging Buffer
    
    READY --> DISPATCHED: Hand-off to Delivery Rider
    DISPATCHED --> DELIVERED: Reaches Customer at Promised Time
    DELIVERED --> SETTLED: Commission, Rent & Penalties Computed (BR-09, 10, 11)
    
    QUEUED --> CANCELLED_FREE: Cancelled Before Any Item Prep Starts (BR-08)
    SCHEDULED --> CANCELLED_FREE: Cancelled Before Prep Start Time (BR-08)
    PREPARING --> CANCELLED_PARTIAL: Cancelled at/after Prep Start (BR-08 Liability)
    
    CANCELLED_FREE --> SETTLED: Zero Food Liability
    CANCELLED_PARTIAL --> SETTLED: Started Items Settled
    CANCELLED --> [*]
    SETTLED --> [*]
```
