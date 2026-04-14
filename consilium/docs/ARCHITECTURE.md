# 智囊团技术架构文档

> 版本：v1.1
> 日期：2026-04-05
> 状态：基于评审决策更新

---

## 1. 架构原则

> **架构原则**：客户端优先 + 极简服务器。核心讨论引擎完全在客户端运行，服务器仅做模板分发和版本管理。LLM 调用由客户端通过用户 Key 直连。

---

## 2. 整体架构

### 2.1 架构分层

```
┌─────────────────────────────────────────────┐
│              客户端层 (React/Next.js)        │
│  ┌─────────┐ ┌─────────┐ ┌─────────────┐  │
│  │ UI层    │ │ 引擎层   │ │ LLM抽象层    │  │
│  │components│ │ engine/ │ │ llm/client  │  │
│  └─────────┘ └─────────┘ └─────────────┘  │
├─────────────────────────────────────────────┤
│              服务端层 (极简)                 │
│  ┌─────────┐ ┌─────────┐ ┌─────────────┐  │
│  │模板存储 │ │ 版本管理 │ │ 推荐模型    │  │
│  │CDN      │ │ API     │ │ API        │  │
│  └─────────┘ └─────────┘ └─────────────┘  │
├─────────────────────────────────────────────┤
│              外部服务层                      │
│  OpenAI / Anthropic / Gemini / Deepseek 等 │
└─────────────────────────────────────────────┘
```

### 2.2 技术选型

| 层面 | 技术选型 | 选择理由 |
|-----|---------|---------|
| 框架 | Next.js 14 (App Router) | React 生态，SSG 静态部署 |
| 语言 | TypeScript 5.x | 类型安全 |
| 样式 | Tailwind CSS + CSS Variables | 主题系统需要 CSS 变量 |
| 状态管理 | Zustand | 轻量，无需 Redux |
| 本地存储 | IndexedDB (via idb) | 存储会话历史和模板缓存 |
| **LLM 调用** | **Vercel AI SDK** | 开箱即用，流式支持，内置 hooks |
| **自定义模型** | **必须支持** | BaseURL + Key + ModelList |
| 部署 | Vercel（前端）+ CDN（模板） | 零运维 |

---

## 3. LLM 服务抽象层

### 3.1 核心接口

使用 **Vercel AI SDK**，所有 LLM 调用通过统一接口：

```typescript
// llm/client.ts
import { createAI } from 'ai/react'
import { openai } from '@ai-sdk/openai'
import { anthropic } from '@ai-sdk/anthropic'
import { google } from '@ai-sdk/google'

// 支持自定义 Provider（必须）
interface CustomProvider {
  name: string
  baseURL: string
  apiKey: string
  models: string[]
}

// 创建 Client
function createLLMClient(config: LLMConfig): AIConfig {
  // 根据 provider 类型创建对应的 AI 实例
}
```

### 3.2 支持的 Provider

| Provider | SDK | 支持自定义 URL | 说明 |
|----------|-----|--------------|------|
| OpenAI | @ai-sdk/openai | 是 | 官方 API |
| Anthropic | @ai-sdk/anthropic | 是 | Anthropic API |
| Gemini | @ai-sdk/google | 是 | Google AI |
| Deepseek | 自定义 | 是 | Deepseek API |
| **自定义** | **必须支持** | **是** | 用户提供 BaseURL + Key + ModelList |

### 3.3 自定义模型 Provider 示例

```typescript
// 用户在 LLM 配置页添加自定义模型
interface CustomModelConfig {
  name: string           // 显示名称
  baseURL: string        // 如 http://localhost:11434/v1
  apiKey: string          // API Key
  modelList: string[]     // 可用模型列表，如 ['llama3', 'qwen2']
}

// 自定义 Provider 实现
const customProvider = createCustomProvider({
  name: '本地 Ollama',
  baseURL: 'http://localhost:11434/v1',
  apiKey: 'ollama',
  modelList: ['llama3', 'qwen2', 'mistral']
})
```

---

## 4. 讨论引擎架构

### 4.1 模块划分

```
engine/
├── director.ts    # 导演逻辑：决策核心
├── scheduler.ts   # 角色调度算法
├── rhythm.ts     # 节奏控制
├── events.ts     # 爽点机制（打脸/站队/投票/反转）
├── intent.ts     # 用户意图识别（LLM 分类）
└── state.ts      # 引擎状态机
```

### 4.2 状态机定义

```typescript
type Phase = 'opening' | 'developing' | 'climax' | 'closing'

interface EngineState {
  sessionId: string
  templateId: string
  topic: string
  messages: Message[]
  currentTurn: number
  phase: Phase
  // 爽点状态
  slapCount: number
  campFormed: boolean
  voteTriggered: boolean
  reverseTriggered: boolean
  // 邀请状态
  inviteCount: number
  pendingInvite: boolean
  // 发言追踪
  lastSpeakerId: string
  speakingQueue: string[]
}
```

### 4.3 Phase 转换条件

```
┌──────────┐  用户进入讨论   ┌────────────┐
│  idle    │ ──────────────→ │  opening   │
└──────────┘                └────────────┘
                               │ 用户发消息
                               ↓
                          ┌────────────┐  检测到明显分歧
                          │ developing │ ──────────────────┐
                          └────────────┘                    │
                               │                           │
                               │ 轮次过半 或                 │
                               │ 检测到重大分歧              ↓
                               ↓                      ┌──────────┐
                          ┌────────────┐            │ climax   │
                          │ climax     │ ←──────────┘          │
                          └────────────┘   用户最终表态 或       │
                               │            轮次达到上限         │
                               │                              │
                               └──────────────────────────────↓
                                              ↓
                                       ┌──────────┐
                                       │ closing  │
                                       └──────────┘
```

### 4.4 director.ts 决策矩阵

**意图处理**：
```typescript
// 用户发言后，LLM 分类为三种意图
type Intent = 'interrupt' | 'command' | 'passive'

// interrupt：用户主动插话 → 定向调度相关角色
// command：用户下达指令 → 执行指令调度指定角色
// passive：用户旁观 → 按正常流程推进
```

**开团条件**（制造冲突）：
- 两个角色对同一问题表态方向相反
- 检测关键词矛盾："但是"/"不对"/"我不同意"/"不一定"

**邀请用户时机**：
- 出现观点分歧
- 角色质疑用户观点
- 讨论到达分叉点
- 出现意外信息或反转
- 讨论即将收敛

**收束条件**：
- 轮次达到上限（`maxTurnsPerRole * roles.length`）
- 用户发出结束信号（"总结"/"结束"/"结论"）
- 角色一致同意某观点（无分歧）

### 4.5 意图识别实现（LLM 分类）

```typescript
// intent.ts
import { classifyIntent } from 'ai/actions'

async function recognizeIntent(userMessage: string, context: Message[]): Promise<Intent> {
  const result = await classifyIntent({
    messages: context.slice(-10), // 最近 10 条消息
    userMessage,
    prompt: `
      分析用户最新发言，判断其意图类型：
      - interrupt：用户主动插话表达观点
      - command：用户下达明确指令（如"让X反驳"）
      - passive：用户旁观，等待邀请
    `
  })
  return result.intent
}
```

---

## 5. 数据模型

### 5.1 Message

```typescript
type MessageRole = 'host' | 'character' | 'user' | 'system'

interface Message {
  id: string
  role: MessageRole
  characterId?: string
  content: string
  timestamp: number
  isStreaming?: boolean
  eventType?: 'slap' | 'camp' | 'vote' | 'reverse'
}
```

### 5.2 Role

```typescript
interface Role {
  id: string
  name: string
  char: string
  type: string
  isHost: boolean
  color: 'amber' | 'blue' | 'jade' | 'rose' | 'violet' | 'muted'
  personality: string
  tags: string[]
  catchphrase: string
  attitude: string
  systemPrompt: string
  model: string
  temperature: string
  preview: string[]
}
```

### 5.3 Template

```typescript
interface Template {
  id: string
  name: string
  version: string
  icon: string
  description: string
  category: 'history' | 'biz' | 'fairy' | 'custom'
  theme: 'silicon' | 'ink' | 'fairy' | 'space'
  userIdentity: { name: string; avatar: string }
  worldview: {
    background: string
    tone: 'dramatic' | 'humorous' | 'serious' | 'dark'
    entryMessage: string
  }
  roles: Role[]
  events: {
    inviteConditions: string[]
    slapEnabled: boolean
    campEnabled: boolean
    voteEnabled: boolean
    reverseEnabled: boolean
  }
  rhythm: {
    maxTurnsPerRole: number
    maxCharsPerTurn: number
    inviteFrequency: number
    speakerDelay: number
  }
  freeModels?: { id: string; name: string; provider: string }[]
}
```

### 5.4 LLMConfig

```typescript
interface LLMConfig {
  provider: 'openai' | 'anthropic' | 'gemini' | 'deepseek' | 'custom'
  model: string
  apiKey: string
  baseUrl?: string
  temperature: number
  maxTokens: number
  timeout: number
  stream: boolean
  headers?: Record<string, string>
  // 自定义模型配置
  customModels?: CustomModelConfig[]
}
```

---

## 6. 本地存储策略

| 数据 | 存储位置 | 过期策略 | 说明 |
|-----|---------|---------|------|
| API Keys | localStorage | 永久 | 用户手动删除 |
| LLM 全局配置 | localStorage | 永久 | 模型、参数等 |
| 主题/上次模板 | localStorage | 永久 | 启动时读取 |
| 模板缓存 | IndexedDB | 7 天 | 服务端下发的模板 JSON |
| 会话历史 | IndexedDB | 30 天 | 最近 50 条消息，按时间清理 |
| 角色配置 | IndexedDB | 永久 | 用户自定义的角色信息 |

---

## 7. 服务端接口

### 7.1 接口列表

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/templates` | GET | 返回模板列表（含版本号） |
| `/api/templates/:id` | GET | 返回完整模板 JSON，支持 ETag |
| `/api/models` | GET | 返回推荐免费模型列表 |
| `/api/health` | GET | 健康检查 |
| `/api/templates` | POST | 上传自定义模板（可选） |

### 7.2 统一错误响应格式

```typescript
interface ErrorResponse {
  code: string      // 错误码
  message: string    // 友好错误信息
  details?: unknown // 详细错误信息
}

// 错误码定义
const ErrorCodes = {
  TEMPLATE_NOT_FOUND: 'TEMPLATE_NOT_FOUND',
  INVALID_TEMPLATE: 'INVALID_TEMPLATE',
  RATE_LIMITED: 'RATE_LIMITED',
  SERVER_ERROR: 'SERVER_ERROR'
}
```

### 7.3 CORS 配置

```typescript
// 服务端需配置 CORS，允许前端直接调用
const corsConfig = {
  origin: '*', // 生产环境应限制具体域名
  methods: ['GET', 'POST'],
  allowedHeaders: ['Content-Type']
}
```

---

## 8. 目录结构

```
src/
├── app/
│   ├── layout.tsx
│   ├── page.tsx            # 启动屏
│   ├── templates/page.tsx
│   ├── llm/page.tsx
│   ├── roles/page.tsx
│   └── chat/page.tsx
│
├── components/
│   ├── ui/                 # 原子组件
│   ├── template/
│   ├── llm/
│   ├── role/
│   └── chat/               # 讨论界面组件
│
├── engine/                 # 讨论引擎（核心）
│   ├── director.ts         # 导演逻辑
│   ├── scheduler.ts        # 角色调度
│   ├── rhythm.ts           # 节奏控制
│   ├── events.ts           # 爽点机制
│   ├── intent.ts           # 意图识别（LLM）
│   └── state.ts            # 状态机
│
├── llm/                    # LLM 抽象层
│   ├── client.ts           # 统一客户端
│   └── providers/
│       └── custom.ts       # 自定义 Provider
│
├── store/                  # Zustand 状态
├── db/                     # IndexedDB 封装
├── types/                  # TypeScript 类型
└── styles/
    └── globals.css         # CSS 变量主题系统
```

---

## 9. 关键技术决策

| 决策 | 选择 | 理由 |
|------|------|------|
| LLM SDK | Vercel AI SDK | 开箱即用，减少开发量 |
| 自定义模型 | 必须支持 | BaseURL + Key + ModelList |
| 意图识别 | LLM 分类 | Phase 1 即采用，准确率高 |
| 爽点触发 | 关键词冲突检测 | Phase 1 简化实现 |
| API Key 存储 | localStorage 明文 | Phase 1 简化，后期迭代加密 |
| 多设备同步 | 不支持 | Phase 3 再考虑 |

---

*ARCHITECTURE 版本：v1.1 | 更新日期：2026-04-05 | 评审决策已合并*
