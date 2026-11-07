"""CSV dataset loader and parser using pathlib and the standard csv library."""

import csv
from datetime import datetime, time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from src.loaders.data_validator import DataValidator, ValidationError
from src.models import (
    Brand,
    Channel,
    DeliveryZone,
    Event,
    EventType,
    Kitchen,
    MenuItem,
    Order,
    OrderItem,
    Recipe,
    Station,
    StationType,
)


def _parse_time(time_str: str) -> time:
    """Parse time in HH:MM or HH:MM:SS format."""
    clean = time_str.strip()
    parts = clean.split(":")
    if len(parts) == 2:
        return time(int(parts[0]), int(parts[1]))
    if len(parts) == 3:
        return time(int(parts[0]), int(parts[1]), int(parts[2]))
    raise ValueError(f"Invalid time format: {time_str}")


def _parse_datetime(dt_str: str) -> datetime:
    """Parse timestamp in common ISO or space-separated formats."""
    clean = dt_str.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(clean, fmt)
        except ValueError:
            pass
    return datetime.fromisoformat(clean)


def _split_set(val: str, delimiter: str = ";") -> Set[str]:
    """Split string by delimiter into trimmed set, handling commas if semicolon not found."""
    if not val or not val.strip():
        return set()
    if delimiter not in val and "," in val:
        delimiter = ","
    return {p.strip() for p in val.split(delimiter) if p.strip()}


class CsvLoader:
    """Loads and links domain models from CSV files."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)

    def load_brands(self, filename: str = "brands.csv") -> Dict[str, Brand]:
        path = self.data_dir / filename
        brands: Dict[str, Brand] = {}
        if not path.exists():
            raise FileNotFoundError(f"Missing file: {path}")

        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                brand_id = row["brand_id"].strip()
                name = row["name"].strip()
                brands[brand_id] = Brand(brand_id=brand_id, name=name)
        return brands

    def load_recipes(self, filename: str = "recipes.csv") -> Dict[str, Recipe]:
        path = self.data_dir / filename
        recipes: Dict[str, Recipe] = {}
        if not path.exists():
            raise FileNotFoundError(f"Missing file: {path}")

        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                recipe_id = row["recipe_id"].strip()
                st_type = StationType.from_str(row["station_type"])
                prep_min = int(row["prep_minutes"].strip())
                batch_sz = int(row.get("max_batch_size", 1))
                dep = row.get("dependency_recipe_id", "").strip() or None
                recipe = Recipe(
                    recipe_id=recipe_id,
                    station_type=st_type,
                    prep_minutes=prep_min,
                    max_batch_size=batch_sz,
                    dependency_recipe_id=dep,
                )
                DataValidator.validate_recipe(recipe)
                recipes[recipe_id] = recipe
        return recipes

    def load_menu_items(
        self,
        brands: Dict[str, Brand],
        recipes: Dict[str, Recipe],
        filename: str = "menu_items.csv"
    ) -> Dict[str, MenuItem]:
        path = self.data_dir / filename
        menu_items: Dict[str, MenuItem] = {}
        if not path.exists():
            raise FileNotFoundError(f"Missing file: {path}")

        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                item_id = row["item_id"].strip()
                brand_id = row["brand_id"].strip()
                name = row["name"].strip()
                price = float(row["price"].strip())
                recipe_id = row["recipe_id"].strip()

                item = MenuItem(
                    item_id=item_id,
                    brand_id=brand_id,
                    name=name,
                    price=price,
                    recipe_id=recipe_id,
                )
                DataValidator.validate_menu_item(item, brands, recipes)
                menu_items[item_id] = item
                if brand_id in brands:
                    brands[brand_id].add_menu_item(item)
        return menu_items

    def load_zones(self, filename: Optional[str] = None) -> Dict[str, DeliveryZone]:
        """Loads delivery zones from delivery_zones.csv or fallback zones.csv."""
        if filename:
            path = self.data_dir / filename
        else:
            path = self.data_dir / "delivery_zones.csv"
            if not path.exists():
                path = self.data_dir / "zones.csv"

        if not path.exists():
            raise FileNotFoundError(f"Missing delivery zones CSV at: {path}")

        zones: Dict[str, DeliveryZone] = {}
        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                zone_id = row["zone_id"].strip()
                delivery_min = int(row["delivery_minutes"].strip())
                eligible_kitchens = _split_set(row.get("eligible_kitchen_ids", ""))
                zones[zone_id] = DeliveryZone(
                    zone_id=zone_id,
                    delivery_minutes=delivery_min,
                    eligible_kitchen_ids=eligible_kitchens,
                )
        return zones

    def load_stations(self, filename: str = "stations.csv") -> Dict[Tuple[str, StationType], Station]:
        path = self.data_dir / filename
        stations: Dict[Tuple[str, StationType], Station] = {}
        if not path.exists():
            raise FileNotFoundError(f"Missing file: {path}")

        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                kitchen_id = row["kitchen_id"].strip()
                st_type = StationType.from_str(row["station_type"])
                capacity = int(row["capacity"].strip())
                st = Station(
                    station_id=f"{kitchen_id}_{st_type.value}",
                    station_type=st_type,
                    capacity=capacity,
                )
                stations[(kitchen_id, st_type)] = st
        return stations

    def load_kitchens(
        self,
        kitchens_filename: str = "kitchens.csv",
        stations_filename: str = "stations.csv"
    ) -> Dict[str, Kitchen]:
        k_path = self.data_dir / kitchens_filename
        if not k_path.exists():
            raise FileNotFoundError(f"Missing file: {k_path}")

        stations = self.load_stations(stations_filename)
        kitchens: Dict[str, Kitchen] = {}

        with open(k_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                k_id = row["kitchen_id"].strip()
                name = row["name"].strip()
                open_t = _parse_time(row["open_time"])
                close_t = _parse_time(row["close_time"])
                brands = _split_set(row.get("supported_brands", ""))
                zones = _split_set(row.get("delivery_zones", ""))

                k_stations: Dict[StationType, Station] = {}
                for (kid, st_type), station_obj in stations.items():
                    if kid == k_id:
                        k_stations[st_type] = station_obj

                kitchen = Kitchen(
                    kitchen_id=k_id,
                    name=name,
                    open_time=open_t,
                    close_time=close_t,
                    supported_brands=brands,
                    delivery_zones=zones,
                    stations=k_stations,
                )
                DataValidator.validate_kitchen(kitchen)
                kitchens[k_id] = kitchen
        return kitchens

    def load_orders(
        self,
        brands: Dict[str, Brand],
        zones: Dict[str, DeliveryZone],
        menu_items: Dict[str, MenuItem],
        recipes: Dict[str, Recipe],
        filename: str = "orders.csv"
    ) -> List[Order]:
        path = self.data_dir / filename
        orders: List[Order] = []
        if not path.exists():
            raise FileNotFoundError(f"Missing file: {path}")

        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                order_id = row["order_id"].strip()
                brand_id = row["brand_id"].strip()
                channel = Channel.from_str(row["channel"])
                zone_id = row["delivery_zone"].strip()
                order_time = _parse_datetime(row["order_time"])

                priority_str = row.get("channel_priority", "false").strip().lower()
                channel_priority = priority_str in ("true", "1", "yes", "priority")

                raw_items = [it.strip() for it in row["items"].split(";") if it.strip()]
                order_items: List[OrderItem] = []
                for idx, itm_code in enumerate(raw_items):
                    if itm_code in menu_items:
                        m_item = menu_items[itm_code]
                        order_items.append(
                            OrderItem(
                                order_item_id=f"{order_id}_{idx+1}",
                                order_id=order_id,
                                item_id=m_item.item_id,
                                price=m_item.price,
                                recipe_id=m_item.recipe_id,
                                brand_id=m_item.brand_id,
                            )
                        )

                order = Order(
                    order_id=order_id,
                    brand_id=brand_id,
                    items=order_items,
                    channel=channel,
                    delivery_zone=zone_id,
                    order_time=order_time,
                    channel_priority=channel_priority,
                )
                DataValidator.validate_order(order, brands, zones, menu_items)
                orders.append(order)
        return orders

    def load_substitutions(self, filename: str = "substitutions.csv") -> Dict[Tuple[str, str], str]:
        """Loads brand substitutions: (brand_id, original_item_id) -> substitute_item_id."""
        path = self.data_dir / filename
        substitutions: Dict[Tuple[str, str], str] = {}
        if not path.exists():
            return substitutions

        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                brand_id = row.get("brand_id", "").strip()
                orig_item = (
                    row.get("original_item_id")
                    or row.get("item_id")
                    or row.get("out_item_id")
                    or ""
                ).strip()
                sub_item = (
                    row.get("substitute_item_id")
                    or row.get("substitute_id")
                    or row.get("replacement_item_id")
                    or ""
                ).strip()
                if brand_id and orig_item and sub_item:
                    substitutions[(brand_id, orig_item)] = sub_item
        return substitutions

    def load_events(self, filename: str = "events.csv") -> List[Event]:
        """Loads events from events.csv if present."""
        path = self.data_dir / filename
        events: List[Event] = []
        if not path.exists():
            return events

        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                ev_id = row.get("event_id", f"EV-{idx+1}").strip()
                ev_type = EventType.from_str(row["event_type"])
                ts = _parse_datetime(row["timestamp"])
                oid = row.get("order_id", "").strip() or None
                kid = row.get("kitchen_id", "").strip() or None
                item_id = row.get("item_id", "").strip() or None
                source = row.get("source", "").strip() or None
                details = row.get("details", "").strip() or None

                event = Event(
                    event_id=ev_id,
                    event_type=ev_type,
                    timestamp=ts,
                    order_id=oid,
                    kitchen_id=kid,
                    item_id=item_id,
                    source=source,
                    details=details,
                )
                DataValidator.validate_event(event)
                events.append(event)
        return events
