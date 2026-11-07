"""Unit tests for AccountingEngine covering BR-09 channel economics and fees."""

from datetime import datetime
import pytest

from src.accounting.accounting_engine import AccountingEngine
from src.models import Channel, Order, OrderItem


def _build_order(channel: Channel, num_items: int, item_price: float = 100.0) -> Order:
    items = [
        OrderItem(f"ITM-{i}", "ORD-TEST", f"PROD-{i}", item_price, "REC-X")
        for i in range(num_items)
    ]
    return Order(
        order_id="ORD-TEST",
        brand_id="B-01",
        items=items,
        channel=channel,
        delivery_zone="ZONE-1",
        order_time=datetime(2026, 11, 6, 12, 0, 0),
    )


def test_aggregator_a_economics_br09():
    """BR-09: Aggregator A has 22% commission, 0 fixed fee, 5% GST, and packaging."""
    # 2 items @ Rs. 200 = Rs. 400 food value
    order = _build_order(Channel.AGGREGATOR_A, num_items=2, item_price=200.0)
    fin = AccountingEngine.calculate_order_financials(order)

    assert fin.gross_food_value == 400.0
    assert fin.commission_rate == 0.22
    assert fin.commission_amount == 88.0  # 400 * 0.22
    assert fin.fixed_fee == 0.0
    assert fin.packaging_fee == 20.0  # 2 * 10
    assert fin.gst_amount == 20.0  # 5% of 400
    assert fin.customer_total == 440.0  # 400 + 20 + 20
    assert fin.brand_earnings == 312.0  # 400 - 88


def test_aggregator_b_economics_br09():
    """BR-09: Aggregator B has 18% commission, 0 fixed fee."""
    order = _build_order(Channel.AGGREGATOR_B, num_items=3, item_price=100.0)
    fin = AccountingEngine.calculate_order_financials(order)

    assert fin.gross_food_value == 300.0
    assert fin.commission_rate == 0.18
    assert fin.commission_amount == 54.0  # 300 * 0.18
    assert fin.fixed_fee == 0.0
    assert fin.packaging_fee == 30.0  # 3 * 10
    assert fin.gst_amount == 15.0  # 5% of 300
    assert fin.customer_total == 345.0  # 300 + 30 + 15
    assert fin.brand_earnings == 246.0  # 300 - 54


def test_own_app_economics_br09():
    """BR-09: Own App has 0% commission plus Rs. 15 fixed payment fee."""
    order = _build_order(Channel.OWN_APP, num_items=1, item_price=500.0)
    fin = AccountingEngine.calculate_order_financials(order)

    assert fin.gross_food_value == 500.0
    assert fin.commission_rate == 0.0
    assert fin.commission_amount == 0.0
    assert fin.fixed_fee == 15.0
    assert fin.packaging_fee == 10.0  # 1 * 10
    assert fin.gst_amount == 25.0  # 5% of 500
    assert fin.customer_total == 535.0  # 500 + 10 + 25
    assert fin.brand_earnings == 485.0  # 500 - 15


def test_packaging_cap_with_5_items_edge_case_7():
    """MANDATORY EDGE CASE 7 / BR-09: Packaging fee capped at Rs. 40 with 5 items (5 * 10 = 50 -> 40)."""
    order = _build_order(Channel.AGGREGATOR_A, num_items=5, item_price=100.0)
    fin = AccountingEngine.calculate_order_financials(order)

    assert fin.item_count == 5
    assert fin.packaging_fee == 40.0  # Capped at 40 instead of 50


def test_packaging_cap_with_large_order_br09():
    """BR-09: Large order with 8 items remains capped at Rs. 40."""
    order = _build_order(Channel.AGGREGATOR_B, num_items=8, item_price=50.0)
    fin = AccountingEngine.calculate_order_financials(order)

    assert fin.item_count == 8
    assert fin.packaging_fee == 40.0


def test_brand_kitchen_rent_minimum_fee_br11():
    """BR-11: Brand with < 30 orders/day at kitchen pays Rs. 500 minimum if raw rent < Rs. 500."""
    # 2 orders for Brand B-01 at kitchen K-01
    o1 = _build_order(Channel.AGGREGATOR_A, num_items=1, item_price=100.0)
    o1.assigned_kitchen_id = "K-01"
    f1 = AccountingEngine.calculate_order_financials(o1)

    o2 = _build_order(Channel.AGGREGATOR_A, num_items=1, item_price=100.0)
    o2.assigned_kitchen_id = "K-01"
    f2 = AccountingEngine.calculate_order_financials(o2)

    pnl_list = AccountingEngine.calculate_daily_brand_pnl([(o1, f1), (o2, f2)])
    assert len(pnl_list) == 1
    pnl = pnl_list[0]

    assert pnl.order_count == 2
    # Raw rent = 2 * Rs.2 + 3% of net food (2 * 78 = 156 * 0.03 = 4.68) = Rs. 8.68
    assert pnl.raw_calculated_rent == 8.68
    # Since 2 < 30, minimum rent Rs. 500 applies
    assert pnl.minimum_rent_applied is True
    assert pnl.final_kitchen_rent == 500.0


def test_brand_kitchen_rent_exactly_30_orders_edge_case_8():
    """MANDATORY EDGE CASE 8 / BR-11: Brand with exactly 30 orders does NOT qualify for Rs. 500 minimum."""
    records = []
    for i in range(30):
        o = _build_order(Channel.AGGREGATOR_A, num_items=1, item_price=100.0)
        o.order_id = f"ORD-BATCH30-{i}"
        o.assigned_kitchen_id = "K-01"
        f = AccountingEngine.calculate_order_financials(o)
        records.append((o, f))

    pnl_list = AccountingEngine.calculate_daily_brand_pnl(records)
    pnl = pnl_list[0]

    assert pnl.order_count == 30
    # Exactly 30 orders: rule states "Exactly 30 orders does not qualify for the minimum"
    # Net food per order = 100 - 22 = 78. Total net food = 30 * 78 = 2340.
    # Rent = 30 * 2 (Rs. 60) + 3% of 2340 (Rs. 70.20) = Rs. 130.20
    assert pnl.raw_calculated_rent == 130.20
    assert pnl.minimum_rent_applied is False
    assert pnl.final_kitchen_rent == 130.20  # Minimum Rs. 500 NOT applied!


def test_late_delivery_penalty_11_minutes_br10():
    """BR-10 & T-BR10-01: Hand-off 11 minutes late incurs Rs. 100 penalty (2 started 10-min blocks)."""
    prom = datetime(2026, 11, 6, 12, 30, 0)
    # 11 minutes late -> 12:41:00
    actual = datetime(2026, 11, 6, 12, 41, 0)
    penalty = AccountingEngine.calculate_late_penalty(prom, actual)
    assert penalty == 100.0  # 2 * 50

    # 5 minutes late -> 1 block = Rs. 50
    penalty_5 = AccountingEngine.calculate_late_penalty(prom, datetime(2026, 11, 6, 12, 35, 0))
    assert penalty_5 == 50.0

    # 45 minutes late -> capped at Rs. 200
    penalty_45 = AccountingEngine.calculate_late_penalty(prom, datetime(2026, 11, 6, 13, 15, 0))
    assert penalty_45 == 200.0

    # On time -> Rs. 0
    penalty_ontime = AccountingEngine.calculate_late_penalty(prom, prom)
    assert penalty_ontime == 0.0

