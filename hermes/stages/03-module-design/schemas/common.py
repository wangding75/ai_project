"""公共类型：响应包装、错误码基类、分页"""
from __future__ import annotations

from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

__all__ = [
    "ApiResponse",
    "Pagination",
    "ErrorCode",
]


class Pagination(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=200)
    total: int = Field(..., ge=0)


class ApiResponse(BaseModel):
    """统一响应包装

    所有对外接口返回此结构。成功时 code=200，data 为业务数据。
    失败时 code 为 HTTP 状态码，error_type 为错误码字符串（来自 <Module>Errors）。
    """

    code: int = 200
    data: Any | None = None
    message: str = "success"
    error_type: str | None = None


class ErrorCode:
    """错误码字符串常量基类。

    命名约定：`<module>.<error_name>`（小写 + 点分隔）。
    业务错误使用对应的 <Module>Errors 子类。
    """

    INTERNAL_ERROR = "common.internal_error"
    INVALID_REQUEST = "common.invalid_request"
    UNAUTHORIZED = "common.unauthorized"
    RATE_LIMITED = "common.rate_limited"
