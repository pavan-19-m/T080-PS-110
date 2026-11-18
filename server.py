"""
FastAPI Backend Server and Web Interface for T080 PS-110.
Exposes engine simulation data and serves the interactive dashboard.
"""

from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.loaders.csv_loader import CsvLoader
from src.services.order_service import OrderService
from src.accounting.accounting_engine import AccountingEngine
from src.models import OrderStatus

app = FastAPI(
    title="Cloud Kitchen Order Routing & Kitchen Capacity Engine (PS-110)",
    description="Team T080 - Padmavathi B & Pavan Neelappa Mirji",
    version="1.0.0"
)

# Enable CORS for local web interactions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "sample-data"

if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def get_dashboard():
    """Serves the interactive web dashboard."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Cloud Kitchen Engine API is live. Place index.html in static/"}


@app.get("/api/run-simulation")
def run_simulation() -> Dict[str, Any]:
    """
    Executes the full cloud kitchen pipeline:
    1. Loads configuration & catalogs from sample-data/
    2. Ingests orders and lifecycle events
    3. Runs eligibility, scheduling, priority jumps, and accounting
    4. Returns consolidated JSON payloads for web visualization
    """
    loader = CsvLoader(DATA_DIR)
    brands = loader.load_brands()
    recipes = loader.load_recipes()
    menu_items = loader.load_menu_items(brands, recipes)
    zones = loader.load_zones()
    kitchens = loader.load_kitchens()
    substitutions = loader.load_substitutions()
    events = loader.load_events()
    orders = loader.load_orders(brands, zones, menu_items, recipes)

    service = OrderService(
        kitchens=kitchens,
        brands=brands,
        menu_items=menu_items,
        recipes=recipes,
        zones=zones,
        substitutions=substitutions,
    )
    results = service.process_all_orders(orders, events=events)

    order_fin_records = [(r.order, r.financials) for r in results if r.financials]

    # Calculate Brand P&L and Rent (BR-11)
    brand_pnl_list = AccountingEngine.calculate_daily_brand_pnl(order_fin_records)

    # Calculate Channel Economics (BR-09)
    channel_reports = AccountingEngine.calculate_channel_reports(order_fin_records)

    # Aggregate Key Metrics
    total_gmv = sum(f.customer_total for _, f in order_fin_records)
    total_commissions = sum(f.commission_amount for _, f in order_fin_records)
    total_rent = sum(p.final_kitchen_rent for p in brand_pnl_list)
    fulfilled_count = sum(1 for r in results if r.order.status != OrderStatus.REJECTED)
    rejected_count = sum(1 for r in results if r.order.status == OrderStatus.REJECTED)

    # Kitchen rental revenue mapping
    kitchen_rent_map = {}
    for p in brand_pnl_list:
        k_id = p.kitchen_id
        kitchen_rent_map[k_id] = kitchen_rent_map.get(k_id, 0.0) + p.final_kitchen_rent

    return {
        "status": "success",
        "total_orders": len(results),
        "fulfilled_count": fulfilled_count,
        "rejected_count": rejected_count,
        "total_gmv": round(total_gmv, 2),
        "total_commissions": round(total_commissions, 2),
        "total_rent": round(total_rent, 2),
        "orders": [
            {
                "order_id": r.order.order_id,
                "brand": r.order.brand_id,
                "channel": r.order.channel.value,
                "kitchen": r.order.assigned_kitchen_id or "NONE",
                "order_time": r.order.order_time.strftime("%H:%M:%S"),
                "ready_time": r.order.projected_ready_time.strftime("%H:%M:%S") if r.order.projected_ready_time else "N/A",
                "promised_time": r.order.promised_time.strftime("%H:%M:%S") if r.order.promised_time else "N/A",
                "customer_total": r.financials.customer_total if r.financials else 0.0,
                "net_food": r.financials.net_food_value if r.financials else 0.0,
                "status": r.order.status.value,
                "is_rush": r.order.is_rush,
            }
            for r in results
        ],
        "brand_pnl": [
            {
                "brand_id": p.brand_id,
                "kitchen_id": p.kitchen_id,
                "order_count": p.order_count,
                "gross_sales": p.gross_food_sales,
                "commissions": p.platform_commissions,
                "net_food": p.net_food_sales,
                "rent": p.final_kitchen_rent,
                "min_rent_applied": p.minimum_rent_applied,
                "brand_net_pnl": p.brand_net_profit,
            }
            for p in brand_pnl_list
        ],
        "channels": [
            {
                "channel": c.channel.value,
                "order_count": c.order_count,
                "gross_gmv": c.total_gross_value,
                "commissions": c.total_commissions_earned,
                "fixed_fees": c.total_fixed_fees_earned,
                "gst": c.total_gst_processed,
            }
            for c in channel_reports
        ],
        "kitchens": [
            {
                "kitchen_id": k.kitchen_id,
                "name": k.name,
                "hours": f"{k.open_time.strftime('%H:%M')} - {k.close_time.strftime('%H:%M')}",
                "stations": [st.value for st in k.stations.keys()],
                "delivery_zones": list(k.delivery_zones),
                "rent_revenue": round(kitchen_rent_map.get(k.kitchen_id, 0.0), 2),
            }
            for k in kitchens.values()
        ],
    }


if __name__ == "__main__":
    import uvicorn
    print("\nStarting Cloud Kitchen Web Dashboard on http://127.0.0.1:8000 ...")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
