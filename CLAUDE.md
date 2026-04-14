# AI Project 开发规范

## 结构说明

本仓库管理多个 AI 驱动项目。每个项目是独立的阶段化工作流：

- 全局规范在 `standards/`（对所有项目生效）
- 每个项目有自己的 `CLAUDE.md`（阶段指针）、`PROGRESS.md`（自动生成的进度）、`stages/`（阶段产出）
- 每个阶段有 `deliverables.yaml` 定义产出清单，由 `scripts/check_stage.py` 机器验证

## 全局规范（必读）

- [编码规范](standards/coding-standards.md)
- [TDD 工作流规范](standards/tdd-workflow.md)
- [Git 工作流规范](standards/git-workflow.md)
- [API 设计规范](standards/api-design-standards.md)

## 项目列表

| 项目 | 描述 | 入口 |
|------|------|------|
| [hermes/](hermes/CLAUDE.md) | AI 金融量化投资平台 | [PROGRESS](hermes/PROGRESS.md) |
| [consilium/](consilium/CLAUDE.md) | 智囊团共识平台 | [PROGRESS](consilium/PROGRESS.md) |

## 自动化工作流

工作流由脚本驱动，用 `make` 调用：

```bash
# 自动更新进度（根据事实重写 PROGRESS.md）
make progress PROJECT=hermes

# 验证某阶段产出清单
make check-stage PROJECT=hermes STAGE=03-module-design

# 推进到下一阶段（check 必须 PASS）
make advance PROJECT=hermes

# 检查 schema 覆盖率
make schema-coverage PROJECT=hermes

# 锁定/解锁测试目录
make lock-tests PROJECT=hermes
make unlock-tests PROJECT=hermes REASON="接口变更原因"

# 安装 git hooks（首次使用）
make install-hooks
```

## 硬约束机制

- **测试文件锁定**：三层保护（Claude Code deny 规则 + git pre-commit hook + chmod 444）
- **阶段门禁**：`deliverables.yaml` 定义产出，`check_stage.py` 机器验证，不通过不能推进
- **进度自动化**：`update_progress.py` 扫描事实自动重写 `PROGRESS.md`，人工无需维护

## 使用规则

1. 进入项目时，读取该项目的 `CLAUDE.md`
2. `CLAUDE.md` 指定的文档之外，**不主动读取**其他阶段文档
3. 所有编码遵循 `standards/` 下的规范
4. 阶段推进用 `make advance`，不手动修改 `PROGRESS.md`（会被脚本覆盖）
