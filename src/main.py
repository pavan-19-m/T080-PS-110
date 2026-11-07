"""Main entry point for Cloud Kitchen Multi-brand Order Routing and Kitchen Capacity Engine."""

import argparse
import sys
from pathlib import Path

from src.input.csv_loader import CsvLoader
from src.reporting.report_generator import ReportGenerator
from src.services.order_service import OrderService


def run_pipeline(data_dir: Path, output_dir: Path) -> int:
    """Execute the end-to-end cloud kitchen order routing and capacity pipeline."""
    print("=" * 90)
    print(" 10 SECONDS CAPSTONE PROJECT | TEAM T080 | PROBLEM STATEMENT: PS-110")
    print(" Cloud Kitchen Multi-brand Order Routing and Kitchen Capacity Engine")
    print(f" Data Directory:   {data_dir.resolve()}")
    print(f" Output Directory: {output_dir.resolve()}")
    print("=" * 90)

    try:
        loader = CsvLoader(data_dir)

        print("\n[1/5] Loading configuration and catalogs...")
        brands = loader.load_brands()
        print(f"  -> Loaded {len(brands)} virtual brands")

        recipes = loader.load_recipes()
        print(f"  -> Loaded {len(recipes)} recipes")

        menu_items = loader.load_menu_items(brands, recipes)
        print(f"  -> Loaded {len(menu_items)} menu items")

        zones = loader.load_zones()
        print(f"  -> Loaded {len(zones)} delivery zones")

        kitchens = loader.load_kitchens()
        total_stations = sum(len(k.stations) for k in kitchens.values())
        print(f"  -> Loaded {len(kitchens)} physical kitchens with {total_stations} workstations")

        print("\n[2/5] Ingesting and validating incoming orders...")
        orders = loader.load_orders(brands, zones, menu_items, recipes)
        print(f"  -> Loaded and validated {len(orders)} customer orders")

        print("\n[3/5] Executing routing, scheduling, priority jumps, and accounting...")
        service = OrderService(
            kitchens=kitchens,
            brands=brands,
            menu_items=menu_items,
            recipes=recipes,
            zones=zones,
        )
        records = service.process_all_orders(orders)
        print(f"  -> Successfully processed {len(records)} orders through pipeline")

        print("\n[4/5] Pipeline execution results:")
        ReportGenerator.print_terminal_summary(records)

        print("[5/5] Exporting CSV audit reports...")
        ReportGenerator.export_csv_reports(records, output_dir)
        print(f"  -> Reports written to: {output_dir.resolve()}")
        print("     - routing_decisions.csv")
        print("     - station_timelines.csv")
        print("     - order_financials.csv")
        print("     - daily_brand_pnl.csv")

        print("\n Pipeline execution finished successfully.")
        return 0

    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cloud Kitchen Multi-brand Order Routing and Kitchen Capacity Engine (PS-110)"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("sample-data"),
        help="Path to folder containing input CSV files (default: sample-data)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Path to folder for generated output CSV files (default: output)",
    )

    args = parser.parse_args()
    exit_code = run_pipeline(args.data_dir, args.output_dir)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
