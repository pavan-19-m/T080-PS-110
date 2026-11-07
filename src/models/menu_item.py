"""MenuItem model linking brand products to pricing and recipes."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MenuItem:
    """Catalog item belonging to a brand with price and recipe linkage."""
    item_id: str
    brand_id: str
    name: str
    price: float
    recipe_id: str

    def __post_init__(self):
        if self.price < 0:
            raise ValueError(f"price cannot be negative, got {self.price}")
        if not self.item_id:
            raise ValueError("item_id cannot be empty")
        if not self.brand_id:
            raise ValueError("brand_id cannot be empty")
        if not self.recipe_id:
            raise ValueError("recipe_id cannot be empty")
