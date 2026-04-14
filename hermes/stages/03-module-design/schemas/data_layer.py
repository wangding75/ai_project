"""数据层接口 Schema（行情数据获取）"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

__all__ = [
    "FetchDailyRequest",
    "FetchDailyResponse",
    "DailyBar",
    "DataLayerErrors",
]


class FetchDailyRequest(BaseModel):
    """获取日线行情数据的请求"""

    symbol: str = Field(
        ...,
        pattern=r"^\d{6}\.(SZ|SH)$",
        description="股票代码，格式 '000001.SZ' 或 '600000.SH'",
    )
    start_date: date = Field(..., description="起始日期（含）")
    end_date: date = Field(..., description="结束日期（含）")
    adjust: Literal["qfq", "hfq", "none"] = Field(
        "qfq", description="复权方式：qfq=前复权, hfq=后复权, none=不复权"
    )

    @field_validator("end_date")
    @classmethod
    def end_date_must_not_be_before_start(cls, v: date, info) -> date:
        start = info.data.get("start_date")
        if start and v < start:
            raise ValueError("end_date must not be before start_date")
        return v


class DailyBar(BaseModel):
    """单日 OHLCV 数据"""

    trade_date: date
    open: float = Field(..., gt=0, description="开盘价")
    high: float = Field(..., gt=0, description="最高价")
    low: float = Field(..., gt=0, description="最低价")
    close: float = Field(..., gt=0, description="收盘价")
    volume: int = Field(..., ge=0, description="成交量（手）")


class FetchDailyResponse(BaseModel):
    symbol: str
    adjust: Literal["qfq", "hfq", "none"]
    bars: list[DailyBar]
    upstream_source: Literal["tushare", "akshare", "cache"] = Field(
        ..., description="实际命中的数据源，用于降级追踪"
    )


class DataLayerErrors:
    """数据层错误码"""

    INVALID_SYMBOL = "data_layer.invalid_symbol"
    DATA_NOT_FOUND = "data_layer.data_not_found"
    UPSTREAM_TIMEOUT = "data_layer.upstream_timeout"
    UPSTREAM_UNAVAILABLE = "data_layer.upstream_unavailable"
    CACHE_STALE = "data_layer.cache_stale"
    DATE_RANGE_TOO_LARGE = "data_layer.date_range_too_large"
