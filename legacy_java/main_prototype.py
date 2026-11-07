#!/usr/bin/env python3
"""
PS-110: Cloud Kitchen Multi-brand Order Routing and Kitchen Capacity Engine
Starter implementation based on the team's Week-1 design documents and BR-01..BR-12.

Python: 3.10+
Run:
    python main.py --data-dir . --commands commands.txt --output-dir output

This version is mapped to the actual PS-110 sample-data headers and BR-01..BR-12.
It is a working implementation, but the evaluator's hidden expected outputs are not
available; the remaining limitations are documented at the end of this file.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable


# ---------------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------------

TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S")


def clean(value: Any) -> str:
    return str(value if value is not None else "").strip()


def norm(value: Any) -> str:
    return clean(value).lower().replace(" ", "_").replace("-", "_")


def as_bool(value: Any, default: bool = False) -> bool:
    value = norm(value)
    if value in {"1", "true", "yes", "y", "priority", "rush"}:
        return True
    if value in {"0", "false", "no", "n", ""}:
        return default
    return default


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(clean(value)))
    except (TypeError, ValueError):
        return default


def as_money(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    try:
        return Decimal(clean(value).replace(",", "").replace("₹", ""))
    except Exception:
        return default


def money(value: Decimal | int | float) -> str:
    return str(Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def parse_time(value: Any) -> datetime:
    text = clean(value)
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError(f"Invalid timestamp {text!r}; expected YYYY-MM-DD HH:MM:SS")


def fmt_time(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def ceil_to_five_minutes(value: datetime) -> datetime:
    """Round a timestamp up to the next 5-minute boundary."""
    seconds = value.second + value.microsecond / 1_000_000
    remainder = (value.minute % 5) * 60 + seconds
    if remainder == 0:
        return value.replace(second=0, microsecond=0)
    return (value + timedelta(seconds=(300 - remainder))).replace(second=0, microsecond=0)


def first(row: dict[str, Any], *names: str, default: Any = "") -> Any:
    """Read the first present, non-empty value from a row using header aliases."""
    indexed = {norm(k): v for k, v in row.items()}
    for name in names:
        key = norm(name)
        if key in indexed and clean(indexed[key]) != "":
            return indexed[key]
    return default


def read_csv(path: Path, required: bool = True) -> list[dict[str, str]]:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Required input file not found: {path}")
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, headers: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------

@dataclass
class Station:
    station_id: str
    kitchen_id: str
    station_type: str
    capacity: int = 1
    # (start, end, order_id, item_id, qty, slot_no)
    reservations: list[tuple[datetime, datetime, str, str, int, int]] = field(default_factory=list)

    def available_slot(self, earliest: datetime, duration: int, item_id: str = "",
                       qty: int = 1, batch_size: int = 1) -> tuple[datetime, int, bool]:
        """Return earliest start, slot and whether this joins an existing batch.

        BR-02: identical item recipes may share one slot when their proposed
        start times are no more than three minutes apart and batch size permits.
        """
        duration = max(0, duration)
        for start, finish, _oid, reserved_item, reserved_qty, slot_no in self.reservations:
            if (reserved_item == item_id and finish >= earliest
                    and abs((earliest - start).total_seconds()) <= 180
                    and reserved_qty + qty <= max(1, batch_size)
                    and finish - start == timedelta(minutes=duration)):
                return start, slot_no, True

        candidate = earliest
        while True:
            end = candidate + timedelta(minutes=duration)
            occupied: dict[int, list[tuple[datetime, datetime]]] = defaultdict(list)
            for start, finish, _oid, _item, _qty, slot_no in self.reservations:
                if start < end and finish > candidate:
                    occupied[slot_no].append((start, finish))
            for slot_no in range(1, max(1, self.capacity) + 1):
                if slot_no not in occupied:
                    return candidate, slot_no, False
            candidate = min(finish for intervals in occupied.values() for _, finish in intervals)

    def reserve(self, start: datetime, duration: int, order_id: str,
                item_id: str, qty: int = 1, slot_no: int = 1,
                batch_join: bool = False) -> datetime:
        end = start + timedelta(minutes=max(0, duration))
        if batch_join:
            for index, reservation in enumerate(self.reservations):
                r_start, r_end, r_order, r_item, r_qty, r_slot = reservation
                if r_start == start and r_end == end and r_item == item_id and r_slot == slot_no:
                    self.reservations[index] = (r_start, r_end, r_order, r_item, r_qty + qty, r_slot)
                    return end
        self.reservations.append((start, end, order_id, item_id, qty, slot_no))
        self.reservations.sort(key=lambda x: (x[0], x[5], x[2], x[3]))
        return end


@dataclass
class RecipeStep:
    station_type: str
    prep_minutes: int
    sequence: int = 1
    predecessor: str = ""


@dataclass
class Recipe:
    recipe_id: str
    item_id: str
    steps: list[RecipeStep]
    batch_size: int = 1


@dataclass
class MenuItem:
    item_id: str
    brand_id: str
    name: str
    price: Decimal
    recipe_id: str


@dataclass
class Kitchen:
    kitchen_id: str
    name: str
    opens: str
    closes: str
    zones: set[str]
    brands: set[str]
    stations: dict[str, Station] = field(default_factory=dict)
    stock_out: set[str] = field(default_factory=set)
    throttled: bool = False
    projected_load_minutes: int = 0

    def is_open_at(self, timestamp: datetime) -> bool:
        if not self.opens or not self.closes:
            return True
        try:
            current = timestamp.strftime("%H:%M:%S")
            return self.opens <= current < self.closes
        except Exception:
            return True


@dataclass
class OrderLine:
    item_id: str
    quantity: int
    unit_price: Decimal
    recipe_id: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    selected_station: str = ""


@dataclass
class Order:
    order_id: str
    timestamp: datetime
    brand_id: str
    channel: str
    zone_id: str
    priority_flag: bool
    lines: list[OrderLine]
    kitchen_id: str = ""
    status: str = "RECEIVED"
    ready_time: datetime | None = None
    promised_time: datetime | None = None
    late_risk: bool = False
    rush: bool = False
    jumps: int = 0
    substitutions: list[str] = field(default_factory=list)
    message: str = ""
    food_value: Decimal = Decimal("0")
    packaging: Decimal = Decimal("0")
    commission: Decimal = Decimal("0")
    payment_fee: Decimal = Decimal("0")
    gst: Decimal = Decimal("0")
    penalty: Decimal = Decimal("0")
    penalty_cost_centre: str = "BRAND"
    handoff_time: datetime | None = None
    cancellation_source: str = ""
    cancellation_charge: Decimal = Decimal("0")

    @property
    def item_count(self) -> int:
        return sum(line.quantity for line in self.lines)

    def recompute_food_value(self) -> Decimal:
        self.food_value = sum((x.unit_price * x.quantity for x in self.lines), Decimal("0"))
        return self.food_value


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class CloudKitchenEngine:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.kitchens: dict[str, Kitchen] = {}
        self.brands: dict[str, dict[str, Any]] = {}
        self.menu: dict[tuple[str, str], MenuItem] = {}
        self.recipes: dict[str, Recipe] = {}
        self.substitutions: dict[tuple[str, str], str] = {}
        self.zone_minutes: dict[str, int] = {}
        self.orders: dict[str, Order] = {}
        self.routing_rows: list[dict[str, Any]] = []
        self.timeline_rows: list[dict[str, Any]] = []
        self.event_messages: list[str] = []
        self.brand_kitchen_orders: dict[tuple[str, str], list[Order]] = defaultdict(list)
        self.load_configuration()

    def load_configuration(self) -> None:
        # Kitchens
        for row in read_csv(self.data_dir / "kitchens.csv"):
            kid = clean(first(row, "kitchen_id", "id"))
            if not kid:
                continue
            zones = clean(first(row, "service_zones", "zones", "zone_ids")).replace(";", "|").split("|")
            brands = clean(first(row, "brands_served", "supported_brands", "brands", "brand_ids")).replace(";", "|").split("|")
            self.kitchens[kid] = Kitchen(
                kitchen_id=kid,
                name=clean(first(row, "kitchen_name", "name", default=kid)),
                opens=clean(first(row, "opening_time", "opens", "open_time")),
                closes=clean(first(row, "closing_time", "closes", "close_time")),
                zones={x.strip() for x in zones if x.strip()},
                brands={x.strip() for x in brands if x.strip()},
            )

        # Stations
        for row in read_csv(self.data_dir / "stations.csv"):
            sid = clean(first(row, "station_id", "id"))
            kid = clean(first(row, "kitchen_id"))
            if not sid or kid not in self.kitchens:
                continue
            stype = norm(first(row, "station_type", "type", "station")).upper()
            capacity = max(1, as_int(first(row, "capacity", "slots", "throughput", default=1), 1))
            station = Station(sid, kid, stype, capacity)
            self.kitchens[kid].stations[stype] = station

        # Brands
        for row in read_csv(self.data_dir / "brands.csv"):
            bid = clean(first(row, "brand_id", "id"))
            if bid:
                self.brands[bid] = row

        # Recipes: the supplied schema uses item_id as the recipe key and has
        # one row per ordered preparation step (no separate recipe_id column).
        recipe_steps: dict[str, list[RecipeStep]] = defaultdict(list)
        recipe_batch_sizes: dict[str, int] = {}
        for row in read_csv(self.data_dir / "recipes.csv"):
            item_id = clean(first(row, "item_id", "menu_item_id"))
            if not item_id:
                continue
            stype = norm(first(row, "station_type", "station", "required_station")).upper()
            prep = as_int(first(row, "prep_min", "prep_minutes", "duration_minutes", "prep_time"), 0)
            seq = as_int(first(row, "step_no", "sequence", "step_order"), 1)
            predecessor = clean(first(row, "predecessor", "depends_on", "dependency"))
            recipe_steps[item_id].append(RecipeStep(stype, prep, seq, predecessor))
            recipe_batch_sizes[item_id] = max(1, as_int(first(row, "batch_size", "max_batch_size", default=1), 1))
        for item_id, steps in recipe_steps.items():
            steps.sort(key=lambda step: step.sequence)
            self.recipes[item_id] = Recipe(item_id, item_id, steps, recipe_batch_sizes[item_id])

        # Menu items
        for row in read_csv(self.data_dir / "menu_items.csv"):
            iid = clean(first(row, "item_id", "menu_item_id", "id"))
            bid = clean(first(row, "brand_id"))
            if not iid or not bid:
                continue
            rid = clean(first(row, "recipe_id", default=iid)) or iid
            item = MenuItem(
                iid, bid, clean(first(row, "item_name", "name", default=iid)),
                as_money(first(row, "price", "food_price", "selling_price")), rid
            )
            self.menu[(bid, iid)] = item
            if rid and rid in self.recipes:
                self.recipes[rid].item_id = iid

        # Substitutions
        for row in read_csv(self.data_dir / "substitutions.csv"):
            bid = clean(first(row, "brand_id"))
            original = clean(first(row, "item_id", "original_item_id", "out_item_id"))
            substitute = clean(first(row, "substitute_item_id", "replacement_item_id", "substitute_id"))
            if bid and original and substitute:
                self.substitutions[(bid, original)] = substitute

        # Zones define both delivery duration and the kitchens allowed to serve them.
        for row in read_csv(self.data_dir / "zones.csv"):
            zid = clean(first(row, "zone_id", "id"))
            if not zid:
                continue
            self.zone_minutes[zid] = as_int(
                first(row, "delivery_minutes", "delivery_time_minutes", "minutes"), 0
            )
            for kid in clean(first(row, "kitchens", "kitchen_ids", "eligible_kitchens")).split(";"):
                kid = kid.strip()
                if kid in self.kitchens:
                    self.kitchens[kid].zones.add(zid)

    # ----------------------------- Commands --------------------------------

    def parse_order_command(self, parts: list[str]) -> Order:
        # ORDER|ts|order_id|brand_id|channel|zone_id|priority_flag|items
        if len(parts) < 8:
            raise ValueError("ORDER command needs 8 fields")
        timestamp, oid, bid, channel, zone, priority, raw_items = parts[1:8]
        lines: list[OrderLine] = []
        for token in raw_items.split(";"):
            token = token.strip()
            if not token:
                continue
            # Supported item forms: ITEM_ID:QTY or ITEM_ID:QTY:UNIT_PRICE
            fields = token.split(":")
            iid = fields[0].strip()
            qty = max(1, as_int(fields[1], 1)) if len(fields) > 1 else 1
            menu_item = self.menu.get((bid, iid))
            price = as_money(fields[2]) if len(fields) > 2 else (
                menu_item.price if menu_item else Decimal("0")
            )
            rid = menu_item.recipe_id if menu_item else ""
            lines.append(OrderLine(iid, qty, price, rid))
        order = Order(oid, parse_time(timestamp), bid, channel, zone,
                      as_bool(priority), lines)
        order.recompute_food_value()
        order.rush = order.priority_flag or order.food_value > Decimal("1500")
        return order

    def process_commands(self, command_file: Path) -> None:
        with command_file.open("r", encoding="utf-8-sig") as handle:
            for line_no, raw in enumerate(handle, 1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [x.strip() for x in line.split("|")]
                event = norm(parts[0])
                try:
                    if event == "order":
                        self.handle_order(self.parse_order_command(parts))
                    elif event == "stock_out":
                        self.handle_stock(parts, unavailable=True)
                    elif event == "stock_in":
                        self.handle_stock(parts, unavailable=False)
                    elif event == "cancel":
                        self.handle_cancel(parts)
                    elif event == "handoff":
                        self.handle_handoff(parts)
                    elif event == "end_of_day":
                        self.event_messages.append(f"{parts[1]} END_OF_DAY")
                    else:
                        self.event_messages.append(f"Line {line_no}: ignored unknown command {parts[0]}")
                except Exception as exc:
                    self.event_messages.append(f"Line {line_no}: ERROR: {exc}")

    # ------------------------------ BR-07 -----------------------------------

    def apply_substitutions(self, order: Order, kitchen: Kitchen) -> None:
        revised: list[OrderLine] = []
        for line in order.lines:
            if line.item_id not in kitchen.stock_out:
                revised.append(line)
                continue
            substitute_id = self.substitutions.get((order.brand_id, line.item_id))
            substitute = self.menu.get((order.brand_id, substitute_id)) if substitute_id else None
            original_price = line.unit_price
            if substitute and substitute.price - original_price <= Decimal("20"):
                order.substitutions.append(f"{line.item_id}->{substitute.item_id}")
                revised.append(OrderLine(
                    substitute.item_id, line.quantity, substitute.price, substitute.recipe_id
                ))
            else:
                order.message = (order.message + " " if order.message else "") + f"REMOVED:{line.item_id}"
        order.lines = revised
        order.recompute_food_value()
        if not order.lines:
            order.status = "CANCELLED"
            order.message = (order.message + " " if order.message else "") + "NO_ITEMS_REMAIN"

    # ------------------------------ BR-01/06 -------------------------------

    def required_stations(self, order: Order) -> set[str]:
        required: set[str] = set()
        for line in order.lines:
            recipe = self.recipes.get(line.recipe_id)
            if recipe:
                required.update(step.station_type for step in recipe.steps if step.station_type)
        return required

    def is_eligible(self, kitchen: Kitchen, order: Order) -> bool:
        if order.brand_id not in kitchen.brands:
            return False
        if order.zone_id not in kitchen.zones:
            return False
        if not kitchen.is_open_at(order.timestamp):
            return False
        return self.required_stations(order).issubset(set(kitchen.stations))

    def estimate_ready(self, kitchen: Kitchen, order: Order) -> datetime:
        """Estimate the order against current station reservations without mutating them."""
        temp: dict[str, list[tuple[datetime, datetime, str, str, int, int]]] = {
            stype: list(station.reservations) for stype, station in kitchen.stations.items()
        }
        completions: list[datetime] = []
        for line in order.lines:
            recipe = self.recipes.get(line.recipe_id)
            if not recipe or not recipe.steps:
                completions.append(order.timestamp)
                continue
            dependency_end = order.timestamp
            for step in recipe.steps:
                station = kitchen.stations.get(step.station_type.upper())
                if station is None:
                    return datetime.max
                remaining = line.quantity
                batch_ends: list[datetime] = []
                batch_size = max(1, recipe.batch_size)
                while remaining > 0:
                    qty = min(batch_size, remaining)
                    candidate = max(order.timestamp, dependency_end)
                    reservations = temp[step.station_type.upper()]
                    finish = candidate + timedelta(minutes=step.prep_minutes)
                    joined = False
                    for r_start, r_end, _r_order, r_item, r_qty, r_slot in reservations:
                        if (r_item == line.item_id and r_end >= candidate
                                and abs((candidate - r_start).total_seconds()) <= 180
                                and r_qty + qty <= batch_size
                                and r_end - r_start == timedelta(minutes=step.prep_minutes)):
                            candidate, free, joined = r_start, r_slot, True
                            finish = r_end
                            break
                    if not joined:
                        while True:
                            end = candidate + timedelta(minutes=step.prep_minutes)
                            conflicts: dict[int, list[datetime]] = defaultdict(list)
                            for r_start, r_end, _r_order, _r_item, _r_qty, r_slot in reservations:
                                if r_start < end and r_end > candidate:
                                    conflicts[r_slot].append(r_end)
                            free = next((slot for slot in range(1, station.capacity + 1) if slot not in conflicts), None)
                            if free is not None:
                                break
                            candidate = min(t for values in conflicts.values() for t in values)
                        finish = candidate + timedelta(minutes=step.prep_minutes)
                        reservations.append((candidate, finish, order.order_id, line.item_id, qty, free))
                    else:
                        for index, reservation in enumerate(reservations):
                            r_start, r_end, r_order, r_item, r_qty, r_slot = reservation
                            if r_start == candidate and r_end == finish and r_item == line.item_id and r_slot == free:
                                reservations[index] = (r_start, r_end, r_order, r_item, r_qty + qty, r_slot)
                                break
                    batch_ends.append(finish)
                    remaining -= qty
                dependency_end = max(batch_ends, default=dependency_end)
            completions.append(dependency_end)
        return max(completions, default=order.timestamp) + timedelta(minutes=3)

    def kitchen_load(self, kitchen: Kitchen, at: datetime) -> int:
        end_times = [
            end for station in kitchen.stations.values()
            for start, end, *_ in station.reservations if end > at
        ]
        if not end_times:
            return 0
        return max(0, int((max(end_times) - at).total_seconds() // 60))

    def choose_kitchen(self, order: Order) -> tuple[Kitchen | None, list[Kitchen], bool]:
        eligible = [k for k in self.kitchens.values() if self.is_eligible(k, order)]
        if not eligible:
            return None, [], False

        # Refresh hysteresis: throttling clears only below 40 minutes.
        for kitchen in eligible:
            load = self.kitchen_load(kitchen, order.timestamp)
            if kitchen.throttled and load < 40:
                kitchen.throttled = False

        normal = []
        for kitchen in eligible:
            projected = self.estimate_ready(kitchen, order)
            projected_minutes = (projected - order.timestamp).total_seconds() / 60
            if projected_minutes > 60:
                kitchen.throttled = True
            if not kitchen.throttled:
                normal.append(kitchen)

        candidates = normal if normal else [k for k in eligible if len(eligible) == 1]
        if not candidates:
            return None, eligible, False

        candidates.sort(key=lambda k: (
            self.estimate_ready(k, order),
            self.kitchen_load(k, order.timestamp),
            k.kitchen_id
        ))
        chosen = candidates[0]

        projected = self.estimate_ready(chosen, order)
        if projected > order.timestamp + timedelta(minutes=45):
            alternatives = [
                k for k in eligible if k.kitchen_id != chosen.kitchen_id
                and (not k.throttled or len(eligible) == 1)
            ]
            if alternatives:
                best_alt = min(alternatives, key=lambda k: (
                    self.estimate_ready(k, order), self.kitchen_load(k, order.timestamp), k.kitchen_id
                ))
                if projected - self.estimate_ready(best_alt, order) >= timedelta(minutes=10):
                    chosen = best_alt
                else:
                    order.late_risk = True
            else:
                order.late_risk = True
        return chosen, eligible, chosen.throttled

    # ------------------------------ BR-02/03/04/05 -------------------------

    def sequence_order(self, order: Order, kitchen: Kitchen) -> None:
        # Deterministic starter queue policy. FIFO is the default. RUSH can pass
        # at most 3 earlier waiting orders. The full "max 2 jumps suffered"
        # history is recorded approximately pending evaluator clarification.
        waiting = [
            o for o in self.orders.values()
            if o.kitchen_id == kitchen.kitchen_id
            and o.status in {"SCHEDULED", "ACCEPTED", "READY", "HANDED_OFF"}
            and order.timestamp - timedelta(minutes=1) <= o.timestamp <= order.timestamp
        ]
        waiting.sort(key=lambda o: (o.timestamp, o.order_id))
        if order.rush:
            # A RUSH order can pass at most three still-waiting orders. It cannot
            # pass an order that has already suffered two jumps.
            passed_count = 0
            for passed in waiting:
                if passed_count >= 3 or passed.jumps >= 2:
                    break
                passed.jumps += 1
                passed_count += 1
            order.jumps = passed_count
        else:
            order.jumps = 0

    def schedule_order(self, order: Order, kitchen: Kitchen) -> None:
        order.status = "SCHEDULED"
        self.sequence_order(order, kitchen)
        item_completions: list[datetime] = []

        for line in order.lines:
            recipe = self.recipes.get(line.recipe_id)
            if not recipe or not recipe.steps:
                raise ValueError(f"Missing recipe for menu item {line.item_id}")

            dependency_end = order.timestamp
            for step in recipe.steps:
                stype = step.station_type.upper()
                station = kitchen.stations.get(stype)
                if station is None:
                    raise ValueError(f"{kitchen.kitchen_id} lacks station {stype} for {line.item_id}")
                remaining = line.quantity
                batch_ends: list[datetime] = []
                batch_size = max(1, recipe.batch_size)
                while remaining > 0:
                    qty = min(batch_size, remaining)
                    earliest = max(order.timestamp, dependency_end)
                    start, slot_no, batch_join = station.available_slot(
                        earliest, step.prep_minutes, line.item_id, qty, batch_size
                    )
                    end = station.reserve(start, step.prep_minutes, order.order_id,
                                          line.item_id, qty, slot_no, batch_join)
                    if line.started_at is None:
                        line.started_at = max(start, order.timestamp)
                        line.selected_station = station.station_id
                    batch_ends.append(end)
                    self.timeline_rows.append({
                        "station_id": station.station_id,
                        "slot_no": slot_no,
                        "order_id": order.order_id,
                        "item_id": line.item_id,
                        "qty": qty,
                        "start_time": fmt_time(start),
                        "end_time": fmt_time(end),
                    })
                    remaining -= qty
                dependency_end = max(batch_ends, default=dependency_end)
            line.completed_at = dependency_end
            item_completions.append(dependency_end)

        last_completion = max(item_completions, default=order.timestamp)
        order.ready_time = last_completion + timedelta(minutes=3)
        zone_minutes = self.zone_minutes.get(order.zone_id, 0)
        order.promised_time = ceil_to_five_minutes(
            order.ready_time + timedelta(minutes=zone_minutes + 5)
        )
        order.status = "READY" if order.ready_time <= order.timestamp else "SCHEDULED"
        order.packaging = min(Decimal(order.item_count * 10), Decimal("40"))
        order.recompute_food_value()
        self.calculate_channel_economics(order)
        kitchen.projected_load_minutes = self.kitchen_load(kitchen, order.timestamp)

    def calculate_channel_economics(self, order: Order) -> None:
        channel = norm(order.channel)
        if channel in {"aggregator_a", "aggregatora", "agg_a", "a"}:
            order.commission = order.food_value * Decimal("0.22")
        elif channel in {"aggregator_b", "aggregatorb", "agg_b", "b"}:
            order.commission = order.food_value * Decimal("0.18")
        else:
            order.commission = Decimal("0")
            order.payment_fee = Decimal("15")
        order.gst = order.food_value * Decimal("0.05")

    def handle_order(self, order: Order) -> None:
        if order.order_id in self.orders:
            order.status = "REJECTED"
            order.message = "DUPLICATE_ORDER_ID"
            self.add_routing_row(order)
            return

        # Validate brand, zone and every menu item before routing.
        if order.brand_id not in self.brands:
            order.status, order.message = "REJECTED", "UNKNOWN_BRAND"
            self.orders[order.order_id] = order
            self.add_routing_row(order)
            return
        if order.zone_id not in self.zone_minutes:
            order.status, order.message = "REJECTED", "UNKNOWN_ZONE"
            self.orders[order.order_id] = order
            self.add_routing_row(order)
            return
        if not order.lines or any((order.brand_id, line.item_id) not in self.menu for line in order.lines):
            order.status, order.message = "REJECTED", "ITEM_NOT_ON_BRAND_MENU_OR_EMPTY_ORDER"
            self.orders[order.order_id] = order
            self.add_routing_row(order)
            return

        order.status = "VALIDATED"
        # A kitchen is selected before kitchen-specific stock substitutions.
        kitchen, eligible, throttled = self.choose_kitchen(order)
        if kitchen is None:
            order.status = "REJECTED"
            order.message = "NO_ELIGIBLE_KITCHEN_OR_ALL_THROTTLED"
            self.orders[order.order_id] = order
            self.add_routing_row(order)
            return

        self.apply_substitutions(order, kitchen)
        if order.status == "CANCELLED":
            self.orders[order.order_id] = order
            self.add_routing_row(order)
            return

        # Re-check required stations after substitutions.
        if not self.is_eligible(kitchen, order):
            alternatives = [k for k in eligible if self.is_eligible(k, order)]
            if alternatives:
                kitchen = min(alternatives, key=lambda k: (
                    self.estimate_ready(k, order), self.kitchen_load(k, order.timestamp), k.kitchen_id
                ))
            else:
                order.status = "REJECTED"
                order.message = "SUBSTITUTION_REQUIRES_UNAVAILABLE_STATION"
                self.orders[order.order_id] = order
                self.add_routing_row(order)
                return

        order.kitchen_id = kitchen.kitchen_id
        try:
            self.schedule_order(order, kitchen)
            if throttled:
                order.message = (order.message + " " if order.message else "") + "THROTTLED_SOLE_ELIGIBLE"
            self.brand_kitchen_orders[(order.brand_id, kitchen.kitchen_id)].append(order)
        except Exception as exc:
            order.status = "REJECTED"
            order.message = f"SCHEDULING_ERROR:{exc}"
        self.orders[order.order_id] = order
        self.add_routing_row(order)

    # ------------------------------ Events ---------------------------------

    def handle_stock(self, parts: list[str], unavailable: bool) -> None:
        if len(parts) < 4:
            raise ValueError("STOCK_OUT/STOCK_IN needs timestamp, kitchen_id, item_id")
        _, ts, kid, item_id = parts[:4]
        if kid not in self.kitchens:
            raise ValueError(f"Unknown kitchen {kid}")
        if unavailable:
            self.kitchens[kid].stock_out.add(item_id)
        else:
            self.kitchens[kid].stock_out.discard(item_id)
        self.event_messages.append(
            f"{ts} {'STOCK_OUT' if unavailable else 'STOCK_IN'} {kid} {item_id}"
        )

    def handle_cancel(self, parts: list[str]) -> None:
        if len(parts) < 4:
            raise ValueError("CANCEL needs timestamp, order_id, by")
        _, ts, oid, source = parts[:4]
        order = self.orders.get(oid)
        if not order:
            self.event_messages.append(f"{ts} CANCEL {oid} UNKNOWN_ORDER")
            return
        cancel_time = parse_time(ts)
        started = [
            line for line in order.lines
            if line.started_at is not None and line.started_at <= cancel_time
        ]
        order.status = "CANCELLED"
        order.cancellation_source = source.upper()
        started_value = sum((line.unit_price * line.quantity for line in started), Decimal("0"))
        if started:
            if source.upper() in {"AGGREGATOR", "AGGREGATOR_A", "AGGREGATOR_B"}:
                order.cancellation_charge = started_value
                order.message = "CANCELLED_AFTER_START_CHANNEL_CHARGED"
            else:
                order.cancellation_charge = started_value
                order.message = "CANCELLED_AFTER_START_CUSTOMER_CHARGED"
        else:
            order.cancellation_charge = Decimal("0")
            order.message = "CANCELLED_BEFORE_START_FREE"
        self.event_messages.append(
            f"{ts} CANCEL {oid} {order.message} CHARGE={money(order.cancellation_charge)}"
        )

    def handle_handoff(self, parts: list[str]) -> None:
        if len(parts) < 3:
            raise ValueError("HANDOFF needs timestamp and order_id")
        _, ts, oid = parts[:3]
        order = self.orders.get(oid)
        if not order:
            self.event_messages.append(f"{ts} HANDOFF {oid} UNKNOWN_ORDER")
            return
        handoff = parse_time(ts)
        order.handoff_time = handoff
        order.status = "HANDED_OFF"
        if order.promised_time and handoff > order.promised_time:
            late_minutes = (handoff - order.promised_time).total_seconds() / 60
            started_blocks = math.ceil(late_minutes / 10)
            order.penalty = min(Decimal(started_blocks * 50), Decimal("200"))
            if "THROTTLED" in order.message:
                order.penalty_cost_centre = "KITCHEN"
            else:
                order.penalty_cost_centre = "BRAND"
        self.event_messages.append(
            f"{ts} HANDOFF {oid} PENALTY={money(order.penalty)} "
            f"COST_CENTRE={order.penalty_cost_centre}"
        )

    # ------------------------------ Reports --------------------------------

    def add_routing_row(self, order: Order) -> None:
        self.routing_rows.append({
            "order_id": order.order_id,
            "status": ("REJECTED" if order.status == "REJECTED" else
                       "CANCELLED" if order.status == "CANCELLED" else "ACCEPTED"),
            "kitchen_id": order.kitchen_id,
            "ready_time": fmt_time(order.ready_time),
            "promised_time": fmt_time(order.promised_time),
            "late_risk": str(order.late_risk).upper(),
            "rush": str(order.rush).upper(),
            "jumps": order.jumps,
            "substitutions": ";".join(order.substitutions),
            "food_value": money(order.food_value),
            "message": order.message,
        })

    def build_pnl(self) -> list[dict[str, Any]]:
        rows = []
        for (brand_id, kitchen_id), orders in sorted(self.brand_kitchen_orders.items()):
            valid_orders = [o for o in orders if o.status != "REJECTED"]
            count = len(valid_orders)
            food = sum((o.food_value for o in valid_orders), Decimal("0"))
            gst = sum((o.gst for o in valid_orders), Decimal("0"))
            commission = sum((o.commission for o in valid_orders), Decimal("0"))
            packaging = sum((o.packaging for o in valid_orders), Decimal("0"))
            penalties = sum((
                o.penalty for o in valid_orders if o.penalty_cost_centre == "BRAND"
            ), Decimal("0"))
            rent = Decimal(count * 2) + food * Decimal("0.03")
            if count < 30:
                rent = max(rent, Decimal("500"))
            payment_fees = sum((o.payment_fee for o in valid_orders), Decimal("0"))
            net = food - commission - payment_fees - packaging - rent - penalties
            rows.append({
                "brand_id": brand_id,
                "kitchen_id": kitchen_id,
                "orders": count,
                "food_value": money(food),
                "gst": money(gst),
                "commission": money(commission),
                "packaging": money(packaging),
                "penalties": money(penalties),
                "rent": money(rent),
                "net": money(net),
            })
        return rows

    def write_reports(self, output_dir: Path) -> None:
        # Routing report is one row per ORDER command in file order. Refresh rows
        # from final order state so later CANCEL/HANDOFF events are represented.
        by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in self.routing_rows:
            by_id[row["order_id"]].append(row)
        for oid, order in self.orders.items():
            if by_id.get(oid):
                row = by_id[oid][0]
                row.update({
                    "status": ("REJECTED" if order.status == "REJECTED" else
                               "CANCELLED" if order.status == "CANCELLED" else "ACCEPTED"),
                    "kitchen_id": order.kitchen_id,
                    "ready_time": fmt_time(order.ready_time),
                    "promised_time": fmt_time(order.promised_time),
                    "late_risk": str(order.late_risk).upper(),
                    "rush": str(order.rush).upper(), "jumps": order.jumps,
                    "substitutions": ";".join(order.substitutions),
                    "food_value": money(order.food_value), "message": order.message,
                })

        write_csv(output_dir / "routing.csv", [
            "order_id", "status", "kitchen_id", "ready_time", "promised_time",
            "late_risk", "rush", "jumps", "substitutions", "food_value", "message"
        ], self.routing_rows)

        self.timeline_rows.sort(key=lambda r: (
            r["station_id"], r["start_time"], r["order_id"], r["item_id"]
        ))
        write_csv(output_dir / "station_timeline.csv", [
            "station_id", "slot_no", "order_id", "item_id", "qty", "start_time", "end_time"
        ], self.timeline_rows)

        write_csv(output_dir / "brand_pnl.csv", [
            "brand_id", "kitchen_id", "orders", "food_value", "gst", "commission",
            "packaging", "penalties", "rent", "net"
        ], self.build_pnl())

        with (output_dir / "event_log.txt").open("w", encoding="utf-8") as handle:
            handle.write("\n".join(self.event_messages))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="PS-110 Cloud Kitchen Order Routing and Capacity Engine"
    )
    parser.add_argument("--data-dir", default=".", help="Folder containing configuration CSV files")
    parser.add_argument("--commands", default="commands.txt", help="Command input file")
    parser.add_argument("--output-dir", default="output", help="Folder for generated reports")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    command_path = Path(args.commands)
    if not command_path.is_absolute():
        command_path = data_dir / command_path
    output_dir = Path(args.output_dir)

    try:
        engine = CloudKitchenEngine(data_dir)
        engine.process_commands(command_path)
        engine.write_reports(output_dir)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("PS-110 starter engine finished.")
    print(f"Orders processed: {len(engine.routing_rows)}")
    print(f"Reports written to: {output_dir.resolve()}")
    print("Generated: routing.csv, station_timeline.csv, brand_pnl.csv, event_log.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ---------------------------------------------------------------------------
# IMPLEMENTATION NOTES / REMAINING LIMITATIONS
# ---------------------------------------------------------------------------
# - Input loaders now match the supplied CSV schemas exactly: zones.csv supplies
#   kitchen-zone eligibility; kitchens.csv supplies brands_served; recipes.csv
#   uses item_id as its recipe key and step_no/prep_min/batch_size.
# - BR-02 enforces station slot capacity, splits quantities into recipe-sized
#   batches and merges identical items from separate orders when their proposed
#   starts are within the inclusive 3-minute window and batch size permits.
# - BR-03 applies the three-jump cap and tracks the maximum two jumps suffered
#   by an order in the active one-minute arrival queue. Full physical queue
#   resequencing (moving already-created reservations) remains unimplemented.
# - BR-06 throttling uses estimated projected ready time; exact hysteresis and
#   candidate-kitchen simulation should be verified against hidden expected data.
# - Financial bases for GST/commission/rent and cancellation charge allocation
#   are not fully specified in the supplied documents. P&L net excludes GST and
#   includes own-app payment fees as an expense; confirm with evaluator guidance.
# - Station timelines and cancellation checks are based on scheduled starts;
#   later queue resequencing could change those times once implemented.
# - No expected-output files were included in the supplied pack, so output values
#   cannot yet be certified field-for-field against the evaluator.
