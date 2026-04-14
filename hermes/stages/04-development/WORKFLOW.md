# 开发阶段 TDD 工作流

> 进入本阶段前，确认 `stages/03-module-design/api-spec.md` 已完成并评审通过。

## 前提条件

- [x] 阶段 03（模块接口设计）已完成
- [x] `stages/03-module-design/api-spec.md` 已定稿
- [ ] 开发环境已配置（数据库、依赖包）

## 严格规则

**测试文件写入后即锁定，禁止任何修改。**

如需变更接口，走接口变更流程（见下方），不得直接修改测试文件。

## 步骤

### Step 1：读取接口文档

```
读取：../03-module-design/api-spec.md
目标：
  - 列出所有需要实现的模块
  - 理解每个模块的输入/输出/异常
  - 识别模块间依赖关系，确定开发顺序
```

### Step 2：写测试用例（Red Phase）

对每个模块，在 `tests/` 下创建 `test_<module_name>.py`：

```
覆盖维度：
  1. Happy Path：正常输入，验证输出结构和内容
  2. Error Path：无效参数、外部服务不可用、数据为空
  3. Edge Cases：边界值、超大数据量、并发场景

完成后运行：pytest tests/test_<module_name>.py
预期结果：全部 FAIL（Red） ← 此时无实现代码
提交：git commit -m "test(<module>): add TDD test cases from api-spec"
```

### Step 3：实现业务代码（Green Phase）

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

### Step 4：集成测试

所有模块完成后：

```bash
pytest tests/ -v
```

全部通过，更新 PROGRESS.md，进入阶段 05（测试验证）。

## 模块开发顺序（示例）

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

若发现 `api-spec.md` 有误，必须走此流程，**禁止直接修改测试文件**：

```
1. 修改 stages/03-module-design/api-spec.md
2. 在 PROGRESS.md 中记录变更原因和日期
3. 评审：变更是否影响其他已完成模块？
4. 删除受影响的测试文件
5. 重新执行 Step 2 → Step 3
```
