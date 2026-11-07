"""Reporting and export utilities generating clean CLI logs and CSV outputs."""

import csv
from pathlib import Path
from typing import List

from src.accounting.accounting_engine import AccountingEngine, BrandDailyPnL
from src.services.order_service import ProcessedOrderRecord


class ReportGenerator:
    """Prints formatted console summaries and exports CSV audit reports."""

    @classmethod
    def print_terminal_summary(cls, records: List[ProcessedOrderRecord]) -> None:
        """Print comprehensive order matrix, station timeline, and brand P&L report."""
        sep_double = "=" * 115
        sep_single = "-" * 115

        print("\n" + sep_double)
        print("          10 SECONDS CLOUD KITCHEN MULTI-BRAND ORDER ROUTING & CAPACITY ENGINE (PS-110)")
        print("               TEAM T080 | Pavan Neelappa Mirji & Padmavathi B | Section CSD")
        print(sep_double)

        # 1. EXECUTIVE MASTER ORDER TABLE
        print("\n>>> MASTER ORDER ROUTING & FULFILLMENT MATRIX")
        print(sep_single)
        header = f"{'Order ID':<10} {'Brand':<12} {'Channel':<13} {'Kitchen':<8} {'Placed':<9} {'Ready':<9} {'Promised':<9} {'Customer':<10} {'Net Food':<10} {'Status':<10}"
        print(header)
        print(sep_single)

        for rec in records:
            o = rec.order
            f = rec.financials
            placed_str = o.order_time.strftime("%H:%M:%S")
            ready_str = o.projected_ready_time.strftime("%H:%M:%S") if o.projected_ready_time else "N/A"
            prom_str = o.promised_time.strftime("%H:%M:%S") if o.promised_time else "N/A"
            k_id = o.assigned_kitchen_id or "NONE"
            cust_str = f"Rs.{f.customer_total:.2f}"
            net_str = f"Rs.{f.net_food_value:.2f}"
            status_tag = o.status.value
            if o.is_rush:
                status_tag += "*"
            print(f"{o.order_id:<10} {o.brand_id:<12} {o.channel.value:<13} {k_id:<8} {placed_str:<9} {ready_str:<9} {prom_str:<9} {cust_str:<10} {net_str:<10} {status_tag:<10}")

        print(sep_single)
        print("  * indicates RUSH Priority Order")

        # 2. DETAILED ORDER TIMELINES & ALLOCATION
        print("\n>>> DETAILED ORDER DISPATCH & STATION ALLOCATION")
        print(sep_single)

        for rec in records:
            o = rec.order
            r = rec.routing
            f = rec.financials

            rush_tag = " [RUSH PRIORITY]" if o.is_rush else ""
            late_tag = " [LATE_RISK]" if o.late_risk else ""
            throttle_tag = " [THROTTLED_ROUTING]" if o.throttled_routing else ""

            print(f"\nOrder: {o.order_id}{rush_tag}{late_tag}{throttle_tag}")
            print(f"  Brand: {o.brand_id} | Channel: {o.channel.value} | Zone: {o.delivery_zone} | Placed: {o.order_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Selected Kitchen: {r.selected_kitchen_id or 'NONE'} | Routing Logic: {r.routing_reason}")

            if o.projected_ready_time and o.promised_time:
                ready_str = o.projected_ready_time.strftime('%H:%M:%S')
                promised_str = o.promised_time.strftime('%H:%M:%S')
                print(f"  Schedule Timing: Ready = {ready_str} (incl. 3m packaging) | Promised Delivery = {promised_str}")

            print("  Station Timeline & Item Slots:")
            for item in o.items:
                start_str = item.prep_start_time.strftime('%H:%M:%S') if item.prep_start_time else "N/A"
                end_str = item.prep_end_time.strftime('%H:%M:%S') if item.prep_end_time else "N/A"
                batch_str = f"Batch: {item.batch_id}" if item.batch_id else "Solo"
                slot_str = f"Slot #{item.slot_id}" if item.slot_id else "Slot N/A"
                print(f"    - {item.item_id} (Recipe: {item.recipe_id}): {start_str} -> {end_str} [{slot_str}, {batch_str}]")

            print("  Financials (BR-09):")
            print(f"    Food Value: Rs. {f.gross_food_value:.2f} | Commission ({f.commission_rate*100:.0f}%): Rs. {f.commission_amount:.2f} | Fixed Fee: Rs. {f.fixed_fee:.2f}")
            print(f"    Packaging: Rs. {f.packaging_fee:.2f} (cap Rs.40) | GST (5%): Rs. {f.gst_amount:.2f} | Customer Total: Rs. {f.customer_total:.2f}")

        # 3. END-OF-DAY BRAND P&L AND RENT SETTLEMENT (BR-11)
        pnl_records = AccountingEngine.calculate_daily_brand_pnl(
            [(rec.order, rec.financials) for rec in records]
        )

        print("\n" + sep_single)
        print(">>> END-OF-DAY BRAND P&L & KITCHEN RENT SETTLEMENT (BR-11)")
        print(sep_single)
        pnl_header = f"{'Brand ID':<12} {'Kitchen':<8} {'Orders':<8} {'Gross Sales':<12} {'Commissions':<13} {'Net Food':<12} {'Rent (BR-11)':<14} {'Min Fee?':<10} {'Brand Net P&L':<14}"
        print(pnl_header)
        print(sep_single)

        for p in pnl_records:
            min_tag = "YES (Rs.500)" if p.minimum_rent_applied else "NO"
            print(f"{p.brand_id:<12} {p.kitchen_id:<8} {p.order_count:<8} Rs.{p.gross_food_sales:<10.2f} Rs.{p.platform_commissions:<11.2f} Rs.{p.net_food_sales:<10.2f} Rs.{p.final_kitchen_rent:<12.2f} {min_tag:<10} Rs.{p.brand_net_profit:<12.2f}")

        print(sep_single)
        print("  BR-11 Rent Formula: Rs. 2/order + 3% of net food value (Rs. 500 minimum if daily orders < 30).")
        print(sep_double + "\n")

    @classmethod
    def export_csv_reports(cls, records: List[ProcessedOrderRecord], output_dir: Path) -> None:
        """Export CSV reports to output_dir."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Routing Decisions CSV
        routing_file = output_dir / "routing_decisions.csv"
        with open(routing_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "order_id",
                "brand_id",
                "channel",
                "delivery_zone",
                "order_time",
                "selected_kitchen",
                "routing_reason",
                "projected_ready_time",
                "promised_time",
                "is_rush",
                "rush_jumps",
                "delayed_jumps",
                "late_risk",
                "throttled_routing",
                "order_status",
            ])
            for rec in records:
                o = rec.order
                r = rec.routing
                writer.writerow([
                    o.order_id,
                    o.brand_id,
                    o.channel.value,
                    o.delivery_zone,
                    o.order_time.strftime("%Y-%m-%d %H:%M:%S"),
                    r.selected_kitchen_id or "NONE",
                    r.routing_reason,
                    o.projected_ready_time.strftime("%Y-%m-%d %H:%M:%S") if o.projected_ready_time else "",
                    o.promised_time.strftime("%Y-%m-%d %H:%M:%S") if o.promised_time else "",
                    o.is_rush,
                    o.rush_jumps_made,
                    o.delayed_jumps_count,
                    o.late_risk,
                    o.throttled_routing,
                    o.status.value,
                ])

        # 2. Station Timelines CSV
        timeline_file = output_dir / "station_timelines.csv"
        with open(timeline_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "order_id",
                "order_item_id",
                "item_id",
                "recipe_id",
                "kitchen_id",
                "slot_id",
                "batch_id",
                "prep_start_time",
                "prep_end_time",
            ])
            for rec in records:
                o = rec.order
                for it in o.items:
                    writer.writerow([
                        o.order_id,
                        it.order_item_id,
                        it.item_id,
                        it.recipe_id,
                        o.assigned_kitchen_id or "",
                        it.slot_id or "",
                        it.batch_id or "",
                        it.prep_start_time.strftime("%Y-%m-%d %H:%M:%S") if it.prep_start_time else "",
                        it.prep_end_time.strftime("%Y-%m-%d %H:%M:%S") if it.prep_end_time else "",
                    ])

        # 3. Order Financials CSV
        financials_file = output_dir / "order_financials.csv"
        with open(financials_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "order_id",
                "channel",
                "gross_food_value",
                "commission_rate",
                "commission_amount",
                "fixed_fee",
                "item_count",
                "packaging_fee",
                "gst_amount",
                "customer_total",
                "net_food_value",
                "brand_earnings",
            ])
            for rec in records:
                f_data = rec.financials
                writer.writerow([
                    f_data.order_id,
                    f_data.channel.value,
                    f_data.gross_food_value,
                    f_data.commission_rate,
                    f_data.commission_amount,
                    f_data.fixed_fee,
                    f_data.item_count,
                    f_data.packaging_fee,
                    f_data.gst_amount,
                    f_data.customer_total,
                    f_data.net_food_value,
                    f_data.brand_earnings,
                ])

        # 4. Daily Brand P&L CSV (BR-11)
        pnl_file = output_dir / "daily_brand_pnl.csv"
        pnl_records = AccountingEngine.calculate_daily_brand_pnl(
            [(rec.order, rec.financials) for rec in records]
        )
        with open(pnl_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "brand_id",
                "kitchen_id",
                "order_count",
                "gross_food_sales",
                "platform_commissions",
                "fixed_fees",
                "net_food_sales",
                "packaging_revenue",
                "gst_collected",
                "rent_orders_component",
                "rent_percentage_component",
                "raw_calculated_rent",
                "minimum_rent_applied",
                "final_kitchen_rent",
                "brand_net_profit",
            ])
            for p in pnl_records:
                writer.writerow([
                    p.brand_id,
                    p.kitchen_id,
                    p.order_count,
                    p.gross_food_sales,
                    p.platform_commissions,
                    p.fixed_fees,
                    p.net_food_sales,
                    p.packaging_revenue,
                    p.gst_collected,
                    p.rent_orders_component,
                    p.rent_percentage_component,
                    p.raw_calculated_rent,
                    p.minimum_rent_applied,
                    p.final_kitchen_rent,
                    p.brand_net_profit,
                ])
