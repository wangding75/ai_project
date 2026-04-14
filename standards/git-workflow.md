# Git 工作流规范

> 适用范围：所有项目

## 分支策略

```
main          # 生产分支，只接受 PR 合并，不直接推送
develop       # 集成分支，各功能分支合并到这里
feature/xxx   # 功能开发分支，从 develop 创建
fix/xxx       # Bug 修复分支
stage/N-name  # 阶段开发分支（如 stage/04-development）
iter/vX.Y     # 迭代分支（如 iter/v1.1）
```

## 提交信息规范（Conventional Commits）

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

### Type 类型

| Type | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `test` | 添加或修改测试 |
| `docs` | 文档变更 |
| `refactor` | 重构（不改变行为） |
| `chore` | 构建/工具/依赖变更 |
| `stage` | 阶段推进（如进入阶段 04） |

### 示例

```
feat(data): add ClickHouse daily OHLCV writer

test(factor): add unit tests for momentum factor calculation

stage: advance to 04-development, lock api-spec

docs(progress): update hermes PROGRESS.md to stage 03 complete
```

## 提交原则

- 每次提交只做一件事（原子提交）
- 测试写完后立即提交一次（Red commit）
- 实现完成后再提交一次（Green commit）
- 不提交未通过测试的代码到 main/develop
- `.env` 文件、密钥文件、大型数据文件加入 `.gitignore`

## 阶段推进提交

每次推进到下一阶段，创建一个专门的 stage commit：

```bash
git commit -m "stage: complete 02-system-design, advance to 03-module-design

- system-design.md reviewed and finalized
- PROGRESS.md updated
- CLAUDE.md updated to point to stage 03 docs"
```
