"""Financial record models representing order economics, brand P&L, and penalties."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from src.models.order import Channel


class CostCentre(str, Enum):
    """Cost centre responsible for penalties."""
    BRAND = "BRAND"
    KITCHEN = "KITCHEN"


@dataclass
class OrderFinancials:
    """Financial breakdown of an individual order (BR-09, BR-10)."""
    order_id: str
    channel: Channel
    gross_food_value: float
    commission_rate: float
    commission_amount: float
    fixed_fee: float
    item_count: int
    packaging_fee: float
    gst_amount: float
    customer_total: float
    net_food_value: float
    brand_earnings: float
    late_penalty: float = 0.0
    penalty_cost_centre: CostCentre = CostCentre.BRAND
    cancellation_charge: float = 0.0


@dataclass
class BrandDailyPnL:
    """End-of-day P&L and kitchen lease settlement per brand per kitchen (BR-11)."""
    brand_id: str
    kitchen_id: str
    order_count: int
    gross_food_sales: float
    platform_commissions: float
    fixed_fees: float
    net_food_sales: float
    packaging_revenue: float
    gst_collected: float
    rent_orders_component: float  # Rs. 2 per order
    rent_percentage_component: float  # 3% of net food value
    raw_calculated_rent: float
    minimum_rent_applied: bool
    final_kitchen_rent: float
    penalties_absorbed: float = 0.0
    brand_net_profit: float = 0.0


@dataclass
class KitchenDailyReport:
    """Daily operational and financial performance report for a physical kitchen."""
    kitchen_id: str
    total_orders_handled: int
    total_revenue_rent: float
    minimum_rent_count: int
    penalties_charged: float
    net_kitchen_income: float
    total_operating_minutes: float


@dataclass
class ChannelReport:
    """Performance and commission summary by ordering platform."""
    channel: Channel
    order_count: int
    total_gross_value: float
    total_commissions_earned: float
    total_fixed_fees_earned: float
    total_gst_processed: float


@dataclass
class FinancialRecord:
    """Comprehensive financial record container combining order, P&L and reconciliation."""
    record_id: str
    order_financials: Optional[OrderFinancials] = None
    brand_pnl: Optional[BrandDailyPnL] = None
