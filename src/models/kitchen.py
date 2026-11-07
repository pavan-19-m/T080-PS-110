"""Kitchen domain model representing a physical cloud kitchen facility."""

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Dict, Set

from src.models.station import Station, StationType


@dataclass
class Kitchen:
    """Physical kitchen facility with operating hours, stations, and brand partnerships."""
    kitchen_id: str
    name: str
    open_time: time
    close_time: time
    supported_brands: Set[str] = field(default_factory=set)
    delivery_zones: Set[str] = field(default_factory=set)
    stations: Dict[StationType, Station] = field(default_factory=dict)
    is_throttled: bool = False

    def is_operating_at(self, dt: datetime) -> bool:
        """Check if kitchen is operating at the given datetime."""
        t = dt.time()
        if self.open_time <= self.close_time:
            return self.open_time <= t <= self.close_time
        # Handling overnight shifts (e.g., 20:00 to 02:00)
        return t >= self.open_time or t <= self.close_time

    def supports_brand(self, brand_id: str) -> bool:
        """Check if brand is registered and supported at this kitchen."""
        return brand_id.strip().upper() in {b.strip().upper() for b in self.supported_brands}

    def serves_delivery_zone(self, zone_id: str) -> bool:
        """Check if kitchen is registered to serve the given delivery zone."""
        return zone_id.strip().upper() in {z.strip().upper() for z in self.delivery_zones}

    def has_station(self, station_type: StationType) -> bool:
        """Check if station equipment exists at this kitchen."""
        return station_type in self.stations and self.stations[station_type].capacity > 0

    def has_all_stations(self, station_types: Set[StationType]) -> bool:
        """Check if every required station type exists with positive capacity."""
        return all(self.has_station(st) for st in station_types)

    def get_current_load(self, at_time: datetime) -> float:
        """Calculate total remaining work minutes across all station slots at at_time."""
        return sum(st.get_remaining_load(at_time) for st in self.stations.values())
