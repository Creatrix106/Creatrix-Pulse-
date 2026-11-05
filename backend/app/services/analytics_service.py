import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np

from app.config import settings
from app.db.database import db
from app.schemas.filters import AnalyticsFilters, GroupBy, DatePreset
from app.schemas.analytics import (
    Kpi,
    TimeSeriesPoint,
    BreakdownItem,
    ProductPerformance,
    OverviewData,
    SalesData,
    ProductsData,
    CustomersResponse,
    CustomersData,
    FinanceResponse,
    FinanceData,
    ExplorerData,
    ExplorerColumn,
    CustomerSegment,
    NewVsReturningPoint,
    FrequencyBin,
    CategoryTrendPoint,
)
from app.services.insights_service import InsightsService, pct_change

def add_days(iso_date: str, n: int) -> str:
    dt = datetime.datetime.strptime(iso_date[:10], "%Y-%m-%d") + datetime.timedelta(days=n)
    return dt.strftime("%Y-%m-%d")

def days_between(a: str, b: str) -> int:
    d1 = datetime.datetime.strptime(a[:10], "%Y-%m-%d")
    d2 = datetime.datetime.strptime(b[:10], "%Y-%m-%d")
    return (d2 - d1).days

def bucket_key(date_str: str, group_by: GroupBy) -> str:
    if group_by == "day":
        return date_str[:10]
    if group_by == "month":
        return f"{date_str[:7]}-01"
    # week (Monday start)
    dt = datetime.datetime.strptime(date_str[:10], "%Y-%m-%d")
    monday = dt - datetime.timedelta(days=dt.weekday())
    return monday.strftime("%Y-%m-%d")

class AnalyticsService:
    @classmethod
    async def load_dataframe(cls, dataset_id: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        dataset = await db.get_dataset(dataset_id)
        if not dataset:
            raise KeyError(f"Dataset {dataset_id} not found.")

        parquet_path = settings.PARQUET_DIR / f"{dataset_id}.parquet"
        if parquet_path.exists():
            df = pd.read_parquet(parquet_path)
        else:
            raw_rows = await db.get_raw_rows(dataset_id)
            if not raw_rows:
                df = pd.DataFrame(columns=[
                    "order_id", "transaction_date", "product_id", "product_name",
                    "product_category", "region", "customer_identifier",
                    "quantity", "unit_price", "revenue", "cost"
                ])
            else:
                df = pd.DataFrame(raw_rows)
            # Cache parquet
            if not df.empty:
                df.to_parquet(parquet_path, index=False)

        # Ensure correct column types
        if not df.empty:
            df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce").fillna(0.0)
            df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(1).astype(int)
            if "cost" in df.columns:
                df["cost"] = pd.to_numeric(df["cost"], errors="coerce")
            df["transaction_date"] = df["transaction_date"].astype(str).str[:10]

        return df, dataset

    @classmethod
    def slice_dataframe(
        cls,
        df: pd.DataFrame,
        filters: AnalyticsFilters
    ) -> Tuple[pd.DataFrame, Optional[pd.DataFrame], Dict[str, str], pd.DataFrame]:
        if df.empty:
            return df, None, {"from": "2026-01-01", "to": "2026-10-31"}, df

        scoped = df.copy()
        if filters.categories:
            scoped = scoped[scoped["product_category"].isin(filters.categories)]
        if filters.regions and "region" in scoped.columns:
            scoped = scoped[scoped["region"].isin(filters.regions)]

        all_dates = sorted(scoped["transaction_date"].dropna().unique())
        if not all_dates:
            min_date = "2026-01-01"
            max_date = "2026-10-31"
        else:
            min_date = all_dates[0]
            max_date = all_dates[-1]

        from_date = min_date
        to_date = max_date

        preset = filters.date_preset
        if preset == "last_30d":
            from_date = add_days(max_date, -29)
        elif preset == "last_90d":
            from_date = add_days(max_date, -89)
        elif preset == "last_180d":
            from_date = add_days(max_date, -179)
        elif preset == "ytd":
            from_date = f"{max_date[:4]}-01-01"
        elif preset == "custom" and filters.date_from and filters.date_to:
            from_date = filters.date_from
            to_date = filters.date_to

        current_df = scoped[(scoped["transaction_date"] >= from_date) & (scoped["transaction_date"] <= to_date)].copy()

        previous_df = None
        if filters.comparison == "previous_period" and preset != "all":
            span = days_between(from_date, to_date) + 1
            prev_to = add_days(from_date, -1)
            prev_from = add_days(from_date, -span)
            prev_rows = scoped[(scoped["transaction_date"] >= prev_from) & (scoped["transaction_date"] <= prev_to)].copy()
            if not prev_rows.empty:
                previous_df = prev_rows

        return current_df, previous_df, {"from": from_date, "to": to_date}, scoped

    @staticmethod
    def calculate_totals(df: pd.DataFrame, has_cost: bool) -> Dict[str, Any]:
        if df.empty:
            return {
                "revenue": 0.0,
                "orders": 0,
                "units": 0,
                "aov": 0.0,
                "cost": 0.0 if has_cost else None,
                "profit": 0.0 if has_cost else None,
                "margin": 0.0 if has_cost else None,
            }
        revenue = float(df["revenue"].sum())
        orders = int(df["order_id"].nunique())
        units = int(df["quantity"].sum())
        aov = revenue / orders if orders > 0 else 0.0

        cost = None
        profit = None
        margin = None
        if has_cost and "cost" in df.columns and not df["cost"].isna().all():
            cost = float(df["cost"].sum())
            profit = revenue - cost
            margin = (profit / revenue * 100.0) if revenue > 0 else 0.0

        return {
            "revenue": revenue,
            "orders": orders,
            "units": units,
            "aov": aov,
            "cost": cost,
            "profit": profit,
            "margin": margin,
        }

    @classmethod
    def build_core_kpis(
        cls,
        cur: Dict[str, Any],
        prev: Optional[Dict[str, Any]],
        has_cost: bool
    ) -> List[Kpi]:
        kpis = [
            Kpi(
                id="revenue",
                label="Revenue",
                value=round(cur["revenue"], 2),
                format="currency",
                change=round(pct_change(cur["revenue"], prev["revenue"]), 1) if prev else None
            ),
            Kpi(
                id="orders",
                label="Orders",
                value=cur["orders"],
                format="number",
                change=round(pct_change(cur["orders"], prev["orders"]), 1) if prev else None
            ),
            Kpi(
                id="units",
                label="Units sold",
                value=cur["units"],
                format="number",
                change=round(pct_change(cur["units"], prev["units"]), 1) if prev else None
            ),
            Kpi(
                id="aov",
                label="Avg. order value",
                value=round(cur["aov"], 2),
                format="currency",
                change=round(pct_change(cur["aov"], prev["aov"]), 1) if prev else None
            ),
        ]
        if has_cost and cur.get("profit") is not None and cur.get("margin") is not None:
            prev_margin = prev.get("margin") if prev else None
            margin_diff = round(cur["margin"] - prev_margin, 1) if prev_margin is not None else None
            kpis.extend([
                Kpi(
                    id="profit",
                    label="Gross profit",
                    value=round(cur["profit"], 2),
                    format="currency",
                    change=round(pct_change(cur["profit"], prev.get("profit")), 1) if prev else None
                ),
                Kpi(
                    id="margin",
                    label="Profit margin",
                    value=round(cur["margin"], 1),
                    format="percent",
                    change=margin_diff,
                    hint="Change in percentage points"
                )
            ])
        return kpis

    @classmethod
    def build_timeseries(
        cls,
        df: pd.DataFrame,
        group_by: GroupBy,
        has_cost: bool
    ) -> List[TimeSeriesPoint]:
        if df.empty:
            return []

        df_copy = df.copy()
        df_copy["bucket"] = df_copy["transaction_date"].apply(lambda d: bucket_key(d, group_by))
        points: List[TimeSeriesPoint] = []

        grouped = df_copy.groupby("bucket")
        for bucket, grp in sorted(grouped, key=lambda x: x[0]):
            tot = cls.calculate_totals(grp, has_cost)
            pt = TimeSeriesPoint(
                date=bucket,
                revenue=round(tot["revenue"], 2),
                orders=tot["orders"],
                units=tot["units"],
                aov=round(tot["aov"], 2),
            )
            if has_cost and tot["cost"] is not None:
                pt.cost = round(tot["cost"], 2)
                pt.profit = round(tot["profit"], 2)
                pt.margin = round(tot["margin"], 1)
            points.append(pt)
        return points

    @classmethod
    def build_breakdown(
        cls,
        current_df: pd.DataFrame,
        previous_df: Optional[pd.DataFrame],
        column: str
    ) -> List[BreakdownItem]:
        if current_df.empty or column not in current_df.columns:
            return []

        total_rev = float(current_df["revenue"].sum())
        cur_grp = current_df.groupby(column).agg({"revenue": "sum", "quantity": "sum"}).reset_index()

        prev_map = {}
        if previous_df is not None and not previous_df.empty and column in previous_df.columns:
            p_grp = previous_df.groupby(column)["revenue"].sum()
            prev_map = p_grp.to_dict()

        items: List[BreakdownItem] = []
        for _, row in cur_grp.iterrows():
            name = str(row[column])
            val = float(row["revenue"])
            units = int(row["quantity"])
            share = (val / total_rev * 100.0) if total_rev > 0 else 0.0
            prev_val = prev_map.get(name)
            chg = pct_change(val, prev_val) if prev_val is not None else None
            items.append(
                BreakdownItem(
                    name=name,
                    value=round(val, 2),
                    share=round(share, 1),
                    secondary=units,
                    change=round(chg, 1) if chg is not None else None
                )
            )
        items.sort(key=lambda x: x.value, reverse=True)
        return items

    @classmethod
    def build_product_performance(
        cls,
        current_df: pd.DataFrame,
        previous_df: Optional[pd.DataFrame],
        has_cost: bool
    ) -> List[ProductPerformance]:
        if current_df.empty:
            return []

        total_rev = float(current_df["revenue"].sum())
        cur_grouped = current_df.groupby(["product_id", "product_name", "product_category"]).agg(
            revenue=("revenue", "sum"),
            units=("quantity", "sum"),
            orders=("order_id", "nunique"),
            cost=("cost", "sum") if (has_cost and "cost" in current_df.columns) else ("revenue", lambda x: np.nan)
        ).reset_index()

        prev_map = {}
        if previous_df is not None and not previous_df.empty:
            p_grp = previous_df.groupby("product_id")["revenue"].sum()
            prev_map = p_grp.to_dict()

        out: List[ProductPerformance] = []
        for _, row in cur_grouped.iterrows():
            pid = str(row["product_id"])
            pname = str(row["product_name"])
            pcat = str(row["product_category"])
            rev = float(row["revenue"])
            units = int(row["units"])
            orders = int(row["orders"])
            share = (rev / total_rev * 100.0) if total_rev > 0 else 0.0
            prev_rev = prev_map.get(pid)
            chg = pct_change(rev, prev_rev) if prev_rev is not None else None

            margin = None
            if has_cost and pd.notna(row["cost"]) and rev > 0:
                cost_val = float(row["cost"])
                margin = ((rev - cost_val) / rev) * 100.0

            out.append(
                ProductPerformance(
                    id=pid,
                    name=pname,
                    category=pcat,
                    revenue=round(rev, 2),
                    units=units,
                    orders=orders,
                    share=round(share, 1),
                    change=round(chg, 1) if chg is not None else None,
                    margin=round(margin, 1) if margin is not None else None
                )
            )
        out.sort(key=lambda x: x.revenue, reverse=True)
        return out

    # ---------------- Specific API Endpoints ---------------- #

    @classmethod
    async def get_overview(cls, dataset_id: str, filters: AnalyticsFilters) -> OverviewData:
        df, dataset = await cls.load_dataframe(dataset_id)
        cur_df, prev_df, date_range, _ = cls.slice_dataframe(df, filters)
        has_cost = dataset.get("capabilities", {}).get("cost", False)
        has_customers = dataset.get("capabilities", {}).get("customers", False)

        cur_tot = cls.calculate_totals(cur_df, has_cost)
        prev_tot = cls.calculate_totals(prev_df, has_cost) if prev_df is not None else None

        kpis = cls.build_core_kpis(cur_tot, prev_tot, has_cost)
        trend = cls.build_timeseries(cur_df, filters.group_by, has_cost)
        products = cls.build_product_performance(cur_df, prev_df, has_cost)
        categories = cls.build_breakdown(cur_df, prev_df, "product_category")
        regions = cls.build_breakdown(cur_df, prev_df, "region")
        insights = InsightsService.generate_insights(cur_df, prev_df, has_cost, has_customers)[:4]

        return OverviewData(
            period=date_range,
            kpis=kpis,
            revenueTrend=trend,
            topProducts=products[:5],
            categories=categories,
            regions=regions,
            insights=insights
        )

    @classmethod
    async def get_sales(cls, dataset_id: str, filters: AnalyticsFilters) -> SalesData:
        df, dataset = await cls.load_dataframe(dataset_id)
        cur_df, prev_df, _, _ = cls.slice_dataframe(df, filters)
        has_cost = dataset.get("capabilities", {}).get("cost", False)

        cur_tot = cls.calculate_totals(cur_df, has_cost)
        prev_tot = cls.calculate_totals(prev_df, has_cost) if prev_df is not None else None

        kpis = cls.build_core_kpis(cur_tot, prev_tot, has_cost)
        trend = cls.build_timeseries(cur_df, filters.group_by, has_cost)
        prev_trend = cls.build_timeseries(prev_df, filters.group_by, has_cost) if prev_df is not None else None
        categories = cls.build_breakdown(cur_df, prev_df, "product_category")
        regions = cls.build_breakdown(cur_df, prev_df, "region")

        # Category trend
        cat_trend: List[CategoryTrendPoint] = []
        if not cur_df.empty:
            cur_copy = cur_df.copy()
            cur_copy["bucket"] = cur_copy["transaction_date"].apply(lambda d: bucket_key(d, filters.group_by))
            pivoted = cur_copy.pivot_table(index="bucket", columns="product_category", values="revenue", aggfunc="sum").fillna(0.0)
            for b_date, row in pivoted.iterrows():
                cat_trend.append(CategoryTrendPoint(date=str(b_date), values={str(k): round(float(v), 2) for k, v in row.items()}))
            cat_trend.sort(key=lambda x: x.date)

        return SalesData(
            kpis=kpis,
            trend=trend,
            previousTrend=prev_trend,
            categories=categories,
            regions=regions,
            categoryNames=[c.name for c in categories],
            categoryTrend=cat_trend
        )

    @classmethod
    async def get_products(cls, dataset_id: str, filters: AnalyticsFilters) -> ProductsData:
        df, dataset = await cls.load_dataframe(dataset_id)
        cur_df, prev_df, _, _ = cls.slice_dataframe(df, filters)
        has_cost = dataset.get("capabilities", {}).get("cost", False)

        all_products = cls.build_product_performance(cur_df, prev_df, has_cost)
        categories = cls.build_breakdown(cur_df, prev_df, "product_category")

        return ProductsData(
            top=all_products[:5],
            low=list(reversed(all_products))[:5],
            all=all_products,
            categories=categories
        )

    @classmethod
    async def get_customers(cls, dataset_id: str, filters: AnalyticsFilters) -> CustomersResponse:
        df, dataset = await cls.load_dataframe(dataset_id)
        has_customers = dataset.get("capabilities", {}).get("customers", False)
        if not has_customers or "customer_identifier" not in df.columns or df["customer_identifier"].dropna().empty:
            return CustomersResponse(
                available=False,
                reason="This dataset has no customer column. Map a customer ID column when uploading to unlock customer analytics."
            )

        cur_df, prev_df, date_range, scoped_df = cls.slice_dataframe(df, filters)

        # First purchase date across all scoped records
        first_dates = scoped_df.groupby("customer_identifier")["transaction_date"].min().to_dict()

        # Current period customer stats
        cur_cust_grp = cur_df.groupby("customer_identifier").agg(
            orders=("order_id", "nunique"),
            revenue=("revenue", "sum")
        )
        total_customers = len(cur_cust_grp)
        total_revenue = float(cur_df["revenue"].sum())
        rpc = total_revenue / total_customers if total_customers > 0 else 0.0

        new_customers = sum(
            1 for cid in cur_cust_grp.index
            if first_dates.get(cid, "") >= date_range["from"]
        )
        returning_customers = total_customers - new_customers

        # Previous period stats
        prev_cust_count = None
        prev_rpc = None
        if prev_df is not None and not prev_df.empty:
            prev_cust_grp = prev_df.groupby("customer_identifier").agg(revenue=("revenue", "sum"))
            prev_cust_count = len(prev_cust_grp)
            prev_rev = float(prev_df["revenue"].sum())
            prev_rpc = prev_rev / prev_cust_count if prev_cust_count > 0 else 0.0

        kpis = [
            Kpi(
                id="customers",
                label="Total customers",
                value=total_customers,
                format="number",
                change=round(pct_change(total_customers, prev_cust_count), 1) if prev_cust_count else None
            ),
            Kpi(
                id="new",
                label="New customers",
                value=new_customers,
                format="number"
            ),
            Kpi(
                id="returning",
                label="Returning customers",
                value=returning_customers,
                format="number"
            ),
            Kpi(
                id="rpc",
                label="Revenue per customer",
                value=round(rpc, 2),
                format="currency",
                change=round(pct_change(rpc, prev_rpc), 1) if prev_rpc else None
            ),
        ]

        # New vs Returning time series
        cur_df_copy = cur_df.copy()
        cur_df_copy["bucket"] = cur_df_copy["transaction_date"].apply(lambda d: bucket_key(d, filters.group_by))
        new_vs_returning: List[NewVsReturningPoint] = []

        for bucket, b_df in sorted(cur_df_copy.groupby("bucket"), key=lambda x: x[0]):
            b_cids = set(b_df["customer_identifier"].dropna().unique())
            fresh = sum(1 for cid in b_cids if bucket_key(first_dates.get(cid, ""), filters.group_by) == bucket)
            new_vs_returning.append(
                NewVsReturningPoint(
                    date=bucket,
                    newCustomers=fresh,
                    returningCustomers=len(b_cids) - fresh
                )
            )

        # Order frequency bins
        bins_data = [
            ("1 order", 0), ("2 orders", 0), ("3 orders", 0),
            ("4 orders", 0), ("5 orders", 0), ("6+ orders", 0)
        ]
        bin_counts = [0] * 6
        for o_count in cur_cust_grp["orders"]:
            idx = min(o_count, 6) - 1
            bin_counts[idx] += 1
        frequency = [FrequencyBin(label=bins_data[i][0], count=bin_counts[i]) for i in range(6)]

        # Segments
        seg_defs = [
            {"name": "Champions", "desc": "6 or more orders", "filter": lambda o: o >= 6},
            {"name": "Loyal", "desc": "3–5 orders", "filter": lambda o: (o >= 3) & (o <= 5)},
            {"name": "Returning", "desc": "2 orders", "filter": lambda o: o == 2},
            {"name": "One-time", "desc": "1 order", "filter": lambda o: o == 1},
        ]
        segments: List[CustomerSegment] = []
        for sdef in seg_defs:
            mask = sdef["filter"](cur_cust_grp["orders"])
            sub = cur_cust_grp[mask]
            sub_count = len(sub)
            sub_rev = float(sub["revenue"].sum())
            sub_share = (sub_count / total_customers * 100.0) if total_customers > 0 else 0.0
            segments.append(
                CustomerSegment(
                    name=sdef["name"],
                    description=sdef["desc"],
                    customers=sub_count,
                    revenue=round(sub_rev, 2),
                    share=round(sub_share, 1)
                )
            )

        # Regional distribution of customers
        dist_col = "region" if "region" in cur_df.columns and not cur_df["region"].dropna().empty else "product_category"
        dist_grp = cur_df.groupby(dist_col)["customer_identifier"].nunique().sort_values(ascending=False)
        distribution: List[BreakdownItem] = [
            BreakdownItem(
                name=str(name),
                value=int(cnt),
                share=round((cnt / total_customers * 100.0) if total_customers > 0 else 0.0, 1)
            )
            for name, cnt in dist_grp.items()
        ]

        return CustomersResponse(
            available=True,
            data=CustomersData(
                kpis=kpis,
                newVsReturning=new_vs_returning,
                distribution=distribution,
                frequency=frequency,
                segments=segments
            )
        )

    @classmethod
    async def get_finance(cls, dataset_id: str, filters: AnalyticsFilters) -> FinanceResponse:
        df, dataset = await cls.load_dataframe(dataset_id)
        has_cost = dataset.get("capabilities", {}).get("cost", False)
        if not has_cost or "cost" not in df.columns or df["cost"].isna().all():
            return FinanceResponse(
                available=False,
                reason="This dataset has no cost column, so profit and margin cannot be calculated. Map a cost column when uploading to unlock financial analytics."
            )

        cur_df, prev_df, _, _ = cls.slice_dataframe(df, filters)
        cur_tot = cls.calculate_totals(cur_df, has_cost=True)
        prev_tot = cls.calculate_totals(prev_df, has_cost=True) if prev_df is not None else None

        kpis = [
            Kpi(
                id="revenue",
                label="Revenue",
                value=round(cur_tot["revenue"], 2),
                format="currency",
                change=round(pct_change(cur_tot["revenue"], prev_tot["revenue"]), 1) if prev_tot else None
            ),
            Kpi(
                id="cost",
                label="Total cost",
                value=round(cur_tot["cost"] or 0.0, 2),
                format="currency",
                change=round(pct_change(cur_tot["cost"] or 0.0, prev_tot["cost"] if prev_tot else None), 1) if prev_tot else None,
                inverse=True
            ),
            Kpi(
                id="profit",
                label="Gross profit",
                value=round(cur_tot["profit"] or 0.0, 2),
                format="currency",
                change=round(pct_change(cur_tot["profit"], prev_tot.get("profit") if prev_tot else None), 1) if prev_tot else None
            ),
            Kpi(
                id="margin",
                label="Profit margin",
                value=round(cur_tot["margin"] or 0.0, 1),
                format="percent",
                change=round((cur_tot["margin"] - prev_tot["margin"]), 1) if (prev_tot and prev_tot.get("margin") is not None) else None,
                hint="Change in percentage points"
            )
        ]

        trend = cls.build_timeseries(cur_df, filters.group_by, has_cost=True)

        # Margins by category
        cat_margins: List[BreakdownItem] = []
        if not cur_df.empty:
            grp = cur_df.groupby("product_category").agg({"revenue": "sum", "cost": "sum"}).reset_index()
            tot_profit = float((cur_df["revenue"] - cur_df["cost"]).sum())
            for _, r in grp.iterrows():
                r_rev = float(r["revenue"])
                r_cost = float(r["cost"])
                r_profit = r_rev - r_cost
                r_margin = (r_profit / r_rev * 100.0) if r_rev > 0 else 0.0
                r_share = (r_profit / tot_profit * 100.0) if tot_profit > 0 else 0.0
                cat_margins.append(
                    BreakdownItem(
                        name=str(r["product_category"]),
                        value=round(r_margin, 1),
                        share=round(r_share, 1),
                        secondary=round(r_profit, 2)
                    )
                )
            cat_margins.sort(key=lambda x: x.value, reverse=True)

        return FinanceResponse(
            available=True,
            data=FinanceData(
                kpis=kpis,
                trend=trend,
                categoryMargins=cat_margins
            )
        )

    @classmethod
    async def get_explorer_data(
        cls,
        dataset_id: str,
        limit: int = 200,
        offset: int = 0,
        sort_by: Optional[str] = None
    ) -> ExplorerData:
        df, dataset = await cls.load_dataframe(dataset_id)
        caps = dataset.get("capabilities", {})

        columns: List[ExplorerColumn] = [
            ExplorerColumn(key="orderId", label="Order ID", type="string"),
            ExplorerColumn(key="date", label="Date", type="date"),
            ExplorerColumn(key="product", label="Product", type="string"),
            ExplorerColumn(key="category", label="Category", type="string"),
        ]
        if caps.get("regions"):
            columns.append(ExplorerColumn(key="region", label="Region", type="string"))
        if caps.get("customers"):
            columns.append(ExplorerColumn(key="customerId", label="Customer", type="string"))
        columns.extend([
            ExplorerColumn(key="quantity", label="Quantity", type="number"),
            ExplorerColumn(key="unitPrice", label="Unit price", type="number", format="currency"),
            ExplorerColumn(key="revenue", label="Revenue", type="number", format="currency"),
        ])
        if caps.get("cost"):
            columns.append(ExplorerColumn(key="cost", label="Cost", type="number", format="currency"))

        if df.empty:
            return ExplorerData(columns=columns, rows=[], total=0)

        # Map internal column names to Explorer keys
        rows_df = df.copy()
        if sort_by and sort_by in rows_df.columns:
            rows_df = rows_df.sort_values(by=sort_by, ascending=False)
        else:
            rows_df = rows_df.sort_values(by="transaction_date", ascending=False)

        total_rows = len(rows_df)
        paged_df = rows_df.iloc[offset:offset+limit]

        explorer_rows: List[Dict[str, Any]] = []
        for _, r in paged_df.iterrows():
            item = {
                "orderId": r.get("order_id"),
                "date": r.get("transaction_date"),
                "product": r.get("product_name"),
                "category": r.get("product_category"),
                "quantity": int(r.get("quantity", 1)),
                "unitPrice": round(float(r.get("unit_price", 0.0)), 2),
                "revenue": round(float(r.get("revenue", 0.0)), 2),
            }
            if caps.get("regions"):
                item["region"] = r.get("region")
            if caps.get("customers"):
                item["customerId"] = r.get("customer_identifier")
            if caps.get("cost") and pd.notna(r.get("cost")):
                item["cost"] = round(float(r["cost"]), 2)
            explorer_rows.append(item)

        return ExplorerData(columns=columns, rows=explorer_rows, total=total_rows)
