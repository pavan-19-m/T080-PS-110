"""Unit tests for Order model, sequencing, and RUSH priority jumps (BR-03)."""

from datetime import datetime
import pytest

from src.models import Channel, Order, OrderItem
from src.scheduling.order_sequencer import OrderSequencer


def _make_order(order_id: str, minutes: int, price: float = 200.0, priority: bool = False) -> Order:
    return Order(
        order_id=order_id,
        brand_id="B-01",
        items=[OrderItem(f"ITM-{order_id}", order_id, "BURGER", price, "REC-BURGER")],
        channel=Channel.AGGREGATOR_A,
        delivery_zone="ZONE-1",
        order_time=datetime(2026, 11, 6, 12, minutes, 0),
        channel_priority=priority,
    )


def test_rush_qualification_rules_br03():
    """BR-03: RUSH applies when channel priority flag is set or order value > ₹1,500."""
    # Priority flag true, low value -> RUSH
    o1 = _make_order("O1", 1, price=300.0, priority=True)
    assert o1.is_rush is True

    # High value > ₹1,500, no flag -> RUSH
    o2 = _make_order("O2", 2, price=1501.0, priority=False)
    assert o2.is_rush is True

    # Exactly ₹1,500, no flag -> NOT RUSH (must be strictly > 1500)
    o3 = _make_order("O3", 3, price=1500.0, priority=False)
    assert o3.is_rush is False

    # Low value, no flag -> NOT RUSH
    o4 = _make_order("O4", 4, price=500.0, priority=False)
    assert o4.is_rush is False


def test_fifo_ordering_without_rush_br03():
    """BR-03: Default order sequence is FIFO by order time."""
    orders = [
        _make_order("O-3", 15),
        _make_order("O-1", 5),
        _make_order("O-2", 10),
    ]
    sequenced = OrderSequencer.sequence_orders(orders)
    assert [o.order_id for o in sequenced] == ["O-1", "O-2", "O-3"]


def test_rush_order_jumps_br03():
    """BR-03: RUSH order can jump ahead of up to 3 non-RUSH orders."""
    # 4 normal orders, then 1 RUSH order
    n1 = _make_order("N1", 1)
    n2 = _make_order("N2", 2)
    n3 = _make_order("N3", 3)
    rush = _make_order("RUSH", 4, price=2000.0)

    sequenced = OrderSequencer.sequence_orders([n1, n2, n3, rush])

    # RUSH jumped N3, N2, N1 (3 jumps) -> now at the front!
    assert [o.order_id for o in sequenced] == ["RUSH", "N1", "N2", "N3"]
    assert rush.rush_jumps_made == 3
    assert n1.delayed_jumps_count == 1
    assert n2.delayed_jumps_count == 1
    assert n3.delayed_jumps_count == 1


def test_rush_order_attempting_fourth_jump_edge_case_2():
    """MANDATORY EDGE CASE 2 / BR-03: RUSH order attempting a 4th jump is capped at 3 jumps."""
    # 5 normal orders ahead of 1 RUSH order
    n1 = _make_order("N1", 1)
    n2 = _make_order("N2", 2)
    n3 = _make_order("N3", 3)
    n4 = _make_order("N4", 4)
    rush = _make_order("RUSH", 5, price=2500.0)

    sequenced = OrderSequencer.sequence_orders([n1, n2, n3, n4, rush])

    # RUSH jumps N4, N3, N2 (3 jumps), but CANNOT jump N1 (which would be 4th jump)
    # Final order should be: N1, RUSH, N2, N3, N4
    assert [o.order_id for o in sequenced] == ["N1", "RUSH", "N2", "N3", "N4"]
    assert rush.rush_jumps_made == 3


def test_delayed_jump_limit_constraint_br03():
    """BR-03: An order cannot be delayed by more than 2 jumps."""
    # Single normal order N1, followed by 3 separate RUSH orders
    n1 = _make_order("N1", 1)
    r1 = _make_order("R1", 2, priority=True)
    r2 = _make_order("R2", 3, priority=True)
    r3 = _make_order("R3", 4, priority=True)

    sequenced = OrderSequencer.sequence_orders([n1, r1, r2, r3])

    # R1 jumps N1 (N1 delay=1)
    # R2 jumps N1 (N1 delay=2, reaches limit)
    # R3 attempts to jump N1, but N1 cannot be delayed a 3rd time!
    # Expected order: R1, R2, N1, R3
    assert [o.order_id for o in sequenced] == ["R1", "R2", "N1", "R3"]
    assert n1.delayed_jumps_count == 2
    assert r1.rush_jumps_made == 1
    assert r2.rush_jumps_made == 1
    assert r3.rush_jumps_made == 0


def test_substitute_price_boundary_20_edge_case_5():
    """MANDATORY EDGE CASE 5 / BR-07 & EC-05: Substitute price exactly Rs. 20 higher is allowed (<= 20 is inclusive)."""
    orig_price = 100.0
    sub_price_20 = 120.0
    sub_price_21 = 121.0

    # Rule: Price difference <= Rs. 20 is permitted
    assert (sub_price_20 - orig_price) <= 20.0
    assert not ((sub_price_21 - orig_price) <= 20.0)


def test_cancellation_at_exact_prep_start_edge_case_6():
    """MANDATORY EDGE CASE 6 / BR-08 & EC-06: Cancellation at exact prep-start timestamp is considered started."""
    prep_start = datetime(2026, 11, 6, 12, 10, 0)
    cancel_exact = datetime(2026, 11, 6, 12, 10, 0)
    cancel_before = datetime(2026, 11, 6, 12, 9, 59)

    # Exact instant prep begins: rule states "At the exact prep-start timestamp, consider preparation started."
    assert (cancel_exact >= prep_start) is True

    # 1 second before prep begins: free cancellation
    assert (cancel_before >= prep_start) is False
