# 编码规范

> 适用范围：所有项目，所有语言

## 通用原则

- **可读性优先**：代码是写给人看的，其次才是机器执行
- **单一职责**：每个函数/类只做一件事
- **命名即注释**：变量名、函数名应自解释，减少注释依赖
- **失败快速**：在函数入口校验参数，尽早 raise/return

## Python 规范（主要语言）

### 命名
- 模块、文件：`snake_case`（如 `data_fetcher.py`）
- 类名：`PascalCase`（如 `StockDataFetcher`）
- 函数、变量：`snake_case`（如 `fetch_daily_data`）
- 常量：`UPPER_SNAKE_CASE`（如 `MAX_RETRY_COUNT = 3`）
- 私有方法：前缀 `_`（如 `_validate_symbol`）

### 类型注解
- 所有公开函数必须有完整类型注解（参数 + 返回值）
- 使用 `from __future__ import annotations` 支持前向引用
- 复杂类型用 `TypeAlias` 定义别名
- **接口层的输入/输出必须用 `stages/03-module-design/schemas/` 中的 Pydantic model**，不自定义 dataclass
- 禁止在实现中重新定义接口模型，必须 import 自 schemas

```python
# Good
def fetch_daily(symbol: str, date: date) -> pd.DataFrame:
    ...

# Bad
def fetch_daily(symbol, date):
    ...
```

### 异常处理
- 捕获具体异常，不用裸 `except:`
- 业务异常定义在 `exceptions.py`，继承自项目基础异常类
- 网络/IO 操作统一加重试装饰器

### 代码组织
- 单文件不超过 400 行；超出则拆分模块
- 导入顺序：标准库 → 第三方库 → 本项目模块，各组之间空一行
- 每个模块顶部有 `__all__` 声明公开接口

### 格式化
- 使用 `ruff` 进行 lint 和格式化
- 行宽：100 字符
- 字符串引号：双引号

## 数据库操作规范

- SQL 语句全大写关键字（`SELECT`, `FROM`, `WHERE`）
- 参数化查询，禁止字符串拼接 SQL（防止注入）
- 事务操作使用上下文管理器
- 查询结果超过 10 万行的操作，必须分批处理

## 禁止项

- 禁止 `print()` 调试代码提交（用 `logging`）
- 禁止硬编码密钥、Token、密码（用环境变量）
- 禁止 `import *`
- 禁止空 `except` 块
- 禁止注释掉的死代码提交
