"""Unit tests for OrderRouter covering BR-01, BR-05, and BR-06."""

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
from src.scheduling.scheduler import StationScheduler


@pytest.fixture
def base_recipes():
    return {
        "REC-GRILL": Recipe(recipe_id="REC-GRILL", station_type=StationType.GRILL, prep_minutes=10),
        "REC-FRY": Recipe(recipe_id="REC-FRY", station_type=StationType.FRYER, prep_minutes=5),
    }


@pytest.fixture
def base_zone():
    return DeliveryZone(zone_id="ZONE-1", delivery_minutes=15, eligible_kitchen_ids={"K-01", "K-02"})


def test_kitchen_eligibility_br01(base_recipes, base_zone):
    """BR-01: Kitchen is eligible only if brand, zone, hours, and stations match."""
    router = OrderRouter()

    k_valid = Kitchen(
        kitchen_id="K-01",
        name="Valid Hub",
        open_time=time(8, 0),
        close_time=time(22, 0),
        supported_brands={"BRAND-X"},
        delivery_zones={"ZONE-1"},
        stations={StationType.GRILL: Station(station_type=StationType.GRILL, capacity=1)},
    )
    k_wrong_brand = Kitchen(
        kitchen_id="K-02",
        name="Wrong Brand",
        open_time=time(8, 0),
        close_time=time(22, 0),
        supported_brands={"OTHER-BRAND"},
        delivery_zones={"ZONE-1"},
        stations={StationType.GRILL: Station(station_type=StationType.GRILL, capacity=1)},
    )

    order = Order(
        order_id="ORD-01",
        brand_id="BRAND-X",
        items=[OrderItem(order_item_id="1", order_id="ORD-01", item_id="ITM-1", price=200, recipe_id="REC-GRILL")],
        channel=Channel.AGGREGATOR_A,
        delivery_zone="ZONE-1",
        order_time=datetime(2026, 11, 6, 12, 0, 0),
    )

    eligible = router.find_eligible_kitchens(
        order=order,
        all_kitchens={"K-01": k_valid, "K-02": k_wrong_brand},
        zone=base_zone,
        recipes=base_recipes,
    )
    assert len(eligible) == 1
    assert eligible[0].kitchen_id == "K-01"


def test_routing_lowest_projected_ready_time_br01(base_recipes, base_zone):
    """BR-01: Select kitchen with lowest projected ready time."""
    router = OrderRouter()

    # K-01 has 1 slot (busy until 12:15)
    k1 = Kitchen(
        kitchen_id="K-01",
        name="Hub 1",
        open_time=time(8, 0),
        close_time=time(22, 0),
        supported_brands={"BRAND-X"},
        delivery_zones={"ZONE-1"},
        stations={StationType.GRILL: Station(station_type=StationType.GRILL, capacity=1)},
    )
    # Book K-01 slot from 12:00 to 12:15
    from src.models import SlotBooking
    k1.stations[StationType.GRILL].slots[0].bookings.append(
        SlotBooking("B1", "ITM-0", "ORD-0", "REC-GRILL", datetime(2026, 11, 6, 12, 0), datetime(2026, 11, 6, 12, 15))
    )

    # K-02 has 1 slot (completely free at 12:00)
    k2 = Kitchen(
        kitchen_id="K-02",
        name="Hub 2",
        open_time=time(8, 0),
        close_time=time(22, 0),
        supported_brands={"BRAND-X"},
        delivery_zones={"ZONE-1"},
        stations={StationType.GRILL: Station(station_type=StationType.GRILL, capacity=1)},
    )

    order = Order(
        order_id="ORD-10",
        brand_id="BRAND-X",
        items=[OrderItem("1", "ORD-10", "ITM-1", 200, "REC-GRILL")],
        channel=Channel.AGGREGATOR_A,
        delivery_zone="ZONE-1",
        order_time=datetime(2026, 11, 6, 12, 0, 0),
    )

    eval_result = router.route_order(order, {"K-01": k1, "K-02": k2}, base_zone, base_recipes)
    assert eval_result.selected_kitchen_id == "K-02"


def test_routing_tie_break_load_and_id_br01(base_recipes, base_zone):
    """BR-01: Tie break by lowest current load, then lowest kitchen ID."""
    router = OrderRouter()

    k1 = Kitchen(
        kitchen_id="K-01",
        name="Hub 1",
        open_time=time(8, 0),
        close_time=time(22, 0),
        supported_brands={"BRAND-X"},
        delivery_zones={"ZONE-1"},
        stations={StationType.GRILL: Station(station_type=StationType.GRILL, capacity=2)},
    )
    k2 = Kitchen(
        kitchen_id="K-02",
        name="Hub 2",
        open_time=time(8, 0),
        close_time=time(22, 0),
        supported_brands={"BRAND-X"},
        delivery_zones={"ZONE-1"},
        stations={StationType.GRILL: Station(station_type=StationType.GRILL, capacity=2)},
    )

    # Both are completely idle; projected ready times are equal.
    # Tie break should choose lowest kitchen ID: K-01
    order = Order(
        order_id="ORD-TIE",
        brand_id="BRAND-X",
        items=[OrderItem("1", "ORD-TIE", "ITM-1", 100, "REC-GRILL")],
        channel=Channel.AGGREGATOR_A,
        delivery_zone="ZONE-1",
        order_time=datetime(2026, 11, 6, 12, 0, 0),
    )
    eval_result = router.route_order(order, {"K-02": k2, "K-01": k1}, base_zone, base_recipes)
    assert eval_result.selected_kitchen_id == "K-01"


def test_late_risk_flag_br05(base_recipes, base_zone):
    """BR-05: Projected ready time > 45 minutes triggers LATE_RISK flag when no reroute reduces >=10m."""
    router = OrderRouter()
    # Create recipe with 50 minutes prep
    long_recipe = {"REC-LONG": Recipe(recipe_id="REC-LONG", station_type=StationType.GRILL, prep_minutes=50)}

    k1 = Kitchen(
        kitchen_id="K-01",
        name="Only Kitchen",
        open_time=time(8, 0),
        close_time=time(22, 0),
        supported_brands={"B-1"},
        delivery_zones={"ZONE-1"},
        stations={StationType.GRILL: Station(station_type=StationType.GRILL, capacity=1)},
    )

    order = Order(
        order_id="ORD-LATE",
        brand_id="B-1",
        items=[OrderItem("1", "ORD-LATE", "ITM-1", 150, "REC-LONG")],
        channel=Channel.OWN_APP,
        delivery_zone="ZONE-1",
        order_time=datetime(2026, 11, 6, 12, 0, 0),
    )

    res = router.route_order(order, {"K-01": k1}, base_zone, long_recipe)
    # 50 min prep + 3 min packaging = 53 min > 45 min threshold -> LATE_RISK
    assert res.late_risk is True
    assert order.late_risk is True


def test_throttling_br06(base_recipes, base_zone):
    """BR-06: Kitchen projected ready time > 60 min marks it THROTTLED."""
    router = OrderRouter()
    super_long_recipe = {"REC-GIANT": Recipe(recipe_id="REC-GIANT", station_type=StationType.GRILL, prep_minutes=65)}

    k1 = Kitchen(
        kitchen_id="K-01",
        name="Throttled Hub",
        open_time=time(8, 0),
        close_time=time(22, 0),
        supported_brands={"B-1"},
        delivery_zones={"ZONE-1"},
        stations={StationType.GRILL: Station(station_type=StationType.GRILL, capacity=1)},
    )

    order = Order(
        order_id="ORD-THROTTLE",
        brand_id="B-1",
        items=[OrderItem("1", "ORD-THROTTLE", "ITM-1", 300, "REC-GIANT")],
        channel=Channel.AGGREGATOR_B,
        delivery_zone="ZONE-1",
        order_time=datetime(2026, 11, 6, 12, 0, 0),
    )

    res = router.route_order(order, {"K-01": k1}, base_zone, super_long_recipe)
    assert k1.is_throttled is True
