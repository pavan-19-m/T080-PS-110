"""CSV dataset loader and parser using pathlib and the standard csv library."""

import csv
from datetime import datetime, time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from src.input.validator import ValidationError, Validator
from src.models import (
    Brand,
    Channel,
    DeliveryZone,
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
                Validator.validate_recipe(recipe)
                recipes[recipe_id] = recipe
        return recipes

    def load_menu_items(
        self,
        brands: Dict[str, Brand],
        recipes: Dict[str, Recipe],
        filename: str = "menu_items.csv"
    ) -> Dict[str, MenuItem]:
        path = self.data_dir / filename
        items: Dict[str, MenuItem] = {}
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

                menu_item = MenuItem(
                    item_id=item_id,
                    brand_id=brand_id,
                    name=name,
                    price=price,
                    recipe_id=recipe_id,
                )
                Validator.validate_menu_item(menu_item, brands, recipes)
                items[item_id] = menu_item
                brands[brand_id].add_menu_item(menu_item)
        return items

    def load_zones(self, filename: str = "zones.csv") -> Dict[str, DeliveryZone]:
        path = self.data_dir / filename
        zones: Dict[str, DeliveryZone] = {}
        if not path.exists():
            raise FileNotFoundError(f"Missing file: {path}")

        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                zone_id = row["zone_id"].strip()
                delivery_min = int(row["delivery_minutes"].strip())
                kitchens = _split_set(row.get("eligible_kitchen_ids", ""))
                zones[zone_id] = DeliveryZone(
                    zone_id=zone_id,
                    delivery_minutes=delivery_min,
                    eligible_kitchen_ids=kitchens,
                )
        return zones

    def load_kitchens(
        self,
        kitchens_file: str = "kitchens.csv",
        stations_file: str = "stations.csv"
    ) -> Dict[str, Kitchen]:
        k_path = self.data_dir / kitchens_file
        s_path = self.data_dir / stations_file
        kitchens: Dict[str, Kitchen] = {}

        if not k_path.exists():
            raise FileNotFoundError(f"Missing file: {k_path}")

        with open(k_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                k_id = row["kitchen_id"].strip()
                name = row["name"].strip()
                open_t = _parse_time(row["open_time"])
                close_t = _parse_time(row["close_time"])
                brands = _split_set(row.get("supported_brands", ""))
                zones = _split_set(row.get("delivery_zones", ""))

                kitchen = Kitchen(
                    kitchen_id=k_id,
                    name=name,
                    open_time=open_t,
                    close_time=close_t,
                    supported_brands=brands,
                    delivery_zones=zones,
                )
                Validator.validate_kitchen(kitchen)
                kitchens[k_id] = kitchen

        if s_path.exists():
            with open(s_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    k_id = row["kitchen_id"].strip()
                    st_type = StationType.from_str(row["station_type"])
                    cap = int(row["capacity"].strip())
                    if k_id in kitchens:
                        kitchens[k_id].stations[st_type] = Station(
                            station_type=st_type,
                            capacity=cap,
                        )

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
                order_dt = _parse_datetime(row["order_time"])
                priority_flag = str(row.get("channel_priority", "false")).strip().lower() in (
                    "true", "1", "yes", "y"
                )

                raw_items_str = row["items"].strip()
                delim = ";" if ";" in raw_items_str else ","
                item_ids = [it.strip() for it in raw_items_str.split(delim) if it.strip()]

                order_items: List[OrderItem] = []
                for idx, item_id in enumerate(item_ids):
                    if item_id in menu_items:
                        m_item = menu_items[item_id]
                        order_items.append(
                            OrderItem(
                                order_item_id=f"{order_id}-ITM-{idx + 1}",
                                order_id=order_id,
                                item_id=item_id,
                                price=m_item.price,
                                recipe_id=m_item.recipe_id,
                            )
                        )
                    else:
                        raise ValidationError(f"Unknown item {item_id} in order {order_id}")

                order = Order(
                    order_id=order_id,
                    brand_id=brand_id,
                    items=order_items,
                    channel=channel,
                    delivery_zone=zone_id,
                    order_time=order_dt,
                    channel_priority=priority_flag,
                )
                Validator.validate_order(order, brands, zones, menu_items)
                orders.append(order)

        return orders
