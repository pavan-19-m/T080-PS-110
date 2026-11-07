"""Unit tests for scheduling, batching, station capacity, and ready times (BR-02, BR-04, BR-05)."""

from datetime import datetime, time, timedelta
import pytest

from src.models import (
    Channel,
    DeliveryZone,
    Kitchen,
    Order,
    OrderItem,
    Recipe,
    Station,
    StationType,
)
from src.routing.order_router import OrderRouter
from src.scheduling.batching import BatchingEngine
from src.scheduling.dependency_manager import DependencyManager
from src.scheduling.scheduler import StationScheduler


@pytest.fixture
def mock_kitchen():
    return Kitchen(
        kitchen_id="K-01",
        name="Main Hub",
        open_time=time(8, 0),
        close_time=time(23, 0),
        supported_brands={"B-01"},
        delivery_zones={"ZONE-1"},
        stations={
            StationType.GRILL: Station(station_type=StationType.GRILL, capacity=2),
            StationType.FRYER: Station(station_type=StationType.FRYER, capacity=1),
            StationType.COLD: Station(station_type=StationType.COLD, capacity=2),
        },
    )


@pytest.fixture
def mock_recipes():
    return {
        "REC-PATTY": Recipe("REC-PATTY", StationType.GRILL, prep_minutes=8, max_batch_size=4),
        "REC-BURGER": Recipe("REC-BURGER", StationType.COLD, prep_minutes=3, max_batch_size=2, dependency_recipe_id="REC-PATTY"),
        "REC-FRIES": Recipe("REC-FRIES", StationType.FRYER, prep_minutes=5, max_batch_size=2),
    }


def test_station_slot_capacity_br02(mock_kitchen, mock_recipes):
    """BR-02: Each station slot handles 1 task concurrently; excess items wait for slot availability."""
    scheduler = StationScheduler()
    order_time = datetime(2026, 11, 6, 12, 0, 0)

    # FRYER has capacity 1, REC-FRIES max_batch_size=1 (override for test)
    solo_fries_recipe = {
        "REC-SOLO-FRIES": Recipe("REC-SOLO-FRIES", StationType.FRYER, prep_minutes=5, max_batch_size=1)
    }

    order = Order(
        order_id="ORD-CAP",
        brand_id="B-01",
        items=[
            OrderItem("ITM-1", "ORD-CAP", "FRIES", 100, "REC-SOLO-FRIES"),
            OrderItem("ITM-2", "ORD-CAP", "FRIES", 100, "REC-SOLO-FRIES"),
        ],
        channel=Channel.OWN_APP,
        delivery_zone="ZONE-1",
        order_time=order_time,
    )

    outcome = scheduler.commit_order(mock_kitchen, order, solo_fries_recipe, persist=True)
    # First item: 12:00 to 12:05
    assert order.items[0].prep_start_time == datetime(2026, 11, 6, 12, 0, 0)
    assert order.items[0].prep_end_time == datetime(2026, 11, 6, 12, 5, 0)

    # Second item must wait until 12:05 because fryer has only 1 slot
    assert order.items[1].prep_start_time == datetime(2026, 11, 6, 12, 5, 0)
    assert order.items[1].prep_end_time == datetime(2026, 11, 6, 12, 10, 0)

    # Ready time = 12:10 + 3 min packaging = 12:13
    assert outcome.ready_time == datetime(2026, 11, 6, 12, 13, 0)


def test_batching_within_3_minutes_br02(mock_kitchen, mock_recipes):
    """BR-02: Identical recipes on same station placed within 3 minutes batch into one slot."""
    scheduler = StationScheduler()
    t1 = datetime(2026, 11, 6, 12, 0, 0)
    t2 = datetime(2026, 11, 6, 12, 2, 0)  # 2 minutes later (< 3 min)

    order1 = Order(
        order_id="ORD-1",
        brand_id="B-01",
        items=[OrderItem("1", "ORD-1", "FRIES", 100, "REC-FRIES")],
        channel=Channel.AGGREGATOR_A,
        delivery_zone="ZONE-1",
        order_time=t1,
    )
    order2 = Order(
        order_id="ORD-2",
        brand_id="B-01",
        items=[OrderItem("2", "ORD-2", "FRIES", 100, "REC-FRIES")],
        channel=Channel.AGGREGATOR_B,
        delivery_zone="ZONE-1",
        order_time=t2,
    )

    scheduler.commit_order(mock_kitchen, order1, mock_recipes, persist=True)
    scheduler.commit_order(mock_kitchen, order2, mock_recipes, persist=True)

    # Both items should share the same batch_id, start_time, and slot
    assert order1.items[0].batch_id == order2.items[0].batch_id
    assert order1.items[0].prep_start_time == order2.items[0].prep_start_time
    assert order1.items[0].slot_id == order2.items[0].slot_id


def test_exact_3_minute_boundary_batching_edge_case_1(mock_kitchen, mock_recipes):
    """MANDATORY EDGE CASE 1 / BR-02: Two identical recipe items placed exactly 3 minutes apart must batch."""
    batching = BatchingEngine()
    recipe = mock_recipes["REC-FRIES"]

    t1 = datetime(2026, 11, 6, 12, 0, 0)
    t2 = datetime(2026, 11, 6, 12, 3, 0)  # Exactly 180 seconds apart

    item1 = OrderItem("1", "ORD-1", "FRIES", 100, "REC-FRIES")
    item2 = OrderItem("2", "ORD-2", "FRIES", 100, "REC-FRIES")

    b1 = batching.find_or_create_batch(item1, recipe, t1)
    b2 = batching.find_or_create_batch(item2, recipe, t2)

    # Must be the exact same batch!
    assert b1.batch_id == b2.batch_id
    assert b1.current_size == 2


def test_batching_exceeding_3_minutes_does_not_batch_br02(mock_kitchen, mock_recipes):
    """BR-02: Identical recipes placed > 3 minutes apart (e.g. 3m 1s) must not batch."""
    batching = BatchingEngine()
    recipe = mock_recipes["REC-FRIES"]

    t1 = datetime(2026, 11, 6, 12, 0, 0)
    t2 = datetime(2026, 11, 6, 12, 3, 1)  # 181 seconds apart

    item1 = OrderItem("1", "ORD-1", "FRIES", 100, "REC-FRIES")
    item2 = OrderItem("2", "ORD-2", "FRIES", 100, "REC-FRIES")

    b1 = batching.find_or_create_batch(item1, recipe, t1)
    b2 = batching.find_or_create_batch(item2, recipe, t2)

    assert b1.batch_id != b2.batch_id


def test_batch_capacity_limit_enforced_br02(mock_kitchen, mock_recipes):
    """BR-02: Batch size cannot exceed max_batch_size (REC-FRIES max_batch_size=2)."""
    batching = BatchingEngine()
    recipe = mock_recipes["REC-FRIES"]
    t = datetime(2026, 11, 6, 12, 0, 0)

    i1 = OrderItem("1", "O1", "FRIES", 100, "REC-FRIES")
    i2 = OrderItem("2", "O2", "FRIES", 100, "REC-FRIES")
    i3 = OrderItem("3", "O3", "FRIES", 100, "REC-FRIES")

    b1 = batching.find_or_create_batch(i1, recipe, t)
    b2 = batching.find_or_create_batch(i2, recipe, t)
    b3 = batching.find_or_create_batch(i3, recipe, t)

    assert b1.batch_id == b2.batch_id
    assert b3.batch_id != b1.batch_id  # Third item creates a new batch


def test_dependency_scheduling_br04(mock_kitchen, mock_recipes):
    """BR-04: Dependent recipe (REC-BURGER) must start after predecessor (REC-PATTY) completes."""
    scheduler = StationScheduler()
    t = datetime(2026, 11, 6, 12, 0, 0)

    order = Order(
        order_id="ORD-DEP",
        brand_id="B-01",
        items=[
            OrderItem("ITM-BURGER", "ORD-DEP", "BURGER", 200, "REC-BURGER"),
            OrderItem("ITM-PATTY", "ORD-DEP", "PATTY", 150, "REC-PATTY"),
        ],
        channel=Channel.OWN_APP,
        delivery_zone="ZONE-1",
        order_time=t,
    )

    outcome = scheduler.commit_order(mock_kitchen, order, mock_recipes, persist=True)

    patty_item = [it for it in order.items if it.recipe_id == "REC-PATTY"][0]
    burger_item = [it for it in order.items if it.recipe_id == "REC-BURGER"][0]

    # Patty starts at 12:00:00 and finishes at 12:08:00 (8 mins prep)
    assert patty_item.prep_start_time == datetime(2026, 11, 6, 12, 0, 0)
    assert patty_item.prep_end_time == datetime(2026, 11, 6, 12, 8, 0)

    # Burger depends on Patty, so it cannot start before 12:08:00
    assert burger_item.prep_start_time >= patty_item.prep_end_time
    assert burger_item.prep_start_time == datetime(2026, 11, 6, 12, 8, 0)
    assert burger_item.prep_end_time == datetime(2026, 11, 6, 12, 11, 0)

    # Packaging addition: ready time = 12:11 + 3 min = 12:14
    assert outcome.ready_time == datetime(2026, 11, 6, 12, 14, 0)


def test_promised_time_calculation_and_rounding_br05():
    """BR-05: Promised time = ready time + delivery minutes + 5-min buffer, rounded UP to 5-min boundary."""
    ready_time = datetime(2026, 11, 6, 12, 14, 0)
    delivery_min = 15  # + 5 min buffer = 20 min added -> 12:34:00
    # 12:34 rounded up to next 5-min boundary is 12:35:00
    promised = OrderRouter.calculate_promised_time(ready_time, delivery_min)
    assert promised == datetime(2026, 11, 6, 12, 35, 0)

    # Test exact boundary (12:10 + 15 + 5 = 12:30:00) -> remains 12:30:00
    exact_ready = datetime(2026, 11, 6, 12, 10, 0)
    promised_exact = OrderRouter.calculate_promised_time(exact_ready, delivery_min)
    assert promised_exact == datetime(2026, 11, 6, 12, 30, 0)

    # Test 1 second past boundary (12:10:01 + 15 + 5 = 12:30:01) -> rounds up to 12:35:00
    past_ready = datetime(2026, 11, 6, 12, 10, 1)
    promised_past = OrderRouter.calculate_promised_time(past_ready, delivery_min)
    assert promised_past == datetime(2026, 11, 6, 12, 35, 0)
