"""Tests for Kitchen and Station models (BR-01)."""

from datetime import datetime, time
import pytest

from src.models import Kitchen, Station, StationSlot, StationType


def test_kitchen_operating_hours_br01():
    """BR-01: Check kitchen operating hours within daytime shift."""
    kitchen = Kitchen(
        kitchen_id="K-01",
        name="Indiranagar Hub",
        open_time=time(8, 0),
        close_time=time(23, 0),
        supported_brands={"B-01"},
        delivery_zones={"ZONE-1"},
    )
    # Open at 12:00
    assert kitchen.is_operating_at(datetime(2026, 11, 6, 12, 0, 0)) is True
    # Open at exact boundary 08:00
    assert kitchen.is_operating_at(datetime(2026, 11, 6, 8, 0, 0)) is True
    # Closed at 07:59
    assert kitchen.is_operating_at(datetime(2026, 11, 6, 7, 59, 59)) is False
    # Closed at 23:01
    assert kitchen.is_operating_at(datetime(2026, 11, 6, 23, 1, 0)) is False


def test_kitchen_overnight_operating_hours_br01():
    """BR-01: Check overnight shift (e.g. 20:00 to 04:00)."""
    kitchen = Kitchen(
        kitchen_id="K-NIGHT",
        name="Late Night Kitchen",
        open_time=time(20, 0),
        close_time=time(4, 0),
    )
    assert kitchen.is_operating_at(datetime(2026, 11, 6, 23, 30, 0)) is True
    assert kitchen.is_operating_at(datetime(2026, 11, 6, 2, 0, 0)) is True
    assert kitchen.is_operating_at(datetime(2026, 11, 6, 14, 0, 0)) is False


def test_kitchen_brand_and_zone_support_br01():
    """BR-01: Kitchen must support brand and serve delivery zone."""
    kitchen = Kitchen(
        kitchen_id="K-01",
        name="Hub",
        open_time=time(9, 0),
        close_time=time(22, 0),
        supported_brands={"B-01", "B-02"},
        delivery_zones={"ZONE-A", "ZONE-B"},
    )
    assert kitchen.supports_brand("B-01") is True
    assert kitchen.supports_brand("b-02") is True
    assert kitchen.supports_brand("B-99") is False

    assert kitchen.serves_delivery_zone("ZONE-A") is True
    assert kitchen.serves_delivery_zone("zone-b") is True
    assert kitchen.serves_delivery_zone("ZONE-Z") is False


def test_kitchen_station_requirements_br01():
    """BR-01: Kitchen must have every required station type."""
    kitchen = Kitchen(
        kitchen_id="K-01",
        name="Hub",
        open_time=time(9, 0),
        close_time=time(22, 0),
        stations={
            StationType.GRILL: Station(station_type=StationType.GRILL, capacity=2),
            StationType.FRYER: Station(station_type=StationType.FRYER, capacity=1),
        },
    )
    assert kitchen.has_station(StationType.GRILL) is True
    assert kitchen.has_station(StationType.FRYER) is True
    assert kitchen.has_station(StationType.WOK) is False

    assert kitchen.has_all_stations({StationType.GRILL, StationType.FRYER}) is True
    assert kitchen.has_all_stations({StationType.GRILL, StationType.WOK}) is False
