"""Penalty calculator implementing BR-10 late hand-off penalties."""

import math
from datetime import datetime
from typing import Optional, Tuple
from src.models import CostCentre, Order


class PenaltyCalculator:
    """Calculates late hand-off penalties and assigns responsibility cost centres (BR-10)."""

    PENALTY_PER_10_MIN_BLOCK: float = 50.0
    PENALTY_CAP: float = 200.0

    @classmethod
    def calculate_penalty(
        cls,
        promised_time: Optional[datetime],
        actual_handoff_time: Optional[datetime]
    ) -> float:
        """
        BR-10:
        - Rs. 50 per started 10 minutes late.
        - Maximum penalty Rs. 200.
        Returns float penalty amount.
        """
        if not promised_time or not actual_handoff_time:
            return 0.0

        if actual_handoff_time <= promised_time:
            return 0.0

        delta_seconds = (actual_handoff_time - promised_time).total_seconds()
        lateness_minutes = delta_seconds / 60.0
        blocks = math.ceil(lateness_minutes / 10.0)
        raw_penalty = blocks * cls.PENALTY_PER_10_MIN_BLOCK
        return min(raw_penalty, cls.PENALTY_CAP)

    @classmethod
    def calculate_penalty_with_cost_centre(
        cls,
        promised_time: Optional[datetime],
        actual_handoff_time: Optional[datetime],
        is_throttled_routing: bool = False
    ) -> Tuple[float, CostCentre]:
        """
        BR-10:
        - Rs. 50 per started 10 minutes late, max Rs. 200.
        - Charged to the brand, or to kitchen cost centre if caused by THROTTLED routing.
        Returns: (penalty_amount, cost_centre)
        """
        penalty = cls.calculate_penalty(promised_time, actual_handoff_time)
        cost_centre = CostCentre.KITCHEN if is_throttled_routing else CostCentre.BRAND
        return penalty, cost_centre

    @classmethod
    def apply_penalty_to_order(cls, order: Order, actual_handoff_time: datetime) -> float:
        """Applies BR-10 penalty directly to the given order."""
        order.actual_handoff_time = actual_handoff_time
        penalty, cost_centre = cls.calculate_penalty_with_cost_centre(
            promised_time=order.promised_time,
            actual_handoff_time=actual_handoff_time,
            is_throttled_routing=order.throttled_routing,
        )
        order.late_penalty = penalty
        order.penalty_cost_centre = cost_centre.value
        return penalty
