# Hermes · 系统设计文档

> **版本**: V1.1 | **日期**: 2026年4月 | **依据需求文档**: V1.4

---

## 目录

1. [总体架构](#一总体架构)
2. [目录结构](#二目录结构)
3. [数据库设计](#三数据库设计)
4. [模块设计](#四模块设计)
5. [数据流设计](#五数据流设计)
6. [API 接口设计](#六api-接口设计)
7. [调度任务设计（N8N）](#七调度任务设计n8n)
8. [基础设施设计](#八基础设施设计)
9. [消息通信设计](#九消息通信设计)
10. [安全设计](#十安全设计)
11. [可观测性设计](#十一可观测性设计)
12. [任务执行链路设计](#十二任务执行链路设计)
13. [模型训练基础设施](#十三模型训练基础设施)

---

## 一、总体架构

### 1.1 架构风格

Hermes 采用**模块化单体（Modular Monolith）**架构部署在单台 VPS 上，通过 Docker Compose 容器编排。各业务模块以 Python Package 形式独立封装，共享进程内调用，通过 N8N 编排外部触发，预留未来拆分为微服务的接口边界。

```
┌─────────────────────────────────────────────────────────────────┐
│                        VPS (Docker Compose)                     │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │  N8N     │  │ FastAPI  │  │ Worker   │  │  Scheduler   │   │
│  │ 调度引擎  │  │ Web服务  │  │ 异步任务  │  │  (Celery/   │   │
│  │ :5678    │  │ :8000    │  │ 处理器   │  │   ARQ)       │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘   │
│       │             │              │                │           │
│  ─────┴─────────────┴──────────────┴────────────────┴───────   │
│                    内部服务总线（Python 函数调用）                │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                      业务模块层                             │ │
│  │  数据系统 │ 因子引擎 │ AI模型 │ 策略体系 │ 情绪系统         │ │
│  │  风控体系 │ 交易系统 │ 监控   │ 回测    │ 报告 │ 通信       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌────────────┐  ┌────────────┐  ┌────────┐  ┌─────────────┐  │
│  │ PostgreSQL │  │ ClickHouse │  │ Redis  │  │   MinIO     │  │
│  │ 业务数据库  │  │ 行情/因子库 │  │ 热缓存 │  │  文件存储   │  │
│  └────────────┘  └────────────┘  └────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
   Telegram Bot                    飞书机器人
```

### 1.2 核心设计原则

| 原则 | 说明 |
|------|------|
| **单一数据入口** | 所有 A 股数据通过 DataAdapter 统一获取，业务模块不直接调用数据源 API |
| **时序严格性** | 所有计算严格遵守 T 日只能使用 T-1 及之前数据（前向偏差防控） |
| **无 Mock 数据** | 开发与测试均使用真实数据，CP 验证点为硬性门槛 |
| **接口预留** | A 阶段（人工回填）与 B 阶段（券商 API）数据结构完全一致 |
| **幂等性** | 所有数据写入操作支持重入（失败重试不产生重复数据） |
| **可追溯** | 每个信号记录完整触发链路，支持事后复盘 |
| **面向接口** | 数据源、模型实现、训练后端、消息渠道均通过抽象接口定义，运行时可替换 |

### 1.3 技术栈确认

| 组件 | 选型 | 版本 |
|------|------|------|
| 开发语言 | Python | 3.11+ |
| Web 框架 | FastAPI | 0.115+ |
| 任务队列 | ARQ（基于 Redis） | 0.25+ |
| 调度引擎 | N8N（自托管） | 最新稳定版 |
| 业务数据库 | PostgreSQL | 16 |
| 行情/因子库 | ClickHouse | 24+ |
| 热缓存 | Redis | 7 |
| 文件存储 | MinIO | 最新稳定版 |
| 容器编排 | Docker Compose | v2 |
| 主数据源 | Tushare Pro | — |
| 备用数据源 | AkShare | — |
| ML 框架 | XGBoost + PyTorch + scikit-learn | — |

---

## 二、目录结构

```
hermes/
├── docker-compose.yml              # 容器编排配置
├── .env.example                    # 环境变量模板
├── pyproject.toml                  # 项目依赖与配置
├── Makefile                        # 常用运维命令（含 train-quarterly 等命令）
├── alembic/                        # PostgreSQL 数据库迁移（Alembic）
│   ├── alembic.ini
│   └── versions/
├── docs/                           # 文档体系（对应需求 §15）
│   ├── strategies/                 # 各策略说明文档
│   ├── models/                     # 模型训练记录
│   └── superpowers/specs/          # 设计规格文档
│
├── hermes/                         # 主包
│   ├── __init__.py
│   ├── config.py                   # 全局配置（从环境变量读取）
│   │
│   ├── core/                       # 核心基础设施
│   │   ├── db.py                   # 数据库连接池（PostgreSQL + ClickHouse）
│   │   ├── cache.py                # Redis 缓存工具
│   │   ├── logger.py               # 统一日志配置
│   │   ├── exceptions.py           # 自定义异常类
│   │   └── utils.py                # 通用工具函数
│   │
│   ├── data/                       # 数据系统
│   │   ├── adapters/
│   │   │   ├── base.py             # DataAdapter 抽象基类
│   │   │   ├── tushare.py          # Tushare Pro 适配器
│   │   │   └── akshare.py          # AkShare 适配器
│   │   ├── fetcher.py              # 数据获取入口（含自动切换逻辑）
│   │   ├── cleaner.py              # 数据清洗（去极值、标准化、中性化）
│   │   ├── validator.py            # 数据完整性校验
│   │   ├── writer.py               # 数据写入 ClickHouse/PostgreSQL
│   │   └── exporter.py             # DataExporter 接口：导出训练数据至 MinIO/本地
│   │
│   ├── universe/                   # 股票池管理
│   │   ├── filter.py               # 过滤规则（ST、新股、科创板等）
│   │   └── snapshot.py             # 历史股票池快照管理
│   │
│   ├── factors/                    # 因子引擎
│   │   ├── base.py                 # Factor 抽象基类
│   │   ├── pipeline.py             # 两阶段计算流水线（同步核心 + 异步全量）
│   │   ├── registry.py             # 因子注册表
│   │   ├── basic/                  # 基础因子（160+）
│   │   ├── microstructure/         # 微观结构因子（80）
│   │   ├── alternative/            # 另类数据因子（70）
│   │   ├── industry_chain/         # 产业链因子（100）
│   │   ├── behavioral/             # 行为金融因子（100）
│   │   └── macro/                  # 宏观因子（50）
│   │
│   ├── models/                     # AI 模型体系
│   │   ├── base.py                 # BaseModel 抽象基类（预测接口）
│   │   ├── trainer_base.py         # BaseTrainer 抽象基类（训练接口）
│   │   ├── trainer_backend.py      # TrainingBackend 抽象基类（CPU/云GPU 可替换）
│   │   ├── backends/
│   │   │   ├── cpu_backend.py      # 本地 CPU 训练后端
│   │   │   └── cloud_gpu_backend.py# 云 GPU 训练后端（按需启动）
│   │   ├── xgboost_scorer.py       # 选股评分模型（XGBoost）
│   │   ├── sector_rotation.py      # 板块轮动模型（Transformer + GAT）
│   │   ├── trend_predictor.py      # 趋势预测模型（LSTM + Attention）
│   │   ├── sentiment_nlp.py        # 情感分析模型（BERT）
│   │   ├── hf_signal.py            # 高频信号模型
│   │   ├── position_optimizer.py   # 仓位优化模型（PPO）
│   │   ├── ensemble.py             # 集成决策模型（Stacking）
│   │   ├── walk_forward.py         # Walk-forward 训练框架（调用 BaseTrainer）
│   │   ├── online_learner.py       # 在线学习（增量训练，仅 XGBoost，CPU 可接受）
│   │   └── registry.py             # 模型版本管理（新模型 AUC≥旧模型才激活）
│   │
│   ├── strategies/                 # 策略体系（14套）
│   │   ├── base.py                 # Strategy 抽象基类
│   │   ├── registry.py             # 策略注册与权重管理
│   │   ├── limitup.py              # 涨停板策略（首板/二板/三板）
│   │   ├── hot_money.py            # 游资跟踪策略
│   │   ├── dragon_tiger.py         # 龙虎榜策略
│   │   ├── hot_money_pattern.py    # 游资战法识别
│   │   ├── northbound.py           # 北向资金策略
│   │   ├── margin.py               # 融资融券策略
│   │   ├── institution.py          # 机构抱团策略
│   │   ├── main_capital.py         # 主力资金策略
│   │   ├── multi_cycle.py          # 多周期共振策略
│   │   ├── sector_rotation.py      # 板块轮动策略
│   │   ├── limitup_data.py         # 涨停数据分析策略
│   │   ├── day_trading.py          # 日内做 T 策略
│   │   ├── cross_market.py         # 跨市场联动策略（扩展）
│   │   └── options_hedge.py        # 期权策略（扩展）
│   │
│   ├── sentiment/                  # 情绪周期系统
│   │   ├── calculator.py           # 情绪分计算
│   │   ├── phases.py               # 四阶段判断与平滑（MA5 穿越机制）
│   │   └── monitor.py              # SentimentMonitor 类
│   │
│   ├── signals/                    # 信号生成与聚合
│   │   ├── generator.py            # 信号生成（汇总策略结果 + AI 评分）
│   │   ├── aggregator.py           # 加权评分聚合
│   │   ├── ranker.py               # 候选股排序（Top 20）
│   │   └── grade.py                # 买点分级（SS/S/A/B）
│   │
│   ├── risk/                       # 风控体系
│   │   ├── position.py             # 仓位风控（25% 上限、Kelly 公式）
│   │   ├── portfolio.py            # 组合风控（回撤、单日亏损）
│   │   ├── sentiment_guard.py      # 情绪保护机制
│   │   └── emergency.py            # 紧急预案（一键清仓）
│   │
│   ├── trading/                    # 交易系统
│   │   ├── accounts.py             # 多账户管理
│   │   ├── positions.py            # 持仓管理
│   │   ├── execution.py            # 执行层（A 阶段：人工 / B 阶段：API）
│   │   ├── fill.py                 # 回填处理（A 阶段用户回填）
│   │   ├── stop_loss.py            # 止损止盈逻辑
│   │   └── tracker.py              # 效果追踪
│   │
│   ├── monitoring/                 # 实时监控
│   │   ├── realtime.py             # 盘中实时监控（每5分钟）
│   │   ├── alert.py                # 即时预警
│   │   ├── dragon_tiger_live.py    # 龙虎榜实时解析
│   │   └── t_trading.py            # 做 T 系统
│   │
│   ├── backtest/                   # 回测系统
│   │   ├── engine.py               # 回测引擎主入口
│   │   ├── data_loader.py          # 历史数据加载（历史截面股票池）
│   │   ├── simulator.py            # 交易模拟（滑点、手续费、涨跌停处理）
│   │   ├── metrics.py              # 风险指标计算（夏普、最大回撤等）
│   │   └── optimizer.py            # 参数优化（无限迭代）
│   │
│   ├── reports/                    # 报告系统
│   │   ├── daily.py                # 日终总结报告
│   │   ├── weekly.py               # 周报（信号效果追踪）
│   │   ├── intraday.py             # 盘中报告
│   │   └── model_report.py         # 模型迭代报告
│   │
│   ├── messaging/                  # 消息通信
│   │   ├── base.py                 # MessageChannel 抽象基类（面向接口，渠道可替换）
│   │   ├── gateway.py              # 统一消息网关
│   │   ├── telegram_bot.py         # Telegram Bot 实现
│   │   └── feishu_bot.py           # 飞书机器人实现
│   │
│   ├── learning/                   # 学习系统
│   │   ├── feedback_collector.py   # 实盘反馈收集（从 signal_outcomes 聚合训练样本）
│   │   ├── trigger.py              # 增量训练触发器（实盘反馈积累 N 条后触发 online_learner）
│   │   └── progress_report.py      # 学习进度报告生成
│   │
│   └── api/                        # FastAPI Web 服务
│       ├── main.py                 # App 入口
│       ├── routers/
│       │   ├── webhook.py          # Telegram/飞书 Webhook 接收
│       │   ├── n8n.py              # N8N 回调接口
│       │   ├── trading.py          # 回填与交易记录接口
│       │   └── status.py           # 系统状态查询
│       └── middleware.py           # 认证、限流中间件
│
├── scripts/                        # 运维脚本
│   ├── init_db.py                  # 初始化数据库表结构
│   ├── backfill.py                 # 历史数据补跑
│   └── health_check.py             # 健康检查
│
└── tests/                          # 测试（仅集成测试，无 Mock）
    ├── cp1_data_layer/             # CP1：数据层验证
    ├── cp2_factor_model/           # CP2：因子+模型验证
    ├── cp3_strategy_signal/        # CP3：策略+信号验证
    ├── cp4_push/                   # CP4：推送验证
    └── cp5_fill_record/            # CP5：回填+记录验证
```

---

## 三、数据库设计

### 3.1 PostgreSQL 16（业务数据库）

#### 账户与持仓

```sql
-- 交易账户
CREATE TABLE accounts (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    mode        CHAR(1) NOT NULL CHECK (mode IN ('A', 'B')), -- A：同策略多账户 / B：A/B对比
    total_asset NUMERIC(18, 2) NOT NULL DEFAULT 0,           -- 总资产（现金+持仓市值）
    cash        NUMERIC(18, 2) NOT NULL DEFAULT 0,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    broker_type VARCHAR(50),                                  -- B阶段：QMT/XTP等
    broker_cfg  JSONB,                                        -- B阶段：券商连接配置（加密存储）
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 当前持仓
CREATE TABLE positions (
    id             SERIAL PRIMARY KEY,
    account_id     INT NOT NULL REFERENCES accounts(id),
    ts_code        VARCHAR(12) NOT NULL,                      -- 股票代码（Tushare格式，如 000001.SZ）
    stock_name     VARCHAR(50),
    quantity       INT NOT NULL,
    avg_cost       NUMERIC(10, 4) NOT NULL,                   -- 持仓均价
    current_price  NUMERIC(10, 4),
    market_value   NUMERIC(18, 2),
    unrealized_pnl NUMERIC(18, 2),
    stop_loss_price NUMERIC(10, 4),                           -- 当前止损价
    opened_at      TIMESTAMPTZ NOT NULL,
    last_updated   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (account_id, ts_code)
);
```

#### 信号与交易记录

```sql
-- 信号记录（完整触发链路）
CREATE TABLE signals (
    id              BIGSERIAL PRIMARY KEY,
    signal_date     DATE NOT NULL,
    ts_code         VARCHAR(12) NOT NULL,
    stock_name      VARCHAR(50),
    composite_score NUMERIC(5, 2) NOT NULL,                   -- 综合评分 0-100
    grade           VARCHAR(4) NOT NULL CHECK (grade IN ('SS', 'S', 'A', 'B', 'SKIP')),
    suggested_pct   NUMERIC(5, 2),                            -- 建议仓位%
    triggered_strategies JSONB NOT NULL,                      -- [{"name":"limitup","score":88.5,"weight":0.15}, ...]
    ai_score        NUMERIC(5, 2),                            -- XGBoost评分
    sentiment_phase VARCHAR(20),                              -- 情绪阶段
    sentiment_score NUMERIC(5, 2),                            -- 情绪分
    signal_type     VARCHAR(20) NOT NULL DEFAULT 'buy',       -- buy / sell / warning
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',   -- pending / adopted / rejected / expired
    reject_reason   VARCHAR(200),
    pushed_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_signals_date ON signals(signal_date);
CREATE INDEX idx_signals_ts_code ON signals(ts_code);

-- 交易执行记录（A/B阶段字段一致）
CREATE TABLE trades (
    id              BIGSERIAL PRIMARY KEY,
    signal_id       BIGINT REFERENCES signals(id),
    account_id      INT NOT NULL REFERENCES accounts(id),
    ts_code         VARCHAR(12) NOT NULL,
    trade_type      VARCHAR(10) NOT NULL CHECK (trade_type IN ('buy', 'sell')),
    quantity        INT NOT NULL,
    price           NUMERIC(10, 4) NOT NULL,                  -- 实际成交均价
    amount          NUMERIC(18, 2) NOT NULL,                  -- 实际成交金额
    commission      NUMERIC(10, 4),                           -- 手续费
    slippage        NUMERIC(10, 4),                           -- 滑点（建议价与成交价差）
    trade_time      TIMESTAMPTZ NOT NULL,
    source          VARCHAR(20) NOT NULL DEFAULT 'manual',    -- manual（A阶段）/ api（B阶段）
    sell_reason     VARCHAR(50),                              -- stop_loss/take_profit/sentiment/time/other
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 效果追踪（每笔信号的完整生命周期）
CREATE TABLE signal_outcomes (
    id              BIGSERIAL PRIMARY KEY,
    signal_id       BIGINT NOT NULL REFERENCES signals(id),
    buy_trade_id    BIGINT REFERENCES trades(id),
    sell_trade_id   BIGINT REFERENCES trades(id),
    hold_days       INT,
    max_gain_pct    NUMERIC(8, 4),                            -- 最高浮盈%
    max_loss_pct    NUMERIC(8, 4),                            -- 最大浮亏%
    realized_pnl    NUMERIC(18, 2),
    realized_pnl_pct NUMERIC(8, 4),
    is_profitable   BOOLEAN,
    closed_at       TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### 策略与模型管理

```sql
-- 策略历史胜率（动态更新）
CREATE TABLE strategy_performance (
    id              SERIAL PRIMARY KEY,
    strategy_name   VARCHAR(100) NOT NULL,
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    total_signals   INT NOT NULL DEFAULT 0,
    win_count       INT NOT NULL DEFAULT 0,
    win_rate        NUMERIC(5, 4),                            -- 0.0000 - 1.0000
    avg_return      NUMERIC(8, 4),
    current_weight  NUMERIC(6, 4),                            -- 当前策略权重
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (strategy_name, period_end)
);

-- AI 模型版本管理
CREATE TABLE model_versions (
    id              SERIAL PRIMARY KEY,
    model_name      VARCHAR(100) NOT NULL,                    -- xgboost_scorer / ensemble 等
    version         VARCHAR(50) NOT NULL,
    train_start     DATE NOT NULL,
    train_end       DATE NOT NULL,
    validate_start  DATE NOT NULL,
    validate_end    DATE NOT NULL,
    metrics         JSONB NOT NULL,                           -- {"auc": 0.85, "ic": 0.12, ...}
    artifact_path   VARCHAR(500),                             -- MinIO 路径
    is_active       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (model_name, version)
);
```

#### 情绪与股票池

```sql
-- 情绪历史记录
CREATE TABLE sentiment_history (
    trade_date      DATE PRIMARY KEY,
    limitup_count   INT,                                      -- 涨停家数
    limitup_ratio   NUMERIC(6, 4),                            -- 涨停率
    blowup_rate     NUMERIC(6, 4),                            -- 炸板率
    consecutive_rate NUMERIC(6, 4),                           -- 连板率
    profit_effect   NUMERIC(8, 4),                            -- 赚钱效应指数
    sentiment_score NUMERIC(5, 2) NOT NULL,                   -- 情绪分 0-100
    sentiment_ma5   NUMERIC(5, 2),                            -- 5日均线
    phase           VARCHAR(20) NOT NULL,                     -- 冰点期/回暖期/主升期/高潮期
    max_position_pct NUMERIC(5, 2),                           -- 当日仓位上限%
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 股票池日历史快照（防幸存者偏差）
CREATE TABLE universe_snapshots (
    trade_date      DATE NOT NULL,
    ts_code         VARCHAR(12) NOT NULL,
    stock_name      VARCHAR(50),
    list_date       DATE,
    market_cap      NUMERIC(18, 2),                           -- 流通市值（亿元）
    avg_amount_20d  NUMERIC(18, 2),                           -- 近20日日均成交额（万元）
    close_price     NUMERIC(10, 4),
    PRIMARY KEY (trade_date, ts_code)
);

-- 任务执行日志（N8N 任务追踪）
CREATE TABLE task_logs (
    id              BIGSERIAL PRIMARY KEY,
    task_name       VARCHAR(100) NOT NULL,
    trade_date      DATE,
    started_at      TIMESTAMPTZ NOT NULL,
    finished_at     TIMESTAMPTZ,
    status          VARCHAR(20) NOT NULL DEFAULT 'running',   -- running/success/failed/retrying
    retry_count     INT NOT NULL DEFAULT 0,
    error_msg       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_task_logs_name_date ON task_logs(task_name, trade_date);
```

---

### 3.2 ClickHouse（行情 / 因子数据库）

#### 行情数据

```sql
-- 日线行情（前复权）
CREATE TABLE daily_klines (
    ts_code     String,
    trade_date  Date,
    open        Float64,
    high        Float64,
    low         Float64,
    close       Float64,
    volume      Float64,           -- 成交量（手）
    amount      Float64,           -- 成交额（元）
    pct_chg     Float64,           -- 涨跌幅%
    turnover    Float64,           -- 换手率%
    is_st       UInt8 DEFAULT 0,
    is_limitup  UInt8 DEFAULT 0,
    is_limitdown UInt8 DEFAULT 0,
    adj_type    String DEFAULT 'qfq'  -- 复权类型
) ENGINE = MergeTree()
ORDER BY (ts_code, trade_date)
PARTITION BY toYYYYMM(trade_date);

-- 分钟线行情
CREATE TABLE minute_klines (
    ts_code     String,
    datetime    DateTime,
    freq        String,            -- '1min'/'5min'/'15min'/'30min'/'60min'
    open        Float64,
    high        Float64,
    low         Float64,
    close       Float64,
    volume      Float64,
    amount      Float64
) ENGINE = MergeTree()
ORDER BY (ts_code, freq, datetime)
PARTITION BY toYYYYMM(datetime)
TTL datetime + INTERVAL 3 YEAR;

-- 涨停板数据
CREATE TABLE limitup_data (
    trade_date      Date,
    ts_code         String,
    stock_name      String,
    close           Float64,
    pct_chg         Float64,
    limit_amount    Float64,       -- 封单金额（元）
    is_blowup       UInt8,         -- 是否炸板
    consecutive_days Int32,        -- 连板数
    board_type      String         -- 首板/二板/三板/...
) ENGINE = MergeTree()
ORDER BY (trade_date, ts_code)
PARTITION BY toYYYYMM(trade_date);

-- 龙虎榜数据
CREATE TABLE dragon_tiger (
    trade_date  Date,
    ts_code     String,
    exalter     String,            -- 席位名称
    buy         Float64,           -- 买入金额（元）
    sell        Float64,           -- 卖出金额（元）
    net_buy     Float64,           -- 净买入
    side        String             -- 'institution'/'hot_money'
) ENGINE = MergeTree()
ORDER BY (trade_date, ts_code)
PARTITION BY toYYYYMM(trade_date);

-- 资金流向
CREATE TABLE capital_flow (
    trade_date      Date,
    ts_code         String,
    super_large_net Float64,       -- 超大单净流入（元）
    large_net       Float64,       -- 大单净流入
    medium_net      Float64,       -- 中单净流入
    small_net       Float64        -- 小单净流入
) ENGINE = MergeTree()
ORDER BY (trade_date, ts_code)
PARTITION BY toYYYYMM(trade_date);
```

#### 因子与模型评分

```sql
-- 因子值（窄表 EAV 模式）
-- 设计原则：加新因子只需写新行，无需 ALTER TABLE；LowCardinality 大幅压缩因子名存储
-- 数据规模估算：3000股 × 500因子 × 250交易日 = 3.75亿行/年，ClickHouse 可高效处理
-- 查询注意：必须加 FINAL 关键字（ReplacingMergeTree 去重为后台异步，读时需强制去重）
CREATE TABLE factors (
    ts_code      String,
    trade_date   Date,
    factor_name  LowCardinality(String),   -- 因子唯一名称，如 'mom_5d'、'rsi_14'
    factor_value Float64,
    updated_at   DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (trade_date, ts_code, factor_name)
PARTITION BY toYYYYMM(trade_date);

-- 查询示例（读取某日某股所有因子，必须 FINAL）：
-- SELECT factor_name, factor_value
-- FROM factors FINAL
-- WHERE trade_date = '2026-04-07' AND ts_code = '000001.SZ'

-- 因子元数据（注册表，记录因子名、类别、是否核心因子等）
CREATE TABLE factor_registry (
    factor_name  String,
    category     LowCardinality(String),   -- basic/microstructure/alternative/...
    is_core      UInt8 DEFAULT 0,          -- 1=阶段一同步计算，0=阶段二异步
    description  String,
    created_at   DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(created_at)
ORDER BY (factor_name);

-- AI 模型每日评分
CREATE TABLE ai_scores (
    ts_code         String,
    trade_date      Date,
    model_name      String,        -- 'xgboost_scorer'/'trend_predictor'等
    score           Float64,       -- 评分
    model_version   String,
    updated_at      DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (ts_code, trade_date, model_name)
PARTITION BY toYYYYMM(trade_date);
```

---

### 3.3 Redis 7（热缓存）

| Key 模式 | 数据类型 | TTL | 内容 |
|----------|----------|-----|------|
| `universe:{date}` | Set | 24h | 当日有效股票池（ts_code 集合） |
| `score:{date}:{ts_code}` | Hash | 24h | AI 评分 + 综合分 |
| `sentiment:{date}` | Hash | 24h | 当日情绪分、阶段、仓位上限 |
| `position:{account_id}` | Hash | 1h | 当前持仓快照 |
| `signal:pending:{signal_id}` | String | 30min | 待用户确认的信号 |
| `tg_callback:{callback_data}` | String | 1h | Telegram 回调状态 |
| `factor:core:{date}:{ts_code}` | Hash | 48h | 核心因子缓存（用于实时重评分） |
| `ratelimit:tushare` | String | 60s | Tushare API 调用频率限制 |

---

## 四、模块设计

### 4.1 数据系统（data/）

**DataAdapter 接口规范**：

```python
class DataAdapter(ABC):
    """所有数据源适配器的统一接口"""

    @abstractmethod
    def get_daily_klines(
        self,
        ts_codes: list[str],
        start_date: str,
        end_date: str,
        adj: str = "qfq"
    ) -> pd.DataFrame:
        """获取日线行情（前复权）"""

    @abstractmethod
    def get_limitup_list(self, trade_date: str) -> pd.DataFrame:
        """获取涨停板数据"""

    @abstractmethod
    def get_dragon_tiger(self, trade_date: str) -> pd.DataFrame:
        """获取龙虎榜数据"""

    @abstractmethod
    def get_financial_data(
        self,
        ts_code: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """获取财务数据（按公告披露日 ann_date 对齐）"""

    @abstractmethod
    def get_capital_flow(self, trade_date: str) -> pd.DataFrame:
        """获取资金流向数据"""
```

**故障切换逻辑**：

```
DataFetcher.get_daily_klines(...)
    → 尝试 TushareAdapter（最多3次，间隔5s）
    → 失败 → 切换 AkShareAdapter
    → 失败 → 推送 Telegram 告警 + 记录失败日志 + 抛出 DataUnavailableError
```

---

### 4.2 因子引擎（factors/）

**Factor 基类接口**：

```python
class Factor(ABC):
    name: str           # 因子名，唯一标识
    category: str       # basic/microstructure/alternative/industry_chain/behavioral/macro
    is_core: bool       # True = 阶段一（同步核心）因子

    @abstractmethod
    def compute(
        self,
        ts_codes: list[str],
        trade_date: str,
        data_ctx: DataContext     # 封装行情/财务/资金流向等原始数据
    ) -> pd.Series:
        """返回 index=ts_code，values=因子值 的 Series"""

    def validate(self, result: pd.Series) -> bool:
        """校验结果合法性（非全空、值域合理）"""
```

**两阶段流水线**：

```
触发: N8N 夜间因子计算工作流
        │
        ▼
阶段一（同步，约10分钟）
  - 计算 is_core=True 的核心因子（~50个）
  - 写入 ClickHouse factors_basic
  - 缓存至 Redis factor:core:{date}:*
  - 完成后触发 AI 评分模块
        │
        ▼
阶段二（异步后台，约60分钟）
  - 计算全量因子（500+）
  - 分批写入 ClickHouse 各因子表
  - 日志记录进度
```

---

### 4.3 策略体系（strategies/）

**Strategy 基类接口**：

```python
class Strategy(ABC):
    name: str
    description: str
    default_weight: float   # 初始权重（由 strategy_performance 动态覆盖）

    @abstractmethod
    def evaluate(
        self,
        ts_code: str,
        trade_date: str,
        data_ctx: DataContext
    ) -> StrategyResult:
        """
        返回独立评估结果，不影响其他策略
        """

@dataclass
class StrategyResult:
    ts_code: str
    strategy_name: str
    score: float                # 0-100，该策略对该股的评估分
    confidence: float           # 0-1，信号置信度
    signals: list[str]          # 触发的具体信号描述
    is_triggered: bool          # 是否触发（分数超过策略阈值）
```

**涨停板策略特殊设计**（首板/二板/三板独立评分）：

```python
class LimitUpStrategy(Strategy):
    def evaluate(self, ts_code, trade_date, data_ctx) -> StrategyResult:
        board_type = self._get_board_type(ts_code, trade_date, data_ctx)
        # 各阶段权重与风险参数不同
        weights = {"首板": 0.6, "二板": 0.8, "三板": 0.9}
        risk_params = {"首板": {...}, "二板": {...}, "三板": {...}}
        score = self._compute_score(board_type, weights, risk_params, data_ctx)
        return StrategyResult(...)
```

---

### 4.4 情绪周期系统（sentiment/）

**情绪分计算数据来源**：

| 指标 | 来源表 | 触发时机 |
|------|--------|----------|
| 涨停数量 | ClickHouse `limitup_data` | 每日收盘后（15:05 N8N 触发） |
| 炸板率 | ClickHouse `limitup_data`（is_blowup 字段） | 同上 |
| 连板率 | ClickHouse `limitup_data`（consecutive_days 字段，跨日计算） | 同上 |
| 赚钱效应指数 | ClickHouse `daily_klines`（胜率 × 平均涨幅 × 活跃度加权） | 同上 |

计算结果写入 PostgreSQL `sentiment_history`，同时更新 Redis `sentiment:{date}`。

**SentimentMonitor 接口**：

```python
class SentimentMonitor:
    def compute_daily(self, trade_date: str) -> SentimentResult:
        """收盘后计算当日情绪分，写入 DB + Redis"""

    def get_current_phase(self, trade_date: str) -> SentimentPhase:
        """返回当前阶段（含 MA5 穿越确认）"""

    def get_position_limit(self, trade_date: str) -> float:
        """返回当日最大仓位比例"""
```

---

### 4.5 信号生成与聚合（signals/）

**信号生成流程**：

```
候选股池（Universe，3000-3500只）
        │
        ▼ （并行）
各策略 evaluate() → 14个 StrategyResult
        │
        ▼
AI 模型评分（XGBoost + 集成模型）
        │
        ▼
加权聚合（综合参考分 0-100）
  composite_score = Σ(strategy_score_i × weight_i × is_triggered_i)
                  + ai_weight × ai_score
        │
        ▼
过滤（< 65分剔除）→ 分级（SS/S/A/B）
        │
        ▼
情绪阶段仓位约束（冰点期上限20%等）
        │
        ▼
Top 20 候选股 → 写入 signals 表 → 推送 Telegram
```

---

### 4.5 风控体系（risk/）

**仓位计算器**：

```python
class PositionCalculator:
    def compute_position(
        self,
        account: Account,
        signal: Signal,
        strategy_win_rate: float,
        avg_return: float,
        avg_loss: float
    ) -> PositionRecommendation:
        """
        1. Kelly 公式：f* = (p*b - q) / b
           其中 p=胜率, q=1-p, b=盈亏比
        2. 实际仓位 = min(Kelly结果, 25%)
        3. 情绪约束：min(实际仓位, 情绪最大仓位)
        4. 组合约束：检查总持仓不超过当前情绪上限
        """
```

---

### 4.6 交易系统（trading/）

**回填处理流程（A 阶段）**：

```
用户点击 [✅ 已买入]
    → TelegramBot 发送回填表单
    → 用户提交：成交价、数量
    → FastAPI /api/trading/fill 接收
    → FillHandler.process()
        → 校验数据合法性
        → 写入 trades 表（source='manual'）
        → 更新 positions 表
        → 更新 signal_outcomes 表
        → 写入 Redis position:{account_id}
        → 回复确认消息（含止损价、仓位占比）
```

**B 阶段升级**：仅修改 `execution.py`，将数据来源从用户回填切换为券商 API 成交回报，`trades` 表结构不变，仅 `source` 字段从 `'manual'` 变为 `'api'`。

---

## 五、数据流设计

### 5.1 夜间批处理数据流（20:00-23:00）

```
20:00  N8N: 夜间数据拉取工作流
    → DataFetcher.fetch_daily(trade_date)
        → 日线行情 → ClickHouse daily_klines
        → 涨停数据 → ClickHouse limitup_data
        → 龙虎榜   → ClickHouse dragon_tiger
        → 资金流向  → ClickHouse capital_flow
        → 财务更新  → ClickHouse / PostgreSQL（按 ann_date 对齐）
    → 更新 universe_snapshots（次日股票池）
    → 写入 task_logs（success）

20:30  N8N: 夜间因子计算工作流
    → FactorPipeline.run(trade_date)
        → 阶段一：核心因子 → ClickHouse + Redis
        → 阶段二（异步）：全量因子 → ClickHouse

22:00  N8N: 夜间AI评分工作流
    → ModelInference.score_all(trade_date)
        → 读 ClickHouse factors_*
        → XGBoost 推理 → ClickHouse ai_scores
        → 集成模型 → 综合评分
    → SignalGenerator.generate(trade_date)
        → 策略评估 + 评分聚合 → 候选股 Top 20
        → 写入 PostgreSQL signals
        → 推送 Telegram（盘前候选清单）
```

### 5.2 盘前实时数据流（07:30-09:30）

```
07:30  N8N: 盘前推送工作流
    → 读 PostgreSQL signals（前一夜生成）
    → 竞价异动分析（对候选股预竞价数据评估）
    → MessageGateway.send(候选清单)
    → Telegram 推送候选股池

09:15  N8N: 竞价分析工作流
    → DataFetcher.get_auction_data(候选股)
    → 读 Redis factor:core:{date}:*
    → XGBoost 实时重评分（结合竞价数据）
    → 更新 signals 综合评分
    → 推送最终买入清单（Top 5-10）
```

### 5.3 盘中监控数据流（09:30-15:00，每5分钟）

```
每5分钟  N8N: 盘中监控工作流
    → RealtimeMonitor.check_all()
        → 查询 PostgreSQL positions（当前持仓）
        → 获取实时价格（Tushare/AkShare）
        → StopLossChecker.check()
            → 若触及止损线 → 推送告警
        → ScoreTracker.update_scores()
            → 评分跌破阈值 → 推送卖出信号
        → 更新 Redis position:{account_id}
```

---

## 六、API 接口设计

### 6.1 FastAPI 路由总览

| 方法 | 路径 | 说明 | 调用方 |
|------|------|------|--------|
| POST | `/webhook/telegram` | Telegram Bot Webhook 入口 | Telegram 服务器 |
| POST | `/webhook/feishu` | 飞书 Bot Webhook 入口 | 飞书服务器 |
| POST | `/api/n8n/trigger/{task_name}` | N8N 触发任务执行 | N8N |
| POST | `/api/trading/fill` | 用户回填成交信息 | Telegram Bot 回调 |
| GET | `/api/status` | 系统运行状态 | 监控/Bot |
| GET | `/api/positions/{account_id}` | 当前持仓查询 | Bot /positions |
| GET | `/api/sentiment` | 今日情绪分查询 | Bot /sentiment |
| GET | `/api/score/{ts_code}` | 指定股票评分查询 | Bot /score |
| GET | `/api/risk/{account_id}` | 风控状态查询 | Bot /risk |
| POST | `/api/report/trigger` | 手动触发报告生成 | Bot /report |

### 6.2 认证设计

- **Telegram Webhook**：校验 `X-Telegram-Bot-Api-Secret-Token` Header
- **N8N 内部接口**：共享密钥认证（`X-Internal-Token`），仅接受 Docker 内网请求
- **Bot 指令**：白名单 Chat ID 校验（`TELEGRAM_CHAT_ID` 环境变量）

---

## 七、调度任务设计（N8N）

### 7.1 工作流清单

| 工作流名称 | Cron 表达式 | 说明 |
|-----------|-------------|------|
| `nightly_data_fetch` | `0 20 * * 1-5` | 周一至周五 20:00 拉取数据 |
| `nightly_factor_calc` | `30 20 * * 1-5` | 20:30 触发因子计算 |
| `nightly_ai_score` | `0 22 * * 1-5` | 22:00 AI 评分 + 信号生成 |
| `premarket_push` | `30 7 * * 1-5` | 07:30 推送候选清单 |
| `auction_analysis` | `15 9 * * 1-5` | 09:15 竞价分析 + 实时评分 |
| `intraday_monitor` | `*/5 9-14 * * 1-5` | 盘中每5分钟监控 |
| `midday_report` | `0 12 * * 1-5` | 12:00 盘中报告 |
| `close_archive` | `5 15 * * 1-5` | 15:05 日终归档 + 复盘 |
| `close_push` | `30 15 * * 1-5` | 15:30 日终总结推送 |
| `universe_update` | `0 8 * * 1-5` | 08:00 更新当日股票池 |
| `quarterly_train` | `0 2 1 1,4,7,10 *` | 每季度首日凌晨 2:00 触发全量重训 |

### 7.2 非交易日判断

所有 N8N 工作流在执行前均调用 `/api/n8n/check-trading-day` 接口：

```
工作流触发（cron）
  → GET /api/n8n/check-trading-day?date={today}
  → 若非交易日（节假日/周末）→ 返回 {is_trading: false} → 工作流直接结束
  → 若是交易日 → 返回 {is_trading: true} → 继续执行后续节点
```

交易日历从 Tushare `trade_cal` 接口获取，每月初缓存至 Redis（`trade_cal:{year_month}`，TTL 35 天）。

### 7.2 统一故障恢复流程

每个 N8N 工作流均配置：
1. **最大重试次数**：3 次
2. **重试间隔**：5 分钟
3. **失败后**：调用 `/api/n8n/trigger/alert` → 推送 Telegram 告警 → 写入 `task_logs`（status='failed'）
4. **补跑**：管理员在 Telegram 发送 `/rerun {task_name} {date}` 手动触发

---

## 八、基础设施设计

### 8.1 Docker Compose 服务拓扑

```yaml
services:
  # 业务服务
  api:            # FastAPI，端口 8000（仅内网暴露）
  worker:         # ARQ Worker，处理异步任务
  
  # 调度
  n8n:            # N8N，端口 5678（Nginx 反代，外网访问需认证）
  
  # 数据库
  postgres:       # PostgreSQL 16，端口 5432（内网）
  clickhouse:     # ClickHouse，端口 8123/9000（内网）
  redis:          # Redis 7，端口 6379（内网）
  minio:          # MinIO，端口 9000/9001（内网）
  
  # 反向代理
  nginx:          # 80/443，SSL 终止，转发 Telegram Webhook 到 api
```

### 8.2 网络隔离

```
外网
  │
  ▼
nginx（80/443）
  ├── /webhook/* → api:8000（Telegram/飞书 Webhook）
  └── /n8n/* → n8n:5678（N8N 管理界面，Basic Auth 保护）

内网（Docker 网络）
  api → postgres, clickhouse, redis, minio
  worker → postgres, clickhouse, redis
  n8n → api（通过 HTTP 触发任务）
```

### 8.3 数据持久化

| 服务 | Volume | 说明 |
|------|--------|------|
| postgres | `/data/postgres` | 业务数据库 |
| clickhouse | `/data/clickhouse` | 行情/因子数据（预估 500GB+） |
| redis | `/data/redis` | 持久化开启（AOF） |
| minio | `/data/minio` | 模型文件、训练数据导出、报告文件 |
| n8n | `/data/n8n` | N8N 工作流配置 |

### 8.4 数据库迁移（Alembic）

PostgreSQL 表结构变更通过 Alembic 管理，禁止手动修改生产库：

```bash
# 新增迁移脚本
alembic revision --autogenerate -m "add_xxx_column"
# 执行迁移
alembic upgrade head
# 回滚
alembic downgrade -1
```

`Makefile` 提供快捷命令：`make db-migrate`、`make db-rollback`。

### 8.4 资源规划（VPS 最低配置建议）

| 资源 | 建议规格 | 说明 |
|------|----------|------|
| CPU | 8 核 | 因子并行计算、模型推理 |
| 内存 | 32 GB | ClickHouse 内存操作、PyTorch 推理 |
| 磁盘 | 1 TB SSD | ClickHouse 行情数据（3年历史约 300GB） |
| 带宽 | 100 Mbps | 数据拉取、Telegram 推送 |

---

## 九、消息通信设计

### 9.1 统一消息网关

```python
class MessageGateway:
    """屏蔽底层通道差异，业务模块只调用此类"""

    def send_signal(self, signal: Signal, channels: list[str] = ["telegram"]):
        """发送买卖信号（含交互按钮）"""

    def send_alert(self, alert: Alert, priority: str = "normal"):
        """发送告警（high优先级同时发送所有渠道）"""

    def send_report(self, report: Report, channels: list[str] = ["telegram"]):
        """发送报告（Markdown 格式）"""
```

### 9.2 Telegram Bot 状态机

```
用户收到信号消息
        │
        ├── 点击 [✅ 已买入]
        │       → 状态: AWAITING_FILL
        │       → 发送回填表单（内联键盘）
        │       → 用户输入均价/数量
        │       → 调用 /api/trading/fill
        │       → 状态: COMPLETED → 发送确认
        │
        ├── 点击 [❌ 未采纳]
        │       → 发送原因选择键盘（可选）
        │       → 信号标记为 rejected
        │
        └── 点击 [⏳ 待定]
                → 状态: PENDING_REMINDER
                → 30分钟后 ARQ 任务触发重推
                → 最多重推 2 次 → 超时标记 expired
```

### 9.3 Telegram Bot 指令处理

| 指令 | 处理模块 | 数据来源 |
|------|----------|----------|
| `/status` | api/routers/status.py | task_logs + Redis |
| `/positions` | api/routers/status.py | positions + Redis |
| `/score <代码>` | api/routers/status.py | ai_scores + signals |
| `/sentiment` | api/routers/status.py | sentiment_history + Redis |
| `/report` | reports/ | 触发报告生成任务 |
| `/risk` | risk/ | positions + portfolio |

---

## 十、安全设计

| 安全域 | 措施 |
|--------|------|
| 环境变量 | 所有密钥通过 `.env` 注入，不入代码仓库 |
| Telegram | Webhook Secret Token 校验；Chat ID 白名单 |
| 内网隔离 | 数据库端口不对外暴露，仅 Docker 内网可达 |
| N8N | Basic Auth + 仅内网可访问 |
| B 阶段券商 | 券商连接配置加密存储（AES-256-GCM），加密密钥通过环境变量 `BROKER_ENCRYPTION_KEY` 注入，仅 Worker 进程持有，不写入数据库或日志 |
| 日志脱敏 | API Key、Token 等敏感字段不写入日志 |
| 写操作确认 | Telegram 所有写操作（回填、触发报告）需二次确认 |
| 数据库事务 | 所有业务写入使用事务，失败自动回滚 |

---

## 十一、可观测性设计

### 11.1 日志规范

```python
# 统一日志格式（JSON 结构化）
{
    "timestamp": "2026-04-07T09:15:00+08:00",
    "level": "INFO",
    "module": "factors.pipeline",
    "trade_date": "2026-04-07",
    "message": "Factor calculation phase 1 completed",
    "duration_ms": 523,
    "factor_count": 50,
    "stock_count": 3412
}
```

日志级别规范：
- `ERROR`：需人工介入（数据获取失败、DB 写入失败）
- `WARNING`：降级运行（切换备用数据源、使用前日因子）
- `INFO`：正常业务流程节点
- `DEBUG`：调试信息（默认关闭）

### 11.2 健康检查

`GET /api/status` 返回各模块状态：

```json
{
    "status": "healthy",
    "timestamp": "2026-04-07T09:15:00+08:00",
    "modules": {
        "database": "ok",
        "clickhouse": "ok",
        "redis": "ok",
        "tushare": "ok",
        "last_data_date": "2026-04-04",
        "last_factor_date": "2026-04-04",
        "last_score_date": "2026-04-04"
    },
    "tasks": {
        "nightly_data_fetch": {"status": "success", "last_run": "2026-04-06T20:15:00+08:00"},
        "nightly_ai_score": {"status": "success", "last_run": "2026-04-06T22:05:00+08:00"}
    }
}
```

### 11.3 数据一致性校验

每日 15:05 收盘后自动执行：

```python
class DailyConsistencyCheck:
    def run(self, trade_date: str):
        checks = [
            self.check_kline_count(trade_date),      # 日线记录数是否合理
            self.check_factor_coverage(trade_date),   # 因子覆盖率 > 99%
            self.check_signal_generation(trade_date), # 信号是否已生成
            self.check_score_coverage(trade_date),    # AI 评分覆盖率
        ]
        if any(not c.passed for c in checks):
            # 推送 Telegram 告警 + 写入 task_logs
```

---

## 十二、任务执行链路设计

### 12.1 N8N → FastAPI → ARQ → Worker 完整链路

所有长时间运行任务（因子计算、AI评分等）均采用以下异步执行模式：

```
N8N cron 触发
  → POST /api/n8n/trigger/{task_name}   # N8N 调用 FastAPI
  → FastAPI 立即返回 202 { "job_id": "xxx" }  # 不阻塞
  → ARQ 将任务入队（存入 Redis）
  → ARQ Worker 拉取任务执行
      → 成功：写 task_logs(status='success') → 可选推 Telegram 通知
      → 失败：自动重试（最多3次，间隔5分钟）
               → 3次均失败：写 task_logs(status='failed') + 推 Telegram 告警
```

**工作流间依赖靠时间间隔保障**（非事件驱动）：
- 20:00 数据拉取 → 20:30 因子计算（30分钟缓冲）
- 20:30 因子计算 → 22:00 AI 评分（90分钟缓冲，含阶段二异步因子）
- 各工作流独立，互不等待，失败不级联阻断后续工作流

### 12.2 Telegram Webhook 幂等性

Telegram 推送失败会自动重试，FastAPI 须保证幂等处理：

```python
# webhook.py
async def handle_telegram_update(update: dict):
    update_id = update["update_id"]
    # 以 update_id 为幂等键，Redis SETNX 去重
    if not await redis.set(f"tg:processed:{update_id}", 1, nx=True, ex=86400):
        return  # 已处理，静默忽略
    # 正常处理逻辑...
```

### 12.3 Telegram Callback Data 大小限制

Telegram callback_data 上限 **64 字节**，不足以传递完整业务数据。解决方案：

```
用户点击按钮
  → callback_data 仅传递 signal_id（如 "fill:12345"，< 20字节）
  → FastAPI 收到后从 PostgreSQL 读取完整 signal 信息
  → 继续处理回填流程
```

---

## 十三、模型训练基础设施

### 13.1 核心接口定义

**所有模型和训练相关组件均面向接口，运行时可替换：**

```python
class BaseModel(ABC):
    """所有 AI 模型的预测接口"""
    model_name: str

    @abstractmethod
    def predict(self, features: pd.DataFrame) -> pd.Series:
        """输入特征矩阵，返回 index=ts_code 的预测分"""

    @abstractmethod
    def load(self, artifact_path: str) -> None:
        """从 MinIO/本地路径加载模型"""


class BaseTrainer(ABC):
    """模型训练接口（Walk-forward 框架调用此接口）"""
    model_name: str

    @abstractmethod
    def train(self, X_train: pd.DataFrame, y_train: pd.Series) -> None:
        """训练模型"""

    @abstractmethod
    def evaluate(self, X_val: pd.DataFrame, y_val: pd.Series) -> dict:
        """返回评估指标，如 {"auc": 0.85, "ic": 0.12}"""

    @abstractmethod
    def save(self, artifact_path: str) -> None:
        """保存模型至指定路径"""


class TrainingBackend(ABC):
    """训练执行后端（CPU 本地 / 云 GPU 按需，可替换）"""

    @abstractmethod
    def run_training_job(
        self,
        model_name: str,
        data_path: str,           # MinIO 数据路径
        output_path: str,         # MinIO 模型输出路径
        config: dict
    ) -> str:
        """提交训练任务，返回 job_id"""

    @abstractmethod
    def get_job_status(self, job_id: str) -> str:
        """返回 running/success/failed"""


class DataExporter(ABC):
    """训练数据导出接口（ClickHouse → MinIO/本地）"""

    @abstractmethod
    def export_features(
        self,
        train_start: str,
        train_end: str,
        output_path: str
    ) -> str:
        """导出因子数据为 Parquet，返回文件路径"""

    @abstractmethod
    def export_labels(
        self,
        train_start: str,
        train_end: str,
        output_path: str
    ) -> str:
        """导出标签数据（未来N日收益率）"""
```

### 13.2 Walk-forward 训练流程

```
N8N quarterly_train 触发（每季度首日 02:00）
  → DataExporter.export_features/labels → 上传至 MinIO
  → TrainingBackend.run_training_job（CPUBackend 或 CloudGPUBackend）
      CPUBackend：直接在 VPS Worker 执行（仅用于 XGBoost）
      CloudGPUBackend：
        → 启动云 GPU 实例（autodl/阿里云，按小时计费）
        → 拉取代码 + 从 MinIO 下载数据
        → 执行训练
        → 上传模型至 MinIO
        → 关闭 GPU 实例（单次约 ¥50–200）
  → ModelRegistry.compare_and_activate()
      → 加载新模型 evaluate() 指标
      → 新模型 AUC ≥ 旧模型 → 更新 model_versions.is_active
      → 否则保留旧模型，推送 Telegram 告警
```

### 13.3 在线学习（增量训练）

仅对 **XGBoost** 做在线学习（CPU 可接受），其余深度学习模型等季度重训：

```
signal_outcomes 新增 N 条已平仓记录（N 由配置决定，默认 200）
  → learning/trigger.py 检测到触发条件
  → feedback_collector.py 从 signal_outcomes 聚合新增训练样本
  → XGBoostTrainer.incremental_train(new_samples)
  → 评估：若 IC 无明显下降 → 原地更新模型权重
  → 写入 model_versions（version 带时间戳）
```

### 13.4 GPU 策略与资源规划

| 场景 | 运行环境 | 预估成本 |
|------|----------|----------|
| 日常推理（XGBoost/集成） | VPS CPU | 包含在月租内 |
| 日常推理（LSTM/Transformer 冻结模型） | VPS CPU | 包含在月租内 |
| 季度重训（XGBoost） | VPS CPU（~30–60分钟） | 包含在月租内 |
| 季度重训（LSTM/Transformer/BERT/PPO） | 云 GPU 按需 | 约 ¥50–200/次 |
| VPS 配置 | 8核 CPU / 32GB RAM / 1TB SSD | 月租约 ¥300–600 |

---

## 附录：开发顺序（对应 CP 验证点）

按 CLAUDE.md 规定，开发顺序严格按模块推进，每模块用真实数据验证通过后才继续：

| 顺序 | 模块 | CP | 验收标准 |
|------|------|----|----------|
| 1 | 基础设施（Docker Compose + DB 初始化） | — | 所有容器启动，表结构创建成功 |
| 2 | 数据系统（data/ + universe/） | CP1 | 真实日线数据写入 ClickHouse |
| 3 | 因子引擎（factors/，先核心因子） | — | 对 100 只股票批量计算核心因子 |
| 4 | AI 模型（models/，先 XGBoost） | CP2 | 对一只股票算出 AI 评分并打印 |
| 5 | 策略体系（strategies/，先3-5套） | — | 策略评估返回正确的 StrategyResult |
| 6 | 信号生成（signals/） | CP3 | 对一天候选股生成信号列表 |
| 7 | 消息通信（messaging/） | CP4 | Telegram 收到格式正确的信号消息 |
| 8 | 交易系统（trading/，A 阶段） | CP5 | 手动回填后数据库有记录、效果追踪有数据 |
| 9 | 风控体系（risk/） | — | 仓位计算、止损触发正确 |
| 10 | 监控系统（monitoring/） | — | 盘中监控循环运行，告警正确触发 |
| 11 | 回测系统（backtest/） | — | 单策略回测结果符合严格性标准 |
| 12 | 报告系统（reports/） | — | 日终报告格式正确推送 |
| 13 | 剩余AI模型（LSTM/Transformer/集成） | — | 各模型训练完成，IC 达标 |
| 14 | 学习系统（learning/） | — | 实盘反馈触发增量训练 |
