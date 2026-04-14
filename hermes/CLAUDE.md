# Project: Hermes · AI 金融量化投资平台

> 当前进度见 [PROGRESS.md](PROGRESS.md)（由 `make progress PROJECT=hermes` 自动生成）

## 必读（全局规范）

- [编码规范](../standards/coding-standards.md)
- [TDD 工作流规范](../standards/tdd-workflow.md)
- [Git 工作流规范](../standards/git-workflow.md)
- [API 设计规范](../standards/api-design-standards.md)

## 当前阶段文档（仅读此阶段）

**当前阶段：02 - System Design**

- [系统设计文档](stages/02-system-design/system-design.md)

## 已确认的关键技术决策

| 决策 | 选型 |
|------|------|
| 开发语言 | Python 3.11+ |
| 部署 | 云端 VPS + Docker Compose |
| 业务数据库 | PostgreSQL 16 |
| 行情/因子数据库 | ClickHouse |
| 热缓存 | Redis 7 |
| 任务调度 | N8N（自托管） |
| 消息推送 | Telegram Bot（主）+ 飞书（次） |
| Web 服务 | FastAPI |
| AI/ML | XGBoost + PyTorch + scikit-learn |
| 主数据源 | Tushare Pro |
| 备用数据源 | AkShare（自动降级切换） |

## 阶段规则

- 每个阶段必须产出对应文档后才能进入下一阶段
- **阶段 04 开发**：严格 TDD，先写测试再写实现，测试文件写入后禁止修改
- **不使用 Mock 数据**：A 股接口字段差异大，Mock 掩盖真实问题
- 5个验证检查点（CP），按顺序推进，CP 未通过不进入下一个

## ⛔ 禁止事项（机械保障）

以下约束**不是口头要求，而是脚本/hooks/权限强制执行的**：

- **禁读非当前阶段文档**：CLAUDE.md 只引用当前阶段，其他阶段需手动主动读取
- **禁改锁定测试**：`stages/04-development/tests/` 进入阶段 04 后自动锁定：
  - Claude Code 的 Edit/Write 工具被 `.claude/settings.local.json` 的 deny 规则拒绝
  - Git 的 pre-commit hook 拒绝 commit
  - 文件权限 `chmod 444` 让任何进程写入得到 EACCES
  - 解锁必须走 `make unlock-tests REASON="..."`，留审计记录
- **禁跳过阶段**：`make advance` 要求当前阶段 `check_stage.py` 全部 PASS 才允许推进
- **禁手动改 PROGRESS.md**：`pre-commit` hook 会用 `update_progress.py` 自动重写

## 其他阶段文档（勿主动读取，存档备查）

- `stages/01-requirements/requirements.md` ✅ 完成
- `stages/03-module-design/` ⏳ 待开始
- `stages/04-development/` ⏳ 待开始
- `stages/05-testing/` ⏳ 待开始
- `stages/06-deployment/` ⏳ 待开始
- `stages/07-operations/` ⏳ 待开始
