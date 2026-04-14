# Project: Consilium · 智囊团共识平台

> 当前进度见 [PROGRESS.md](PROGRESS.md)（由 `make progress PROJECT=consilium` 自动生成）

## 必读（全局规范）

- [编码规范](../standards/coding-standards.md)
- [TDD 工作流规范](../standards/tdd-workflow.md)
- [Git 工作流规范](../standards/git-workflow.md)
- [API 设计规范](../standards/api-design-standards.md)

## 当前阶段文档（仅读此阶段）

**当前阶段：01 - Requirements**

- [完整设计开发文档](stages/01-requirements/design-doc.md)
- [产品需求文档 PRD](stages/01-requirements/prd.md)

## 阶段规则

- 每个阶段必须产出对应文档后才能进入下一阶段
- **阶段 04 开发**：严格 TDD，先写测试再写实现，测试文件写入后禁止修改
- 5个验证检查点（CP），按顺序推进，CP 未通过不进入下一个

## ⛔ 禁止事项（机械保障）

- **禁读非当前阶段文档**：CLAUDE.md 只引用当前阶段
- **禁改锁定测试**：三层保护（Claude Code deny + git hook + chmod 444），解锁需 `make unlock-tests REASON="..."`
- **禁跳过阶段**：`make advance` 要求当前阶段 check 全部 PASS
- **禁手动改 PROGRESS.md**：pre-commit hook 自动重写

## 其他阶段文档（勿主动读取，存档备查）

- `stages/02-system-design/architecture.md` ⏳ 待开始
- `stages/03-module-design/development.md` ⏳ 待开始
- `stages/04-development/` ⏳ 待开始
- `stages/05-testing/` ⏳ 待开始
- `stages/06-deployment/` ⏳ 待开始
- `stages/07-operations/` ⏳ 待开始
