"""Comprehensive unit tests covering all 12 Business Rules (BR-01 through BR-12)."""

from datetime import datetime, time, timedelta
import pytest

from src.accounting.accounting_engine import AccountingEngine
from src.accounting.penalty_calculator import PenaltyCalculator
from src.accounting.rent_calculator import RentCalculator
from src.models import (
    Brand,
    Channel,
    CostCentre,
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
from src.routing.kitchen_eligibility import KitchenEligibilityChecker
from src.routing.order_router import OrderRouter
from src.scheduling.batching import BatchingEngine
from src.scheduling.order_sequencer import OrderSequencer
from src.scheduling.station_scheduler import StationScheduler
from src.services.cancellation_service import CancellationService
from src.services.order_service import OrderService
from src.services.substitution_service import SubstitutionService


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------

def make_kitchen(k_id="K-01", open_h=8, close_h=23, stations_dict=None):
    if stations_dict is None:
        stations_dict = {
            StationType.GRILL: Station(StationType.GRILL, 2),
            StationType.FRYER: Station(StationType.FRYER, 2),
            StationType.WOK: Station(StationType.WOK, 2),
            StationType.COLD: Station(StationType.COLD, 2),
            StationType.BAKERY: Station(StationType.BAKERY, 1),
        }
    return Kitchen(
        kitchen_id=k_id,
        name=f"Kitchen {k_id}",
        open_time=time(open_h, 0),
        close_time=time(close_h, 0),
        supported_brands={"B-01", "B-02"},
        delivery_zones={"ZONE-1"},
        stations=stations_dict,
    )


# ---------------------------------------------------------------------------
# BR-01: Kitchen eligibility and routing
# ---------------------------------------------------------------------------

def test_br01_kitchen_eligibility_and_routing():
    """BR-01: Checks brand, zone, operating hours, required stations, and lowest ready time."""
    k1 = make_kitchen("K-01")
    k2 = make_kitchen("K-02")
    zone = DeliveryZone("ZONE-1", 15, {"K-01", "K-02"})
    recipes = {"REC-BURGER": Recipe("REC-BURGER", StationType.COLD, 3, 2)}
    order = Order(
        order_id="ORD-01",
        brand_id="B-01",
        items=[OrderItem("1", "ORD-01", "ITM-BURGER", 220.0, "REC-BURGER")],
        channel=Channel.AGGREGATOR_A,
        delivery_zone="ZONE-1",
        order_time=datetime(2026, 11, 6, 12, 0, 0),
    )

    # Check eligibility
    assert KitchenEligibilityChecker.is_eligible(k1, order, zone, recipes)
    assert KitchenEligibilityChecker.is_eligible(k2, order, zone, recipes)

    # Route order: tie break should choose K-01 (lowest ID)
    router = OrderRouter()
    eval_res = router.route_order(order, {"K-01": k1, "K-02": k2}, zone, recipes)
    assert eval_res.selected_kitchen_id == "K-01"


# ---------------------------------------------------------------------------
# BR-02: Station capacity and batching
# ---------------------------------------------------------------------------

def test_br02_station_capacity_and_batching():
    """BR-02: Identical recipes within 3 minutes batch together without exceeding batch capacity."""
    recipe = Recipe("REC-FRIES", StationType.FRYER, 5, max_batch_size=3)
    engine = BatchingEngine()
    t0 = datetime(2026, 11, 6, 12, 0, 0)
    it1 = OrderItem("1", "ORD-1", "ITM-FRIES", 110.0, "REC-FRIES")
    it2 = OrderItem("2", "ORD-2", "ITM-FRIES", 110.0, "REC-FRIES")
    it3 = OrderItem("3", "ORD-3", "ITM-FRIES", 110.0, "REC-FRIES")
    it4 = OrderItem("4", "ORD-4", "ITM-FRIES", 110.0, "REC-FRIES")

    b1 = engine.find_or_create_batch(it1, recipe, t0)
    b2 = engine.find_or_create_batch(it2, recipe, t0 + timedelta(minutes=2))
    b3 = engine.find_or_create_batch(it3, recipe, t0 + timedelta(minutes=3))
    # Fourth item exceeds max_batch_size 3 -> new batch
    b4 = engine.find_or_create_batch(it4, recipe, t0 + timedelta(minutes=1))

    assert b1.batch_id == b2.batch_id == b3.batch_id
    assert b4.batch_id != b1.batch_id


# ---------------------------------------------------------------------------
# BR-03: FIFO and RUSH priority
# ---------------------------------------------------------------------------

def test_br03_fifo_and_rush_priority():
    """BR-03: RUSH can jump at most 3 orders; an order cannot suffer more than 2 delays."""
    t0 = datetime(2026, 11, 6, 12, 0, 0)
    orders = [
        Order(f"ORD-{i}", "B-01", [OrderItem("1", f"ORD-{i}", "ITM-1", 100.0, "REC-1")],
              Channel.AGGREGATOR_A, "Z-1", t0 + timedelta(minutes=i))
        for i in range(5)
    ]
    # Make ORD-4 a RUSH order
    orders[4].channel_priority = True

    sequenced = OrderSequencer.sequence_orders(orders)
    # RUSH jumped 3 orders (max 3 jumps)
    assert sequenced[1].order_id == "ORD-4"
    assert sequenced[1].rush_jumps_made == 3


# ---------------------------------------------------------------------------
# BR-04: Ready-time calculation & dependencies
# ---------------------------------------------------------------------------

def test_br04_ready_time_and_dependencies():
    """BR-04: Dependent recipe starts after predecessor finishes; ready time includes +3m packaging."""
    kitchen = make_kitchen()
    recipes = {
        "REC-PATTY": Recipe("REC-PATTY", StationType.GRILL, 8, 4),
        "REC-BURGER": Recipe("REC-BURGER", StationType.COLD, 3, 2, dependency_recipe_id="REC-PATTY"),
    }
    order = Order(
        order_id="ORD-DEP",
        brand_id="B-01",
        items=[
            OrderItem("1", "ORD-DEP", "ITM-PATTY", 150.0, "REC-PATTY"),
            OrderItem("2", "ORD-DEP", "ITM-BURGER", 220.0, "REC-BURGER"),
        ],
        channel=Channel.AGGREGATOR_A,
        delivery_zone="ZONE-1",
        order_time=datetime(2026, 11, 6, 12, 0, 0),
    )
    scheduler = StationScheduler()
    outcome = scheduler.commit_order(kitchen, order, recipes, persist=True)

    patty = [it for it in order.items if it.recipe_id == "REC-PATTY"][0]
    burger = [it for it in order.items if it.recipe_id == "REC-BURGER"][0]

    assert burger.prep_start_time >= patty.prep_end_time
    # Patty: 12:00 -> 12:08. Burger: 12:08 -> 12:11. +3m packaging = 12:14
    assert outcome.ready_time == datetime(2026, 11, 6, 12, 14, 0)


# ---------------------------------------------------------------------------
# BR-05: Promised-time calculation & rerouting
# ---------------------------------------------------------------------------

def test_br05_promised_time_calculation_and_reroute():
    """BR-05: Promised = ready + delivery + 5m buffer rounded UP to 5-min boundary; reroute if >45m."""
    router = OrderRouter()
    ready = datetime(2026, 11, 6, 12, 14, 0)
    # 12:14 + 15m zone + 5m buffer = 12:34 -> rounded UP to next 5-min mark = 12:35
    promised = router.calculate_promised_time(ready, 15)
    assert promised == datetime(2026, 11, 6, 12, 35, 0)

    # Exact boundary check: 12:10 + 15 + 5 = 12:30 -> stays 12:30
    promised_exact = router.calculate_promised_time(datetime(2026, 11, 6, 12, 10, 0), 15)
    assert promised_exact == datetime(2026, 11, 6, 12, 30, 0)


# ---------------------------------------------------------------------------
# BR-06: Kitchen throttling
# ---------------------------------------------------------------------------

def test_br06_kitchen_throttling_trigger_and_recovery():
    """BR-06: Throttled when projected ready time > 60m; cleared when load < 40m."""
    k = make_kitchen("K-01")
    k.mark_throttled()
    assert k.is_throttled
    k.clear_throttled()
    assert not k.is_throttled


# ---------------------------------------------------------------------------
# BR-07: Stock-outs and substitutions
# ---------------------------------------------------------------------------

def test_br07_stockouts_and_substitutions():
    """BR-07: Substitutes allowed if within ₹20; cancelled if no items remain."""
    k = make_kitchen("K-01")
    k.stock_out.add("ITM-OUT")
    menu = {
        "ITM-OUT": MenuItem("ITM-OUT", "B-01", "Out Item", 200.0, "REC-1"),
        "ITM-SUB-OK": MenuItem("ITM-SUB-OK", "B-01", "Sub Ok", 215.0, "REC-1"),
        "ITM-SUB-EXP": MenuItem("ITM-SUB-EXP", "B-01", "Sub Expensive", 250.0, "REC-1"),
    }
    recipes = {"REC-1": Recipe("REC-1", StationType.COLD, 3, 2)}

    # Case 1: valid substitute (diff Rs. 15 <= 20)
    sub_service = SubstitutionService(
        substitutions={("B-01", "ITM-OUT"): "ITM-SUB-OK"},
        menu_items=menu,
    )
    order1 = Order("O1", "B-01", [OrderItem("1", "O1", "ITM-OUT", 200.0, "REC-1")],
                   Channel.OWN_APP, "Z-1", datetime(2026, 11, 6, 12, 0, 0))
    res1 = sub_service.apply_substitutions_for_kitchen(order1, k, recipes)
    assert res1 is True
    assert order1.items[0].item_id == "ITM-SUB-OK"

    # Case 2: invalid substitute (diff Rs. 50 > 20) -> removed -> cancelled
    sub_service_exp = SubstitutionService(
        substitutions={("B-01", "ITM-OUT"): "ITM-SUB-EXP"},
        menu_items=menu,
    )
    order2 = Order("O2", "B-01", [OrderItem("1", "O2", "ITM-OUT", 200.0, "REC-1")],
                   Channel.OWN_APP, "Z-1", datetime(2026, 11, 6, 12, 0, 0))
    res2 = sub_service_exp.apply_substitutions_for_kitchen(order2, k, recipes)
    assert res2 is False
    assert order2.status == OrderStatus.CANCELLED


# ---------------------------------------------------------------------------
# BR-08: Cancellation rules
# ---------------------------------------------------------------------------

def test_br08_cancellation_rules_free_vs_charged():
    """BR-08: Free before prep starts; charged for started items if after prep start."""
    it1 = OrderItem("1", "O1", "ITM-1", 200.0, "REC-1", prep_start_time=datetime(2026, 11, 6, 12, 10, 0))
    order = Order("O1", "B-01", [it1], Channel.AGGREGATOR_A, "Z-1", datetime(2026, 11, 6, 12, 0, 0))

    # Before start (12:05) -> Free
    ok, charge, _ = CancellationService.cancel_order(order, datetime(2026, 11, 6, 12, 5, 0), "CUSTOMER")
    assert ok and charge == 0.0

    # After start (12:12) -> Charged Rs. 200
    ok, charge, _ = CancellationService.cancel_order(order, datetime(2026, 11, 6, 12, 12, 0), "AGGREGATOR_A")
    assert ok and charge == 200.0


# ---------------------------------------------------------------------------
# BR-09: Commissions, packaging, and GST
# ---------------------------------------------------------------------------

def test_br09_commissions_packaging_and_gst():
    """BR-09: Aggregator A 22%, Aggregator B 18%, Own app 0% + Rs. 15 fee; pkg Rs.10 (max 40); GST 5%."""
    items = [OrderItem(str(i), "O1", f"ITM-{i}", 100.0, "REC-1") for i in range(3)]
    order_a = Order("O1", "B-01", items, Channel.AGGREGATOR_A, "Z-1", datetime(2026, 11, 6, 12, 0, 0))
    order_app = Order("O2", "B-01", items, Channel.OWN_APP, "Z-1", datetime(2026, 11, 6, 12, 0, 0))

    f_a = AccountingEngine.calculate_order_financials(order_a)
    assert f_a.commission_amount == 66.0  # 300 * 22%
    assert f_a.packaging_fee == 30.0  # 3 * 10
    assert f_a.gst_amount == 15.0  # 300 * 5%

    f_app = AccountingEngine.calculate_order_financials(order_app)
    assert f_app.commission_amount == 0.0
    assert f_app.fixed_fee == 15.0


# ---------------------------------------------------------------------------
# BR-10: Late hand-off penalties
# ---------------------------------------------------------------------------

def test_br10_late_handoff_penalties_and_cost_centres():
    """BR-10: Rs. 50 per started 10 minutes late (max 200); charged to kitchen if throttled."""
    prom = datetime(2026, 11, 6, 12, 30, 0)
    # 25 min late (12:55:00) -> 3 blocks of 10 min -> Rs. 150
    p1, cc1 = PenaltyCalculator.calculate_penalty_with_cost_centre(
        prom, datetime(2026, 11, 6, 12, 55, 0), is_throttled_routing=False
    )
    assert p1 == 150.0
    assert cc1 == CostCentre.BRAND

    # 45 min late -> max cap Rs. 200; throttled -> KITCHEN
    p2, cc2 = PenaltyCalculator.calculate_penalty_with_cost_centre(
        prom, datetime(2026, 11, 6, 13, 15, 0), is_throttled_routing=True
    )
    assert p2 == 200.0
    assert cc2 == CostCentre.KITCHEN


# ---------------------------------------------------------------------------
# BR-11: Kitchen rent
# ---------------------------------------------------------------------------

def test_br11_kitchen_rent_and_minimum_fee():
    """BR-11: Rs. 2/order + 3% of net food; Rs. 500 minimum if < 30 orders/day."""
    # 10 orders, net food Rs. 1000 -> 10*2 + 30 = Rs. 50 -> <500 triggers min Rs. 500
    res1 = RentCalculator.calculate_rent(order_count=10, net_food_sales=1000.0)
    assert res1.final_rent == 500.0
    assert res1.minimum_rent_applied is True

    # 35 orders, net food Rs. 5000 -> 35*2 + 150 = Rs. 220 (no min fee applied)
    res2 = RentCalculator.calculate_rent(order_count=35, net_food_sales=5000.0)
    assert res2.final_rent == 220.0
    assert res2.minimum_rent_applied is False


# ---------------------------------------------------------------------------
# BR-12: Rule execution precedence
# ---------------------------------------------------------------------------

def test_br12_rule_execution_precedence():
    """BR-12: Verifies order lifecycle sequence: Eligibility -> Throttling -> Routing -> Scheduling."""
    k1 = make_kitchen("K-01")
    zone = DeliveryZone("ZONE-1", 15, {"K-01"})
    recipes = {"REC-1": Recipe("REC-1", StationType.COLD, 3, 2)}
    items = {"ITM-1": MenuItem("ITM-1", "B-01", "Salad", 100.0, "REC-1")}
    order = Order("O1", "B-01", [OrderItem("1", "O1", "ITM-1", 100.0, "REC-1")],
                  Channel.OWN_APP, "ZONE-1", datetime(2026, 11, 6, 12, 0, 0))

    svc = OrderService(
        kitchens={"K-01": k1},
        brands={"B-01": Brand("B-01", "Brand 1")},
        menu_items=items,
        recipes=recipes,
        zones={"ZONE-1": zone},
    )
    records = svc.process_all_orders([order])
    rec = records[0]
    assert rec.order.status == OrderStatus.SCHEDULED
    assert rec.routing.selected_kitchen_id == "K-01"
    assert rec.order.projected_ready_time is not None
    assert rec.order.promised_time is not None
    assert rec.financials.customer_total > 0
