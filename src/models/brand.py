"""Brand model representing a virtual food brand."""

from dataclasses import dataclass, field
from typing import Dict

from src.models.menu_item import MenuItem


@dataclass
class Brand:
    """Virtual food brand with its menu offerings."""
    brand_id: str
    name: str
    menu_items: Dict[str, MenuItem] = field(default_factory=dict)

    def add_menu_item(self, item: MenuItem) -> None:
        self.menu_items[item.item_id] = item

    def get_menu_item(self, item_id: str) -> MenuItem:
        return self.menu_items[item_id]

    def has_menu_item(self, item_id: str) -> bool:
        return item_id in self.menu_items
