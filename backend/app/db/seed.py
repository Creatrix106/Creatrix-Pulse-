import asyncio
import datetime
import json
import math
import os
import time
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd
import numpy as np

from app.config import settings
from app.db.database import db
from app.core.security import hash_password

DATA_START = "2026-01-01"
DATA_END = "2026-10-31"

CATALOG = [
    {"id": "P-101", "name": "Pulse Earbuds Pro", "category": "Electronics", "price": 6499, "costRatio": 0.62, "weight": 0.14},
    {"id": "P-102", "name": "Orbit Smartwatch", "category": "Electronics", "price": 8999, "costRatio": 0.66, "weight": 0.07},
    {"id": "P-103", "name": "Nimbus Speaker", "category": "Electronics", "price": 4299, "costRatio": 0.6, "weight": 0.06},
    {"id": "P-201", "name": "Everyday Tee", "category": "Apparel", "price": 799, "costRatio": 0.38, "weight": 0.13},
    {"id": "P-202", "name": "Trail Jacket", "category": "Apparel", "price": 3499, "costRatio": 0.47, "weight": 0.05},
    {"id": "P-203", "name": "Studio Joggers", "category": "Apparel", "price": 1499, "costRatio": 0.42, "weight": 0.07},
    {"id": "P-301", "name": "Aurora Table Lamp", "category": "Home & Living", "price": 1899, "costRatio": 0.5, "weight": 0.06},
    {"id": "P-302", "name": "Weave Throw Blanket", "category": "Home & Living", "price": 1299, "costRatio": 0.44, "weight": 0.06},
    {"id": "P-303", "name": "Ceramic Brew Set", "category": "Home & Living", "price": 2199, "costRatio": 0.52, "weight": 0.05},
    {"id": "P-401", "name": "Glow Serum", "category": "Personal Care", "price": 999, "costRatio": 0.3, "weight": 0.09},
    {"id": "P-402", "name": "Herbal Shampoo", "category": "Personal Care", "price": 449, "costRatio": 0.34, "weight": 0.08},
    {"id": "P-501", "name": "Leather Daily Wallet", "category": "Accessories", "price": 1199, "costRatio": 0.41, "weight": 0.05},
    {"id": "P-502", "name": "Canvas Tote", "category": "Accessories", "price": 699, "costRatio": 0.36, "weight": 0.04},
    {"id": "P-503", "name": "Everyday Backpack", "category": "Accessories", "price": 2299, "costRatio": 0.55, "weight": 0.05},
]

REGIONS = [
    {"name": "North", "weight": 0.3},
    {"name": "South", "weight": 0.28},
    {"name": "West", "weight": 0.25},
    {"name": "East", "weight": 0.17},
]

def hash_seed(text: str) -> int:
    h = 2166136261
    for char in text:
        h ^= ord(char)
        h = (h * 16777619) & 0xFFFFFFFF
    return h

class Mulberry32:
    def __init__(self, seed: int):
        self.state = seed & 0xFFFFFFFF

    def next(self) -> float:
        self.state = (self.state + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.state ^ (self.state >> 15)
        t = (t * (1 | self.state)) & 0xFFFFFFFF
        t = (t + ((t ^ (t >> 7)) * 61)) & 0xFFFFFFFF
        t = t ^ (t >> 14)
        return (t & 0xFFFFFFFF) / 4294967296.0

def pick_weighted(items: List[Dict[str, Any]], rand: Mulberry32) -> Dict[str, Any]:
    total_w = sum(i["weight"] for i in items)
    r = rand.next() * total_w
    for item in items:
        r -= item["weight"]
        if r <= 0:
            return item
    return items[-1]

def generate_deterministic_rows(seed_key: str, caps: Dict[str, bool]) -> List[Dict[str, Any]]:
    rand = Mulberry32(hash_seed(seed_key))
    rows = []
    
    start_dt = datetime.datetime.strptime(DATA_START, "%Y-%m-%d")
    end_dt = datetime.datetime.strptime(DATA_END, "%Y-%m-%d")
    total_days = (end_dt - start_dt).days + 1

    dow_factor = [1.15, 0.9, 0.9, 0.95, 1.0, 1.1, 1.25]  # Sun..Sat
    customer_pool: List[Dict[str, str]] = []
    order_no = 10000

    for i in range(total_days):
        dt = start_dt + datetime.timedelta(days=i)
        date_str = dt.strftime("%Y-%m-%d")
        dow = (dt.weekday() + 1) % 7  # 0=Sun
        month = dt.month - 1  # 0-indexed

        factor = (3.4 + (3.2 * i) / total_days) * dow_factor[dow]
        if month == 9:  # Festive season
            factor *= 1.25
        if "2026-08-15" <= date_str <= "2026-08-17":
            factor *= 2.6
        if "2026-04-10" <= date_str <= "2026-04-12":
            factor *= 0.35

        orders_count = max(0, int(round(factor + (rand.next() - 0.5) * 3)))

        for _ in range(orders_count):
            order_no += 1
            ord_id = f"ORD-{order_no}"
            prod = pick_weighted(CATALOG, rand)
            qty = 1 + (1 if rand.next() < 0.25 else 0) + (2 if rand.next() < 0.08 else 0)
            unit_price = int(round(prod["price"] * (0.92 + rand.next() * 0.12)))
            rev = unit_price * qty

            row: Dict[str, Any] = {
                "id": f"{seed_key}-row-{order_no}",
                "dataset_id": seed_key,
                "order_id": ord_id,
                "transaction_date": date_str,
                "product_id": prod["id"],
                "product_name": prod["name"],
                "product_category": prod["category"],
                "quantity": qty,
                "unit_price": float(unit_price),
                "revenue": float(rev),
                "cost": None,
                "region": None,
                "customer_identifier": None,
                "raw_payload": None,
            }

            if caps.get("cost"):
                row["cost"] = float(round(rev * prod["costRatio"] * (0.96 + rand.next() * 0.08)))

            if caps.get("customers"):
                returning = len(customer_pool) > 20 and rand.next() < 0.5
                if returning:
                    idx = int(math.floor((rand.next() ** 1.6) * len(customer_pool)))
                    c = customer_pool[idx]
                    row["customer_identifier"] = c["id"]
                    if caps.get("regions"):
                        row["region"] = c["region"]
                else:
                    reg = pick_weighted(REGIONS, rand)["name"]
                    c = {"id": f"C-{str(len(customer_pool) + 1).zfill(4)}", "region": reg}
                    customer_pool.append(c)
                    row["customer_identifier"] = c["id"]
                    if caps.get("regions"):
                        row["region"] = c["region"]
            elif caps.get("regions"):
                row["region"] = pick_weighted(REGIONS, rand)["name"]

            rows.append(row)

    return rows

SEED_MARKER = settings.DATA_DIR / ".demo_seeded"


async def seed_all(force: bool = False):
    """Create the demo admin and demo datasets.

    Demo datasets are only created on the first run (tracked by a marker file); otherwise a
    demo dataset the user deleted in the UI would reappear on every restart.
    Pass force=True (or `python -m app.db.seed --force`) to restore any missing demo dataset.
    """
    print("Initializing Database...")
    await db.init_db()

    # 1. Seed Demo Admin User
    admin = await db.get_user_by_email("admin@creatrix.io")
    if not admin:
        print("Creating demo admin user (admin@creatrix.io / password123)...")
        await db.create_user({
            "id": "user-demo",
            "name": "Demo Admin",
            "email": "admin@creatrix.io",
            "hashed_password": hash_password("password123"),
            "role": "admin"
        })

    if SEED_MARKER.exists() and not force:
        print("Demo data already seeded (use --force to restore deleted demo datasets).")
        return

    # 2. Seed Demo Datasets
    seeds_config = [
        {
            "id": "demo-retail",
            "name": "Retail Sales 2026",
            "fileName": "retail_sales_2026.csv",
            "fileSize": 412_000,
            "caps": {"customers": True, "cost": True, "regions": True},
            "uploadedAt": "2026-10-31T09:14:00.000Z",
            "status": "ready",
            "error": None
        },
        {
            "id": "demo-marketplace",
            "name": "Marketplace Orders (no cost data)",
            "fileName": "marketplace_orders.xlsx",
            "fileSize": 268_000,
            "caps": {"customers": True, "cost": False, "regions": True},
            "uploadedAt": "2026-10-12T14:40:00.000Z",
            "status": "ready",
            "error": None
        },
        {
            "id": "demo-wholesale",
            "name": "Wholesale Ledger (no customer data)",
            "fileName": "wholesale_ledger.csv",
            "fileSize": 190_000,
            "caps": {"customers": False, "cost": True, "regions": False},
            "uploadedAt": "2026-09-02T08:05:00.000Z",
            "status": "ready",
            "error": None
        },
        {
            "id": "demo-failed",
            "name": "Q3 Export",
            "fileName": "q3_export_final.csv",
            "fileSize": 98_000,
            "caps": {"customers": True, "cost": True, "regions": True},
            "uploadedAt": "2026-08-21T17:22:00.000Z",
            "status": "failed",
            "error": "The date column could not be parsed in 214 rows. Re-export the file with ISO dates (YYYY-MM-DD) and upload it again."
        }
    ]

    for item in seeds_config:
        existing = await db.get_dataset(item["id"])
        if existing:
            continue

        print(f"Seeding dataset '{item['name']}' ({item['id']})...")
        if item["status"] == "failed":
            d_record = {
                "id": item["id"],
                "user_id": "user-demo",
                "name": item["name"],
                "file_name": item["fileName"],
                "file_size": item["fileSize"],
                "status": "failed",
                "row_count": 0,
                "column_count": 8,
                "capabilities": item["caps"],
                "columns": [
                    {"name": "Order ID", "type": "string", "mappedTo": "orderId"},
                    {"name": "Date", "type": "date", "mappedTo": "date"},
                    {"name": "Product", "type": "string", "mappedTo": "product"},
                    {"name": "Category", "type": "string", "mappedTo": "category"},
                    {"name": "Quantity", "type": "number", "mappedTo": "quantity"},
                    {"name": "Revenue", "type": "number", "mappedTo": "revenue"},
                ],
                "date_range": None,
                "filter_options": {"categories": [], "regions": []},
                "error_message": item["error"],
                "schema_metadata": None,
                "uploaded_at": item["uploadedAt"],
                "started_at": int(time.time() * 1000)
            }
            await db.create_dataset(d_record)
            continue

        rows = generate_deterministic_rows(item["id"], item["caps"])
        df = pd.DataFrame(rows)

        # Save Parquet
        parquet_path = settings.PARQUET_DIR / f"{item['id']}.parquet"
        df.to_parquet(parquet_path, index=False)

        # Columns definition
        cols = [
            {"name": "Order ID", "type": "string", "mappedTo": "orderId"},
            {"name": "Date", "type": "date", "mappedTo": "date"},
            {"name": "Product", "type": "string", "mappedTo": "product"},
            {"name": "Category", "type": "string", "mappedTo": "category"},
        ]
        if item["caps"]["regions"]:
            cols.append({"name": "Region", "type": "string", "mappedTo": "region"})
        if item["caps"]["customers"]:
            cols.append({"name": "Customer ID", "type": "string", "mappedTo": "customer"})
        cols.extend([
            {"name": "Quantity", "type": "number", "mappedTo": "quantity"},
            {"name": "Revenue", "type": "number", "mappedTo": "revenue"},
        ])
        if item["caps"]["cost"]:
            cols.append({"name": "Cost", "type": "number", "mappedTo": "cost"})

        filter_options = {
            "categories": sorted(list(df["product_category"].dropna().unique())),
            "regions": sorted(list(df["region"].dropna().unique())) if item["caps"]["regions"] else []
        }

        d_record = {
            "id": item["id"],
            "user_id": "user-demo",
            "name": item["name"],
            "file_name": item["fileName"],
            "file_size": item["fileSize"],
            "status": "ready",
            "row_count": len(rows),
            "column_count": len(cols),
            "capabilities": item["caps"],
            "columns": cols,
            "date_range": {"from": rows[0]["transaction_date"], "to": DATA_END},
            "filter_options": filter_options,
            "error_message": None,
            "schema_metadata": None,
            "uploaded_at": item["uploadedAt"],
            "started_at": int(time.time() * 1000)
        }
        await db.create_dataset(d_record)
        await db.insert_rows(item["id"], rows)

    SEED_MARKER.write_text(datetime.datetime.utcnow().isoformat() + "Z")
    print("Seed complete successfully!")

if __name__ == "__main__":
    import sys
    asyncio.run(seed_all(force="--force" in sys.argv))
