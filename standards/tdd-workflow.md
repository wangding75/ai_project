# TDD 工作流规范

> 测试驱动开发是所有开发阶段的**强制且机械保障**的工作流。

## 核心原则

**测试即契约**：测试从 schema 派生，一旦写入即被机械锁定。实现必须适配测试，而不是反过来。

## 三层保护机制（Finding 1）

测试锁定不是靠说服，而是靠三层机械阻断，任一层都能拦截未授权的修改：

| 层 | 工具 | 效果 |
|----|------|------|
| 1 | `.claude/settings.local.json` 的 `permissions.deny` | Claude Code 的 `Edit`/`Write` 工具对 `tests/` 路径直接拒绝 |
| 2 | `.githooks/pre-commit` | 检测 staged 文件，若命中锁定目录 → `git commit` 被拒 |
| 3 | `chmod 444` (由 `lock_tests.sh` 设置) | OS 文件权限，任何进程写入得到 EACCES |

推进到阶段 04 时会自动触发 `lock_tests.sh`，锁定状态记录在 `.git/locks/`。

解锁只能走 `unlock_tests.sh`，必须提供理由（≥ 10 字符），留下审计记录到 `.git/locks/unlock-audit.log`。

## 标准流程

### 第一步：确认 Schema 已就绪

进入阶段 04 前，必须满足：

- `stages/03-module-design/schemas/` 存在
- 所有模块的 Pydantic model 已定义（见 [API 设计规范](api-design-standards.md)）
- `scripts/check_stage.py <project> 03-module-design` 返回 PASS
- `make advance PROJECT=<project>` 成功推进到 04

### 第二步：从 Schema 派生测试（Red Phase）

```
对每个模块 schema：
  1. 在 tests/ 下创建 test_<module_name>.py
  2. 必须 import 对应的 Pydantic model
  3. 覆盖：
     - 每个字段的有效值、边界值、无效值（触发 ValidationError）
     - 每个声明的 error code（DataLayerErrors.XXX 等）
     - Happy Path、Error Path、Edge Case
  4. 运行 pytest → 全部 FAIL（尚无实现）
  5. git commit -m "test(<module>): add TDD test cases from schema"
```

完成后立即触发锁定：
```bash
make lock-tests PROJECT=<project>
```

**此后测试文件为只读契约。**

### 第三步：实现业务代码（Green Phase）

```
只能修改 src/ 或实现目录下的代码，禁止触碰 tests/。
  1. 编写最简实现让测试通过
  2. pytest → Green
  3. Refactor → 保持 Green
  4. git commit -m "feat(<module>): implement to pass TDD tests"
```

若测试无法通过，**修改实现**而非测试。

### 第四步：非功能性测试（Finding 3）

除功能测试外，每个模块必须有：

| 文件 | 用途 |
|------|------|
| `test_<module>_logging.py` | 断言必须打印的日志字段（trace_id、业务字段、性能字段） |
| `test_<module>_metrics.py` | 断言 Prometheus 指标已注册和暴露 |
| `test_<module>_fallback.py` | 降级行为测试（Mock 上游失败，验证 fallback 路径）|
| `test_<module>_perf.py` | 性能基线测试（P99 满足 SLO 契约） |

这些测试的要求定义在 `schemas/slo.yaml`。

### 第五步：覆盖度验证

```bash
make schema-coverage PROJECT=<project>
```

确认：
- 每个 Pydantic model 被至少一个测试引用
- 每个 error code 被至少一个测试覆盖
- pytest --cov 行覆盖率 ≥ 85%

## 接口变更流程（禁止跳步）

若必须修改接口（进而需要改测试）：

```
1. 修改 stages/03-module-design/schemas/<module>.py
2. 跑 make check-stage PROJECT=<project> STAGE=03-module-design（必须 PASS）
3. make unlock-tests PROJECT=<project> REASON="接口变更：<详细原因>"
4. 删除旧的 test_<module>*.py
5. 从新 schema 重新生成测试（回到 Red Phase 流程）
6. 实现新功能让测试通过
7. make lock-tests PROJECT=<project>
```

`unlock-audit.log` 会保留所有解锁历史，便于 review。

## 测试质量标准

- 每个测试函数只测试一件事
- 测试函数名描述场景：`test_fetch_daily_raises_invalid_symbol_when_malformed`
- 使用 `pytest.mark`：`@pytest.mark.unit`、`@pytest.mark.integration`
- Mock 外部 IO（网络、数据库），**禁止 Mock 数据内容**（本项目用真实数据验证）
- 覆盖率：单元测试 ≥ 85%，关键模块（数据层、风控）≥ 95%
