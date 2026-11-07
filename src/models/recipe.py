"""Recipe model defining station requirement, prep time, batch limit, and dependency."""

from dataclasses import dataclass
from typing import Optional

from src.models.station import StationType


@dataclass(frozen=True)
class Recipe:
    """Culinary recipe mapping an item to a station, preparation time, and constraints."""
    recipe_id: str
    station_type: StationType
    prep_minutes: int
    max_batch_size: int = 1
    dependency_recipe_id: Optional[str] = None

    def __post_init__(self):
        if self.prep_minutes <= 0:
            raise ValueError(f"prep_minutes must be > 0, got {self.prep_minutes}")
        if self.max_batch_size <= 0:
            raise ValueError(f"max_batch_size must be > 0, got {self.max_batch_size}")

    @property
    def has_dependency(self) -> bool:
        return bool(self.dependency_recipe_id and self.dependency_recipe_id.strip())
