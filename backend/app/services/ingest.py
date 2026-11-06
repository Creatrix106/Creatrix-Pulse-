"""Turn an uploaded CSV/Excel table into Creatrix Pulse's normalised row format.

Framework free (pandas/numpy only) so it can be unit-tested without FastAPI. The guiding
rule is *never fabricate data*: when a file cannot be interpreted we raise IngestError with
a message the user can act on, instead of inventing dates, revenue or products.
"""
import datetime as _dt
import hashlib
import io
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.config import settings
from app.services.errors import IngestError

# Same order / aliases as the frontend (src/config/files.ts) so server-side auto-detection
# (used for Excel files, which the browser cannot preview) agrees with the UI.
CANONICAL_ORDER = ["date", "product", "revenue", "quantity", "orderId", "category", "region", "customer", "cost"]
REQUIRED_FIELDS = ("date", "product", "revenue")
FIELD_LABELS = {
    "date": "Order date", "product": "Product", "revenue": "Revenue", "quantity": "Quantity",
    "orderId": "Order ID", "category": "Category", "region": "Region", "customer": "Customer", "cost": "Cost",
}
ALIASES: Dict[str, List[str]] = {
    "date": ["date", "order date", "orderdate", "invoice date", "transaction date", "day", "created at"],
    "product": ["product", "product name", "item", "item name", "sku", "title"],
    "revenue": ["revenue", "sales", "amount", "total", "total sales", "net sales", "order value", "line total"],
    "quantity": ["quantity", "qty", "units", "units sold"],
    "orderId": ["order id", "orderid", "order no", "invoice", "invoice no", "transaction id"],
    "category": ["category", "product category", "department", "type"],
    "region": ["region", "state", "zone", "area", "city", "location"],
    "customer": ["customer", "customer id", "customerid", "client", "buyer", "customer name"],
    "cost": ["cost", "cogs", "total cost", "expense", "unit cost"],
}

_YEAR_FIRST = re.compile(r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}")
_NUMERIC_DMY = re.compile(r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})\b")


# --------------------------------------------------------------------------- headers

def normalise_header(header: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(header).lower()).strip()


def clean_headers(columns: List[Any]) -> List[str]:
    """Strip BOM/whitespace (the browser trims headers before building the mapping, so the
    server must use the exact same names) and make duplicates unique."""
    seen: Dict[str, int] = {}
    out: List[str] = []
    for i, c in enumerate(columns):
        name = str(c).replace("\ufeff", "").strip() or f"Column {i + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name}.{seen[name]}"
        else:
            seen[name] = 0
        out.append(name)
    return out


def suggest_mapping(headers: List[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    used: set = set()
    for field in CANONICAL_ORDER:
        for h in headers:
            if h not in used and normalise_header(h) in ALIASES[field]:
                mapping[field] = h
                used.add(h)
                break
    return mapping


def resolve_mapping(headers: List[str], provided: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """The mapping the user confirmed in the UI is authoritative: a field they left out stays
    unmapped. Auto-detection is only used for fields that are *required* and missing (and for
    everything when no mapping was sent at all, e.g. Excel uploads)."""
    suggested = suggest_mapping(headers)
    clean: Dict[str, str] = {
        k: v for k, v in (provided or {}).items()
        if k in ALIASES and isinstance(v, str) and v.strip() in headers
    }
    clean = {k: v.strip() for k, v in clean.items()}
    if not clean:
        mapping = dict(suggested)
    else:
        mapping = dict(clean)
        for f in REQUIRED_FIELDS:
            if f not in mapping and f in suggested:
                mapping[f] = suggested[f]
    missing = [f for f in REQUIRED_FIELDS if f not in mapping]
    if missing:
        found = ", ".join(f'"{h}"' for h in headers[:12]) + (" …" if len(headers) > 12 else "")
        raise IngestError(
            "We couldn’t find a column for: " + ", ".join(FIELD_LABELS[m] for m in missing)
            + ". Rename the headers in your file (for example “Order Date”, “Product”, “Revenue”) "
            f"or map them during upload, then try again. Columns found: {found}.",
            "missing_columns",
        )
    return mapping


# --------------------------------------------------------------------------- reading

def _strip_cell(v: Any) -> Any:
    if isinstance(v, str):
        v = v.strip()
        return np.nan if v == "" else v
    return v


def read_table(file_bytes: bytes, filename: str) -> Tuple[pd.DataFrame, str]:
    ext = Path(filename or "").suffix.lower()
    if ext in (".xlsx", ".xlsm", ".xls"):
        try:
            df = pd.read_excel(io.BytesIO(file_bytes), dtype=object)
        except ImportError:
            raise IngestError(
                "Reading .xls files needs the 'xlrd' package on the server. Save the file as .xlsx or CSV and upload it again.",
                "excel_unsupported",
            )
        except Exception:
            raise IngestError(
                "This Excel file couldn’t be read. Make sure it isn’t password-protected or corrupted.",
                "unreadable_file",
            )
        kind = "excel"
    else:
        df = None
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), dtype=str, keep_default_na=False, na_values=[""], encoding=enc)
                break
            except UnicodeDecodeError:
                continue
            except pd.errors.EmptyDataError:
                raise IngestError("The file is empty.", "empty_file")
            except pd.errors.ParserError:
                raise IngestError(
                    "This CSV file couldn’t be parsed. Check that every row has the same number of columns.",
                    "unreadable_file",
                )
        if df is None:
            raise IngestError("This file’s text encoding is not supported. Save it as UTF-8 CSV and try again.", "unreadable_file")
        kind = "csv"

    df = df.astype(object).apply(lambda col: col.map(_strip_cell))
    df.columns = clean_headers(list(df.columns))
    df = df.dropna(how="all").reset_index(drop=True)
    if df.empty or len(df.columns) == 0:
        raise IngestError("The file has no data rows.", "empty_file")
    return df, kind


# --------------------------------------------------------------------------- cell parsers

def _is_missing(v: Any) -> bool:
    if v is None:
        return True
    try:
        return bool(pd.isna(v))
    except (TypeError, ValueError):
        return False


def clean_text(series: pd.Series) -> pd.Series:
    """Strings; integral floats lose the trailing '.0' (Excel stores ids/codes as floats)."""
    def conv(v: Any) -> Optional[str]:
        if _is_missing(v):
            return None
        if isinstance(v, (float, np.floating)) and float(v).is_integer():
            return str(int(v))
        t = str(v).strip()
        return t or None
    return series.map(conv).astype(object)


def to_number(series: pd.Series) -> pd.Series:
    """'₹1,299.50' -> 1299.5, '(100)' -> -100, '' / 'n/a' -> NaN."""
    def conv(v: Any) -> float:
        if _is_missing(v):
            return np.nan
        if isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool):
            return float(v)
        t = str(v).strip()
        neg = t.startswith("(") and t.endswith(")")
        t = re.sub(r"[^\d.\-]", "", t)
        if t in ("", "-", ".", "-."):
            return np.nan
        try:
            x = float(t)
        except ValueError:
            return np.nan
        return -abs(x) if neg else x
    return series.map(conv).astype(float)


def parse_dates(series: pd.Series) -> pd.Series:
    """Return 'YYYY-MM-DD' strings (NaN where unreadable).

    * year-first values (2026-03-04) are always read as Y-M-D;
    * for d/m/y vs m/d/y, unambiguous values in the file decide (13/03/2026 => day-first);
      fully ambiguous files use settings.DATE_DAYFIRST_DEFAULT.
    Parsing runs on the *distinct* values only, so a year of daily data costs ~365 parses.
    """
    resolved: Dict[Any, Optional[str]] = {}
    year_first: List[Tuple[Any, str]] = []
    other: List[Tuple[Any, str]] = []

    for u in pd.unique(series.dropna()):
        if isinstance(u, (_dt.datetime, _dt.date, pd.Timestamp)):
            ts = pd.Timestamp(u)
            resolved[u] = None if pd.isna(ts) else ts.strftime("%Y-%m-%d")
            continue
        t = str(u).strip()
        if not t:
            resolved[u] = None
        elif _YEAR_FIRST.match(t):
            year_first.append((u, t))
        else:
            other.append((u, t))

    def run(items: List[Tuple[Any, str]], **kw: Any) -> None:
        if not items:
            return
        parsed = pd.to_datetime(pd.Series([t for _, t in items]), errors="coerce", format="mixed", **kw)
        for (orig, _), ts in zip(items, parsed):
            resolved[orig] = None if pd.isna(ts) else ts.strftime("%Y-%m-%d")

    run(year_first, yearfirst=True, dayfirst=False)

    dayfirst = settings.DATE_DAYFIRST_DEFAULT
    firsts, seconds = [], []
    for _, t in other:
        m = _NUMERIC_DMY.match(t)
        if m:
            firsts.append(int(m.group(1)))
            seconds.append(int(m.group(2)))
    if firsts:
        if max(firsts) > 12:
            dayfirst = True
        elif max(seconds) > 12:
            dayfirst = False
    run(other, dayfirst=dayfirst)

    return series.map(lambda v: resolved.get(v) if not _is_missing(v) else None).astype(object)


# --------------------------------------------------------------------------- normalise

def _product_id(name: str) -> str:
    key = " ".join(name.split()).casefold()
    return "P-" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]


def normalise(df: pd.DataFrame, mapping: Dict[str, str], dataset_id: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Apply `mapping` (canonical field -> column name) and return (rows, meta).

    `rows` has exactly the columns of the dataset_rows table (plus raw_payload).
    Raises IngestError for files that cannot be interpreted.
    """
    n_in = len(df)
    date_col, rev_col = mapping["date"], mapping["revenue"]

    dates = parse_dates(df[date_col])
    bad = dates.isna()
    n_bad = int(bad.sum())
    if n_bad == n_in or n_bad / n_in > settings.MAX_BAD_DATE_SHARE:
        raise IngestError(
            f"The date column “{date_col}” could not be parsed in {n_bad:,} of {n_in:,} rows. "
            "Re-export the file with ISO dates (YYYY-MM-DD) and upload it again.",
            "invalid_dates",
        )

    revenue = to_number(df[rev_col])
    filled = df[rev_col].notna()
    if filled.any() and revenue[filled].notna().mean() < 0.5:
        raise IngestError(
            f"The revenue column “{rev_col}” does not look numeric. Map a column that holds the sales amount per row.",
            "invalid_revenue",
        )

    keep = ~bad.to_numpy()
    work = df.loc[keep]
    positions = work.index.to_numpy() + 1  # 1-based row number in the file (index was reset on read)

    def col(field: str) -> Optional[pd.Series]:
        return work[mapping[field]] if field in mapping else None

    def optional_text(field: str) -> pd.Series:
        s = col(field)
        return clean_text(s) if s is not None else pd.Series([None] * len(work), index=work.index, dtype=object)

    out = pd.DataFrame(index=work.index)
    out["dataset_id"] = dataset_id

    ids = optional_text("orderId")
    fallback_ids = pd.Series([f"ROW-{p}" for p in positions], index=work.index, dtype=object)
    out["order_id"] = ids.where(ids.notna(), fallback_ids)

    out["transaction_date"] = dates.loc[work.index]

    product = optional_text("product").fillna("Unknown product")
    out["product_name"] = product
    out["product_id"] = product.map({n: _product_id(n) for n in product.unique()})
    out["product_category"] = optional_text("category").fillna("General")
    out["region"] = optional_text("region")
    out["customer_identifier"] = optional_text("customer")

    qty_src = col("quantity")
    qty = to_number(qty_src) if qty_src is not None else pd.Series(np.nan, index=work.index)
    out["quantity"] = qty.fillna(1).round().astype(int)

    out["revenue"] = revenue.loc[work.index].fillna(0.0)
    out["unit_price"] = (out["revenue"] / out["quantity"].where(out["quantity"] > 0, 1)).round(2)

    cost_src = col("cost")
    out["cost"] = to_number(cost_src) if cost_src is not None else pd.Series(np.nan, index=work.index)

    out["id"] = [f"{dataset_id}-row-{p}" for p in positions]

    safe = work.astype(object).where(work.notna(), None)
    out["raw_payload"] = [json.dumps(rec, default=str, ensure_ascii=False) for rec in safe.to_dict("records")]

    meta = {"input_rows": n_in, "dropped_rows": n_bad}
    return out.reset_index(drop=True), meta
