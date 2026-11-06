import math
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

from app.schemas.insight import Insight, InsightEvidence

def format_currency(val: float, currency: str = "₹") -> str:
    if val >= 10_000_000:
        return f"{currency}{val / 10_000_000:.2f} Cr"
    if val >= 100_000:
        return f"{currency}{val / 100_000:.2f} L"
    if val >= 1000:
        return f"{currency}{val:,.0f}"
    return f"{currency}{val:.2f}"

def format_number(val: float) -> str:
    return f"{int(val):,}"

def pct_change(cur: float, prev: Optional[float]) -> Optional[float]:
    if prev is None or prev == 0:
        return None
    return ((cur - prev) / prev) * 100.0

class InsightsService:
    @staticmethod
    def generate_insights(
        current_df: pd.DataFrame,
        previous_df: Optional[pd.DataFrame],
        has_cost: bool,
        has_customers: bool
    ) -> List[Insight]:
        if current_df.empty:
            return []

        insights: List[Insight] = []
        cur_revenue = float(current_df["revenue"].sum())
        cur_orders = int(current_df["order_id"].nunique())
        cur_aov = cur_revenue / cur_orders if cur_orders > 0 else 0.0

        prev_revenue = float(previous_df["revenue"].sum()) if previous_df is not None and not previous_df.empty else None
        prev_orders = int(previous_df["order_id"].nunique()) if previous_df is not None and not previous_df.empty else None

        # 1. Revenue comparison / Observation
        change = pct_change(cur_revenue, prev_revenue)
        if prev_revenue is not None and change is not None:
            orders_chg = pct_change(cur_orders, prev_orders)
            orders_str = f"{orders_chg:+.1f}%" if orders_chg is not None else "N/A"
            insights.append(
                Insight(
                    id="revenue-change",
                    type="positive" if change >= 0 else "negative",
                    metric="revenue",
                    title=f"Revenue {'increased' if change >= 0 else 'decreased'} by {abs(change):.1f}% vs the previous period",
                    summary=f"Revenue moved from {format_currency(prev_revenue)} to {format_currency(cur_revenue)} across comparable periods.",
                    evidence=[
                        InsightEvidence(label="Current period", value=format_currency(cur_revenue)),
                        InsightEvidence(label="Previous period", value=format_currency(prev_revenue)),
                        InsightEvidence(label="Orders change", value=orders_str)
                    ]
                )
            )
        else:
            insights.append(
                Insight(
                    id="revenue-total",
                    type="observation",
                    metric="revenue",
                    title=f"{format_currency(cur_revenue)} in revenue from {format_number(cur_orders)} orders",
                    summary="Enable a comparison period to see how this compares with earlier performance.",
                    evidence=[
                        InsightEvidence(label="Orders", value=format_number(cur_orders)),
                        InsightEvidence(label="Average order value", value=format_currency(cur_aov))
                    ]
                )
            )

        # 2. Top Category Breakdown
        cat_grp = current_df.groupby("product_category")["revenue"].sum().sort_values(ascending=False)
        if not cat_grp.empty:
            top_cat = cat_grp.index[0]
            top_val = float(cat_grp.iloc[0])
            top_share = (top_val / cur_revenue * 100.0) if cur_revenue > 0 else 0.0
            second_cat = cat_grp.index[1] if len(cat_grp) > 1 else "all others"
            
            top_3_evidence = [
                InsightEvidence(
                    label=cat,
                    value=f"{format_currency(val)} · {(val / cur_revenue * 100):.1f}%"
                )
                for cat, val in cat_grp.head(3).items()
            ]
            insights.append(
                Insight(
                    id="top-category",
                    type="observation",
                    metric="category",
                    title=f"{top_cat} contributed {top_share:.1f}% of revenue",
                    summary=f"It is the largest category, ahead of {second_cat}.",
                    evidence=top_3_evidence
                )
            )

        # 3. Product Concentration Risk
        prod_grp = current_df.groupby("product_name")["revenue"].sum().sort_values(ascending=False)
        if len(prod_grp) >= 5:
            top_3_rev = float(prod_grp.head(3).sum())
            top_3_share = (top_3_rev / cur_revenue * 100.0) if cur_revenue > 0 else 0.0
            if top_3_share > 40.0:
                evidence = [InsightEvidence(label="Top 3 products share", value=f"{top_3_share:.1f}%")]
                for p_name, p_rev in prod_grp.head(3).items():
                    p_share = (p_rev / cur_revenue * 100.0) if cur_revenue > 0 else 0.0
                    evidence.append(InsightEvidence(label=p_name, value=f"{p_share:.1f}%"))

                insights.append(
                    Insight(
                        id="concentration",
                        type="recommendation",
                        metric="product",
                        title="Revenue is concentrated in a few products",
                        summary="Review stock levels and promotion plans for the best sellers, and consider supporting mid-ranked products.",
                        evidence=evidence
                    )
                )

        # 4. Product Movers (Best and Worst)
        if previous_df is not None and not previous_df.empty:
            prev_prod_grp = previous_df.groupby("product_name")["revenue"].sum()
            prod_changes = []
            for p_name, p_rev in prod_grp.items():
                if p_name in prev_prod_grp:
                    prev_p_rev = float(prev_prod_grp[p_name])
                    chg = pct_change(float(p_rev), prev_p_rev)
                    if chg is not None:
                        prod_changes.append((p_name, chg, float(p_rev)))

            if prod_changes:
                prod_changes.sort(key=lambda x: x[1], reverse=True)
                best = prod_changes[0]
                worst = prod_changes[-1]
                if best[1] > 0:
                    insights.append(
                        Insight(
                            id="best-mover",
                            type="positive",
                            metric="product",
                            title=f"{best[0]} grew {best[1]:.1f}% in revenue",
                            summary="The strongest improvement among all products versus the previous period.",
                            evidence=[
                                InsightEvidence(label="Revenue", value=format_currency(best[2])),
                                InsightEvidence(label="Growth", value=f"+{best[1]:.1f}%")
                            ]
                        )
                    )
                if worst[1] < 0:
                    insights.append(
                        Insight(
                            id="worst-mover",
                            type="negative",
                            metric="product",
                            title=f"{worst[0]} declined {abs(worst[1]):.1f}% in revenue",
                            summary="The largest decline among products versus the previous period.",
                            evidence=[
                                InsightEvidence(label="Revenue", value=format_currency(worst[2])),
                                InsightEvidence(label="Decline", value=f"{worst[1]:.1f}%")
                            ]
                        )
                    )

        # 5. Anomaly Detection (weekly z-score)
        # Same rule as the frontend reference: the first and last week of the window are usually
        # partial (they would always look like a "drop"), so they are excluded, and at least
        # 8 full weeks are required before a week can be called unusual.
        temp_df = current_df.copy()
        temp_df["dt"] = pd.to_datetime(temp_df["transaction_date"])
        temp_df["week"] = (temp_df["dt"] - pd.to_timedelta(temp_df["dt"].dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")
        weekly_rev = temp_df.groupby("week")["revenue"].sum().sort_index()
        if len(weekly_rev) >= 3:
            weekly_rev = weekly_rev.iloc[1:-1]

        if len(weekly_rev) >= 8:
            mean_rev = float(weekly_rev.mean())
            std_rev = float(weekly_rev.std(ddof=0))
            if std_rev > 0 and mean_rev > 0:
                z_scores = ((weekly_rev - mean_rev) / std_rev).abs()
                max_week = z_scores.idxmax()
                max_z = float(z_scores[max_week])
                if max_z >= 2.0:
                    week_val = float(weekly_rev[max_week])
                    dev_pct = ((week_val - mean_rev) / mean_rev) * 100.0
                    spike_or_drop = "spike" if dev_pct > 0 else "drop"
                    week_label = pd.Timestamp(max_week).strftime("%d %b %Y").lstrip("0")
                    insights.append(
                        Insight(
                            id="anomaly-week",
                            type="anomaly",
                            metric="revenue",
                            title=f"Unusual {spike_or_drop} in the week of {week_label}",
                            summary=f"Weekly revenue was {abs(dev_pct):.0f}% {'above' if dev_pct > 0 else 'below'} the typical week. Check campaigns, outages or data-entry issues for that week.",
                            evidence=[
                                InsightEvidence(label="Revenue that week", value=format_currency(week_val)),
                                InsightEvidence(label="Typical week", value=format_currency(mean_rev)),
                                InsightEvidence(label="Deviation", value=f"{max_z:.1f} standard deviations")
                            ]
                        )
                    )

        # 6. Regional Performance
        if "region" in current_df.columns and current_df["region"].dropna().nunique() >= 3:
            reg_grp = current_df.groupby("region")["revenue"].sum().sort_values(ascending=False)
            reg_count = len(reg_grp)
            avg_share = 100.0 / reg_count
            top_reg = reg_grp.index[0]
            top_reg_share = (float(reg_grp.iloc[0]) / cur_revenue * 100.0) if cur_revenue > 0 else 0.0

            evidence = [
                InsightEvidence(label=r, value=f"{(v / cur_revenue * 100.0):.1f}%")
                for r, v in reg_grp.items()
            ]
            insights.append(
                Insight(
                    id="top-region",
                    type="observation",
                    metric="region",
                    title=f"{top_reg} is the strongest region at {top_reg_share:.1f}% of revenue",
                    summary="Regional share of total revenue across the selected period.",
                    evidence=evidence
                )
            )

            weakest_reg = reg_grp.index[-1]
            weakest_share = (float(reg_grp.iloc[-1]) / cur_revenue * 100.0) if cur_revenue > 0 else 0.0
            if weakest_share < avg_share * 0.8:
                insights.append(
                    Insight(
                        id="weak-region",
                        type="recommendation",
                        metric="region",
                        title=f"Review growth opportunities in {weakest_reg}",
                        summary="Its revenue share is well below an even split across regions.",
                        evidence=[
                            InsightEvidence(label=f"{weakest_reg} share", value=f"{weakest_share:.1f}%"),
                            InsightEvidence(label="Even-split benchmark", value=f"{avg_share:.1f}%")
                        ]
                    )
                )

        # 7. Low Margin Alert
        if has_cost and "cost" in current_df.columns and not current_df["cost"].isna().all():
            cat_costs = current_df[current_df["cost"].notna()].groupby("product_category").agg({"revenue": "sum", "cost": "sum"})
            cat_costs["margin"] = np.where(cat_costs["revenue"] > 0, (cat_costs["revenue"] - cat_costs["cost"]) / cat_costs["revenue"] * 100.0, 0.0)
            cat_costs = cat_costs.sort_values(by="margin")
            if not cat_costs.empty:
                lowest_cat = cat_costs.index[0]
                lowest_margin = float(cat_costs.iloc[0]["margin"])
                evidence = [
                    InsightEvidence(label=cat, value=f"{m:.1f}%")
                    for cat, m in cat_costs["margin"].items()
                ]
                insights.append(
                    Insight(
                        id="low-margin",
                        type="recommendation",
                        metric="margin",
                        title=f"{lowest_cat} has the thinnest margin at {lowest_margin:.1f}%",
                        summary="Review pricing or supplier costs for this category.",
                        evidence=evidence
                    )
                )

        # 8. Customer Repeat Rate (a "repeat" customer has 2+ distinct orders, not 2+ line items)
        if has_customers and "customer_identifier" in current_df.columns:
            with_customer = current_df.dropna(subset=["customer_identifier"])
            if not with_customer.empty:
                orders_per_customer = with_customer.groupby("customer_identifier")["order_id"].nunique()
                total_cust = len(orders_per_customer)
                repeat_cust = int((orders_per_customer > 1).sum())
                if total_cust > 0:
                    rep_rate = (repeat_cust / total_cust) * 100.0
                    insights.append(
                        Insight(
                            id="repeat-rate",
                            type="observation",
                            metric="customers",
                            title=f"{rep_rate:.1f}% of customers purchased more than once",
                            summary="Share of customers with at least two orders in the selected period.",
                            evidence=[
                                InsightEvidence(label="Total customers", value=format_number(total_cust)),
                                InsightEvidence(label="Repeat customers", value=format_number(repeat_cust))
                            ]
                        )
                    )

        return insights
