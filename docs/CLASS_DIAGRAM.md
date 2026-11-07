# UML Class Diagram
**Team ID:** T080 | **Problem Statement:** PS-110  
**Project:** Cloud Kitchen Multi-brand Order Routing and Kitchen Capacity Engine  
**Team Members:** Pavan Neelappa Mirji & Padmavathi B (Section: CSD)

---

```mermaid
classDiagram
    direction TB

    class Kitchen {
        -String kitchenId
        -String name
        -LocalTime openTime
        -LocalTime closeTime
        -Set~String~ supportedBrands
        -Map~StationType, Station~ stations
        -boolean throttled
        +boolean isOperatingAt(LocalTime time)
        +boolean hasRequiredStations(Set~StationType~ types)
        +double getCurrentLoadMinutes(LocalDateTime atTime)
    }

    class Station {
        -String stationId
        -StationType type
        -int slotCapacity
        -List~TimelineSlot~ activeSlots
        +TimelineSlot allocateEarliestSlot(LocalDateTime minStart, int durationMinutes)
    }

    class StationType {
        <<enumeration>>
        GRILL
        FRYER
        WOK
        COLD
        BAKERY
    }

    class Recipe {
        -String recipeId
        -StationType stationType
        -int prepMinutes
        -int maxBatchSize
        -String dependencyRecipeId
    }

    class MenuItem {
        -String itemId
        -String brandId
        -String name
        -double price
        -String recipeId
    }

    class Order {
        -String orderId
        -String brandId
        -Channel channel
        -String deliveryZoneId
        -LocalDateTime orderTime
        -boolean channelPriority
        -List~OrderItem~ items
        -OrderStatus status
        -String assignedKitchenId
        -LocalDateTime projectedReadyTime
        -LocalDateTime promisedDeliveryTime
        -boolean lateRisk
        -boolean throttledRouting
        -int rushJumpsMade
        -int delayedJumpsCount
        +double calculateGrossFoodValue()
        +boolean qualifiesForRush()
    }

    class OrderItem {
        -String orderItemId
        -String orderId
        -String itemId
        -double finalPrice
        -String recipeId
        -LocalDateTime prepStartTime
        -LocalDateTime prepEndTime
        -String assignedStationSlotId
        -String batchId
        -boolean started
        -boolean completed
    }

    class Channel {
        <<enumeration>>
        AGGREGATOR_A
        AGGREGATOR_B
        OWN_APP
        +double getCommissionRate()
        +double getFixedFee()
    }

    class OrderRouter {
        +List~Kitchen~ findEligibleKitchens(Order order, Map~String, Kitchen~ kitchens, DeliveryZone zone)
        +RoutingDecision routeOrder(Order order, List~Kitchen~ eligibleKitchens, LocalDateTime simulatedTime)
    }

    class OrderSequencer {
        +List~Order~ sequenceWithRushJumps(List~Order~ orders)
    }

    class StationScheduler {
        +ScheduleResult scheduleOrder(Kitchen kitchen, Order order, LocalDateTime minStart)
    }

    class SubstitutionManager {
        +SubstitutionResult evaluateSubstitutions(Order order, Kitchen kitchen, Map~String, List~String~~ substitutionCatalog)
    }

    class CancellationHandler {
        +CancellationOutcome processCancellation(Order order, LocalDateTime cancelTime, String initiator)
    }

    class AccountingEngine {
        +OrderFinancials computeOrderFinancials(Order order, LocalDateTime actualHandOffTime)
        +DailyBrandReport computeDailyBrandPnL(String brandId, String kitchenId, List~OrderFinancials~ orders)
    }

    Kitchen "1" *-- "many" Station : contains
    Station "1" o-- "1" StationType : typed by
    Recipe "1" o-- "1" StationType : targets
    MenuItem "1" o-- "1" Recipe : mapped to
    Order "1" *-- "many" OrderItem : contains
    Order "1" o-- "1" Channel : placed via
    OrderRouter ..> Kitchen : queries
    OrderRouter ..> Order : evaluates
    StationScheduler ..> Kitchen : updates
    AccountingEngine ..> Order : settles
```
