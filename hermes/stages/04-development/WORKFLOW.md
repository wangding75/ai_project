# 开发阶段 TDD 工作流

> 进入本阶段前，确认 `stages/03-module-design/` 的 schema 和 api-spec.md 已完成并评审通过。

## 前提条件

- [x] 阶段 03（模块接口设计）已完成
- [x] `stages/03-module-design/schemas/*.py` 已定稿（**Schema 是权威来源，Markdown 为辅助**）
- [x] `stages/03-module-design/api-spec.md` 已定稿
- [ ] 开发环境已配置（数据库、依赖包）

## 严格规则

**测试文件写入后即锁定，禁止任何修改。**

三层保护机制确保锁定不可绕过：
1. `.claude/settings.local.json` 的 `permissions.deny` 阻止 Claude Code 的 Edit/Write
2. `.githooks/pre-commit` 检测 staged 文件，命中锁定目录则拒绝 commit
3. `chmod 444` 由 `lock_tests.sh` 设置，OS 级别阻断写入

如需变更接口，走接口变更流程（见下方），不得直接修改测试文件。

## 步骤

### Step 1：读取接口定义

```
读取：../03-module-design/schemas/*.py（Pydantic model，权威来源）
辅助参考：../03-module-design/api-spec.md（人类可读叙述）
冲突时以 schemas/*.py 为准。

目标：
  - 列出所有需要实现的模块
  - 理解每个模块的输入/输出/异常
  - 理解每个模块的错误码（XxxErrors 类）
  - 识别模块间依赖关系，确定开发顺序
```

### Step 2：写测试用例（Red Phase）

对每个模块，在 `tests/` 下创建 `test_<module_name>.py`：

```
覆盖维度：
  1. Happy Path：正常输入，验证输出结构和内容
  2. Error Path：无效参数、外部服务不可用、数据为空，覆盖所有声明的 error code
  3. Edge Cases：边界值、超大数据量、并发场景

必须 import 对应的 Pydantic model 和 Errors 类。

完成后运行：pytest tests/test_<module_name>.py
预期结果：全部 FAIL（Red） ← 此时无实现代码
提交：git commit -m "test(<module>): add TDD test cases from schema"
```

**全部模块的功能测试写完后，立即锁定：**
```bash
make lock-tests PROJECT=hermes
```

### Step 3：非功能性测试

每个模块还需编写以下测试文件（同样在锁定前完成）：

| 文件 | 用途 | 来源 |
|------|------|------|
| `test_<module>_logging.py` | 断言必须打印的日志字段（trace_id、业务字段、性能字段） | `schemas/slo.yaml` |
| `test_<module>_metrics.py` | 断言 Prometheus 指标已注册和暴露 | `schemas/slo.yaml` |
| `test_<module>_fallback.py` | 降级行为测试（Mock 上游失败，验证 fallback 路径）| `api-spec.md` 降级契约 |
| `test_<module>_perf.py` | 性能基线测试（P99 满足 SLO 契约） | `schemas/slo.yaml` |

完成后再次确认锁定状态，然后提交所有测试。

### Step 4：实现业务代码（Green Phase）

```
规则：
  - 只能编写/修改实现代码
  - 禁止修改 tests/ 下任何文件
  - 最小化实现：先让测试通过，再重构

完成后运行：pytest tests/test_<module_name>.py
预期结果：全部 PASS（Green）
重构后再运行一次，确认仍然全部 PASS
提交：git commit -m "feat(<module>): implement <module> to pass TDD tests"
```

若测试无法通过，**修改实现**而非测试。

### Step 5：覆盖度验证

```bash
make schema-coverage PROJECT=hermes
```

确认所有 Pydantic model 和 error code 都被测试引用。

### Step 6：集成测试

所有模块完成后：

```bash
pytest tests/ -v
```

全部通过后，用 `make advance PROJECT=hermes` 进入阶段 05。

## 模块开发顺序

按依赖关系从底层到上层：

```
1. data_layer      # 数据获取与存储（无依赖）
2. factor_engine   # 因子计算（依赖 data_layer）
3. model           # AI 评分（依赖 factor_engine）
4. strategy        # 信号生成（依赖 model）
5. risk_manager    # 风控（依赖 strategy）
6. notification    # 推送（依赖 strategy/risk_manager）
7. trade_recorder  # 回填记录（独立）
```

## 接口变更流程

若发现 schema 有误，必须走此流程，**禁止直接修改测试文件**：

```
1. 修改 stages/03-module-design/schemas/<module>.py
2. 跑 make check-stage PROJECT=hermes STAGE=03-module-design（必须 PASS）
3. make unlock-tests PROJECT=hermes REASON="接口变更：<详细原因>"
4. 删除受影响的测试文件（test_<module>*.py）
5. 从新 schema 重新生成测试（回到 Red Phase 流程）
6. 实现新功能让测试通过
7. make lock-tests PROJECT=hermes
```

`unlock-audit.log` 会保留所有解锁历史，便于 review。
