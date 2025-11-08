"""Utility for matching purchase prices and customer regions for sales orders.

This module implements the logic required to augment a sales order detail table with
purchase price information (converted to USD) and customer region data. The matching
rules follow the specifications provided in the project documentation:

* Only rows whose order type is "标准销售订单" will attempt to match the purchase price
  based on the two most recent purchase receipts (from the purchase detail table)
  whose posting date is on or before the sales order creation date.
* If only a single purchase receipt exists before the sales order date, the single
  USD price is used. If no receipts exist the row is flagged as a failure.
* Rows whose order type is "标准销售退货订单" receive the purchase price from the most
  recent successful "标准销售订单" row for the same material whose creation date is
  before the return order.
* Other order types leave the purchase price columns empty.
* Purchase prices are normalised to USD using the exchange-rate table. When the
  original currency is already USD, the value is used directly.
* The resulting sales table also includes the customer region obtained by joining
  the sales table and the customer region table on the "售达方" column.

The main entry point is :func:`augment_sales_with_costs`, which accepts either file
paths to the required workbooks or already loaded ``pandas.DataFrame`` objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Union

import pandas as pd

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class PurchaseMatchResult:
    """Container describing the outcome of a purchase price match."""

    price_usd: Optional[float]
    failure: bool
    reason: Optional[str]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _ensure_datetime(df: pd.DataFrame, column: str) -> pd.Series:
    """Return the column converted to ``datetime64[ns]``.

    Parameters
    ----------
    df:
        The dataframe containing the column.
    column:
        Name of the column to convert. The function leaves the original column in
        place and returns the converted series so callers can assign it back.
    """

    return pd.to_datetime(df[column], errors="coerce")


def _normalise_purchase_prices(
    purchases: pd.DataFrame, fx_rates: pd.DataFrame
) -> pd.DataFrame:
    """Attach exchange rates and compute the USD unit price for purchases."""

    if "币种" not in purchases.columns:
        raise KeyError("采购入库明细表缺少 '币种' 列")
    if "单价（不含税）" not in purchases.columns:
        raise KeyError("采购入库明细表缺少 '单价（不含税）' 列")

    merged = purchases.merge(
        fx_rates, how="left", on="币种", validate="many_to_one", suffixes=(None, "_汇率")
    )

    if merged["汇率"].isna().any():
        missing = merged.loc[merged["汇率"].isna(), "币种"].unique()
        raise ValueError(f"汇率表缺少以下币种的汇率: {', '.join(map(str, missing))}")

    merged = merged.copy()
    merged["unit_price_usd"] = merged["单价（不含税）"].astype(float) / merged["汇率"].astype(float)
    return merged


def _group_purchases(purchases: pd.DataFrame) -> dict:
    """Return a mapping of material code to purchase rows sorted by posting date."""

    required_cols = {"物料编码", "过账日期", "unit_price_usd"}
    missing = required_cols - set(purchases.columns)
    if missing:
        raise KeyError(f"采购入库明细表缺少列: {', '.join(sorted(missing))}")

    grouped = {}
    for material, group in purchases.groupby("物料编码"):
        grouped[material] = group.sort_values("过账日期")
    return grouped


def _match_standard_sale(
    sale_row: pd.Series, purchase_groups: dict
) -> PurchaseMatchResult:
    """Match purchase price for a standard sales order."""

    material = sale_row.get("物料编码")
    sale_date = sale_row.get("创建日期")

    if pd.isna(material) or pd.isna(sale_date):
        return PurchaseMatchResult(None, True, "缺少物料编码或创建日期")

    purchases = purchase_groups.get(material)
    if purchases is None:
        return PurchaseMatchResult(None, True, "无历史采购记录")

    valid = purchases[purchases["过账日期"] <= sale_date]
    if valid.empty:
        return PurchaseMatchResult(None, True, "销售日期之前无采购记录")

    recent = valid.tail(2)
    return PurchaseMatchResult(float(recent["unit_price_usd"].mean()), False, None)


def _match_return_sale(
    sale_row: pd.Series, previous_sales: pd.DataFrame
) -> PurchaseMatchResult:
    """Match purchase price for a standard sales return order."""

    material = sale_row.get("物料编码")
    sale_date = sale_row.get("创建日期")

    if pd.isna(material) or pd.isna(sale_date):
        return PurchaseMatchResult(None, True, "缺少物料编码或创建日期")

    candidates = previous_sales[
        (previous_sales["物料编码"] == material)
        & (previous_sales["创建日期"] < sale_date)
        & (previous_sales["订单类型"] == "标准销售订单")
        & (~previous_sales["采购单价匹配失败"])
        & (previous_sales["采购单价USD"].notna())
    ]

    if candidates.empty:
        return PurchaseMatchResult(None, True, "无可参考的标准销售订单")

    latest = candidates.sort_values("创建日期").iloc[-1]
    return PurchaseMatchResult(float(latest["采购单价USD"]), False, None)


def _load_dataframe(data: Union[str, Path, pd.DataFrame]) -> pd.DataFrame:
    """Load a dataframe from a path or return it as-is."""

    if isinstance(data, pd.DataFrame):
        return data.copy()
    path = Path(data)
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_excel(path)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def augment_sales_with_costs(
    sales_data: Union[str, Path, pd.DataFrame],
    purchase_data: Union[str, Path, pd.DataFrame],
    fx_data: Union[str, Path, pd.DataFrame],
    region_data: Union[str, Path, pd.DataFrame],
) -> Tuple[pd.DataFrame, List[str]]:
    """Augment the sales order table with purchase prices and customer regions.

    Returns the augmented sales dataframe and a list of material codes that failed
    to obtain a purchase price.
    """

    sales = _load_dataframe(sales_data)
    purchases = _load_dataframe(purchase_data)
    fx_rates = _load_dataframe(fx_data)
    regions = _load_dataframe(region_data)

    if "创建日期" not in sales.columns:
        raise KeyError("销售订单明细表缺少 '创建日期' 列")
    if "订单类型" not in sales.columns:
        raise KeyError("销售订单明细表缺少 '订单类型' 列")

    sales = sales.copy()
    sales["创建日期"] = _ensure_datetime(sales, "创建日期")

    purchases = purchases.copy()
    purchases["过账日期"] = _ensure_datetime(purchases, "过账日期")
    purchases = _normalise_purchase_prices(purchases, fx_rates)
    purchase_groups = _group_purchases(purchases)

    sales["采购单价USD"] = pd.NA
    sales["采购币种"] = pd.NA
    sales["采购单价匹配失败"] = False
    sales["采购匹配失败原因"] = pd.NA

    # Process standard sales orders
    standard_mask = sales["订单类型"] == "标准销售订单"
    for idx, row in sales[standard_mask].iterrows():
        result = _match_standard_sale(row, purchase_groups)
        if result.failure:
            sales.at[idx, "采购单价匹配失败"] = True
            sales.at[idx, "采购匹配失败原因"] = result.reason
            sales.at[idx, "采购单价USD"] = pd.NA
            sales.at[idx, "采购币种"] = pd.NA
        else:
            sales.at[idx, "采购单价USD"] = result.price_usd
            sales.at[idx, "采购币种"] = "USD"

    # Process standard sales returns using prior successful matches
    return_mask = sales["订单类型"] == "标准销售退货订单"
    for idx, row in sales[return_mask].iterrows():
        result = _match_return_sale(row, sales)
        if result.failure:
            sales.at[idx, "采购单价匹配失败"] = True
            sales.at[idx, "采购匹配失败原因"] = result.reason
            sales.at[idx, "采购单价USD"] = pd.NA
            sales.at[idx, "采购币种"] = pd.NA
        else:
            sales.at[idx, "采购单价USD"] = result.price_usd
            sales.at[idx, "采购币种"] = "USD"

    # Other order types leave the default values (no price match attempt)

    sales = sales.merge(regions[["售达方", "区域"]], how="left", on="售达方")

    failed_materials = (
        sales.loc[sales["采购单价匹配失败"], "物料编码"].dropna().astype(str).unique().tolist()
    )
    return sales, failed_materials


def process_and_export(
    sales_path: Union[str, Path],
    purchase_path: Union[str, Path],
    fx_path: Union[str, Path],
    region_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
) -> Tuple[pd.DataFrame, List[str]]:
    """High-level helper that augments the sales data and optionally exports it."""

    sales_augmented, failed_materials = augment_sales_with_costs(
        sales_path, purchase_path, fx_path, region_path
    )

    if output_path is not None:
        output_path = Path(output_path)
        sales_augmented.to_excel(output_path, index=False)

    return sales_augmented, failed_materials


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Match purchase prices and regions for sales order details."
    )
    parser.add_argument("sales", help="销售订单明细表文件路径")
    parser.add_argument("purchases", help="采购入库明细表文件路径")
    parser.add_argument("fx", help="汇率表文件路径")
    parser.add_argument("regions", help="客户销售区域表文件路径")
    parser.add_argument(
        "-o",
        "--output",
        help="输出的Excel文件路径（可选）",
    )

    args = parser.parse_args()
    result_df, failures = process_and_export(
        args.sales, args.purchases, args.fx, args.regions, args.output
    )

    print("处理完成，共输出 {} 行".format(len(result_df)))
    if failures:
        print("以下物料编码未能匹配采购单价: {}".format(", ".join(map(str, failures))))
    else:
        print("所有物料均成功匹配采购单价。")
