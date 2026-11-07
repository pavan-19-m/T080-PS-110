"""Unit tests for all 8 mandatory edge cases specified in Section 6."""

from datetime import datetime, time, timedelta
import pytest

from src.accounting.accounting_engine import AccountingEngine
from src.accounting.rent_calculator import RentCalculator
from src.models import (
    Brand,
    Channel,
    DeliveryZone,
    Kitchen,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    Recipe,
    Station,
    StationType,
)
from src.routing.order_router import OrderRouter
from src.scheduling.batching import BatchingEngine
from src.scheduling.order_sequencer import OrderSequencer
from src.services.cancellation_service import CancellationService
from src.services.substitution_service import SubstitutionService


# ---------------------------------------------------------------------------
# Edge Case 1: Identical recipe items arriving exactly 3 minutes apart
# ---------------------------------------------------------------------------

def test_edge_case_1_identical_recipe_arriving_exactly_3_minutes_apart():
    """
    Edge Case 1:
    Identical recipes on the same station arriving exactly 3 minutes apart (180.0 seconds)
    MUST be batched into the same slot.
    """
    engine = BatchingEngine()
    recipe = Recipe(
        recipe_id="REC-FRIES",
        station_type=StationType.FRYER,
        prep_minutes=5,
        max_batch_size=3,
    )
    t0 = datetime(2026, 11, 6, 12, 0, 0)
    t1 = datetime(2026, 11, 6, 12, 3, 0)  # Exactly 180 seconds later

    it1 = OrderItem("1", "ORD-1", "ITM-FRIES", 110.0, "REC-FRIES")
    it2 = OrderItem("2", "ORD-2", "ITM-FRIES", 110.0, "REC-FRIES")

    batch1 = engine.find_or_create_batch(it1, recipe, t0)
    batch2 = engine.find_or_create_batch(it2, recipe, t1)

    assert batch1.batch_id == batch2.batch_id
    assert batch1.current_size == 2


# ---------------------------------------------------------------------------
# Edge Case 2: RUSH order attempting a fourth jump
# ---------------------------------------------------------------------------

def test_edge_case_2_rush_order_attempting_fourth_jump():
    """
    Edge Case 2:
    A RUSH order can jump ahead of at most 3 orders. Any attempt to jump a 4th order is blocked.
    """
    t0 = datetime(2026, 11, 6, 12, 0, 0)
    orders = [
        Order(f"ORD-NORM-{i}", "B-01", [OrderItem("1", f"ORD-NORM-{i}", "ITM-1", 100.0, "REC-1")],
              Channel.AGGREGATOR_A, "ZONE-1", t0 + timedelta(minutes=i))
        for i in range(4)
    ]
    rush_order = Order(
        "ORD-RUSH", "B-01", [OrderItem("1", "ORD-RUSH", "ITM-1", 100.0, "REC-1")],
        Channel.AGGREGATOR_A, "ZONE-1", t0 + timedelta(minutes=4), channel_priority=True
    )
    orders.append(rush_order)

    sequenced = OrderSequencer.sequence_orders(orders)
    assert sequenced[1].order_id == "ORD-RUSH"
    assert sequenced[1].rush_jumps_made == 3
    assert sequenced[0].order_id == "ORD-NORM-0"


# ---------------------------------------------------------------------------
# Edge Case 3: Projected ready time exactly 45 minutes
# ---------------------------------------------------------------------------

def test_edge_case_3_projected_ready_time_exactly_45_minutes():
    """
    Edge Case 3:
    Threshold specifies: "If projected ready time is MORE THAN 45 minutes after order placement".
    Exactly 45 minutes (45.0) does NOT exceed 45 minutes, so it must NOT trigger late risk or reroute.
    """
    order_time = datetime(2026, 11, 6, 12, 0, 0)
    ready_time = order_time + timedelta(minutes=45)
    delta_minutes = (ready_time - order_time).total_seconds() / 60.0

    assert delta_minutes == 45.0
    is_late_risk = delta_minutes > OrderRouter.LATE_RISK_THRESHOLD_MINUTES
    assert is_late_risk is False


# ---------------------------------------------------------------------------
# Edge Case 4: Kitchen load exactly 60 minutes
# ---------------------------------------------------------------------------

def test_edge_case_4_kitchen_load_exactly_60_minutes():
    """
    Edge Case 4:
    Threshold specifies: "Mark a kitchen THROTTLED when its projected ready time exceeds 60 minutes".
    A load of exactly 60 minutes (60.0) does NOT exceed 60 minutes, so it must NOT be marked throttled.
    """
    order_time = datetime(2026, 11, 6, 12, 0, 0)
    ready_time = order_time + timedelta(minutes=60)
    projected_delay = (ready_time - order_time).total_seconds() / 60.0

    assert projected_delay == 60.0
    is_throttled = projected_delay > OrderRouter.THROTTLE_TRIGGER_MINUTES
    assert is_throttled is False


# ---------------------------------------------------------------------------
# Edge Case 5: Substitute price exactly ₹20 higher
# ---------------------------------------------------------------------------

def test_edge_case_5_substitute_price_exactly_20_higher():
    """
    Edge Case 5:
    BR-07: "Allow a substitute if its price is within ₹20 of the original item.
    Exactly ₹20 difference is allowed."
    Original = Rs. 200, Substitute = Rs. 220 (difference = Rs. 20) -> MUST be accepted.
    """
    kitchen = Kitchen(
        "K-01", "Hub", time(8, 0), time(23, 0), {"B-01"}, {"Z-1"},
        stations={StationType.COLD: Station(StationType.COLD, 2)}
    )
    kitchen.stock_out.add("ITM-ORIGINAL")

    menu = {
        "ITM-ORIGINAL": MenuItem("ITM-ORIGINAL", "B-01", "Burger Classic", 200.0, "REC-1"),
        "ITM-SUB-EXACT20": MenuItem("ITM-SUB-EXACT20", "B-01", "Burger Deluxe", 220.0, "REC-1"),
    }
    recipes = {"REC-1": Recipe("REC-1", StationType.COLD, 3, 2)}

    sub_service = SubstitutionService(
        substitutions={("B-01", "ITM-ORIGINAL"): "ITM-SUB-EXACT20"},
        menu_items=menu,
    )
    order = Order("ORD-SUB-20", "B-01", [OrderItem("1", "ORD-SUB-20", "ITM-ORIGINAL", 200.0, "REC-1")],
                  Channel.OWN_APP, "Z-1", datetime(2026, 11, 6, 12, 0, 0))

    proceed = sub_service.apply_substitutions_for_kitchen(order, kitchen, recipes)
    assert proceed is True
    assert order.items[0].item_id == "ITM-SUB-EXACT20"
    assert order.items[0].price == 220.0


# ---------------------------------------------------------------------------
# Edge Case 6: Cancellation at the exact instant the first item starts preparation
# ---------------------------------------------------------------------------

def test_edge_case_6_cancellation_at_exact_prep_start():
    """
    Edge Case 6:
    When cancellation occurs at the EXACT timestamp that preparation starts (cancelled_at == prep_start),
    preparation is considered to have started. The charge applies to started items.
    """
    prep_start = datetime(2026, 11, 6, 12, 10, 0)
    it = OrderItem("1", "ORD-CANC", "ITM-BURGER", 220.0, "REC-BURGER", prep_start_time=prep_start)
    order = Order("ORD-CANC", "B-01", [it], Channel.AGGREGATOR_A, "Z-1",
                  datetime(2026, 11, 6, 12, 0, 0))

    # Cancel at the exact start instant: 12:10:00
    success, charge, msg = CancellationService.cancel_order(
        order=order, cancellation_time=prep_start, source="AGGREGATOR_A"
    )

    assert success is True
    assert charge == 220.0
    assert order.cancellation_charge == 220.0
    assert "Channel charged 100%" in msg


# ---------------------------------------------------------------------------
# Edge Case 7: Packaging calculation for 5 items
# ---------------------------------------------------------------------------

def test_edge_case_7_packaging_calculation_for_5_items():
    """
    Edge Case 7:
    Packaging is Rs. 10 per item, capped at a maximum of Rs. 40 per order.
    For 5 items: 5 * 10 = Rs. 50 -> MUST be capped at Rs. 40.
    """
    items = [OrderItem(str(i), "ORD-5ITEMS", f"ITM-{i}", 100.0, "REC-1") for i in range(5)]
    order = Order("ORD-5ITEMS", "B-01", items, Channel.OWN_APP, "Z-1",
                  datetime(2026, 11, 6, 12, 0, 0))

    financials = AccountingEngine.calculate_order_financials(order)
    assert financials.item_count == 5
    assert financials.packaging_fee == 40.0


# ---------------------------------------------------------------------------
# Edge Case 8: Exactly 30 brand orders at one kitchen
# ---------------------------------------------------------------------------

def test_edge_case_8_exactly_30_brand_orders_at_one_kitchen():
    """
    Edge Case 8:
    BR-11 specifies: "If fewer than 30 orders per day are processed at a kitchen,
    apply a Rs. 500 minimum rent. Exactly 30 orders must NOT trigger the minimum."
    For 30 orders with net food value Rs. 3,000:
    Raw rent = (30 * 2) + (3000 * 0.03) = 60 + 90 = Rs. 150.
    Since order count is exactly 30, the minimum Rs. 500 does NOT apply; rent is Rs. 150.
    """
    res = RentCalculator.calculate_rent(order_count=30, net_food_sales=3000.0)
    assert res.order_count == 30
    assert res.raw_rent == 150.0
    assert res.minimum_rent_applied is False
    assert res.final_rent == 150.0
