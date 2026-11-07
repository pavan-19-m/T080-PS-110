"""Accounting engine coordinating BR-09, BR-10, and BR-11 financial calculations."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from src.accounting.penalty_calculator import PenaltyCalculator
from src.accounting.rent_calculator import RentCalculator, RentCalculationResult
from src.models import (
    BrandDailyPnL,
    Channel,
    ChannelReport,
    CostCentre,
    KitchenDailyReport,
    Order,
    OrderFinancials,
)


class AccountingEngine:
    """Coordinates financial calculations: commissions, packaging, GST, penalties, and kitchen rent."""

    PACKAGING_PER_ITEM: float = 10.0
    PACKAGING_CAP: float = 40.0
    GST_RATE: float = 0.05

    # BR-10 late penalty calculator delegate
    calculate_late_penalty = PenaltyCalculator.calculate_penalty

    @classmethod
    def calculate_order_financials(cls, order: Order) -> OrderFinancials:
        """
        BR-09:
        - Aggregator A: 22% commission.
        - Aggregator B: 18% commission.
        - Own app: 0% commission + Rs. 15 payment fee.
        - Packaging: Rs. 10 per item, maximum Rs. 40 per order.
        - GST: 5% on food.
        - Edge Case 7: 5 items = 5 * 10 = Rs. 50, capped at Rs. 40.
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

        cost_centre = CostCentre.KITCHEN if order.penalty_cost_centre == "KITCHEN" else CostCentre.BRAND

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
            late_penalty=order.late_penalty,
            penalty_cost_centre=cost_centre,
            cancellation_charge=order.cancellation_charge,
        )

    @classmethod
    def calculate_daily_brand_pnl(
        cls,
        order_records: List[Tuple[Order, OrderFinancials]]
    ) -> List[BrandDailyPnL]:
        """
        BR-11 & BR-10:
        Calculates daily P&L per brand per kitchen, deducting platform commissions,
        fixed fees, kitchen rent, and late delivery penalties.
        """
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

            # BR-10 Penalties absorbed by brand
            brand_penalties = sum(
                f.late_penalty for _, f in records
                if f.penalty_cost_centre == CostCentre.BRAND
            )

            # BR-11 Rent calculation
            rent_res: RentCalculationResult = RentCalculator.calculate_rent(
                order_count=order_count,
                net_food_sales=net_food,
                is_assigned_kitchen=(kitchen_id != "UNASSIGNED"),
            )

            brand_net_profit = round(
                net_food - fixed_fees - rent_res.final_rent - brand_penalties, 2
            )

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
                    rent_orders_component=rent_res.order_component,
                    rent_percentage_component=rent_res.percentage_component,
                    raw_calculated_rent=rent_res.raw_rent,
                    minimum_rent_applied=rent_res.minimum_rent_applied,
                    final_kitchen_rent=rent_res.final_rent,
                    penalties_absorbed=brand_penalties,
                    brand_net_profit=brand_net_profit,
                )
            )

        return pnl_results

    @classmethod
    def calculate_kitchen_daily_reports(
        cls,
        pnl_records: List[BrandDailyPnL],
        order_records: List[Tuple[Order, OrderFinancials]]
    ) -> List[KitchenDailyReport]:
        """Compiles daily operational performance reports per kitchen facility."""
        kitchen_pnl: Dict[str, List[BrandDailyPnL]] = {}
        for pnl in pnl_records:
            kitchen_pnl.setdefault(pnl.kitchen_id, []).append(pnl)

        reports: List[KitchenDailyReport] = []
        for kitchen_id, pnl_list in sorted(kitchen_pnl.items()):
            total_orders = sum(p.order_count for p in pnl_list)
            total_rent = sum(p.final_kitchen_rent for p in pnl_list)
            min_rent_count = sum(1 for p in pnl_list if p.minimum_rent_applied)

            # Penalties charged to kitchen cost centre
            kitchen_penalties = sum(
                f.late_penalty for order, f in order_records
                if order.assigned_kitchen_id == kitchen_id and f.penalty_cost_centre == CostCentre.KITCHEN
            )

            net_income = round(total_rent - kitchen_penalties, 2)
            reports.append(
                KitchenDailyReport(
                    kitchen_id=kitchen_id,
                    total_orders_handled=total_orders,
                    total_revenue_rent=total_rent,
                    minimum_rent_count=min_rent_count,
                    penalties_charged=kitchen_penalties,
                    net_kitchen_income=net_income,
                    total_operating_minutes=0.0,
                )
            )
        return reports

    @classmethod
    def calculate_channel_reports(
        cls,
        order_records: List[Tuple[Order, OrderFinancials]]
    ) -> List[ChannelReport]:
        """Summarizes platform orders, gross GMV, commissions and fixed fees by channel."""
        grouped: Dict[Channel, List[OrderFinancials]] = {}
        for _, f in order_records:
            grouped.setdefault(f.channel, []).append(f)

        reports: List[ChannelReport] = []
        for channel, fin_list in sorted(grouped.items(), key=lambda x: x[0].value):
            count = len(fin_list)
            gross = sum(f.gross_food_value for f in fin_list)
            comm = sum(f.commission_amount for f in fin_list)
            fees = sum(f.fixed_fee for f in fin_list)
            gst = sum(f.gst_amount for f in fin_list)
            reports.append(
                ChannelReport(
                    channel=channel,
                    order_count=count,
                    total_gross_value=gross,
                    total_commissions_earned=comm,
                    total_fixed_fees_earned=fees,
                    total_gst_processed=gst,
                )
            )
        return reports
