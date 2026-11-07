"""Accounting engine implementing BR-09 channel economics and BR-11 brand-kitchen rent."""

from dataclasses import dataclass
from typing import Dict, List, Tuple

from src.models import Channel, Order


@dataclass
class OrderFinancials:
    """Financial breakdown of an individual order."""
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
    brand_net_profit: float


class AccountingEngine:
    """Calculates channel commissions, packaging fees, GST (BR-09), and brand rent (BR-11)."""

    PACKAGING_PER_ITEM: float = 10.0
    PACKAGING_CAP: float = 40.0
    GST_RATE: float = 0.05

    # BR-11 Parameters
    RENT_PER_ORDER: float = 2.0
    RENT_PERCENTAGE_NET_FOOD: float = 0.03
    RENT_MINIMUM_THRESHOLD_ORDERS: int = 30
    RENT_MINIMUM_AMOUNT: float = 500.0

    # BR-10 Parameters
    PENALTY_PER_10_MIN_BLOCK: float = 50.0
    PENALTY_CAP: float = 200.0

    @classmethod
    def calculate_late_penalty(
        cls,
        promised_time: datetime,
        actual_handoff_time: datetime
    ) -> float:
        """
        BR-10:
        If hand-off occurs later than promised time, charge Rs. 50 per started
        10 minutes of lateness, capped at Rs. 200.
        1 to 10 min = Rs. 50; 11 to 20 min = Rs. 100; 21 to 30 min = Rs. 150; 31+ min = Rs. 200.
        """
        if actual_handoff_time <= promised_time:
            return 0.0
        delta_seconds = (actual_handoff_time - promised_time).total_seconds()
        import math
        lateness_minutes = delta_seconds / 60.0
        blocks = math.ceil(lateness_minutes / 10.0)
        raw_penalty = blocks * cls.PENALTY_PER_10_MIN_BLOCK
        return min(raw_penalty, cls.PENALTY_CAP)

    @classmethod
    def calculate_order_financials(cls, order: Order) -> OrderFinancials:
        """
        BR-09:
        - Aggregator A commission: 22%.
        - Aggregator B commission: 18%.
        - Own app commission: 0% plus Rs. 15 payment fee.
        - Packaging: Rs. 10 per item, capped at Rs. 40 per order.
        - GST: 5% on food.
        """
        food_value = order.gross_food_value
        channel = order.channel

        comm_rate = channel.commission_rate
        comm_amount = round(food_value * comm_rate, 2)
        fixed_fee = channel.fixed_fee

        num_items = len(order.items)
        raw_packaging = num_items * cls.PACKAGING_PER_ITEM
        packaging_fee = min(raw_packaging, cls.PACKAGING_CAP)

        gst_amount = round(food_value * cls.GST_RATE, 2)
        customer_total = round(food_value + packaging_fee + gst_amount, 2)
        net_food_value = round(food_value - comm_amount, 2)
        brand_earnings = round(food_value - comm_amount - fixed_fee, 2)

        return OrderFinancials(
            order_id=order.order_id,
            channel=channel,
            gross_food_value=food_value,
            commission_rate=comm_rate,
            commission_amount=comm_amount,
            fixed_fee=fixed_fee,
            item_count=num_items,
            packaging_fee=packaging_fee,
            gst_amount=gst_amount,
            customer_total=customer_total,
            net_food_value=net_food_value,
            brand_earnings=brand_earnings,
        )

    @classmethod
    def calculate_daily_brand_pnl(
        cls,
        order_records: List[Tuple[Order, OrderFinancials]]
    ) -> List[BrandDailyPnL]:
        """
        BR-11:
        Each brand pays the kitchen Rs. 2 per order plus 3% of net food value.
        If a brand has fewer than 30 orders per day at a kitchen (< 30), apply a Rs. 500 minimum.
        Exactly 30 orders does not qualify for the minimum.
        """
        # Group by (brand_id, kitchen_id)
        grouped: Dict[Tuple[str, str], List[Tuple[Order, OrderFinancials]]] = {}
        for order, fin in order_records:
            kitchen_id = order.assigned_kitchen_id or "UNASSIGNED"
            key = (order.brand_id, kitchen_id)
            grouped.setdefault(key, []).append((order, fin))

        pnl_results: List[BrandDailyPnL] = []
        for (brand_id, kitchen_id), records in sorted(grouped.items()):
            order_count = len(records)
            gross_food = sum(f.gross_food_value for _, f in records)
            commissions = sum(f.commission_amount for _, f in records)
            fixed_fees = sum(f.fixed_fee for _, f in records)
            net_food = sum(f.net_food_value for _, f in records)
            pkg_total = sum(f.packaging_fee for _, f in records)
            gst_total = sum(f.gst_amount for _, f in records)

            # BR-11 Rent: Rs. 2 per order + 3% of net food value
            rent_order_comp = round(order_count * cls.RENT_PER_ORDER, 2)
            rent_pct_comp = round(net_food * cls.RENT_PERCENTAGE_NET_FOOD, 2)
            raw_rent = round(rent_order_comp + rent_pct_comp, 2)

            # Minimum check: < 30 orders qualifies for Rs. 500 minimum; exactly 30 does NOT.
            min_applied = False
            if kitchen_id != "UNASSIGNED" and order_count < cls.RENT_MINIMUM_THRESHOLD_ORDERS:
                if raw_rent < cls.RENT_MINIMUM_AMOUNT:
                    final_rent = cls.RENT_MINIMUM_AMOUNT
                    min_applied = True
                else:
                    final_rent = raw_rent
            else:
                final_rent = raw_rent

            brand_net_profit = round(net_food - fixed_fees - final_rent, 2)

            pnl_results.append(
                BrandDailyPnL(
                    brand_id=brand_id,
                    kitchen_id=kitchen_id,
                    order_count=order_count,
                    gross_food_sales=gross_food,
                    platform_commissions=commissions,
                    fixed_fees=fixed_fees,
                    net_food_sales=net_food,
                    packaging_revenue=pkg_total,
                    gst_collected=gst_total,
                    rent_orders_component=rent_order_comp,
                    rent_percentage_component=rent_pct_comp,
                    raw_calculated_rent=raw_rent,
                    minimum_rent_applied=min_applied,
                    final_kitchen_rent=final_rent,
                    brand_net_profit=brand_net_profit,
                )
            )

        return pnl_results
