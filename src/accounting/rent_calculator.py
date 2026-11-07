"""Kitchen rent calculator implementing BR-11 brand lease agreements."""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class RentCalculationResult:
    """Detailed result of kitchen rent calculation."""
    order_count: int
    net_food_sales: float
    order_component: float  # Rs. 2 per order
    percentage_component: float  # 3% of net food value
    raw_rent: float
    minimum_rent_applied: bool
    final_rent: float


class RentCalculator:
    """Calculates kitchen rental fees payable by brands (BR-11)."""

    RENT_PER_ORDER: float = 2.0
    RENT_PERCENTAGE_NET_FOOD: float = 0.03
    RENT_MINIMUM_THRESHOLD_ORDERS: int = 30
    RENT_MINIMUM_AMOUNT: float = 500.0

    @classmethod
    def calculate_rent(
        cls,
        order_count: int,
        net_food_sales: float,
        is_assigned_kitchen: bool = True
    ) -> RentCalculationResult:
        """
        BR-11:
        - Brand pays kitchen: Rs. 2 per order + 3% of net food value.
        - If fewer than 30 orders per day are processed (< 30), apply a Rs. 500 minimum rent.
        - Edge Case 8: Exactly 30 brand orders at one kitchen does NOT trigger the minimum.
        """
        order_comp = round(order_count * cls.RENT_PER_ORDER, 2)
        pct_comp = round(net_food_sales * cls.RENT_PERCENTAGE_NET_FOOD, 2)
        raw_rent = round(order_comp + pct_comp, 2)

        minimum_applied = False
        if is_assigned_kitchen and order_count < cls.RENT_MINIMUM_THRESHOLD_ORDERS:
            if raw_rent < cls.RENT_MINIMUM_AMOUNT:
                final_rent = cls.RENT_MINIMUM_AMOUNT
                minimum_applied = True
            else:
                final_rent = raw_rent
        else:
            final_rent = raw_rent

        return RentCalculationResult(
            order_count=order_count,
            net_food_sales=net_food_sales,
            order_component=order_comp,
            percentage_component=pct_comp,
            raw_rent=raw_rent,
            minimum_rent_applied=minimum_applied,
            final_rent=final_rent,
        )
