# API 设计规范

> 适用范围：所有项目的接口定义（schemas/）、接口说明（api-spec.md）、REST API 设计

## 核心原则：Schema 是真相源头

接口定义有**两种表达形式**，但**只有一种是真相**：

| 表达 | 作用 | 状态 |
|------|------|------|
| `schemas/*.py` (Pydantic) | 机器可执行的真相源头，测试从此派生 | **权威** |
| `api-spec.md` | 人类可读的叙事说明（设计动机、生产级契约）| 补充性 |

**任何冲突以 schema 为准。** Markdown 只作为理解辅助，不作为测试生成依据。

## Schema 文件组织

```
stages/03-module-design/schemas/
├── __init__.py
├── common.py              # 公共类型（错误码基类、分页、响应包装）
├── data_layer.py          # 每个模块一个文件
├── factor_engine.py
├── strategy.py
└── slo.yaml               # 非功能性约束（SLO/指标/日志字段）
```

## Pydantic Schema 规范

每个模块的 schema 文件必须包含：

1. **Request / Response 模型**：继承 `BaseModel`，字段带约束（`Field(..., pattern=..., gt=..., ge=...)`）
2. **错误码类**：`class <Module>Errors: ...`，字符串常量
3. **显式导出**：`__all__ = [...]`

**示例：**

```python
# schemas/data_layer.py
from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import date
from typing import Literal

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
    adjust: Literal["qfq", "hfq", "none"] = Field("qfq", description="复权方式")


class DailyBar(BaseModel):
    """单日 OHLCV"""

    trade_date: date
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: int = Field(..., ge=0)


class FetchDailyResponse(BaseModel):
    symbol: str
    bars: list[DailyBar]


class DataLayerErrors:
    """数据层错误码"""

    INVALID_SYMBOL = "data_layer.invalid_symbol"
    DATA_NOT_FOUND = "data_layer.data_not_found"
    UPSTREAM_TIMEOUT = "data_layer.upstream_timeout"
    CACHE_STALE = "data_layer.cache_stale"
```

## 生产级契约模板（`api-spec.md` 每个接口必填）

**这不是可选项。** 没有填写这些信息的接口，`check_stage.py` 会判定 FAIL。

```markdown
## 接口：<InterfaceName>

### 功能契约（Schema）
参见 `schemas/<module>.py::<Request>` / `<Response>`

### SLO 契约
| 指标 | 目标 |
|------|------|
| P50 延迟 | < 50ms |
| P99 延迟 | < 300ms |
| 可用性 | 99.5% |
| 错误率 | < 0.1% |

### 可观测性契约

**必须打印的日志字段：**
- `trace_id`（贯穿整条请求链路）
- `<业务参数1>, <业务参数2>, ...`
- `duration_ms`（性能追踪）
- `<外部依赖命中标记>`

**必须暴露的指标（Prometheus）：**
- `<project>_<module>_requests_total{...}` (Counter)
- `<project>_<module>_duration_seconds{...}` (Histogram)

### 降级契约
| 场景 | 降级策略 |
|------|---------|
| 主上游超时 | 切换备用源 |
| 备用源失败 | 返回缓存（stale 标记） |
| 缓存也没有 | 返回明确错误码，入补跑队列 |

### 安全契约
- 认证：<方式>
- 限流：<阈值>
- 输入校验：<依赖 Pydantic Field 约束>
```

## SLO YAML 规范

`schemas/slo.yaml` 是机器可读的非功能性约束：

```yaml
# schemas/slo.yaml
modules:
  data_layer:
    slo:
      p50_latency_ms: 50
      p99_latency_ms: 300
      availability: 0.995
      error_rate: 0.001
    logging_required_fields:
      - trace_id
      - symbol
      - start_date
      - end_date
      - duration_ms
      - upstream_source
    metrics_required:
      - name: hermes_data_fetch_requests_total
        type: counter
        labels: [symbol, source, status]
      - name: hermes_data_fetch_duration_seconds
        type: histogram
        labels: [symbol, source]
    fallback_required: true
```

阶段 04 的 TDD 测试从这个 YAML 生成断言。

## REST API 规范（FastAPI 项目）

### URL 设计

```
GET    /api/v1/stocks/{symbol}/daily
POST   /api/v1/trades
```

- 资源用名词复数，不用动词
- 版本号在路径中
- 层级 ≤ 3 层

### 响应格式（统一包装）

```python
# common.py
class ApiResponse(BaseModel):
    code: int
    data: Any | None = None
    message: str = "success"
    error_type: str | None = None
```

### HTTP 状态码

| 场景 | 状态码 |
|------|--------|
| 成功 | 200 / 201 |
| 参数错误 | 400 |
| 未授权 | 401 |
| 资源不存在 | 404 |
| 限流 | 429 |
| 服务器错误 | 500 |

## 禁止项

- 禁止只写 Markdown 不写 Schema（测试就没有真相源头了）
- 禁止在 GET 请求传敏感信息
- 禁止不同接口返回不同 schema（error 和 success 要统一包装）
- 禁止用 HTTP 200 返回业务错误
- 禁止接口定义缺少 SLO/日志/降级契约
